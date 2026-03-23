from . import shared

PILLAR =     {
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.PDF,
                            },
                            {
                                'title': 'Policy Reflection Quiz',
                                'type': 'quiz', 'duration': 7, 'required': False,
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.IMG,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
                            },
                            {
                                'title': '50 Prompt Templates (PDF)',
                                'type': 'pdf', 'duration': 5, 'required': True,
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
                            },
                            {
                                'title': 'Integrity by Design Quiz',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
        ],
    }
