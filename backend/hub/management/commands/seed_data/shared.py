# Placeholder media URLs
VID = 'https://player.vimeo.com/video/123456789'
PDF = 'https://aidea-poc.example/resources/sample.pdf'
IMG = 'https://placehold.co/1200x675'


def quiz(*qs):
    """Build quiz_data from (question, [options], correct_index) tuples."""
    data = []
    for question, options, correct in qs:
        data.append({
            'question': question,
            'options': [{'text': o, 'is_correct': i == correct} for i, o in enumerate(options)],
        })
    return data


# Shared sample quiz used on every module-end knowledge check.
SAMPLE_QUIZ = quiz(
    ('What is 3 + 4?',  ['5', '6', '7', '8'], 2),
    ('What is 6 × 2?',  ['10', '11', '12', '13'], 2),
    ('What is 15 − 7?', ['6', '7', '8', '9'], 2),
)
