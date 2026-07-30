"""Scoring for the AI self-efficacy assessment.

Teachers rate 24 statements across six dimensions on a shared 5-point Likert
scale (1 = strongly disagree … 5 = strongly agree). Each dimension yields an
average which maps to a self-efficacy band, and the overall average maps to the
learner's competency_score so the existing pathway/recommendation logic keeps
working.
"""

LIKERT_MIN = 1
LIKERT_MAX = 5

# Average → band thresholds (per the instrument's scoring rubric).
#   1.00–2.49 low · 2.50–3.49 moderate · 3.50–5.00 high
def band_for(average):
    if average is None:
        return None
    if average < 2.5:
        return 'low'
    if average < 3.5:
        return 'moderate'
    return 'high'


# Overall band → 0-6 competency_score, chosen so get_competency_level() maps
# low→beginner (≤2), moderate→intermediate (3-4), high→advanced (≥5).
BAND_TO_COMPETENCY = {'low': 1, 'moderate': 3, 'high': 5}


def _normalise(answers):
    """Coerce the stored {qid: value} map (keys may be str) to {int: int}."""
    out = {}
    for key, value in (answers or {}).items():
        try:
            out[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return out


def compute_results(answers, dimensions):
    """Aggregate saved answers into per-dimension and overall scores.

    `dimensions` is an iterable of OnboardingDimension with their active
    questions available via `.questions`. Averages are over answered questions
    only; `completed` is True when every active question has an answer.
    """
    norm = _normalise(answers)
    dims_out = []
    all_values = []
    total = 0
    answered = 0

    for dim in dimensions:
        questions = [q for q in dim.questions.all() if q.is_active]
        values = [norm[q.id] for q in questions if q.id in norm]
        total += len(questions)
        answered += len(values)
        all_values.extend(values)
        average = round(sum(values) / len(values), 2) if values else None
        dims_out.append({
            'slug': dim.slug,
            'average': average,
            'band': band_for(average),
            'answered': len(values),
            'total': len(questions),
        })

    overall = round(sum(all_values) / len(all_values), 2) if all_values else None
    return {
        'dimensions': dims_out,
        'overall_average': overall,
        'overall_band': band_for(overall),
        'answered': answered,
        'total': total,
        'completed': total > 0 and answered == total,
    }
