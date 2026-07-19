"""Per-module LLM assignment reviewer — stub until models are trained.

review_submission is called when a submission arrives for a module with
llm_review_enabled. Returning None means "no verdict — leave it in the
human review queue". A future implementation returns a (status, feedback)
decision instead; only this module changes when that happens.
"""


def review_submission(submission):
    return None
