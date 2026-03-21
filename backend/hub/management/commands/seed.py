from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from hub.models import Course, Enrollment, LearningPillar, Lesson, Module, UserProfile

# Lesson tuples: (title, lesson_type, duration_minutes, is_required)
# Module dicts:  title, description, duration_minutes, lessons

PILLARS = [
    {
        'name': 'Teach with AI',
        'slug': 'teach-with-ai',
        'description': 'Learn to use AI tools, prompting techniques, and classroom workflows to enhance your teaching practice.',
        'order': 1,
        'courses': [
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
                            ('Welcome to the Course', 'video', 5, True),
                            ('What Is Artificial Intelligence?', 'text', 20, True),
                            ('AI in Your Everyday Life', 'text', 12, True),
                            ('Knowledge Check: AI Basics', 'quiz', 8, False),
                        ],
                    },
                    {
                        'title': 'The AI Landscape: Tools Worth Knowing',
                        'description': 'A tour of the most useful AI tools for teachers, from writing assistants to image generators.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('Overview of AI Tools for Educators', 'video', 15, True),
                            ('Writing Assistants and Chatbots', 'text', 20, True),
                            ('Image and Multimedia Generators', 'text', 15, True),
                            ('Tool Comparison Activity', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'Evaluating AI Tools for Educational Use',
                        'description': 'Frameworks for assessing AI tools against pedagogical, ethical, and practical criteria.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Why Evaluation Matters', 'video', 8, True),
                            ('The SAMR Framework Applied to AI', 'text', 20, True),
                            ('Evaluation Rubric (PDF)', 'pdf', 5, True),
                            ('Evaluate a Tool: Guided Assignment', 'assignment', 17, True),
                        ],
                    },
                    {
                        'title': 'Getting Started: Your First AI-Assisted Lesson',
                        'description': 'A hands-on walkthrough of building a lesson with AI support from start to finish.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('Walkthrough: AI-Assisted Lesson Planning', 'video', 20, True),
                            ('Step-by-Step Guide', 'text', 25, True),
                            ('Build Your Own Lesson', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'Responsible Use and School Policies',
                        'description': 'Navigating academic integrity, data privacy, and institutional AI policies.',
                        'duration_minutes': 45,
                        'lessons': [
                            ('Data Privacy and Student Safety', 'text', 18, True),
                            ('Academic Integrity in the AI Age', 'text', 15, True),
                            ('Sample School AI Policy (PDF)', 'pdf', 5, False),
                            ('Policy Reflection Quiz', 'quiz', 7, False),
                        ],
                    },
                ],
            },
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
                            ('Tokens, Predictions, and Probabilities', 'video', 12, True),
                            ('Training Data and What It Means for You', 'text', 18, True),
                            ('Common Misconceptions Quiz', 'quiz', 10, False),
                        ],
                    },
                    {
                        'title': 'Anatomy of a Good Prompt',
                        'description': 'Breaking down the components of an effective prompt: role, context, task, and constraints.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('The Four Elements of a Prompt', 'video', 12, True),
                            ('Role, Context, Task, Constraints — Deep Dive', 'text', 22, True),
                            ('Prompt Anatomy Diagram', 'image', 5, False),
                            ('Rewrite a Weak Prompt', 'assignment', 11, True),
                        ],
                    },
                    {
                        'title': 'Prompting for Lesson Plans and Unit Outlines',
                        'description': 'Step-by-step prompting workflows for planning entire units and individual lessons.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Lesson Plan Prompting Walkthrough', 'video', 18, True),
                            ('Unit Outline Prompt Patterns', 'text', 22, True),
                            ('Generate a Unit Outline', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'Differentiation at Scale: Adapting Content with AI',
                        'description': 'Using prompts to adapt texts and tasks for different reading levels and learning profiles.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Adapting Reading Levels with AI', 'video', 15, True),
                            ('Prompts for Scaffolding and Extension', 'text', 25, True),
                            ('Differentiation Prompt Pack (PDF)', 'pdf', 5, False),
                            ('Adapt a Text for Three Levels', 'assignment', 10, True),
                        ],
                    },
                    {
                        'title': 'Iterating and Refining AI Output',
                        'description': 'Techniques for improving AI responses through follow-up prompts and editing strategies.',
                        'duration_minutes': 40,
                        'lessons': [
                            ('Follow-Up Prompting Strategies', 'video', 10, True),
                            ('When and How to Edit AI Output', 'text', 20, True),
                            ('Iterative Prompting Practice', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'Prompt Templates You Can Use Tomorrow',
                        'description': 'A practical library of ready-to-use prompt templates for common teacher tasks.',
                        'duration_minutes': 40,
                        'lessons': [
                            ('Template Library Overview', 'video', 8, True),
                            ('50 Prompt Templates (PDF)', 'pdf', 5, True),
                            ('Customise a Template for Your Class', 'assignment', 27, False),
                        ],
                    },
                ],
            },
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
                            ('What the Research Says About Feedback', 'video', 12, True),
                            ('The Feedback Gap Explained', 'text', 20, True),
                            ('Reflection: Your Current Feedback Practice', 'assignment', 8, False),
                        ],
                    },
                    {
                        'title': 'Generating Rubrics and Marking Criteria with AI',
                        'description': 'Using AI to create detailed, aligned rubrics for any task or subject.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Rubric Generation Walkthrough', 'video', 15, True),
                            ('Writing Rubric Prompts', 'text', 20, True),
                            ('Create a Rubric for Your Subject', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'Drafting Written Feedback with AI Assistance',
                        'description': 'Workflows for generating personalised feedback comments that teachers can review and send.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('Feedback Drafting Workflow', 'video', 18, True),
                            ('Maintaining Your Voice in AI Feedback', 'text', 22, True),
                            ('Feedback Prompt Templates (PDF)', 'pdf', 5, False),
                            ('Draft Feedback for Sample Student Work', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'Formative Assessment: Exit Tickets and Quizzes',
                        'description': 'Creating quick formative assessment tools with AI to check understanding in real time.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('AI-Generated Exit Tickets', 'video', 10, True),
                            ('Quiz and Poll Prompting Techniques', 'text', 25, True),
                            ('Build a Formative Assessment Bank', 'assignment', 15, False),
                        ],
                    },
                    {
                        'title': 'Academic Integrity in an AI World',
                        'description': 'Strategies for designing assessments that are robust to AI misuse.',
                        'duration_minutes': 45,
                        'lessons': [
                            ('Detection vs. Design: A New Approach', 'video', 15, True),
                            ('Assessment Design Strategies', 'text', 20, True),
                            ('Academic Integrity Policy Guide (PDF)', 'pdf', 5, False),
                            ('Integrity by Design Quiz', 'quiz', 5, False),
                        ],
                    },
                    {
                        'title': 'Keeping the Human in the Loop',
                        'description': 'Principles for maintaining teacher judgement and student relationships when using AI feedback.',
                        'duration_minutes': 35,
                        'lessons': [
                            ('Why Teacher Judgement Still Matters', 'video', 10, True),
                            ('Building Student Trust in AI-Assisted Feedback', 'text', 15, True),
                            ('Personal Commitment Reflection', 'assignment', 10, False),
                        ],
                    },
                ],
            },
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
                            ('Mapping Classroom Diversity', 'video', 15, True),
                            ('Identifying AI Differentiation Opportunities', 'text', 25, True),
                            ('Classroom Diversity Audit', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'Adapting Texts and Reading Levels',
                        'description': 'Using AI to rewrite and simplify texts for different reading abilities.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('Text Adaptation Techniques', 'video', 15, True),
                            ('Prompting for Reading Level Adaptation', 'text', 25, True),
                            ('Adapt a Class Text to Three Levels', 'assignment', 20, True),
                        ],
                    },
                    {
                        'title': 'Creating Extension and Enrichment Activities',
                        'description': 'Generating challenging extension tasks that push advanced learners further.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('What Makes a Good Extension Task?', 'video', 12, True),
                            ('Extension Task Prompt Patterns', 'text', 28, True),
                            ('Design Extension Activities for Your Unit', 'assignment', 15, False),
                        ],
                    },
                    {
                        'title': 'Supporting EAL and Special Needs Students',
                        'description': 'AI tools and prompting techniques for learners with additional language or learning needs.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('AI for EAL Learners: An Overview', 'video', 15, True),
                            ('Scaffolding Techniques and Prompts', 'text', 25, True),
                            ('EAL Resource Prompt Templates (PDF)', 'pdf', 5, False),
                            ('Create Scaffolded Materials', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'Building a Differentiation Workflow',
                        'description': 'Designing a repeatable, time-efficient system for AI-powered differentiation.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Designing Your Workflow', 'video', 15, True),
                            ('Workflow Templates and Time-Saving Tips', 'text', 25, True),
                            ('Build and Document Your Workflow', 'assignment', 15, True),
                        ],
                    },
                ],
            },
        ],
    },
    {
        'name': 'Teach for AI',
        'slug': 'teach-for-ai',
        'description': 'Prepare students for an AI-driven world with data literacy, ethics, responsible AI use, and future-ready skills.',
        'order': 2,
        'courses': [
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
                            ('Data in the AI Age', 'video', 10, True),
                            ('What Data Literacy Means for Students', 'text', 18, True),
                            ('Self-Assessment: Your Data Literacy Starting Point', 'quiz', 7, False),
                        ],
                    },
                    {
                        'title': 'Reading Charts, Graphs, and Statistics',
                        'description': 'Teaching students to interpret the most common data visualisation formats.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Common Chart Types Explained', 'video', 15, True),
                            ('Teaching Students to Read Data', 'text', 22, True),
                            ('Chart Interpretation Activity', 'assignment', 13, True),
                        ],
                    },
                    {
                        'title': 'Where Data Comes From and Who Collects It',
                        'description': 'Exploring data collection methods, sources, and the interests behind them.',
                        'duration_minutes': 45,
                        'lessons': [
                            ('How Data Is Collected', 'video', 12, True),
                            ('Data Sources and Their Biases', 'text', 22, True),
                            ('Data Collection Audit Task', 'assignment', 11, False),
                        ],
                    },
                    {
                        'title': 'Bias in Data: Real-World Examples',
                        'description': 'Case studies of biased datasets and their impact on AI systems and society.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Bias in AI: Three Case Studies', 'video', 18, True),
                            ('The Origins of Dataset Bias', 'text', 20, True),
                            ('Bias Investigation Quiz', 'quiz', 12, True),
                        ],
                    },
                    {
                        'title': 'Teaching Data Literacy Across Subjects',
                        'description': 'Integrating data literacy into English, Science, History, and other subjects.',
                        'duration_minutes': 45,
                        'lessons': [
                            ('Cross-Curricular Data Ideas', 'video', 12, True),
                            ('Subject-Specific Activity Guide', 'text', 20, True),
                            ('Cross-Curricular Lesson Planner (PDF)', 'pdf', 5, False),
                            ('Plan a Data Literacy Lesson', 'assignment', 8, False),
                        ],
                    },
                    {
                        'title': 'Student Projects: Collecting and Analysing Data',
                        'description': 'Project ideas that give students hands-on experience with real data.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Project Design Principles', 'video', 15, True),
                            ('Five Student Data Projects', 'text', 25, True),
                            ('Design Your Own Student Project', 'assignment', 15, False),
                        ],
                    },
                ],
            },
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
                            ('Introduction to AI Ethics', 'video', 12, True),
                            ('The Five Principles of Responsible AI', 'text', 22, True),
                            ('Ethics in Action: Discussion Starter', 'assignment', 11, False),
                        ],
                    },
                    {
                        'title': 'Algorithmic Bias: Case Studies for the Classroom',
                        'description': 'Real examples of biased AI systems and classroom activities to explore them.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('Three Algorithms, Three Biases', 'video', 20, True),
                            ('Running a Bias Case Study in Class', 'text', 25, True),
                            ('Case Study Resource Pack (PDF)', 'pdf', 5, False),
                            ('Class Discussion Facilitator Notes', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'Privacy, Surveillance, and Student Rights',
                        'description': 'How AI is used in surveillance, the data students generate, and their rights.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('AI and Surveillance: What Students Need to Know', 'video', 15, True),
                            ('Student Digital Rights Explained', 'text', 25, True),
                            ('Privacy Audit Activity', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'Misinformation, Deepfakes, and Media Literacy',
                        'description': 'Tools and strategies for detecting AI-generated misinformation and deepfakes.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('Deepfakes and Synthetic Media Explained', 'video', 18, True),
                            ('Detection Strategies and Classroom Tools', 'text', 25, True),
                            ('Spot the Fake: Student Activity', 'assignment', 17, True),
                        ],
                    },
                    {
                        'title': 'The Future of Work and Automation',
                        'description': 'Evidence-based discussion of how AI is changing the labour market.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Which Jobs Are Changing and Why', 'video', 15, True),
                            ('The Evidence on Automation and Employment', 'text', 22, True),
                            ('Future of Work Discussion Quiz', 'quiz', 13, False),
                        ],
                    },
                    {
                        'title': 'Facilitating Ethical Discussions with Students',
                        'description': 'Practical techniques for running productive, age-appropriate AI ethics discussions.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Discussion Facilitation Techniques', 'video', 15, True),
                            ('Age-Appropriate Ethics Frameworks', 'text', 22, True),
                            ('Ethics Discussion Planning Template (PDF)', 'pdf', 5, False),
                            ('Plan and Run an Ethics Discussion', 'assignment', 8, False),
                        ],
                    },
                ],
            },
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
                            ('Industries Being Reshaped by AI', 'video', 15, True),
                            ('What the Research Tells Us', 'text', 25, True),
                            ('Future of Work Reflection', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'Critical Thinking and Problem Solving',
                        'description': 'Practical strategies for teaching higher-order thinking in any subject.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Critical Thinking Frameworks', 'video', 15, True),
                            ('Problem-Solving Strategies for the Classroom', 'text', 25, True),
                            ('Design a Critical Thinking Task', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'Creativity and Collaboration in the AI Era',
                        'description': 'Why human creativity and teamwork are more important than ever, and how to teach them.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Why Human Creativity Still Wins', 'video', 15, True),
                            ('Teaching Collaboration at Scale', 'text', 25, True),
                            ('Creativity and Collaboration Activity Pack (PDF)', 'pdf', 5, False),
                            ('Design a Collaborative Creative Task', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'Adaptability and Lifelong Learning',
                        'description': 'Building learning-to-learn skills and a growth mindset for an uncertain future.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Growth Mindset in Practice', 'video', 12, True),
                            ('Teaching Students to Learn How to Learn', 'text', 25, True),
                            ('Lifelong Learning Self-Assessment', 'quiz', 13, False),
                        ],
                    },
                    {
                        'title': 'Embedding Future-Ready Skills in Your Curriculum',
                        'description': 'Mapping future-ready skills to your existing curriculum and assessment framework.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Curriculum Mapping Overview', 'video', 12, True),
                            ('Skills-to-Curriculum Mapping Guide', 'text', 23, True),
                            ('Map Your Curriculum for Future-Ready Skills', 'assignment', 15, True),
                        ],
                    },
                ],
            },
        ],
    },
    {
        'name': 'Teach about AI',
        'slug': 'teach-about-ai',
        'description': 'Master using AI-generated outputs, lesson enhancement tools, and teaching design innovations to become an AI-confident educator.',
        'order': 3,
        'courses': [
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
                            ('AI Through the Decades', 'video', 15, True),
                            ('Key Milestones in AI History', 'text', 18, True),
                            ('History of AI Knowledge Check', 'quiz', 7, False),
                        ],
                    },
                    {
                        'title': 'How Machine Learning Works',
                        'description': 'An intuitive explanation of training data, models, and prediction without the maths.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Machine Learning Without the Maths', 'video', 18, True),
                            ('Training, Testing, and Predicting', 'text', 25, True),
                            ('ML Concept Diagram', 'image', 5, False),
                            ('Machine Learning Quiz', 'quiz', 7, False),
                        ],
                    },
                    {
                        'title': 'Neural Networks: The Big Picture',
                        'description': 'What neural networks are, how they learn, and why they are so powerful.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('Neurons, Layers, and Weights', 'video', 18, True),
                            ('How Neural Networks Learn', 'text', 25, True),
                            ('Neural Network Visualiser Activity', 'assignment', 12, False),
                        ],
                    },
                    {
                        'title': 'Natural Language Processing Demystified',
                        'description': 'How AI systems understand and generate text, including large language models.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('From Words to Vectors', 'video', 15, True),
                            ('How Large Language Models Work', 'text', 28, True),
                            ('NLP in Practice: Examples', 'assignment', 12, False),
                        ],
                    },
                    {
                        'title': 'Computer Vision and Its Applications',
                        'description': 'How AI sees the world and where it is used in education and everyday life.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('How AI Sees Images', 'video', 15, True),
                            ('Computer Vision in Education and Beyond', 'text', 25, True),
                            ('Computer Vision Examples Gallery', 'image', 5, False),
                            ('Application Spotting Quiz', 'quiz', 5, False),
                        ],
                    },
                    {
                        'title': 'AI Limitations and Common Misconceptions',
                        'description': 'What AI cannot do, where it fails, and how to talk about it accurately.',
                        'duration_minutes': 45,
                        'lessons': [
                            ('The Limits of AI Today', 'video', 15, True),
                            ('Common Misconceptions Debunked', 'text', 20, True),
                            ('Myth-Busting Activity', 'assignment', 10, False),
                        ],
                    },
                ],
            },
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
                            ('Why Unplugged AI Works', 'video', 10, True),
                            ('Unplugged Activity Toolkit', 'text', 20, True),
                            ('Unplugged Activity Resource Pack (PDF)', 'pdf', 5, False),
                            ('Run an Unplugged Activity', 'assignment', 5, False),
                        ],
                    },
                    {
                        'title': 'Training a Classifier: Sorting and Labelling Activities',
                        'description': 'Hands-on activities that simulate the training of a machine learning classifier.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('What Is a Classifier?', 'video', 12, True),
                            ('Sorting and Labelling Games Guide', 'text', 25, True),
                            ('Run a Classroom Sorting Game', 'assignment', 13, True),
                        ],
                    },
                    {
                        'title': 'Decision Trees in the Real World',
                        'description': 'Using everyday decisions to teach students how decision tree algorithms work.',
                        'duration_minutes': 45,
                        'lessons': [
                            ('Decision Trees Explained with Examples', 'video', 15, True),
                            ('Building Decision Trees with Students', 'text', 20, True),
                            ('Decision Tree Activity Worksheet (PDF)', 'pdf', 5, False),
                            ('Student Decision Tree Challenge', 'assignment', 5, False),
                        ],
                    },
                    {
                        'title': 'Pattern Recognition Games for the Classroom',
                        'description': 'Games and puzzles that build intuition for how AI recognises patterns.',
                        'duration_minutes': 45,
                        'lessons': [
                            ('How AI Recognises Patterns', 'video', 12, True),
                            ('Five Pattern Recognition Games', 'text', 22, True),
                            ('Run a Pattern Recognition Game', 'assignment', 11, False),
                        ],
                    },
                    {
                        'title': 'Age-Appropriate AI Projects (Primary)',
                        'description': 'Guided project ideas for primary students that introduce AI concepts through play.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Designing AI Projects for Young Learners', 'video', 12, True),
                            ('Five Primary AI Projects', 'text', 25, True),
                            ('Primary Project Planning Template (PDF)', 'pdf', 5, False),
                            ('Plan a Primary AI Project', 'assignment', 8, False),
                        ],
                    },
                    {
                        'title': 'Age-Appropriate AI Projects (Secondary)',
                        'description': 'Structured project ideas for secondary students that go deeper into AI concepts.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Designing AI Projects for Secondary Students', 'video', 15, True),
                            ('Five Secondary AI Projects', 'text', 25, True),
                            ('Plan a Secondary AI Project', 'assignment', 10, True),
                        ],
                    },
                ],
            },
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
                            ('AI and Authorship: A Discussion Starter', 'video', 15, True),
                            ('AI in the English Classroom', 'text', 30, True),
                            ('English AI Lesson Plans (PDF)', 'pdf', 5, False),
                            ('Design an AI-Themed English Lesson', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'AI in Mathematics',
                        'description': 'Connecting AI and data science to mathematical concepts students already know.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('Where Maths Meets AI', 'video', 15, True),
                            ('Data Science Connections to the Maths Curriculum', 'text', 30, True),
                            ('AI-Themed Maths Activity', 'assignment', 15, True),
                        ],
                    },
                    {
                        'title': 'AI in Science and STEM',
                        'description': 'How AI is transforming scientific research and what that means for science education.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('AI in Scientific Discovery', 'video', 18, True),
                            ('STEM AI Lesson Ideas', 'text', 27, True),
                            ('AI in Science Quiz', 'quiz', 15, False),
                        ],
                    },
                    {
                        'title': 'AI in Humanities and Social Sciences',
                        'description': "Exploring AI's social, historical, and ethical dimensions through Humanities subjects.",
                        'duration_minutes': 55,
                        'lessons': [
                            ('AI Through a Humanities Lens', 'video', 15, True),
                            ('Humanities AI Lesson Ideas', 'text', 28, True),
                            ('Design a Humanities AI Discussion', 'assignment', 12, False),
                        ],
                    },
                    {
                        'title': 'AI in the Arts',
                        'description': 'AI as a creative collaborator: music, visual art, and writing projects for the classroom.',
                        'duration_minutes': 55,
                        'lessons': [
                            ('AI as Creative Collaborator', 'video', 15, True),
                            ('Music, Visual Art, and Writing with AI', 'text', 25, True),
                            ('Student AI Art Gallery Examples', 'image', 5, False),
                            ('Create an AI-Assisted Art Project', 'assignment', 10, False),
                        ],
                    },
                    {
                        'title': 'Cross-Curricular AI Projects',
                        'description': 'Frameworks for designing and running AI projects that span multiple subject areas.',
                        'duration_minutes': 50,
                        'lessons': [
                            ('Cross-Curricular Project Design', 'video', 15, True),
                            ('Project Planning Frameworks', 'text', 22, True),
                            ('Project Planning Template (PDF)', 'pdf', 5, False),
                            ('Plan Your Cross-Curricular AI Project', 'assignment', 8, True),
                        ],
                    },
                ],
            },
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
                            ('The Backwards Design Approach', 'video', 18, True),
                            ('Applying Backwards Design to AI Units', 'text', 27, True),
                            ('Backwards Design Template (PDF)', 'pdf', 5, False),
                            ('Draft Your AI Unit Using Backwards Design', 'assignment', 10, True),
                        ],
                    },
                    {
                        'title': 'Inquiry-Based Learning and AI',
                        'description': 'Designing open-ended investigations that put students in the role of AI researchers.',
                        'duration_minutes': 70,
                        'lessons': [
                            ('What Is Inquiry-Based Learning?', 'video', 15, True),
                            ('Designing AI Inquiry Tasks', 'text', 30, True),
                            ('Student Inquiry Examples', 'image', 5, False),
                            ('Design an AI Inquiry Investigation', 'assignment', 20, True),
                        ],
                    },
                    {
                        'title': 'Aligning AI Topics to Curriculum Standards',
                        'description': 'Mapping AI content to national and international curriculum frameworks.',
                        'duration_minutes': 65,
                        'lessons': [
                            ('Navigating Curriculum Frameworks', 'video', 18, True),
                            ('AI-to-Standards Mapping Guide', 'text', 30, True),
                            ('Standards Mapping Worksheet (PDF)', 'pdf', 5, False),
                            ('Map Your AI Unit to Standards', 'assignment', 12, True),
                        ],
                    },
                    {
                        'title': 'Assessment Strategies for AI Learning',
                        'description': 'Authentic assessment approaches that capture deep learning about AI.',
                        'duration_minutes': 65,
                        'lessons': [
                            ('Why Traditional Tests Fall Short for AI', 'video', 15, True),
                            ('Authentic Assessment Design for AI', 'text', 30, True),
                            ('Assessment Design Workshop', 'assignment', 20, True),
                        ],
                    },
                    {
                        'title': 'Showcasing Student Work: Exhibitions and Portfolios',
                        'description': 'Designing exhibitions and digital portfolios that celebrate student AI learning.',
                        'duration_minutes': 60,
                        'lessons': [
                            ('AI Learning Exhibitions: Inspiration Gallery', 'video', 15, True),
                            ('Designing a Digital Portfolio', 'text', 25, True),
                            ('Exhibition Planning Checklist (PDF)', 'pdf', 5, False),
                            ('Plan Your Student AI Exhibition', 'assignment', 15, False),
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
                    for lesson_order, (l_title, l_type, l_duration, l_required) in enumerate(lessons_data, start=1):
                        Lesson.objects.update_or_create(
                            title=l_title,
                            module=module,
                            defaults={
                                'lesson_type':      l_type,
                                'order':            lesson_order,
                                'duration_minutes': l_duration,
                                'is_required':      l_required,
                            },
                        )
                    total_lessons += len(lessons_data)
                    module_data['lessons'] = lessons_data  # restore

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
