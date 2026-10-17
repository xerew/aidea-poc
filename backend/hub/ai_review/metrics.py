"""Agreement statistics for the AI reviewer.

- Cohen's kappa: agreement beyond what chance would give (an AI that always
  says "approve" scores 0 however often humans approve).
- Wilson lower bound: how low the true approve-agreement could plausibly be
  given how few reviews exist (29/30 looks like 97% but may be 83%).
- Feedback use: how often reviewers send the AI's feedback (nearly) unchanged —
  the warning sign for rubber-stamping."""
import math

DEFINITE = ('approve', 'changes_requested')
UNCHANGED_SIMILARITY = 0.95


def _r(x):
    return None if x is None else round(x, 3)


def wilson_lower(successes, n, z=1.96):
    if n == 0:
        return None
    p = successes / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / (1 + z * z / n)


def cohen_kappa(pairs):
    pairs = [(a, h) for a, h in pairs if a in DEFINITE and h in DEFINITE]
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(a == h for a, h in pairs) / n
    expected = sum((sum(a == v for a, _ in pairs) / n) * (sum(h == v for _, h in pairs) / n) for v in DEFINITE)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def summarise(reviews):
    reviews = list(reviews)
    decided = [r for r in reviews if r.human_verdict and r.agreed is not None]
    ai_approves = [r for r in decided if r.verdict == 'approve']
    approve_ok = sum(r.human_verdict == 'approve' for r in ai_approves)
    used = [r for r in decided if r.feedback_used]
    missed = {}
    for r in reviews:
        for c in r.criteria_results or []:
            if c.get('status') in ('not_met', 'partly_met'):
                missed[c['id']] = missed.get(c['id'], 0) + 1
    names = {c['id']: c['name'] for r in reviews for c in (r.rubric or [])}
    worst = max(missed, key=missed.get) if missed else None
    return {
        'reviews': len(reviews),
        'decided': len(decided),
        'agreement': _r(sum(r.agreed for r in decided) / len(decided)) if decided else None,
        'kappa': _r(cohen_kappa((r.verdict, r.human_verdict) for r in decided)),
        'approve_agreement': _r(approve_ok / len(ai_approves)) if ai_approves else None,
        'approve_lower_bound': _r(wilson_lower(approve_ok, len(ai_approves))),
        'feedback_used': _r(len(used) / len(decided)) if decided else None,
        'feedback_unchanged': (_r(sum((r.feedback_similarity or 0) >= UNCHANGED_SIMILARITY for r in used) / len(used))
                               if used else None),
        'most_missed': worst,
        'most_missed_name': names.get(worst) if worst else None,
    }
