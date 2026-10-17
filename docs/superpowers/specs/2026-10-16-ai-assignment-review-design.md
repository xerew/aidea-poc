# AI Assignment Reviewer — Design

Date: 2026-10-16 · Status: approved in conversation, awaiting spec review

## Purpose

An AI reviewer for assignment submissions that, assignment by assignment, (A) saves reviewers time with suggested verdicts and feedback, (B) gives learners fast preliminary feedback, (C) approves clear passes automatically once proven, and (D) checks evidence that the work was really done. It replaces the stub `hub/llm_review.py` and the module-wide `Module.llm_review_enabled` switch.

### Decisions taken

| Topic | Decision |
|---|---|
| Model hosting | **Self-hosted** on the NTUA server (2 × RTX 4090, 48 GB): a vision model via Ollama (e.g. `qwen2.5vl:32b` or `gemma3:27b`, chosen by a benchmark), pinned to the second GPU; the translator keeps the first. Reached through the existing `ollama-tunnel`. |
| "Training" | Starts with **rubric + examples** (no training). Shadow mode collects every human decision as labelled data; fine-tuning (LoRA on the NTUA GPUs) is a later, separate step once a few hundred reviews exist. |
| Scope of evidence | **General**: text, PDF/Word (text extracted), images/screenshots (vision), links. Evidence checks are optional plug-ins per assignment: duplicate detection (built in); Trust-AI Lab scenario verification (later, once its API/account matching is settled). |
| Rubric | A list of **criteria** (name, what "met" looks like, required / nice-to-have), **drafted by the AI** from the assignment instructions and approved by the author. AI review only runs on an approved rubric. |
| Learner-visible feedback | **Per assignment**: reviewers only (default) or learners immediately, marked preliminary. |
| Auto-approve | Approvals only; unlocked per assignment after **≥ 30** human-checked reviews once the **95 % Wilson lower bound** of agreement on the AI's approvals reaches **90 %** (at least 35 agreeing approvals); requires verdict *approve* with confidence **≥ 0.8**, every required criterion met, no flagged check; **1 in 10** still spot-checked; reviewers can reopen. Rejections are always human. |
| Training data | **All submissions** may be used, anonymised, to improve the reviewer — stated in the Privacy Policy; learners can opt out in their profile (their work is still pre-checked, only excluded from training data). Confirm with the project's data-protection contact before fine-tuning starts. |
| Processing | **In the background** right after submission (Celery), never blocking the learner; failures or an offline server leave the submission to humans as today. |

## Author setup (per assignment resource)

An **"AI review"** panel in the activity editor for each assignment:

1. **AI review on/off.** Migration: assignments in modules with `llm_review_enabled` start on.
2. **Rubric**: "Draft with AI" proposes 3–6 criteria from title + instructions; the author edits, adds, removes, reorders and saves (approves). Criterion names are translatable through the existing translation pipeline so learner feedback reads in their language.
3. **Examples** (optional, ≤ 5): a sample submission (text, optionally an image) with the correct verdict and a short reason — added by hand, or by a reviewer's "Use as AI example" on a real reviewed submission (anonymised).
4. **Evidence checks**: duplicate files (on by default); Trust-AI Lab scenario (shown "coming soon").
5. **Who sees AI feedback**: reviewers only (default) / learners immediately, preliminary.
6. **Auto-approve**: locked until the unlock thresholds are met; then the author may switch it on.
7. **Stats line**: AI reviews so far, agreement with reviewers (overall and on approvals), most-missed criterion.

Editable by anyone who can edit the course.

## Pipeline (after a submission)

