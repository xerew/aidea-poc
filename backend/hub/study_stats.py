"""Analysis of the adaptive-vs-fixed RCT: CONSORT flow counts, per-group
descriptives, the gain-score comparison (t-test + Cohen's d), and the
pre-score-adjusted ANCOVA (the primary analysis for a pre/post design).

ANCOVA is fit as ordinary least squares (post ~ intercept + group + pre) with
numpy; p-values come from scipy's t-distribution. Analyses run over
*completers* (participants with both a pre- and a post-score).
"""
import numpy as np
from scipy import stats

ADAPTIVE = 'adaptive'
FIXED = 'fixed'


def _round(v, n=3):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), n)


def consort_counts(participants):
    """CONSORT flow numbers over all StudyParticipant rows."""
    consented = [p for p in participants if p.in_study]
    declined = [p for p in participants if not p.in_study]

    def by_group(g):
        allocated = [p for p in consented if p.group == g]
        pre = [p for p in allocated if p.pre_score is not None]
        post = [p for p in allocated if p.post_score is not None]
        analyzed = [p for p in allocated if p.pre_score is not None and p.post_score is not None]
        return {
            'allocated': len(allocated),
            'pre_done': len(pre),
            'post_done': len(post),
            'analyzed': len(analyzed),
            'attrition': len(pre) - len(analyzed),  # did pre, missing post
        }

    return {
        'enrolled': len(participants),
        'consented': len(consented),
        'declined': len(declined),
        'adaptive': by_group(ADAPTIVE),
        'fixed': by_group(FIXED),
    }


def _group_arrays(participants, group):
    rows = [
        p for p in participants
        if p.in_study and p.group == group
        and p.pre_score is not None and p.post_score is not None
    ]
    pre = np.array([p.pre_score for p in rows], dtype=float)
    post = np.array([p.post_score for p in rows], dtype=float)
    return pre, post


def _descriptives(pre, post):
    if len(pre) == 0:
        return {'n': 0, 'pre_mean': None, 'pre_sd': None, 'post_mean': None,
                'post_sd': None, 'gain_mean': None, 'gain_sd': None}
    gain = post - pre
    ddof = 1 if len(pre) > 1 else 0
    return {
        'n': int(len(pre)),
        'pre_mean': _round(pre.mean(), 2), 'pre_sd': _round(pre.std(ddof=ddof), 2),
        'post_mean': _round(post.mean(), 2), 'post_sd': _round(post.std(ddof=ddof), 2),
        'gain_mean': _round(gain.mean(), 2), 'gain_sd': _round(gain.std(ddof=ddof), 2),
    }


def _gain_test(pre_a, post_a, pre_f, post_f):
    """Independent-samples comparison of gain scores + Cohen's d."""
    ga, gf = post_a - pre_a, post_f - pre_f
    if len(ga) < 2 or len(gf) < 2:
        return None
    t, p = stats.ttest_ind(ga, gf, equal_var=False)  # Welch
    na, nf = len(ga), len(gf)
    pooled_sd = np.sqrt(((na - 1) * ga.var(ddof=1) + (nf - 1) * gf.var(ddof=1)) / (na + nf - 2))
    d = (ga.mean() - gf.mean()) / pooled_sd if pooled_sd > 0 else None
    return {
        'mean_diff': _round(ga.mean() - gf.mean(), 2),
        'cohens_d': _round(d),
        't': _round(t),
        'p': _round(p, 4),
    }


def _ancova(pre_a, post_a, pre_f, post_f):
    """OLS: post ~ intercept + group(adaptive=1) + pre. Reports the adjusted
    group difference (its coefficient) and adjusted marginal means at the grand
    mean pre-score."""
    n = len(pre_a) + len(pre_f)
    if n < 4:  # need residual df
        return None
    pre = np.concatenate([pre_a, pre_f])
    post = np.concatenate([post_a, post_f])
    grp = np.concatenate([np.ones(len(pre_a)), np.zeros(len(pre_f))])  # adaptive=1
    if pre.std() == 0 or len(np.unique(grp)) < 2:
        return None

    X = np.column_stack([np.ones(n), grp, pre])
    beta, _res, _rank, _sv = np.linalg.lstsq(X, post, rcond=None)
    resid = post - X @ beta
    dof = n - X.shape[1]
    if dof < 1:
        return None
    mse = (resid @ resid) / dof
    cov = mse * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t_group = beta[1] / se[1] if se[1] > 0 else np.nan
    p_group = 2 * stats.t.sf(np.abs(t_group), dof)

    grand_pre = pre.mean()
    adj_adaptive = beta[0] + beta[1] * 1 + beta[2] * grand_pre
    adj_fixed = beta[0] + beta[1] * 0 + beta[2] * grand_pre
    return {
        'adjusted_diff': _round(beta[1], 2),   # adaptive − fixed, controlling for pre
        'se': _round(se[1], 3),
        't': _round(t_group),
        'df': int(dof),
        'p': _round(p_group, 4),
        'adjusted_mean_adaptive': _round(adj_adaptive, 2),
        'adjusted_mean_fixed': _round(adj_fixed, 2),
    }


def compute_study_results(participants):
    participants = list(participants)
    pre_a, post_a = _group_arrays(participants, ADAPTIVE)
    pre_f, post_f = _group_arrays(participants, FIXED)
    return {
        'consort': consort_counts(participants),
        'groups': {
            'adaptive': _descriptives(pre_a, post_a),
            'fixed': _descriptives(pre_f, post_f),
        },
        'gain_test': _gain_test(pre_a, post_a, pre_f, post_f),
        'ancova': _ancova(pre_a, post_a, pre_f, post_f),
    }
