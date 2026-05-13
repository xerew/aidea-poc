# AIDEA Phase 2 — Intelligent Recommendation Engine Design

## 1. Goal

Replace the current single-signal content-based recommender with a four-signal hybrid engine that personalises course recommendations using the teacher's stated profile, explicit preferences, behavioural history, and peer co-enrollment patterns. Introduce a hybrid bandit that starts deterministic and auto-tunes weights once enough interaction data has been collected.

## 2. Architecture overview

Two independent pipelines produce two UI rows on the Home page:

```
Signals ①②③  →  Personal engine  →  "Recommended for you"      (5 cards)
Signal  ④     →  CF engine        →  "Teachers like you also took" (3 cards, deduplicated)
```

The personal engine is tuned over time by a hybrid bandit. The CF engine is always on and requires no tuning — peer counts are self-evidently correct.

---

## 3. The four signals

### Signal ① — Onboarding profile (existing)
Fields already on `UserProfile`: `subject_area`, `teaching_level`, `competency_score`, `goals`.  
Already encoded into a 384-dimension text embedding via `sentence-transformers/all-MiniLM-L6-v2`.  
No changes needed here.

### Signal ② — Explicit preferences (new)
Two new fields added to `UserProfile`:

| Field | Type | Values |
|---|---|---|
| `preferred_pillars` | `JSONField` (list) | `["teach_with_ai", "teach_for_ai", "teach_about_ai"]` |
| `learning_style` | `CharField` (choice) | `video`, `text`, `visual`, `interactive` |

Captured on a new **Profile preferences** section (added to the existing Profile page). These apply a `γ` pillar bias term and a `1.2×` style boost multiplier to matching courses in the personal engine.

Courses also need a new field:

| Model | Field | Type | Values |
|---|---|---|---|
| `Course` | `content_format` | `CharField` (choice) | `video`, `text`, `visual`, `interactive`, `mixed` |

### Signal ③ — Implicit behavioural signals (new)

Every past and future interaction a teacher has with a course is converted to a **preference weight** using this table:

| Action | Source | Weight |
|---|---|---|
| Completed course | `progress_pct = 100` | `+1.0` |
| Deep progress (50–99%) | `progress_pct ≥ 50` | `+0.7` |
| Active learner (10–49%) | `progress_pct ≥ 10` | `+0.4` |
| Just enrolled, recently active | `progress_pct < 10`, `last_accessed < 7d` | `+0.2` |
| Enrolled but abandoned | `progress_pct < 10`, `last_accessed > 30d` | `−0.1` |
| Lesson completed | `LessonProgress` count | `+0.03` each |
| Viewed course detail | `CourseView` record | `+0.1` |

All weights are multiplied by a **recency decay**: `e^(−days_since_last_access / 30)`.

The behavioural user vector is computed as:
```
behaviour_vec = Σ( clamp(score_i, -0.2, 1.0) × course_embedding_i )
                normalised to unit length
```

### Signal ④ — Peer collaborative filtering (new)

Teachers are grouped by the intersection of `subject_area`, `teaching_level`, and competency band (`beginner` / `intermediate` / `advanced`).

Within each group, an item co-occurrence matrix is computed from `Enrollment` records:
- For each pair of courses (A, B) where both are enrolled by the same teacher in the group, increment co-occurrence count.
- Rank courses by count, exclude already-enrolled courses, take top 3.
- The percentage shown ("67% of STEM teachers") = `count_enrolled_in_course / group_size × 100`.

No embeddings or ML required. Recomputed nightly via `compute_cf_recommendations` Celery task.

---

## 4. Personal engine — combining the signals

```
user_vector = α × profile_vector
            + β × behaviour_vector
            + γ × pillar_bias_vector
```

Where:
- `α = 0.3` — onboarding profile weight
- `β = 0.5` — behavioural history weight  
- `γ = 0.2` — explicit pillar preference weight

When a teacher has no enrollment history, `behaviour_vec` is a zero vector and the formula reduces to `α × profile_vector + γ × pillar_bias_vector` automatically — no special cold-start branch needed. As history accumulates, `behaviour_vec` gains magnitude and the `β` term grows in influence naturally.

`pillar_bias_vector` is the mean embedding of all courses in the teacher's preferred pillars.

