# Personalisation changelog

Changes to how the pathway and recommendations rank courses. The study's
adaptive group sees these rankings, so each change is dated for the analysis.
The current version is `ALGORITHM_VERSION` in `backend/hub/personalization.py`.

## 2026-10-01.2

**Recommendations** (`hub/tasks.py`, `hub/completion.py`):
- Candidate pool widened from the 20 to the 50 nearest courses before the
  boosts and level filter re-rank them (a strongly matching course just
  outside the nearest 20 can now reach the top 5).
- "Completed" recommendation events are now recorded: when a course enrolled
  in from a recommendation reaches 100 %, an event with the enrolment's
  source, rank and weight snapshot is logged. The weight tuning's strongest
  reward (1.0) was previously never earned. Teachers only, as for the other
  events.

**Display only** (no ranking effect): recommendation reasons are worded in the
viewer's language; the peer list is titled "Educators like you also took".

## 2026-10-01

**Pathway** (`hub/pathway_gen.py`) — additive score terms:
- Preferred-pillar (+3) and goal-pillar (+1.5) matches count a course's
  additional Academy Pillars, not only its primary pillar.
- Educational level vs the teacher's teaching level: +1 match, −1 mismatch.
  Primary ↔ primary; secondary ↔ lower/upper secondary; a "cross-level" course
  matches everyone. Courses without levels, and higher-ed/vocational/adult-ed
  teachers, are neutral.
- Target audience vs the new profile "school role" (teacher / school leader /
  both): +1 match, −1.5 mismatch. Neutral when either side is unset.

**Recommendations** (`hub/tasks.py`) — multiplicative nudges on similarity:
- Pillar bias vector and the ×1.25 preferred-pillar boost include additional pillars.
- Educational level: ×1.15 match, ×0.85 mismatch (same mapping as above).
- Target audience: ×1.15 match, ×0.7 mismatch.
- Candidates are now ranked by the boosted score. Before, boosts changed the
  stored score but the top 5 were still taken in raw-similarity order.
- Course embeddings now include learning outcomes, prior knowledge and
  cross-axis relevance (were: title, description, subjects). The user profile
  text includes the school role.
- Changing subject, teaching level or school role recomputes recommendations
  immediately (before: only the pathway; recommendations waited for the night).

Deploy note: run `manage.py recompute_course_embeddings` once after deploying.
