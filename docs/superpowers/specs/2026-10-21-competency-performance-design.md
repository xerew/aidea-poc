# Performance-Based AI Competency — Design

Date: 2026-10-21 · Status: approved in conversation, awaiting spec review · Replaces the score rules of `2026-07-19-competency-decay-design.md`

## Purpose

A teacher's **AI competency score** (0–6) should reflect **what they have shown they can do**, not how much time or interest they had. Today the score:
- drops when a course is left untouched for 30 days ("idle decay");
- ignores quiz results unless an admin switch is on;
- never drops for poor results;
- ignores how hard the course was.

The new rule moves the score by **performance relative to the course's difficulty**. This is a simple form of the expected-vs-actual principle used by Elo-style ratings in adaptive learning (Pelánek, 2016, *Applications of the Elo rating system in adaptive educational systems*, Computers & Education).

### Decisions taken

| Topic | Decision |
|---|---|
| What counts | **Every scored item** in the course: all quizzes, H5P activities that report a score, and assignments. Authors mark nothing. |
| Which attempt | **The first attempt.** Quiz: first submitted score. H5P: first finished attempt. Assignment: the first review decision. |
| Assignments | Approved on the first review = 100%. Changes requested on the first review = 0%, even if approved later. |
| Weighting | Each **module counts equally**: average within a module, then across modules. |
| No scored items | **+1** for completing the course (as today). |
| Difficulty | The course's level vs the teacher's current level (table below). |
| Slow pace | **Kept**: −1 when the average time is more than 3× the planned time. Has its own switch. |
| Idle decay | **Off** (its own switch; the code stays). |
| Existing scores | **Not recalculated.** The rule applies from the moment it ships. |

## The rule

It runs when a teacher **first completes a course** (as today).

1. **Performance** `p`:
   - For each module, average the first-attempt scores (0–1) of the scored items the teacher completed in it.
   - Modules with no such items are skipped. `p` is the mean of the module averages.
   - **Passed** = `p ≥ pass threshold`. The threshold is the existing admin setting, default 0.70.
2. **Levels:**
   - teacher level from the current score: 0–2 → beginner (0), 3–4 → intermediate (1), 5–6 → advanced (2);
   - course level: beginner (0), intermediate (1), advanced (2);
   - `gap = course level − teacher level`.
3. **Change:**

   | gap | Passed | Not passed |
   |---|---|---|
   | +2 (two levels harder) | **+2** | 0 |
   | +1 (one level harder) | **+1** | 0 |
   | 0 (same level) | **+1** | 0 |
   | −1 or −2 (easier) | 0 | **−1** |

   - With **no scored items** in any module, the change is **+1**.
4. **Slow pace** (when its switch is on): if the mean ratio of time spent to planned time over the course's timed activities is more than the slow-ratio threshold (3.0), subtract the slow penalty (1). The calculation is unchanged from today.
5. **Apply:** the score stays within 0–6. Crossing into another level still re-assigns the teacher's learning path and rebuilds its course list, and recommendations are recomputed (both unchanged).

**Items that don't count:**
- items the teacher did not complete (optional ones);
- H5P activities with no score (self-completed types);
- quizzes completed without answers;
- assignments with no first review decision yet. In practice there are none at course completion, because a required assignment must be approved first.

## Data

- **`AssignmentSubmission.first_review_status`** (`approved` / `changes_requested`, blank until reviewed).
  - It's set by the first human decision or an AI auto-approve, and never overwritten (not by resubmission, reopen or later reviews).
  - **Migration:** existing reviewed submissions take their current status as a best guess, because their history wasn't kept.
- **`CompetencyChange`** (new, one row per change in the score):
  - user, course (the completed course, or the abandoned one for idle decay), old score, new score, delta, created_at;
  - `reason` (JSON): `{rule: 'performance' | 'completion' | 'idle', performance, passed, course_level, teacher_level, gap, base_delta, slow_penalty}`;
  - read-only in Django admin.
  - A delta that the 0–6 limits clamp to nothing still records nothing, as today.
- **`LearnerActivityConfig` changes:**
  - `decay_enabled` is replaced by `slow_penalty_enabled` (default on) and `idle_decay_enabled` (default off).
  - **Migration:** `slow_penalty_enabled` = on, `idle_decay_enabled` = the current `decay_enabled`, which the admin has unticked.
  - `quiz_affects_competency`, `quiz_weight_pass` and `quiz_weight_fail` are removed.
  - `quiz_pass_threshold`, `slow_ratio_threshold`, `slow_penalty`, `idle_decay_days` and `idle_decay_points` stay.
  - The admin labels say what each setting now does.

## Testing

- Every table cell (gap −2…+2 × passed / not passed).
- The first attempt is used: a later better quiz doesn't change `p`.
- Assignment changes requested first, then approved, counts 0%; approved first counts 100%. The first decision isn't overwritten by a later review or a reopen.
- Modules count equally: three quizzes in one module vs one assignment in another.
- H5P without a score and uncompleted optional items are ignored.
- No scored items gives +1.
- The slow penalty applies only with its switch on. Idle decay runs only with its switch on.
- The score stays within 0–6.
- A level change still re-assigns the path.
- One `CompetencyChange` row per change, with the reason filled in.
- The migration maps the old switch correctly.

## Out of scope

- Recalculating existing scores.
- A teacher-facing "why did my level change" view (the change record makes it possible later).
- Changing the score mid-course or per module.
- Admin-editable table values.