1. The submission is saved as today. If AI review is on and the rubric approved, an **AIReview** is created (*queued*) and a Celery task starts.
2. **Evidence checks**: duplicate detection — SHA-256 per file plus a perceptual hash for images, compared with other learners' submissions to the same assignment; a match is flagged with the other submission for reviewers. (Trust-AI Lab check slots in here later.)
3. **Evidence preparation**: submission text; text extracted from PDF and Word; images resized to a sensible maximum; video links noted as "cannot be watched".
4. **Model request** (Ollama chat API with images, structured JSON output): assignment instructions, rubric, examples, evidence, check results, learner's language. Required answer:
   - per criterion: `met` / `partly_met` / `not_met` / `cannot_judge` + one-sentence reason;
   - suggested verdict `approve` / `changes_requested` / `unsure` + confidence 0–1;
   - feedback for the learner (learner's language);
   - notes for the reviewer.
5. **Validation**: a malformed answer is retried once, then the review is *failed*. If the NTUA server is offline the task retries with back-off for a few hours, then gives up. In every failure case the submission waits for a human.
6. **Stored per AIReview**: model name, prompt version, rubric snapshot, check results, per-criterion results, verdict, confidence, learner feedback, reviewer notes, status, timing, and later the human verdict, agreement and disagreement reason.
7. **Auto-approve** (only if unlocked and on): verdict approve, confidence ≥ 0.8, every required criterion met, no flagged check, not drawn for the 1-in-10 spot check → approved through the normal approval path (progress, competency, notifications unchanged), marked *approved by AI*.
8. **Platform settings** (Django admin singleton): global on/off, model name, Ollama endpoint (reuses the translation settings), confidence threshold (0.8), spot-check rate (10 %), unlock thresholds (30 reviews, 90 % lower bound).

A resubmission gets a fresh AIReview; earlier ones are kept.

## Reviewers

- On the Reviews page each submission shows an **AI panel**: verdict + confidence, criteria table with reasons, flags (e.g. duplicate of another learner's screenshot), AI notes.
- **"Use AI feedback"** copies the AI's feedback into the feedback box for editing; the reviewer still decides.
- After deciding, when disagreeing with the AI, an optional **reason**: missed evidence / too strict / too lenient / misread the image / other.
- **"Use as AI example"** adds the submission (anonymised) to the assignment's examples.
- **Filters**: AI says approve, AI unsure, flagged, auto-approved (with **Reopen**, which sends the submission back to pending and notifies the learner).

## Learners

- When the assignment shows AI feedback: after submitting, an **"AI pre-check (preliminary)"** box with criteria met/missing and feedback, and "A reviewer will confirm."
- Learners may **revise and resubmit while the submission is pending** (today pending submissions are locked); the new version replaces the old and gets a new pre-check.
- An auto-approved submission looks like any approval.

## Measuring

- **Course analytics**, per assignment: AI reviews, agreement with reviewers (overall plus Cohen's kappa; on approvals plus its lower bound), how often reviewers send the AI's feedback unchanged, most-missed criteria; the learner timeline shows the AI verdict next to the human one.
- **Excel**: a new **"AI reviews"** sheet — one row per AIReview: learner, assignment, each criterion's result, AI verdict and confidence, human verdict, agreed?, disagreement reason, AI feedback used? and how close the sent feedback is to it, model, prompt version, auto-approved?, spot-checked?.
- **Training export** (for later fine-tuning): anonymised pairs of submission → human verdict/feedback, excluding opted-out learners and screenshots showing names.

## Privacy

Privacy Policy section: assignments are checked by an AI model running on project servers; a human makes or confirms every rejection; anonymised submissions may be used to improve the reviewer; how to opt out. Profile setting **"Don't use my assignments to improve the AI reviewer."**

## Rollout

1. NTUA: `ollama pull` the candidate models; pin the reviewer to the second GPU.
2. `manage.py ai_review_benchmark`: runs 2–3 candidate models on submissions reviewers already decided; reports agreement, speed, failures and an Excel file with the feedback side by side. The chosen model goes into the admin settings.
3. Enable for one or two assignments (reviewers only), then widen; learner-visible feedback and auto-approve assignment by assignment as the numbers allow.
4. Migration: new tables (rubric/criteria, examples, AI reviews, settings, opt-out flag); `Module.llm_review_enabled` carried over to its assignments; no existing data changes.

## Methodology

No single paper is followed; the design combines established methods. The thresholds are engineering choices.

| Idea | Source | Used for |
|---|---|---|
| LLM as evaluator, and its biases | Zheng et al., 2023, *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* (NeurIPS) | The overall approach; measuring agreement instead of trusting the model |
| Criterion-by-criterion judging with rubrics | Liu et al., 2023, *G-Eval*; Kim et al., *Prometheus* (ICLR 2024) and *Prometheus 2* (2024) | Rubric criteria with reasons; open models as rubric judges |
| In-context examples | Brown et al., 2020, *Language Models are Few-Shot Learners* | The ≤ 5 examples per assignment |
| Selective automation, deferring to humans | Geifman & El-Yaniv, 2017, *Selective Classification for Deep Neural Networks*; Madras et al., 2018, *Predict Responsibly: Learning to Defer* | Auto-approve only clear passes; everything else goes to a human |
| Self-reported confidence is poorly calibrated | Xiong et al., 2024, *Can LLMs Express Their Uncertainty?* (ICLR) | Unlock depends on measured agreement, not the model's confidence |
| Chance-corrected agreement | Cohen, 1960, *A Coefficient of Agreement for Nominal Scales* | Kappa next to raw agreement (raw agreement flatters an AI that mostly says "approve") |
| Confidence interval for a proportion | Wilson, 1927, *Probable Inference, the Law of Succession, and Statistical Inference* | The unlock rule: the lower bound, not the observed rate |
| Automation bias | Parasuraman & Manzey, 2010, *Complacency and Bias in Human Use of Automation* | Spot checks, reopen, disagreement reasons, logging how much reviewers edit the AI's feedback |
| Constrained structured output | Willard & Louf, 2023, *Efficient Guided Generation for Large Language Models* | JSON-schema answers |
| Low-cost fine-tuning | Hu et al., 2021, *LoRA* | The later training step |

## Testing

- **Backend**: rubric drafting and saving; duplicate check (identical files, near-identical images); text extraction; request building and answer validation (good, malformed, missing fields); retries when offline; every auto-approve rule incl. spot-check and unlock thresholds; learner visibility; resubmission while pending; agreement statistics; Excel sheet; opt-out excluded from the training export. The model is faked in tests.
- **Manual**: the benchmark command on real reviewed submissions.

## Out of scope

Fine-tuning itself (this version builds the data and opt-out); the Trust-AI Lab check (planned plug-in); watching videos; numeric grades beyond approve / changes requested; hosted models.
