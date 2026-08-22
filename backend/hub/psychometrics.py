"""Classical-test-theory reliability statistics for the AI self-efficacy scale.

Computed over one response per participant (their first completed attempt) so
the observations are independent — the standard basis for a scale-validation
analysis (Cronbach's alpha, corrected item-total correlations, inter-dimension
correlations).
"""
import numpy as np


def cronbach_alpha(matrix):
    """matrix: n_participants x k_items (numeric). Returns alpha or None when it
    is undefined (too few cases/items, or no total-score variance)."""
    m = np.asarray(matrix, dtype=float)
    if m.ndim != 2 or m.shape[0] < 2 or m.shape[1] < 2:
        return None
    k = m.shape[1]
    item_var_sum = m.var(axis=0, ddof=1).sum()
    total_var = m.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return None
    return float((k / (k - 1)) * (1 - item_var_sum / total_var))


def corrected_item_total(matrix):
    """Corrected item-total correlation for each item: corr(item, sum of the
    other items). Returns a list (None where a variance is zero)."""
    m = np.asarray(matrix, dtype=float)
    n, k = m.shape
    out = []
    for i in range(k):
        item = m[:, i]
        rest = np.delete(m, i, axis=1).sum(axis=1)
        if item.std() == 0 or rest.std() == 0 or n < 2:
            out.append(None)
        else:
            out.append(round(float(np.corrcoef(item, rest)[0, 1]), 3))
    return out


def _round(value, ndigits=3):
    return None if value is None else round(value, ndigits)


def compute_scale_reliability(responses, dimensions):
    """responses: list of {question_id(int): value}; dimensions: ordered list of
    OnboardingDimension with `.questions` (active, ordered). Returns the
    reliability report used by the admin psychometrics view / research export.
    """
    dim_items = []  # [(dimension, [question, ...])]
    ordered_qids = []
    for dim in dimensions:
        qs = sorted((q for q in dim.questions.all() if q.is_active), key=lambda q: q.order)
        dim_items.append((dim, qs))
        ordered_qids.extend(q.id for q in qs)

    # Keep only fully-answered responses so every column is present.
    complete = [r for r in responses if all(qid in r for qid in ordered_qids)]
    n = len(complete)

    empty = {
        'n': n,
        'overall_alpha': None,
        'dimensions': [
            {'slug': d.slug, 'name': d.name, 'alpha': None,
             'items': [{'code': f'Q{i}', 'question_id': q.id} for i, q in enumerate(qs, 1)]}
            for (d, qs) in dim_items
        ],
        'inter_dimension': {'labels': [d.name for d, _ in dim_items], 'matrix': None},
    }
    if n < 2:
        return empty

    full = np.array([[r[qid] for qid in ordered_qids] for r in complete], dtype=float)
    overall_alpha = _round(cronbach_alpha(full))

    dims_out = []
    dim_means = []  # per-dimension participant means, for inter-dim correlation
    col = 0
    code = 1
    for dim, qs in dim_items:
        block = full[:, col:col + len(qs)]
        col += len(qs)
        alpha = _round(cronbach_alpha(block))
        itc = corrected_item_total(block)
        means = block.mean(axis=0)
        sds = block.std(axis=0, ddof=1)
        items = []
        for j, q in enumerate(qs):
            items.append({
                'code': f'Q{code}',
                'question_id': q.id,
                'mean': _round(float(means[j]), 2),
                'sd': _round(float(sds[j]), 2),
                'item_total_r': itc[j],
            })
            code += 1
        dims_out.append({'slug': dim.slug, 'name': dim.name, 'alpha': alpha, 'items': items})
        dim_means.append(block.mean(axis=1))

    dm = np.column_stack(dim_means)  # n x n_dims
    with np.errstate(invalid='ignore'):
        corr = np.corrcoef(dm, rowvar=False)
    matrix = [[_round(float(corr[i, j]), 2) for j in range(corr.shape[1])]
              for i in range(corr.shape[0])]

    return {
        'n': n,
        'overall_alpha': overall_alpha,
        'dimensions': dims_out,
        'inter_dimension': {'labels': [d.name for d, _ in dim_items], 'matrix': matrix},
    }