Scoring pipeline:
1. Compute `user_vector` from the formula above
2. Cosine similarity against all `CourseEmbedding` records (excluding enrolled courses)
3. Apply competency level filter (max one level above teacher's band)
4. Apply learning style boost: `score × 1.2` for courses matching `learning_style`
5. Take top 5

---

## 5. Hybrid bandit — three phases

All weights (`α`, `β`, `γ`, and all Signal ③ weights) live in a single `RecommendationConfig` model and are tunable from Django admin at any time.

| Phase | Events | Behaviour |
|---|---|---|
| **1 — Deterministic** | `0 → N_MIN` | Admin weights in effect. Events collected silently. |
| **2 — Blend (ε-greedy)** | `N_MIN → N_FULL` | 90% exploit best known weights, 10% explore random variation. Explore ratio shrinks linearly to 0% at N_FULL. |
| **3 — Full bandit** | `N_FULL+` | Nightly `tune_recommendation_weights` task computes reward signals and gradient-nudges all weights. Admin can still freeze or override any weight. |

Default thresholds (configurable in admin):
- `N_MIN = 200` — roughly 40 teachers each interacting with 5 recommendations
- `N_FULL = 1000` — enough signal for trustworthy bandit updates

### Reward signals
Collected via `RecommendationEvent`:

| Event | Reward |
|---|---|
| clicked | +0.3 |
| enrolled | +0.5 |
| completed | +1.0 |

The bandit uses gradient descent with `learning_rate = 0.01` to nudge weights toward configurations that produced higher rewards. Only the `source = "personal"` events are used to tune the personal engine weights; `source = "cf"` events are informational only.

---

## 6. Data model changes

### New model: `RecommendationConfig`
Singleton (enforced via `save()` override). All fields have sensible defaults.

```python
class RecommendationConfig(models.Model):
    # Signal weights
    w_completed   = FloatField(default=1.0)
    w_deep        = FloatField(default=0.7)
    w_active      = FloatField(default=0.4)
    w_enrolled    = FloatField(default=0.2)
    w_abandoned   = FloatField(default=-0.1)
    w_lesson      = FloatField(default=0.03)
    w_view        = FloatField(default=0.1)
    # Blend weights
    alpha         = FloatField(default=0.3)   # profile
    beta          = FloatField(default=0.5)   # behaviour
    gamma         = FloatField(default=0.2)   # explicit prefs
    style_boost   = FloatField(default=1.2)
    # Bandit config
    bandit_active = BooleanField(default=False)
    n_min         = IntegerField(default=200)
    n_full        = IntegerField(default=1000)
    learning_rate = FloatField(default=0.01)
    reward_click  = FloatField(default=0.3)
    reward_enroll = FloatField(default=0.5)
    reward_complete = FloatField(default=1.0)
```

### New model: `RecommendationEvent`
```python
class RecommendationEvent(models.Model):
    class EventType(TextChoices):
        SHOWN     = 'shown'
        CLICKED   = 'clicked'
        ENROLLED  = 'enrolled'
        COMPLETED = 'completed'

    user             = ForeignKey(User, on_delete=CASCADE)
    course           = ForeignKey(Course, on_delete=CASCADE)
    event_type       = CharField(choices=EventType.choices)
    rank             = PositiveSmallIntegerField()       # position in recommendation list (1-5)
    source           = CharField()                       # 'personal' or 'cf'
    weights_snapshot = JSONField()                       # copy of RecommendationConfig at time of show
    created_at       = DateTimeField(auto_now_add=True)
```

### New model: `CourseView`
Lightweight signal for "viewed course detail page without enrolling".
```python
class CourseView(models.Model):
    user       = ForeignKey(User, on_delete=CASCADE)
    course     = ForeignKey(Course, on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

### Modified model: `UserProfile`
Add two fields:
```python
preferred_pillars = JSONField(default=list, blank=True)   # e.g. ["teach_with_ai"]
learning_style    = CharField(max_length=20, choices=LearningStyle.choices, blank=True)
```

### Modified model: `Course`
Add one field:
```python
content_format = CharField(max_length=20, choices=ContentFormat.choices, default='mixed')
# choices: video, text, visual, interactive, mixed
```

### Modified model: `CourseRecommendation`
Add one field:
```python
source = CharField(max_length=20, default='personal')   # 'personal' or 'cf'
```

---

## 7. New Celery tasks

### `compute_user_recommendations(user_id)` — rewrite
Replaces the existing task. Uses all four signals to produce the top 5 personal recommendations, writes to `CourseRecommendation` with `source='personal'`.

### `compute_cf_recommendations(user_id)` — new
Computes peer co-enrollment counts for the user's group, writes top 3 to `CourseRecommendation` with `source='cf'`. Deduplication happens at compute time: query existing `CourseRecommendation` records with `source='personal'` for this user and exclude those course IDs from CF results before writing. Should be called after `compute_user_recommendations` completes.

### `tune_recommendation_weights()` — new
Runs nightly via celery-beat. Checks `RecommendationEvent` count against `N_MIN`/`N_FULL`, updates `bandit_active` flag, and when in Phase 2 or 3 applies gradient updates to `RecommendationConfig` weights using accumulated reward signals.

### `recompute_all_recommendations()` — extend
Already exists. Extend to call both `compute_user_recommendations.delay(uid)` and `compute_cf_recommendations.delay(uid)` for each teacher.

---

## 8. API changes

### `GET /api/recommendations/` — extend response
Add `source` field to `RecommendationSerializer`. Frontend uses it to split into the two rows.

### `POST /api/recommendations/events/` — new endpoint
Records a `RecommendationEvent`. Called by the frontend on card impression, click, and enroll.

```
Body: { course_id, event_type, rank, source }
```

### `GET /api/courses/<id>/` — extend
Log a `CourseView` record when an authenticated teacher fetches a course detail. No response change.

### `PATCH /api/profile/preferences/` — new endpoint
Updates `preferred_pillars` and `learning_style` on `UserProfile`. Triggers `compute_user_recommendations.delay(user_id)`.

---

## 9. Frontend changes

### `HomePage` — second recommendation row
Below the existing "Recommended for you" section, add a "Teachers like you also took" row showing the 3 CF recommendations (`source='cf'`). Each card shows the co-enrollment percentage as social proof. Fire `shown` events for both rows on mount.

### `CourseCard` component — event tracking
On click, fire a `clicked` event to `/api/recommendations/events/` before navigating. Pass `rank` and `source` from the parent list.

### `ProfilePage` — preferences section
Add a new "Learning preferences" section with:
- Pillar multi-select (checkboxes for the 3 pillars)
- Learning style single-select (video / text / visual / interactive)

On save, call `PATCH /api/profile/preferences/`.

---

## 10. Out of scope

- Badges and gamification (Phase 2b)
- Engagement time tracking (Phase 2b)
- A/B test harness for systematic weight experimentation (Phase 3)
- Meilisearch full-text search (Phase 3)
- xAPI / Ralph LRS (Phase 4)
- TypeScript migration
