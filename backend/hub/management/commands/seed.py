from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from hub.models import Course, Enrollment, LearningPillar, Lesson, Module, UserProfile

# ---------------------------------------------------------------------------
# Placeholder media URLs
# ---------------------------------------------------------------------------
_VID = 'https://player.vimeo.com/video/123456789'
_PDF = 'https://aidea-poc.example/resources/sample.pdf'
_IMG = 'https://placehold.co/1200x675'


def _quiz(*qs):
    """Build quiz_data from (question, [options], correct_index) tuples."""
    data = []
    for question, options, correct in qs:
        data.append({
            'question': question,
            'options': [{'text': o, 'is_correct': i == correct} for i, o in enumerate(options)],
        })
    return data


# Shared sample quiz used on every module-end knowledge check.
_SAMPLE_QUIZ = _quiz(
    ('What is 3 + 4?',  ['5', '6', '7', '8'], 2),
    ('What is 6 × 2?',  ['10', '11', '12', '13'], 2),
    ('What is 15 − 7?', ['6', '7', '8', '9'], 2),
)

# ---------------------------------------------------------------------------
# Lesson dicts: title, type, duration, required, content, quiz_data
# Module dicts: title, description, duration_minutes, lessons
# ---------------------------------------------------------------------------

PILLARS = [
    # =========================================================================
    # PILLAR 1 — Teach with AI
    # =========================================================================
    {
        'name': 'Teach with AI',
        'slug': 'teach-with-ai',
        'description': 'Learn to use AI tools, prompting techniques, and classroom workflows to enhance your teaching practice.',
        'order': 1,
        'courses': [
            # -----------------------------------------------------------------
            # Course 1: Introduction to AI Tools for Teachers
            # -----------------------------------------------------------------
            {
                'title': 'Introduction to AI Tools for Teachers',
                'description': 'A practical overview of the AI tools transforming education — from chatbots to image generators — and how to evaluate them for classroom use.',
                'level': 'beginner',
                'duration_hours': 4,
                'learning_outcomes': [
                    'Identify and evaluate AI tools suitable for classroom use',
                    'Create your first AI-assisted lesson plan',
                    'Apply responsible AI use policies in your school context',
                    'Explain how generative AI works to colleagues and students',
                ],
                'modules': [
                    {
                        'title': 'What Is AI? A Teacher-Friendly Primer',
                        'description': 'A jargon-free introduction to artificial intelligence and why it matters for educators.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'Welcome to the Course',
                                'type': 'video', 'duration': 5, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'What Is Artificial Intelligence?',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Artificial intelligence refers to computer systems designed to perform tasks '
                                    'that normally require human intelligence, such as recognising speech, making '
                                    'decisions, and translating languages. Modern AI learns patterns from large '
                                    'amounts of data rather than following hand-written rules.'
                                ),
                            },
                            {
                                'title': 'AI in Your Everyday Life',
                                'type': 'text', 'duration': 12, 'required': True,
                                'content': (
                                    'AI is already woven into daily life: email spam filters, phone autocomplete, '
                                    'streaming recommendations, and voice assistants all rely on it. Recognising '
                                    'AI "in the wild" is the first step to thinking critically about it.'
                                ),
                            },
                            {
                                'title': 'Knowledge Check: AI Basics',
                                'type': 'quiz', 'duration': 8, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'The AI Landscape: Tools Worth Knowing',
                        'description': 'A tour of the most useful AI tools for teachers, from writing assistants to image generators.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'Overview of AI Tools for Educators',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Writing Assistants and Chatbots',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Writing assistants like ChatGPT and Gemini help teachers draft lesson plans '
                                    'and differentiated texts in seconds. Treat AI output as a first draft that '
                                    'you review, refine, and personalise before use.'
                                ),
                            },
                            {
                                'title': 'Image and Multimedia Generators',
                                'type': 'text', 'duration': 15, 'required': True,
                                'content': (
                                    'Image-generation tools like DALL-E create custom visuals from text descriptions. '
                                    'Always check generated images for inaccuracies — AI can misrepresent details, '
                                    'embedded text, and human anatomy.'
                                ),
                            },
                            {
                                'title': 'Tool Comparison Activity',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Choose two AI tools from this module. For each, write a short paragraph '
                                    'covering: what tasks it suits best, its key limitations, and how you might '
                                    'use it in your own classroom.'
                                ),
                            },
                            {
                                'title': 'AI Tools Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Evaluating AI Tools for Educational Use',
                        'description': 'Frameworks for assessing AI tools against pedagogical, ethical, and practical criteria.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Why Evaluation Matters',
                                'type': 'video', 'duration': 8, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'The SAMR Framework Applied to AI',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'The SAMR model (Substitution, Augmentation, Modification, Redefinition) helps '
                                    'evaluate how AI changes a teaching task. Aim for Modification or Redefinition '
                                    'to maximise educational value over simple substitution.'
                                ),
                            },
                            {
                                'title': 'Evaluation Rubric (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': True,
                                'content': _PDF,
                            },
                            {
                                'title': 'Evaluate a Tool: Guided Assignment',
                                'type': 'assignment', 'duration': 17, 'required': True,
                                'content': (
                                    'Using the rubric provided, assess one AI tool relevant to your subject. '
                                    'Score it across all dimensions and write a 100-word summary on whether '
                                    'you would use it with students and under what conditions.'
                                ),
                            },
                            {
                                'title': 'Tool Evaluation Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Getting Started: Your First AI-Assisted Lesson',
                        'description': 'A hands-on walkthrough of building a lesson with AI support from start to finish.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'Walkthrough: AI-Assisted Lesson Planning',
                                'type': 'video', 'duration': 20, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Step-by-Step Guide',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Creating an AI-assisted lesson begins with a clear learning objective — AI '
                                    'cannot define your pedagogical goals for you. Prompt an AI assistant for an '
                                    'outline, then review, reshape, and add your own context before teaching.'
                                ),
                            },
                            {
                                'title': 'Build Your Own Lesson',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Use an AI assistant to plan a complete lesson for one of your upcoming classes. '
                                    'Include your subject, year group, topic, and learning objective in your prompt. '
                                    'Submit the final lesson plan with a brief reflection on where AI helped and '
                                    'where you had to intervene.'
                                ),
                            },
                            {
                                'title': 'Lesson Planning Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Responsible Use and School Policies',
                        'description': 'Navigating academic integrity, data privacy, and institutional AI policies.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'Data Privacy and Student Safety',
                                'type': 'text', 'duration': 18, 'required': True,
                                'content': (
                                    'Many free AI tools process your inputs to improve their models, so student data '
                                    'should never be entered into unsanctioned tools. Always verify that your '
                                    'school\'s data processing agreement covers any AI tool you plan to use.'
                                ),
                            },
                            {
                                'title': 'Academic Integrity in the AI Age',
                                'type': 'text', 'duration': 15, 'required': True,
                                'content': (
                                    'Forward-thinking schools are redesigning assessments to value process over '
                                    'product, asking students to reflect on their work or present orally. '
                                    'Transparent classroom agreements about AI use are more effective than bans.'
                                ),
                            },
                            {
                                'title': 'Sample School AI Policy (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Policy Reflection Quiz',
                                'type': 'quiz', 'duration': 7, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 2: Prompt Engineering for Educators
            # -----------------------------------------------------------------
            {
                'title': 'Prompt Engineering for Educators',
                'description': 'Master the art of writing effective prompts to get the most out of AI assistants for lesson planning, differentiation, and content creation.',
                'level': 'intermediate',
                'duration_hours': 5,
                'learning_outcomes': [
                    'Write clear, structured prompts that produce reliable AI output',
                    'Generate differentiated materials for diverse learners',
                    'Build a personal library of reusable prompt templates',
                    'Iterate and refine AI output efficiently',
                ],
                'modules': [
                    {
                        'title': 'How Language Models Work (No Maths Required)',
                        'description': 'An intuitive explanation of how large language models generate text.',
                        'duration_minutes': 40,
                        'lessons': [
                            {
                                'title': 'Tokens, Predictions, and Probabilities',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Training Data and What It Means for You',
                                'type': 'text', 'duration': 18, 'required': True,
                                'content': (
                                    'Language models are trained on vast collections of text from the internet, '
                                    'books, and other sources. This means they reflect the biases and gaps in '
                                    'that data, which is why critical review of AI output is always necessary.'
                                ),
                            },
                            {
                                'title': 'Common Misconceptions Quiz',
                                'type': 'quiz', 'duration': 10, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Anatomy of a Good Prompt',
                        'description': 'Breaking down the components of an effective prompt: role, context, task, and constraints.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'The Four Elements of a Prompt',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Role, Context, Task, Constraints — Deep Dive',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'A strong prompt tells the AI who it is (role), what background it needs '
                                    '(context), what you want it to do (task), and any boundaries to respect '
                                    '(constraints). Including all four elements consistently improves output quality.'
                                ),
                            },
                            {
                                'title': 'Prompt Anatomy Diagram',
                                'type': 'image', 'duration': 5, 'required': False,
                                'content': _IMG,
                            },
                            {
                                'title': 'Rewrite a Weak Prompt',
                                'type': 'assignment', 'duration': 11, 'required': True,
                                'content': (
                                    'Take the weak prompt below and rewrite it using the four-element structure. '
                                    'Weak prompt: "Write a lesson about fractions." '
                                    'Your rewrite should specify a role, context, task, and at least one constraint.'
                                ),
                            },
                            {
                                'title': 'Prompt Structure Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Prompting for Lesson Plans and Unit Outlines',
                        'description': 'Step-by-step prompting workflows for planning entire units and individual lessons.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Lesson Plan Prompting Walkthrough',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Unit Outline Prompt Patterns',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'Effective unit-outline prompts specify the year group, subject, duration, '
                                    'key concepts, and any mandatory assessment points. Breaking a large prompt '
                                    'into a short conversation with the AI often yields better results than one '
                                    'long request.'
                                ),
                            },
                            {
                                'title': 'Generate a Unit Outline',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Use an AI assistant to generate a 4-week unit outline for a topic you teach. '
                                    'Apply the prompt patterns from this module and annotate the output with any '
                                    'changes you made and why.'
                                ),
                            },
                            {
                                'title': 'Lesson Planning Prompts Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Differentiation at Scale: Adapting Content with AI',
                        'description': 'Using prompts to adapt texts and tasks for different reading levels and learning profiles.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Adapting Reading Levels with AI',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Prompts for Scaffolding and Extension',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'To scaffold a text, prompt the AI to simplify vocabulary and add glossary '
                                    'boxes; for extension, ask it to add analytical questions or additional '
                                    'context. Always review adapted texts for accuracy before distributing them.'
                                ),
                            },
                            {
                                'title': 'Differentiation Prompt Pack (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Adapt a Text for Three Levels',
                                'type': 'assignment', 'duration': 10, 'required': True,
                                'content': (
                                    'Choose a paragraph from a class text and use AI prompts to produce three '
                                    'versions: below grade, at grade, and extension. Submit all three versions '
                                    'along with the prompts you used.'
                                ),
                            },
                            {
                                'title': 'Differentiation Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Iterating and Refining AI Output',
                        'description': 'Techniques for improving AI responses through follow-up prompts and editing strategies.',
                        'duration_minutes': 40,
                        'lessons': [
                            {
                                'title': 'Follow-Up Prompting Strategies',
                                'type': 'video', 'duration': 10, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'When and How to Edit AI Output',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Treat the first AI response as a rough draft. Follow-up prompts like '
                                    '"make this shorter", "add a worked example", or "use simpler language" '
                                    'are often more effective than rewriting the original prompt from scratch.'
                                ),
                            },
                            {
                                'title': 'Iterative Prompting Practice',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Start with a basic prompt and improve the AI\'s response through at least '
                                    'three follow-up messages. Document each prompt and the change it produced.'
                                ),
                            },
                            {
                                'title': 'Iterating AI Output Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Prompt Templates You Can Use Tomorrow',
                        'description': 'A practical library of ready-to-use prompt templates for common teacher tasks.',
                        'duration_minutes': 40,
                        'lessons': [
                            {
                                'title': 'Template Library Overview',
                                'type': 'video', 'duration': 8, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': '50 Prompt Templates (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': True,
                                'content': _PDF,
                            },
                            {
                                'title': 'Customise a Template for Your Class',
                                'type': 'assignment', 'duration': 27, 'required': False,
                                'content': (
                                    'Pick three templates from the library that are relevant to your subject. '
                                    'Customise each one for a real upcoming lesson and test them with an AI tool. '
                                    'Note what worked well and what you changed.'
                                ),
                            },
                            {
                                'title': 'Prompt Templates Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 3: AI-Powered Assessment and Feedback
            # -----------------------------------------------------------------
            {
                'title': 'AI-Powered Assessment and Feedback',
                'description': 'Use AI to provide faster, more consistent feedback to students and streamline your assessment workflows without sacrificing quality.',
                'level': 'intermediate',
                'duration_hours': 5,
                'learning_outcomes': [
                    'Generate rubrics and assessment criteria with AI assistance',
                    'Draft personalised written feedback at scale',
                    'Design AI-assisted formative assessment activities',
                    'Maintain academic integrity while using AI feedback tools',
                ],
                'modules': [
                    {
                        'title': 'The Feedback Gap: Why It Matters',
                        'description': 'Understanding the research on feedback quality and how AI can help close the gap.',
                        'duration_minutes': 40,
                        'lessons': [
                            {
                                'title': 'What the Research Says About Feedback',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'The Feedback Gap Explained',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Research consistently shows that timely, specific feedback is one of the '
                                    'highest-impact interventions in education. AI can reduce the time cost of '
                                    'feedback generation, allowing teachers to focus on quality and relationships.'
                                ),
                            },
                            {
                                'title': 'Reflection: Your Current Feedback Practice',
                                'type': 'assignment', 'duration': 8, 'required': False,
                                'content': (
                                    'Write 150 words describing your current feedback workflow: how often you give '
                                    'written feedback, how long it takes, and the biggest barrier to doing it more. '
                                    'Identify one specific place where AI could save you time.'
                                ),
                            },
                            {
                                'title': 'Feedback Gap Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Generating Rubrics and Marking Criteria with AI',
                        'description': 'Using AI to create detailed, aligned rubrics for any task or subject.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Rubric Generation Walkthrough',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Writing Rubric Prompts',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'A good rubric prompt specifies the task type, year group, number of performance '
                                    'levels, and the key criteria you want assessed. Always edit AI-generated rubrics '
                                    'to match your curriculum language and school standards.'
                                ),
                            },
                            {
                                'title': 'Create a Rubric for Your Subject',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Use an AI assistant to generate a marking rubric for an upcoming assessment. '
                                    'Edit the output as needed and submit the final rubric with a note on what '
                                    'you changed and why.'
                                ),
                            },
                            {
                                'title': 'Rubric Generation Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Drafting Written Feedback with AI Assistance',
                        'description': 'Workflows for generating personalised feedback comments that teachers can review and send.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'Feedback Drafting Workflow',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Maintaining Your Voice in AI Feedback',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'AI-drafted feedback should always be reviewed and personalised before it '
                                    'reaches students. Adding the student\'s name, a specific observation, and '
                                    'a forward-looking suggestion transforms generic output into meaningful feedback.'
                                ),
                            },
                            {
                                'title': 'Feedback Prompt Templates (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Draft Feedback for Sample Student Work',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Using the sample student work provided, generate AI-drafted feedback comments '
                                    'and then edit them to sound like your own voice. Submit the AI draft and your '
                                    'edited version side by side.'
                                ),
                            },
                            {
                                'title': 'Written Feedback Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Formative Assessment: Exit Tickets and Quizzes',
                        'description': 'Creating quick formative assessment tools with AI to check understanding in real time.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'AI-Generated Exit Tickets',
                                'type': 'video', 'duration': 10, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Quiz and Poll Prompting Techniques',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Prompt the AI with the lesson\'s learning objective and ask for five '
                                    'multiple-choice questions at a specified difficulty level. Review each '
                                    'question for accuracy and adjust distractors to address common misconceptions.'
                                ),
                            },
                            {
                                'title': 'Build a Formative Assessment Bank',
                                'type': 'assignment', 'duration': 15, 'required': False,
                                'content': (
                                    'Create a bank of ten exit-ticket questions for a unit you currently teach. '
                                    'Use AI to generate a first draft, then edit and organise them by topic '
                                    'and difficulty.'
                                ),
                            },
                            {
                                'title': 'Formative Assessment Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Academic Integrity in an AI World',
                        'description': 'Strategies for designing assessments that are robust to AI misuse.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'Detection vs. Design: A New Approach',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Assessment Design Strategies',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'AI-resistant assessments ask students to draw on personal experience, '
                                    'local context, or in-class observation — things AI cannot fabricate '
                                    'convincingly. Process portfolios, oral defences, and staged drafts also '
                                    'reduce the incentive to use AI dishonestly.'
                                ),
                            },
                            {
                                'title': 'Academic Integrity Policy Guide (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Integrity by Design Quiz',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Keeping the Human in the Loop',
                        'description': 'Principles for maintaining teacher judgement and student relationships when using AI feedback.',
                        'duration_minutes': 35,
                        'lessons': [
                            {
                                'title': 'Why Teacher Judgement Still Matters',
                                'type': 'video', 'duration': 10, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Building Student Trust in AI-Assisted Feedback',
                                'type': 'text', 'duration': 15, 'required': True,
                                'content': (
                                    'Students respond better to AI-assisted feedback when teachers are transparent '
                                    'about the process. Explaining that AI helps with drafting while the teacher '
                                    'reviews everything maintains trust and models responsible AI use.'
                                ),
                            },
                            {
                                'title': 'Personal Commitment Reflection',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Write a short personal commitment (100–150 words) describing how you will '
                                    'use AI in your feedback practice while keeping your professional judgement '
                                    'and student relationships at the centre.'
                                ),
                            },
                            {
                                'title': 'Human in the Loop Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 4: AI for Classroom Differentiation
            # -----------------------------------------------------------------
            {
                'title': 'AI for Classroom Differentiation',
                'description': 'Leverage AI to personalise learning materials for diverse classrooms — adapting reading levels, creating extension tasks, and supporting EAL learners.',
                'level': 'advanced',
                'duration_hours': 6,
                'learning_outcomes': [
                    'Adapt any text to multiple reading levels using AI',
                    'Create tiered tasks and extension activities efficiently',
                    'Support EAL and special needs learners with AI-generated scaffolds',
                    'Build a sustainable AI-powered differentiation workflow',
                ],
                'modules': [
                    {
                        'title': "Understanding Your Learners' Needs",
                        'description': 'Mapping the diversity in your classroom and identifying where AI can add the most value.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Mapping Classroom Diversity',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Identifying AI Differentiation Opportunities',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'The highest-value AI differentiation opportunities are usually text adaptation, '
                                    'vocabulary support, and generating tiered tasks. Start by auditing one unit '
                                    'for places where you currently spend the most time differentiating manually.'
                                ),
                            },
                            {
                                'title': 'Classroom Diversity Audit',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Map the learning needs in one of your classes: list the range of reading '
                                    'levels, any EAL learners, and students with additional needs. Identify two '
                                    'specific differentiation tasks where AI could save you time.'
                                ),
                            },
                            {
                                'title': 'Learner Needs Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Adapting Texts and Reading Levels',
                        'description': 'Using AI to rewrite and simplify texts for different reading abilities.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'Text Adaptation Techniques',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Prompting for Reading Level Adaptation',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Specify the target reading age or grade level in your prompt, and ask the AI '
                                    'to preserve key vocabulary while simplifying sentence structure. Always '
                                    'verify that the adapted text retains the original meaning and factual accuracy.'
                                ),
                            },
                            {
                                'title': 'Adapt a Class Text to Three Levels',
                                'type': 'assignment', 'duration': 20, 'required': True,
                                'content': (
                                    'Take a paragraph from a class text and use AI to produce three versions: '
                                    'below grade level, at grade level, and extension. Submit the prompts you '
                                    'used and the three resulting versions.'
                                ),
                            },
                            {
                                'title': 'Text Adaptation Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Creating Extension and Enrichment Activities',
                        'description': 'Generating challenging extension tasks that push advanced learners further.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'What Makes a Good Extension Task?',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Extension Task Prompt Patterns',
                                'type': 'text', 'duration': 28, 'required': True,
                                'content': (
                                    'Effective extension tasks ask students to evaluate, synthesise, or create '
                                    'rather than simply recall. Prompt the AI with the core topic and ask for '
                                    'tasks that require higher-order thinking using Bloom\'s Taxonomy as a guide.'
                                ),
                            },
                            {
                                'title': 'Design Extension Activities for Your Unit',
                                'type': 'assignment', 'duration': 15, 'required': False,
                                'content': (
                                    'Design three extension activities for a unit you currently teach. Use AI to '
                                    'generate a first draft, then refine them to target higher-order thinking '
                                    'skills appropriate to your students.'
                                ),
                            },
                            {
                                'title': 'Extension Activities Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Supporting EAL and Special Needs Students',
                        'description': 'AI tools and prompting techniques for learners with additional language or learning needs.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'AI for EAL Learners: An Overview',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Scaffolding Techniques and Prompts',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'For EAL learners, ask AI to add bilingual glossaries, sentence starters, '
                                    'and visual descriptions alongside the main text. For students with reading '
                                    'difficulties, chunking content into shorter paragraphs with subheadings '
                                    'significantly improves accessibility.'
                                ),
                            },
                            {
                                'title': 'EAL Resource Prompt Templates (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Create Scaffolded Materials',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Choose a text or task from your current unit and use AI to create a '
                                    'scaffolded version for EAL learners. Include at least a glossary and '
                                    'sentence starters, and submit the original and scaffolded versions.'
                                ),
                            },
                            {
                                'title': 'EAL Support Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Building a Differentiation Workflow',
                        'description': 'Designing a repeatable, time-efficient system for AI-powered differentiation.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Designing Your Workflow',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Workflow Templates and Time-Saving Tips',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'A sustainable differentiation workflow has three steps: adapt the core '
                                    'material with AI, review and quality-check the output, then organise '
                                    'materials in a shared folder for easy access. Batch similar tasks together '
                                    'to minimise context-switching.'
                                ),
                            },
                            {
                                'title': 'Build and Document Your Workflow',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Design a step-by-step differentiation workflow for your classroom context. '
                                    'Include the prompts you will use, how you will review AI output, and how '
                                    'you will store and share differentiated materials.'
                                ),
                            },
                            {
                                'title': 'Differentiation Workflow Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # PILLAR 2 — Teach for AI
    # =========================================================================
    {
        'name': 'Teach for AI',
        'slug': 'teach-for-ai',
        'description': 'Prepare students for an AI-driven world with data literacy, ethics, responsible AI use, and future-ready skills.',
        'order': 2,
        'courses': [
            # -----------------------------------------------------------------
            # Course 1: Data Literacy for K-12 Educators
            # -----------------------------------------------------------------
            {
                'title': 'Data Literacy for K-12 Educators',
                'description': 'Build the foundational knowledge to help your students understand, interpret, and critically question data — a core skill for the AI age.',
                'level': 'beginner',
                'duration_hours': 4,
                'learning_outcomes': [
                    'Teach students to read and interpret common data visualisations',
                    'Explain where data comes from and how it is collected',
                    'Identify bias in data and its real-world consequences',
                    'Design cross-curricular data literacy activities',
                ],
                'modules': [
                    {
                        'title': 'Why Data Literacy Matters Now',
                        'description': 'The case for data literacy in the AI age and what it means for K-12 education.',
                        'duration_minutes': 35,
                        'lessons': [
                            {
                                'title': 'Data in the AI Age',
                                'type': 'video', 'duration': 10, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'What Data Literacy Means for Students',
                                'type': 'text', 'duration': 18, 'required': True,
                                'content': (
                                    'Data literacy is the ability to read, work with, analyse, and argue with data. '
                                    'In an AI-driven world, students who can question data sources and spot '
                                    'misleading visualisations have a critical advantage.'
                                ),
                            },
                            {
                                'title': 'Self-Assessment: Your Data Literacy Starting Point',
                                'type': 'quiz', 'duration': 7, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Reading Charts, Graphs, and Statistics',
                        'description': 'Teaching students to interpret the most common data visualisation formats.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Common Chart Types Explained',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Teaching Students to Read Data',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'Start with the title and axes before looking at the data itself — this simple '
                                    'habit prevents most misreadings. Teach students to ask: Who collected this? '
                                    'When? And what is not shown?'
                                ),
                            },
                            {
                                'title': 'Chart Interpretation Activity',
                                'type': 'assignment', 'duration': 13, 'required': True,
                                'content': (
                                    'Find a chart from a news article or government website and analyse it. '
                                    'Identify the chart type, what it shows, what it might be hiding, and '
                                    'how you would use it as a teaching resource.'
                                ),
                            },
                            {
                                'title': 'Chart Reading Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Where Data Comes From and Who Collects It',
                        'description': 'Exploring data collection methods, sources, and the interests behind them.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'How Data Is Collected',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Data Sources and Their Biases',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'Data is never neutral — it reflects the choices of whoever collected it. '
                                    'Survey data depends on who was asked; sensor data depends on where sensors '
                                    'were placed. Teaching students to ask "who collected this and why?" is a '
                                    'powerful critical-thinking habit.'
                                ),
                            },
                            {
                                'title': 'Data Collection Audit Task',
                                'type': 'assignment', 'duration': 11, 'required': False,
                                'content': (
                                    'Identify three datasets used in your subject area. For each one, note who '
                                    'collected it, how it was collected, and one possible source of bias. '
                                    'Write a one-sentence student-friendly explanation of each limitation.'
                                ),
                            },
                            {
                                'title': 'Data Sources Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Bias in Data: Real-World Examples',
                        'description': 'Case studies of biased datasets and their impact on AI systems and society.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Bias in AI: Three Case Studies',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'The Origins of Dataset Bias',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Dataset bias often originates from under-representation: if a training '
                                    'dataset contains mostly images of one demographic, the AI will perform '
                                    'poorly on others. Historical bias, measurement bias, and sampling bias '
                                    'are the three most common types to teach students.'
                                ),
                            },
                            {
                                'title': 'Bias Investigation Quiz',
                                'type': 'quiz', 'duration': 12, 'required': True,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Teaching Data Literacy Across Subjects',
                        'description': 'Integrating data literacy into English, Science, History, and other subjects.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'Cross-Curricular Data Ideas',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Subject-Specific Activity Guide',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'In English, students can analyse how statistics are used persuasively in '
                                    'speeches and articles. In History, census data reveals demographic change '
                                    'over time. In Science, experimental data raises questions about reliability '
                                    'and reproducibility.'
                                ),
                            },
                            {
                                'title': 'Cross-Curricular Lesson Planner (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Plan a Data Literacy Lesson',
                                'type': 'assignment', 'duration': 8, 'required': False,
                                'content': (
                                    'Plan a 20-minute data literacy activity for your subject using the lesson '
                                    'planner template. Identify the dataset, the visualisation type students '
                                    'will encounter, and two critical questions you will ask them.'
                                ),
                            },
                            {
                                'title': 'Cross-Curricular Data Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Student Projects: Collecting and Analysing Data',
                        'description': 'Project ideas that give students hands-on experience with real data.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Project Design Principles',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Five Student Data Projects',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Five accessible data projects: (1) class survey and visualisation, '
                                    '(2) local weather data analysis, (3) sports statistics comparison, '
                                    '(4) social media engagement audit, (5) school timetable efficiency study. '
                                    'Each can be scaled up or down to suit your year group.'
                                ),
                            },
                            {
                                'title': 'Design Your Own Student Project',
                                'type': 'assignment', 'duration': 15, 'required': False,
                                'content': (
                                    'Design a data collection and analysis project for your class. Specify the '
                                    'question students will investigate, the data they will collect, the tool '
                                    'they will use to visualise it, and how you will assess their conclusions.'
                                ),
                            },
                            {
                                'title': 'Student Data Projects Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 2: Teaching AI Ethics and Responsible Use
            # -----------------------------------------------------------------
            {
                'title': 'Teaching AI Ethics and Responsible Use',
                'description': 'Equip students with the ethical frameworks to navigate AI responsibly — covering bias, privacy, misinformation, and the societal impact of automation.',
                'level': 'intermediate',
                'duration_hours': 6,
                'learning_outcomes': [
                    'Facilitate discussions about algorithmic bias and fairness',
                    'Help students understand their digital rights and privacy',
                    'Identify and counter AI-generated misinformation',
                    'Explore the societal impact of automation with students',
                ],
                'modules': [
                    {
                        'title': 'What Are AI Ethics?',
                        'description': 'An introduction to the key ethical principles that guide responsible AI development.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'Introduction to AI Ethics',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'The Five Principles of Responsible AI',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'The five core principles of responsible AI are: fairness, accountability, '
                                    'transparency, safety, and privacy. These provide a useful framework for '
                                    'classroom discussions and for evaluating AI tools before using them with students.'
                                ),
                            },
                            {
                                'title': 'Ethics in Action: Discussion Starter',
                                'type': 'assignment', 'duration': 11, 'required': False,
                                'content': (
                                    'Present this scenario to a colleague or think through it yourself: "A school '
                                    'uses an AI tool to predict which students are at risk of dropping out. The '
                                    'AI is 80% accurate." Write three ethical questions this scenario raises '
                                    'and how you would use them in a classroom discussion.'
                                ),
                            },
                            {
                                'title': 'AI Ethics Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Algorithmic Bias: Case Studies for the Classroom',
                        'description': 'Real examples of biased AI systems and classroom activities to explore them.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'Three Algorithms, Three Biases',
                                'type': 'video', 'duration': 20, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Running a Bias Case Study in Class',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Start with a real-world example students can relate to (e.g. hiring algorithms '
                                    'or content recommendation), then ask: who was harmed, what data caused the '
                                    'bias, and what could have been done differently? Structured debate formats '
                                    'work well for these discussions.'
                                ),
                            },
                            {
                                'title': 'Case Study Resource Pack (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Class Discussion Facilitator Notes',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Prepare facilitator notes for a 15-minute class discussion on algorithmic '
                                    'bias. Include an opening scenario, three discussion questions, and a '
                                    'closing prompt that asks students to suggest a solution.'
                                ),
                            },
                            {
                                'title': 'Algorithmic Bias Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Privacy, Surveillance, and Student Rights',
                        'description': 'How AI is used in surveillance, the data students generate, and their rights.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'AI and Surveillance: What Students Need to Know',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Student Digital Rights Explained',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Students generate data every time they use a school device or platform. '
                                    'Depending on jurisdiction, they have rights to access, correct, and request '
                                    'deletion of this data. Teaching students their rights is a prerequisite '
                                    'for meaningful consent.'
                                ),
                            },
                            {
                                'title': 'Privacy Audit Activity',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Conduct a quick privacy audit of one app or platform your students use '
                                    'regularly. Read its privacy policy (or a plain-English summary) and '
                                    'list: what data it collects, how it uses it, and whether students can '
                                    'opt out. Write a 100-word summary suitable for sharing with students.'
                                ),
                            },
                            {
                                'title': 'Privacy Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Misinformation, Deepfakes, and Media Literacy',
                        'description': 'Tools and strategies for detecting AI-generated misinformation and deepfakes.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'Deepfakes and Synthetic Media Explained',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Detection Strategies and Classroom Tools',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Common deepfake detection cues include unnatural blinking, inconsistent '
                                    'lighting on the face, and blurry ear/hair edges. Free tools like reverse '
                                    'image search and metadata checkers are accessible classroom resources. '
                                    'Teach students the SIFT method: Stop, Investigate, Find better coverage, Trace.'
                                ),
                            },
                            {
                                'title': 'Spot the Fake: Student Activity',
                                'type': 'assignment', 'duration': 17, 'required': True,
                                'content': (
                                    'Design a "spot the fake" classroom activity: find three images (at least '
                                    'one AI-generated) and write the instructions students will use to analyse '
                                    'them. Include a debrief question that connects the activity to real-world '
                                    'media consumption.'
                                ),
                            },
                            {
                                'title': 'Misinformation Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'The Future of Work and Automation',
                        'description': 'Evidence-based discussion of how AI is changing the labour market.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Which Jobs Are Changing and Why',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'The Evidence on Automation and Employment',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'Research suggests AI is more likely to augment jobs than eliminate them '
                                    'entirely, but the transition will be uneven across sectors and skill levels. '
                                    'Helping students develop adaptable, human-centred skills is the most '
                                    'robust response to this uncertainty.'
                                ),
                            },
                            {
                                'title': 'Future of Work Discussion Quiz',
                                'type': 'quiz', 'duration': 13, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Facilitating Ethical Discussions with Students',
                        'description': 'Practical techniques for running productive, age-appropriate AI ethics discussions.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Discussion Facilitation Techniques',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Age-Appropriate Ethics Frameworks',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'For younger students, use concrete scenarios and fairness language. For older '
                                    'students, introduce formal frameworks such as consequentialism and rights-based '
                                    'ethics. Philosophical chairs and structured academic controversy are both '
                                    'effective discussion formats for ethics topics.'
                                ),
                            },
                            {
                                'title': 'Ethics Discussion Planning Template (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Plan and Run an Ethics Discussion',
                                'type': 'assignment', 'duration': 8, 'required': False,
                                'content': (
                                    'Using the planning template, design a 15-minute ethics discussion for your '
                                    'class on an AI topic of your choice. Run it with students or a colleague '
                                    'and write a 100-word reflection on how it went.'
                                ),
                            },
                            {
                                'title': 'Ethics Discussion Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 3: Future-Ready Skills
            # -----------------------------------------------------------------
            {
                'title': 'Future-Ready Skills: Preparing Students for an AI World',
                'description': 'Understand which skills will matter most in an AI-augmented workforce and how to weave them into your existing curriculum.',
                'level': 'intermediate',
                'duration_hours': 5,
                'learning_outcomes': [
                    'Identify the skills most valued in an AI-augmented workforce',
                    'Embed critical thinking and problem-solving across your curriculum',
                    'Design tasks that develop creativity and collaboration',
                    'Foster adaptability and a growth mindset in your students',
                ],
                'modules': [
                    {
                        'title': 'The Changing Landscape of Work',
                        'description': 'Research-based overview of how AI is reshaping industries and job roles.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Industries Being Reshaped by AI',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'What the Research Tells Us',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Studies from McKinsey, Oxford, and the World Economic Forum agree that '
                                    'repetitive, rules-based tasks are most susceptible to automation. '
                                    'Roles requiring empathy, complex judgement, and creative problem-solving '
                                    'are expected to grow. Teaching to these strengths is the strategic response.'
                                ),
                            },
                            {
                                'title': 'Future of Work Reflection',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Write a 150-word reflection on how the changing landscape of work affects '
                                    'your subject area. Which skills in your curriculum are most future-relevant, '
                                    'and which might need more emphasis?'
                                ),
                            },
                            {
                                'title': 'Changing Landscape Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Critical Thinking and Problem Solving',
                        'description': 'Practical strategies for teaching higher-order thinking in any subject.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Critical Thinking Frameworks',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Problem-Solving Strategies for the Classroom',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Effective problem-solving instruction includes modelling the process aloud, '
                                    'using worked examples before independent practice, and asking students to '
                                    'evaluate multiple solution paths rather than just finding the answer. '
                                    'Ill-structured problems with no single correct answer develop the most '
                                    'transferable thinking skills.'
                                ),
                            },
                            {
                                'title': 'Design a Critical Thinking Task',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Design one critical thinking task for your subject that requires students '
                                    'to evaluate evidence, consider multiple perspectives, or solve an '
                                    'ill-structured problem. Write the task brief and an example of what '
                                    'a strong student response would look like.'
                                ),
                            },
                            {
                                'title': 'Critical Thinking Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Creativity and Collaboration in the AI Era',
                        'description': 'Why human creativity and teamwork are more important than ever, and how to teach them.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Why Human Creativity Still Wins',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Teaching Collaboration at Scale',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Collaborative tasks should assign distinct roles, have a shared product, '
                                    'and include individual accountability. Structuring peer feedback with '
                                    'specific criteria prevents vague responses and builds the communication '
                                    'skills most valued by employers.'
                                ),
                            },
                            {
                                'title': 'Creativity and Collaboration Activity Pack (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Design a Collaborative Creative Task',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Design a collaborative creative task for your class that produces a shared '
                                    'output. Specify each team role, the final product, and how you will assess '
                                    'both the product and each student\'s individual contribution.'
                                ),
                            },
                            {
                                'title': 'Creativity and Collaboration Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Adaptability and Lifelong Learning',
                        'description': 'Building learning-to-learn skills and a growth mindset for an uncertain future.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Growth Mindset in Practice',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Teaching Students to Learn How to Learn',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Metacognitive strategies — such as self-explanation, spaced practice, and '
                                    'retrieval practice — are among the most evidence-based tools for building '
                                    'independent learners. Teaching students to monitor their own understanding '
                                    'is more valuable than any specific content knowledge.'
                                ),
                            },
                            {
                                'title': 'Lifelong Learning Self-Assessment',
                                'type': 'quiz', 'duration': 13, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Embedding Future-Ready Skills in Your Curriculum',
                        'description': 'Mapping future-ready skills to your existing curriculum and assessment framework.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Curriculum Mapping Overview',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Skills-to-Curriculum Mapping Guide',
                                'type': 'text', 'duration': 23, 'required': True,
                                'content': (
                                    'Map future-ready skills to existing units by identifying where critical '
                                    'thinking, collaboration, or creativity already appear — then look for '
                                    'gaps. Small tweaks to existing tasks (adding a reflection, a peer review, '
                                    'or an open-ended question) can add significant skill-development value.'
                                ),
                            },
                            {
                                'title': 'Map Your Curriculum for Future-Ready Skills',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Using the mapping guide, audit one term\'s worth of your curriculum. '
                                    'Identify where each of the four future-ready skills (critical thinking, '
                                    'creativity, collaboration, adaptability) appears, and propose one small '
                                    'change to strengthen the weakest area.'
                                ),
                            },
                            {
                                'title': 'Curriculum Mapping Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # PILLAR 3 — Teach about AI
    # =========================================================================
    {
        'name': 'Teach about AI',
        'slug': 'teach-about-ai',
        'description': 'Master using AI-generated outputs, lesson enhancement tools, and teaching design innovations to become an AI-confident educator.',
        'order': 3,
        'courses': [
            # -----------------------------------------------------------------
            # Course 1: AI Fundamentals for Educators
            # -----------------------------------------------------------------
            {
                'title': 'AI Fundamentals for Educators',
                'description': 'Develop a solid conceptual understanding of how AI systems work — covering machine learning, neural networks, and natural language processing in plain language.',
                'level': 'beginner',
                'duration_hours': 5,
                'learning_outcomes': [
                    'Explain how machine learning works without using jargon',
                    'Describe the role of neural networks in modern AI',
                    'Identify the limitations and failure modes of AI systems',
                    'Distinguish between AI hype and genuine capability',
                ],
                'modules': [
                    {
                        'title': 'A Brief History of Artificial Intelligence',
                        'description': 'From symbolic AI to deep learning: the key milestones and ideas that shaped modern AI.',
                        'duration_minutes': 40,
                        'lessons': [
                            {
                                'title': 'AI Through the Decades',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Key Milestones in AI History',
                                'type': 'text', 'duration': 18, 'required': True,
                                'content': (
                                    'AI research began in the 1950s with rule-based systems; the first AI winter '
                                    'came in the 1970s when early optimism collided with real-world limitations. '
                                    'The deep learning revolution from 2012 onwards, powered by big data and '
                                    'GPU computing, produced the AI tools we use today.'
                                ),
                            },
                            {
                                'title': 'History of AI Knowledge Check',
                                'type': 'quiz', 'duration': 7, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'How Machine Learning Works',
                        'description': 'An intuitive explanation of training data, models, and prediction without the maths.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Machine Learning Without the Maths',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Training, Testing, and Predicting',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'A machine learning model is trained on labelled examples, tested on unseen '
                                    'data to measure accuracy, and then deployed to make predictions on new inputs. '
                                    'The gap between training performance and real-world performance is one of the '
                                    'most common sources of AI failure.'
                                ),
                            },
                            {
                                'title': 'ML Concept Diagram',
                                'type': 'image', 'duration': 5, 'required': False,
                                'content': _IMG,
                            },
                            {
                                'title': 'Machine Learning Quiz',
                                'type': 'quiz', 'duration': 7, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Neural Networks: The Big Picture',
                        'description': 'What neural networks are, how they learn, and why they are so powerful.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'Neurons, Layers, and Weights',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'How Neural Networks Learn',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Neural networks learn by adjusting the strength (weight) of connections '
                                    'between artificial neurons based on how wrong their predictions were. '
                                    'This process, called backpropagation, repeats millions of times until '
                                    'the network makes accurate predictions on training data.'
                                ),
                            },
                            {
                                'title': 'Neural Network Visualiser Activity',
                                'type': 'assignment', 'duration': 12, 'required': False,
                                'content': (
                                    'Use the free Tensorflow Playground tool (playground.tensorflow.org) to '
                                    'experiment with a simple neural network. Try changing the number of layers '
                                    'and neurons and note what happens to the model\'s accuracy. '
                                    'Write two observations you could share with students.'
                                ),
                            },
                            {
                                'title': 'Neural Networks Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Natural Language Processing Demystified',
                        'description': 'How AI systems understand and generate text, including large language models.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'From Words to Vectors',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'How Large Language Models Work',
                                'type': 'text', 'duration': 28, 'required': True,
                                'content': (
                                    'Large language models convert words into numerical vectors that capture '
                                    'meaning and context. They are trained to predict the next token in a '
                                    'sequence, which — at scale — produces remarkably fluent and coherent text. '
                                    'They do not "understand" language the way humans do; they identify patterns.'
                                ),
                            },
                            {
                                'title': 'NLP in Practice: Examples',
                                'type': 'assignment', 'duration': 12, 'required': False,
                                'content': (
                                    'Find three examples of NLP in tools you or your students use (e.g. grammar '
                                    'checkers, translation apps, chatbots). For each, describe what NLP task it '
                                    'is performing and one limitation you have noticed.'
                                ),
                            },
                            {
                                'title': 'NLP Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Computer Vision and Its Applications',
                        'description': 'How AI sees the world and where it is used in education and everyday life.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'How AI Sees Images',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Computer Vision in Education and Beyond',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Computer vision powers facial recognition, medical imaging analysis, '
                                    'self-driving cars, and accessibility tools like automatic alt-text. '
                                    'In education, it is used in proctoring software, student engagement '
                                    'analysis tools, and science lab automation — each raising important '
                                    'ethical questions worth exploring with students.'
                                ),
                            },
                            {
                                'title': 'Computer Vision Examples Gallery',
                                'type': 'image', 'duration': 5, 'required': False,
                                'content': _IMG,
                            },
                            {
                                'title': 'Application Spotting Quiz',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'AI Limitations and Common Misconceptions',
                        'description': 'What AI cannot do, where it fails, and how to talk about it accurately.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'The Limits of AI Today',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Common Misconceptions Debunked',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Common misconceptions: AI is conscious; AI always gets better with more '
                                    'data; AI is objective. In reality, AI systems have no awareness, can '
                                    'plateau or degrade with poor-quality data, and inherit the biases of '
                                    'their training sets. Correcting these misconceptions is foundational '
                                    'to AI literacy.'
                                ),
                            },
                            {
                                'title': 'Myth-Busting Activity',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Find three AI-related headlines from the past year that contain '
                                    'exaggerated or misleading claims. For each, write the accurate version '
                                    'in one sentence and note which misconception it exploits.'
                                ),
                            },
                            {
                                'title': 'AI Limitations Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 2: Teaching AI Concepts Without Code
            # -----------------------------------------------------------------
            {
                'title': 'Teaching AI Concepts Without Code',
                'description': 'A toolkit of unplugged activities, analogies, and project ideas to teach AI concepts to primary and secondary students without requiring programming knowledge.',
                'level': 'beginner',
                'duration_hours': 4,
                'learning_outcomes': [
                    'Teach machine learning concepts through unplugged activities',
                    'Use sorting and labelling games to explain classifiers',
                    'Facilitate pattern recognition activities for any age group',
                    'Design age-appropriate AI projects for primary and secondary students',
                ],
                'modules': [
                    {
                        'title': 'Unplugged AI: Teaching Without Computers',
                        'description': 'The case for unplugged AI education and a toolkit of screen-free activities.',
                        'duration_minutes': 40,
                        'lessons': [
                            {
                                'title': 'Why Unplugged AI Works',
                                'type': 'video', 'duration': 10, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Unplugged Activity Toolkit',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Unplugged activities build conceptual understanding before technical '
                                    'implementation. Students who understand what a classifier does with '
                                    'physical cards will find the concept much easier to grasp when they '
                                    'encounter it in a digital tool or coding environment later.'
                                ),
                            },
                            {
                                'title': 'Unplugged Activity Resource Pack (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Run an Unplugged Activity',
                                'type': 'assignment', 'duration': 5, 'required': False,
                                'content': (
                                    'Choose one unplugged activity from the resource pack and run it with a '
                                    'class or a small group of colleagues. Write a 100-word reflection on '
                                    'what worked well and what you would change.'
                                ),
                            },
                            {
                                'title': 'Unplugged AI Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Training a Classifier: Sorting and Labelling Activities',
                        'description': 'Hands-on activities that simulate the training of a machine learning classifier.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'What Is a Classifier?',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Sorting and Labelling Games Guide',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'A sorting game where students label picture cards as "cat" or "not cat" '
                                    'directly simulates the labelling phase of training a classifier. '
                                    'Following up by testing the classifier on ambiguous images teaches the '
                                    'concept of confidence scores and decision boundaries intuitively.'
                                ),
                            },
                            {
                                'title': 'Run a Classroom Sorting Game',
                                'type': 'assignment', 'duration': 13, 'required': True,
                                'content': (
                                    'Design and run a 10-minute sorting game that simulates classifier training '
                                    'for your year group. Use physical cards, images, or a simple online tool. '
                                    'Write the game instructions and a debrief question that connects it to '
                                    'how real AI classifiers work.'
                                ),
                            },
                            {
                                'title': 'Classifier Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Decision Trees in the Real World',
                        'description': 'Using everyday decisions to teach students how decision tree algorithms work.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'Decision Trees Explained with Examples',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Building Decision Trees with Students',
                                'type': 'text', 'duration': 20, 'required': True,
                                'content': (
                                    'Start with a relatable decision (e.g. "Should I bring an umbrella?") and '
                                    'have students draw the yes/no branches themselves. Once the concept is '
                                    'clear, move to more complex examples such as medical diagnosis or spam '
                                    'filtering to show real-world applications.'
                                ),
                            },
                            {
                                'title': 'Decision Tree Activity Worksheet (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Student Decision Tree Challenge',
                                'type': 'assignment', 'duration': 5, 'required': False,
                                'content': (
                                    'Have students build a decision tree for a topic in your subject (e.g. '
                                    'classifying an animal\'s habitat in Science, or identifying a text type '
                                    'in English). Photograph or scan the completed trees and submit one '
                                    'example with a note on how students engaged with the activity.'
                                ),
                            },
                            {
                                'title': 'Decision Trees Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Pattern Recognition Games for the Classroom',
                        'description': 'Games and puzzles that build intuition for how AI recognises patterns.',
                        'duration_minutes': 45,
                        'lessons': [
                            {
                                'title': 'How AI Recognises Patterns',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Five Pattern Recognition Games',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'Five accessible games: (1) "Odd one out" card sorts, (2) pixel art '
                                    'number recognition, (3) handwriting similarities, (4) music genre '
                                    'sorting by ear, (5) nature photo classification. Each reveals a '
                                    'different aspect of how pattern recognition works in AI.'
                                ),
                            },
                            {
                                'title': 'Run a Pattern Recognition Game',
                                'type': 'assignment', 'duration': 11, 'required': False,
                                'content': (
                                    'Choose one game from the list, run it with students, and write a brief '
                                    'account of how students described the patterns they used. '
                                    'Note any misconceptions that emerged and how you addressed them.'
                                ),
                            },
                            {
                                'title': 'Pattern Recognition Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Age-Appropriate AI Projects (Primary)',
                        'description': 'Guided project ideas for primary students that introduce AI concepts through play.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Designing AI Projects for Young Learners',
                                'type': 'video', 'duration': 12, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Five Primary AI Projects',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Five primary-level projects: (1) train a simple image classifier with '
                                    'Teachable Machine, (2) build a paper robot that "follows rules", '
                                    '(3) create an AI storybook, (4) design an AI helper for the classroom, '
                                    '(5) run a "robot" relay race where students follow an algorithm. '
                                    'All can be done with minimal technology.'
                                ),
                            },
                            {
                                'title': 'Primary Project Planning Template (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Plan a Primary AI Project',
                                'type': 'assignment', 'duration': 8, 'required': False,
                                'content': (
                                    'Using the planning template, design one AI project for your primary class. '
                                    'Specify the AI concept it teaches, the materials needed, the duration, '
                                    'and how you will know if students have understood the concept.'
                                ),
                            },
                            {
                                'title': 'Primary AI Projects Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Age-Appropriate AI Projects (Secondary)',
                        'description': 'Structured project ideas for secondary students that go deeper into AI concepts.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Designing AI Projects for Secondary Students',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Five Secondary AI Projects',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Five secondary-level projects: (1) bias audit of a real AI tool, '
                                    '(2) sentiment analysis of student-written news, (3) build and test '
                                    'a Teachable Machine model, (4) AI ethics debate and policy proposal, '
                                    '(5) data collection and visualisation study. Each involves critical '
                                    'thinking beyond just using the technology.'
                                ),
                            },
                            {
                                'title': 'Plan a Secondary AI Project',
                                'type': 'assignment', 'duration': 10, 'required': True,
                                'content': (
                                    'Plan one secondary AI project from the list above (or design your own). '
                                    'Write a project brief that includes the learning objective, student tasks, '
                                    'resources needed, and assessment criteria.'
                                ),
                            },
                            {
                                'title': 'Secondary AI Projects Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 3: AI Across the Curriculum
            # -----------------------------------------------------------------
            {
                'title': 'AI Across the Curriculum',
                'description': 'Discover how AI connects to every subject area and find ready-to-use lesson ideas for English, Maths, Science, Humanities, and the Arts.',
                'level': 'intermediate',
                'duration_hours': 6,
                'learning_outcomes': [
                    'Connect AI concepts to your existing subject curriculum',
                    'Deliver cross-curricular AI lessons in English, Maths, and Science',
                    'Use AI as a creative tool in Arts and Humanities',
                    'Design a cross-curricular AI project with colleagues',
                ],
                'modules': [
                    {
                        'title': 'AI in English and Language Arts',
                        'description': 'Using AI to explore authorship, creativity, and language — with ready-to-use lesson ideas.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'AI and Authorship: A Discussion Starter',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'AI in the English Classroom',
                                'type': 'text', 'duration': 30, 'required': True,
                                'content': (
                                    'In English, AI raises rich questions about authorship, voice, and creativity. '
                                    'Compare an AI-generated poem with a human one; analyse AI-written persuasive '
                                    'texts for rhetorical techniques; or use AI as a writing "sparring partner" '
                                    'that students must critique and improve.'
                                ),
                            },
                            {
                                'title': 'English AI Lesson Plans (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Design an AI-Themed English Lesson',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Design a 30-minute English lesson that uses AI as a tool or topic. '
                                    'Include the learning objective, student activity, and one discussion '
                                    'question that connects to broader questions about language and authorship.'
                                ),
                            },
                            {
                                'title': 'AI in English Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'AI in Mathematics',
                        'description': 'Connecting AI and data science to mathematical concepts students already know.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'Where Maths Meets AI',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Data Science Connections to the Maths Curriculum',
                                'type': 'text', 'duration': 30, 'required': True,
                                'content': (
                                    'Statistics, probability, functions, and linear algebra all appear in AI '
                                    'and data science. Using real datasets in Maths lessons — rather than '
                                    'textbook numbers — shows students how the concepts they are learning '
                                    'are used to build the AI tools they use every day.'
                                ),
                            },
                            {
                                'title': 'AI-Themed Maths Activity',
                                'type': 'assignment', 'duration': 15, 'required': True,
                                'content': (
                                    'Design one Maths activity that uses a real dataset (e.g. from Kaggle or '
                                    'a government statistics site). Write the student task, identify which '
                                    'curriculum skill it practises, and explain the AI connection in one sentence.'
                                ),
                            },
                            {
                                'title': 'AI in Maths Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'AI in Science and STEM',
                        'description': 'How AI is transforming scientific research and what that means for science education.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'AI in Scientific Discovery',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'STEM AI Lesson Ideas',
                                'type': 'text', 'duration': 27, 'required': True,
                                'content': (
                                    'AI is accelerating scientific discovery in drug development, climate '
                                    'modelling, and materials science. In the classroom, this translates into '
                                    'rich discussions about experimental design, data reliability, and the '
                                    'role of human judgement in interpreting AI-generated results.'
                                ),
                            },
                            {
                                'title': 'AI in Science Quiz',
                                'type': 'quiz', 'duration': 15, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'AI in Humanities and Social Sciences',
                        'description': "Exploring AI's social, historical, and ethical dimensions through Humanities subjects.",
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'AI Through a Humanities Lens',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Humanities AI Lesson Ideas',
                                'type': 'text', 'duration': 28, 'required': True,
                                'content': (
                                    'History: examine how data-driven decision-making echoes historical uses of '
                                    'statistics for social control. Geography: use AI satellite analysis to '
                                    'study land use change. Civics: debate AI regulation and democratic '
                                    'governance. Each connects AI to existing content rather than replacing it.'
                                ),
                            },
                            {
                                'title': 'Design a Humanities AI Discussion',
                                'type': 'assignment', 'duration': 12, 'required': False,
                                'content': (
                                    'Design a structured discussion activity for a Humanities class that '
                                    'connects AI to a topic you currently teach. Write the prompt, three '
                                    'discussion questions, and a closing synthesis question.'
                                ),
                            },
                            {
                                'title': 'AI in Humanities Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'AI in the Arts',
                        'description': 'AI as a creative collaborator: music, visual art, and writing projects for the classroom.',
                        'duration_minutes': 55,
                        'lessons': [
                            {
                                'title': 'AI as Creative Collaborator',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Music, Visual Art, and Writing with AI',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'AI art generators, music composition tools, and writing assistants are '
                                    'all accessible in the classroom. Use them as creative starting points '
                                    'that students then respond to, critique, or transform — positioning '
                                    'the student as the curator and editor, not a passive consumer.'
                                ),
                            },
                            {
                                'title': 'Student AI Art Gallery Examples',
                                'type': 'image', 'duration': 5, 'required': False,
                                'content': _IMG,
                            },
                            {
                                'title': 'Create an AI-Assisted Art Project',
                                'type': 'assignment', 'duration': 10, 'required': False,
                                'content': (
                                    'Design a creative task where students use an AI tool to generate a '
                                    'starting point (image, text, or music) and then respond to it with '
                                    'their own creative work. Write the brief and the assessment criteria '
                                    'you would use to evaluate student responses.'
                                ),
                            },
                            {
                                'title': 'AI in the Arts Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Cross-Curricular AI Projects',
                        'description': 'Frameworks for designing and running AI projects that span multiple subject areas.',
                        'duration_minutes': 50,
                        'lessons': [
                            {
                                'title': 'Cross-Curricular Project Design',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Project Planning Frameworks',
                                'type': 'text', 'duration': 22, 'required': True,
                                'content': (
                                    'Successful cross-curricular AI projects have a clear driving question, '
                                    'defined contributions from each subject, and a shared public product. '
                                    'Agreeing on the assessment framework between departments before starting '
                                    'prevents disputes and ensures coherent student experience.'
                                ),
                            },
                            {
                                'title': 'Project Planning Template (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Plan Your Cross-Curricular AI Project',
                                'type': 'assignment', 'duration': 8, 'required': True,
                                'content': (
                                    'Using the planning template, sketch a cross-curricular AI project '
                                    'involving at least two subjects. Identify the driving question, each '
                                    'subject\'s contribution, the final product, and one potential obstacle.'
                                ),
                            },
                            {
                                'title': 'Cross-Curricular Projects Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
            # -----------------------------------------------------------------
            # Course 4: Designing AI Learning Experiences
            # -----------------------------------------------------------------
            {
                'title': 'Designing AI Learning Experiences',
                'description': 'Learn instructional design principles for creating engaging, inquiry-based AI units that meet curriculum standards and spark student curiosity.',
                'level': 'advanced',
                'duration_hours': 7,
                'learning_outcomes': [
                    'Apply backwards design to create coherent AI learning units',
                    'Facilitate inquiry-based learning about AI',
                    'Map AI learning outcomes to curriculum standards',
                    'Design authentic assessments for AI learning',
                ],
                'modules': [
                    {
                        'title': 'Backwards Design for AI Units',
                        'description': 'Starting with learning outcomes and working backwards to activities and assessments.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'The Backwards Design Approach',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Applying Backwards Design to AI Units',
                                'type': 'text', 'duration': 27, 'required': True,
                                'content': (
                                    'Backwards design (Wiggins & McTighe) starts with the desired end — '
                                    'what should students know, understand, and be able to do? — then '
                                    'determines acceptable evidence, and finally plans learning experiences. '
                                    'Applied to AI, this prevents "cool technology" from driving the unit '
                                    'at the expense of genuine learning.'
                                ),
                            },
                            {
                                'title': 'Backwards Design Template (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Draft Your AI Unit Using Backwards Design',
                                'type': 'assignment', 'duration': 10, 'required': True,
                                'content': (
                                    'Using the template, draft the first two stages of backwards design '
                                    'for an AI unit: (1) desired results — big ideas, essential questions, '
                                    'knowledge and skills; (2) assessment evidence — performance tasks '
                                    'and other evidence.'
                                ),
                            },
                            {
                                'title': 'Backwards Design Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Inquiry-Based Learning and AI',
                        'description': 'Designing open-ended investigations that put students in the role of AI researchers.',
                        'duration_minutes': 70,
                        'lessons': [
                            {
                                'title': 'What Is Inquiry-Based Learning?',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Designing AI Inquiry Tasks',
                                'type': 'text', 'duration': 30, 'required': True,
                                'content': (
                                    'Effective AI inquiry tasks have an authentic driving question, require '
                                    'students to gather and interpret real data, and culminate in a public '
                                    'presentation of findings. Scaffolding inquiry with checkpoints prevents '
                                    'students from getting lost and ensures the teacher can catch '
                                    'misconceptions early.'
                                ),
                            },
                            {
                                'title': 'Student Inquiry Examples',
                                'type': 'image', 'duration': 5, 'required': False,
                                'content': _IMG,
                            },
                            {
                                'title': 'Design an AI Inquiry Investigation',
                                'type': 'assignment', 'duration': 20, 'required': True,
                                'content': (
                                    'Design a student inquiry investigation around an AI question relevant '
                                    'to your subject. Write the driving question, the data sources students '
                                    'will use, the key checkpoints, and the final product or presentation format.'
                                ),
                            },
                            {
                                'title': 'Inquiry-Based Learning Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Aligning AI Topics to Curriculum Standards',
                        'description': 'Mapping AI content to national and international curriculum frameworks.',
                        'duration_minutes': 65,
                        'lessons': [
                            {
                                'title': 'Navigating Curriculum Frameworks',
                                'type': 'video', 'duration': 18, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'AI-to-Standards Mapping Guide',
                                'type': 'text', 'duration': 30, 'required': True,
                                'content': (
                                    'AI topics map most naturally to Digital Technologies, Science, and '
                                    'Social Studies strands, but ethical AI content also connects to '
                                    'humanities and PSHE frameworks. Mapping to standards legitimises '
                                    'AI in the curriculum and makes it easier to get leadership support.'
                                ),
                            },
                            {
                                'title': 'Standards Mapping Worksheet (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Map Your AI Unit to Standards',
                                'type': 'assignment', 'duration': 12, 'required': True,
                                'content': (
                                    'Using the worksheet, map each learning outcome in your AI unit to at '
                                    'least one standard in your national or school curriculum framework. '
                                    'Note any outcomes that are difficult to map and suggest how they '
                                    'could be justified to leadership.'
                                ),
                            },
                            {
                                'title': 'Curriculum Standards Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Assessment Strategies for AI Learning',
                        'description': 'Authentic assessment approaches that capture deep learning about AI.',
                        'duration_minutes': 65,
                        'lessons': [
                            {
                                'title': 'Why Traditional Tests Fall Short for AI',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Authentic Assessment Design for AI',
                                'type': 'text', 'duration': 30, 'required': True,
                                'content': (
                                    'Authentic AI assessments ask students to demonstrate understanding in '
                                    'realistic contexts: presenting an AI ethics argument to a panel, '
                                    'writing a policy brief, or creating a teaching resource that explains '
                                    'an AI concept to a younger audience. These tasks are harder to game '
                                    'with AI tools than traditional essays.'
                                ),
                            },
                            {
                                'title': 'Assessment Design Workshop',
                                'type': 'assignment', 'duration': 20, 'required': True,
                                'content': (
                                    'Design an authentic assessment task for your AI unit. Write the student '
                                    'brief, the success criteria, and a marking rubric with at least three '
                                    'performance levels. Identify one way the task discourages dishonest '
                                    'AI use.'
                                ),
                            },
                            {
                                'title': 'Assessment Strategies Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                    {
                        'title': 'Showcasing Student Work: Exhibitions and Portfolios',
                        'description': 'Designing exhibitions and digital portfolios that celebrate student AI learning.',
                        'duration_minutes': 60,
                        'lessons': [
                            {
                                'title': 'AI Learning Exhibitions: Inspiration Gallery',
                                'type': 'video', 'duration': 15, 'required': True,
                                'content': _VID,
                            },
                            {
                                'title': 'Designing a Digital Portfolio',
                                'type': 'text', 'duration': 25, 'required': True,
                                'content': (
                                    'Digital portfolios work best when students curate their own evidence '
                                    'and write reflections that explain their thinking process. Including '
                                    'early drafts alongside final products shows growth and makes the '
                                    'portfolio more meaningful than a polished highlights reel.'
                                ),
                            },
                            {
                                'title': 'Exhibition Planning Checklist (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': False,
                                'content': _PDF,
                            },
                            {
                                'title': 'Plan Your Student AI Exhibition',
                                'type': 'assignment', 'duration': 15, 'required': False,
                                'content': (
                                    'Plan a student AI learning exhibition or portfolio showcase. '
                                    'Use the checklist to identify: the audience, the format, what '
                                    'students will present, and how you will prepare them to talk '
                                    'about their learning process.'
                                ),
                            },
                            {
                                'title': 'Exhibitions and Portfolios Knowledge Check',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': _SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed the database with learning pillars, courses, modules, lessons, and demo users.'

    def handle(self, *args, **options):
        self._seed_pillars()
        self._seed_demo_user()
        self._seed_demo_content_creator()
        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))

    def _seed_pillars(self):
        for pillar_data in PILLARS:
            courses_data = pillar_data.pop('courses')
            pillar, created = LearningPillar.objects.update_or_create(
                slug=pillar_data['slug'],
                defaults=pillar_data,
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {action} pillar: {pillar.name}')

            for course_data in courses_data:
                modules_data = course_data.pop('modules')
                course, _ = Course.objects.update_or_create(
                    title=course_data['title'],
                    pillar=pillar,
                    defaults={
                        'description':       course_data['description'],
                        'level':             course_data.get('level', 'beginner'),
                        'duration_hours':    course_data.get('duration_hours', 0),
                        'learning_outcomes': course_data.get('learning_outcomes', []),
                        'is_published':      True,
                    },
                )
                total_lessons = 0
                for order, module_data in enumerate(modules_data, start=1):
                    lessons_data = module_data.pop('lessons', [])
                    module, _ = Module.objects.update_or_create(
                        title=module_data['title'],
                        course=course,
                        defaults={
                            'order':            order,
                            'description':      module_data['description'],
                            'duration_minutes': module_data['duration_minutes'],
                        },
                    )
                    for lesson_order, lesson in enumerate(lessons_data, start=1):
                        Lesson.objects.update_or_create(
                            title=lesson['title'],
                            module=module,
                            defaults={
                                'lesson_type':      lesson['type'],
                                'order':            lesson_order,
                                'duration_minutes': lesson['duration'],
                                'is_required':      lesson['required'],
                                'content':          lesson.get('content', ''),
                                'quiz_data':        lesson.get('quiz_data', []),
                            },
                        )
                    total_lessons += len(lessons_data)
                    module_data['lessons'] = lessons_data  # restore for idempotency

                self.stdout.write(
                    f'    Course: {course.title} ({len(modules_data)} modules, {total_lessons} lessons)'
                )

            pillar_data['courses'] = courses_data  # restore for idempotency

    def _seed_demo_user(self):
        user, created = User.objects.get_or_create(
            username='demo_teacher',
            defaults={
                'first_name': 'Nikos',
                'last_name': 'Grammatikos',
                'email': 'nikos@aidea.example.com',
            },
        )
        if created:
            user.set_password('demo1234')
            user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'user_type': UserProfile.UserType.TEACHER,
                'avatar_initials': 'NG',
            },
        )

        course = Course.objects.filter(pillar__slug='teach-with-ai').first()
        if course:
            module = course.modules.filter(order=2).first()
            Enrollment.objects.update_or_create(
                user=user,
                course=course,
                defaults={
                    'current_module': module,
                    'progress_pct': 65,
                },
            )
            self.stdout.write(f'  Demo user enrolled in: {course.title}')

        action = 'Created' if created else 'Already exists'
        self.stdout.write(f'  Demo user ({action}): demo_teacher / demo1234')

    def _seed_demo_content_creator(self):
        user, created = User.objects.get_or_create(
            username='demo_creator',
            defaults={
                'first_name': 'Maria',
                'last_name': 'Papadaki',
                'email': 'maria@aidea.example.com',
            },
        )
        if created:
            user.set_password('demo1234')
            user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'user_type': UserProfile.UserType.CONTENT_CREATOR,
                'avatar_initials': 'MP',
            },
        )

        action = 'Created' if created else 'Already exists'
        self.stdout.write(f'  Demo content creator ({action}): demo_creator / demo1234')
