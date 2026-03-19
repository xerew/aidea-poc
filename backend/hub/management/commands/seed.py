from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from hub.models import Course, Enrollment, LearningPillar, Module, UserProfile

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
                    ('What Is AI? A Teacher-Friendly Primer', 'A jargon-free introduction to artificial intelligence and why it matters for educators.', 45),
                    ('The AI Landscape: Tools Worth Knowing', 'A tour of the most useful AI tools for teachers, from writing assistants to image generators.', 60),
                    ('Evaluating AI Tools for Educational Use', 'Frameworks for assessing AI tools against pedagogical, ethical, and practical criteria.', 50),
                    ('Getting Started: Your First AI-Assisted Lesson', 'A hands-on walkthrough of building a lesson with AI support from start to finish.', 60),
                    ('Responsible Use and School Policies', 'Navigating academic integrity, data privacy, and institutional AI policies.', 45),
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
                    ('How Language Models Work (No Maths Required)', 'An intuitive explanation of how large language models generate text.', 40),
                    ('Anatomy of a Good Prompt', 'Breaking down the components of an effective prompt: role, context, task, and constraints.', 50),
                    ('Prompting for Lesson Plans and Unit Outlines', 'Step-by-step prompting workflows for planning entire units and individual lessons.', 55),
                    ('Differentiation at Scale: Adapting Content with AI', 'Using prompts to adapt texts and tasks for different reading levels and learning profiles.', 55),
                    ('Iterating and Refining AI Output', 'Techniques for improving AI responses through follow-up prompts and editing strategies.', 40),
                    ('Prompt Templates You Can Use Tomorrow', 'A practical library of ready-to-use prompt templates for common teacher tasks.', 40),
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
                    ('The Feedback Gap: Why It Matters', 'Understanding the research on feedback quality and how AI can help close the gap.', 40),
                    ('Generating Rubrics and Marking Criteria with AI', 'Using AI to create detailed, aligned rubrics for any task or subject.', 50),
                    ('Drafting Written Feedback with AI Assistance', 'Workflows for generating personalised feedback comments that teachers can review and send.', 60),
                    ('Formative Assessment: Exit Tickets and Quizzes', 'Creating quick formative assessment tools with AI to check understanding in real time.', 50),
                    ('Academic Integrity in an AI World', 'Strategies for designing assessments that are robust to AI misuse.', 45),
                    ('Keeping the Human in the Loop', 'Principles for maintaining teacher judgement and student relationships when using AI feedback.', 35),
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
                    ('Understanding Your Learners\' Needs', 'Mapping the diversity in your classroom and identifying where AI can add the most value.', 50),
                    ('Adapting Texts and Reading Levels', 'Using AI to rewrite and simplify texts for different reading abilities.', 60),
                    ('Creating Extension and Enrichment Activities', 'Generating challenging extension tasks that push advanced learners further.', 55),
                    ('Supporting EAL and Special Needs Students', 'AI tools and prompting techniques for learners with additional language or learning needs.', 60),
                    ('Building a Differentiation Workflow', 'Designing a repeatable, time-efficient system for AI-powered differentiation.', 55),
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
                    ('Why Data Literacy Matters Now', 'The case for data literacy in the AI age and what it means for K-12 education.', 35),
                    ('Reading Charts, Graphs, and Statistics', 'Teaching students to interpret the most common data visualisation formats.', 50),
                    ('Where Data Comes From and Who Collects It', 'Exploring data collection methods, sources, and the interests behind them.', 45),
                    ('Bias in Data: Real-World Examples', 'Case studies of biased datasets and their impact on AI systems and society.', 50),
                    ('Teaching Data Literacy Across Subjects', 'Integrating data literacy into English, Science, History, and other subjects.', 45),
                    ('Student Projects: Collecting and Analysing Data', 'Project ideas that give students hands-on experience with real data.', 55),
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
                    ('What Are AI Ethics?', 'An introduction to the key ethical principles that guide responsible AI development.', 45),
                    ('Algorithmic Bias: Case Studies for the Classroom', 'Real examples of biased AI systems and classroom activities to explore them.', 60),
                    ('Privacy, Surveillance, and Student Rights', 'How AI is used in surveillance, the data students generate, and their rights.', 55),
                    ('Misinformation, Deepfakes, and Media Literacy', 'Tools and strategies for detecting AI-generated misinformation and deepfakes.', 60),
                    ('The Future of Work and Automation', 'Evidence-based discussion of how AI is changing the labour market.', 50),
                    ('Facilitating Ethical Discussions with Students', 'Practical techniques for running productive, age-appropriate AI ethics discussions.', 50),
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
                    ('The Changing Landscape of Work', 'Research-based overview of how AI is reshaping industries and job roles.', 50),
                    ('Critical Thinking and Problem Solving', 'Practical strategies for teaching higher-order thinking in any subject.', 55),
                    ('Creativity and Collaboration in the AI Era', 'Why human creativity and teamwork are more important than ever, and how to teach them.', 55),
                    ('Adaptability and Lifelong Learning', 'Building learning-to-learn skills and a growth mindset for an uncertain future.', 50),
                    ('Embedding Future-Ready Skills in Your Curriculum', 'Mapping future-ready skills to your existing curriculum and assessment framework.', 50),
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
                    ('A Brief History of Artificial Intelligence', 'From symbolic AI to deep learning: the key milestones and ideas that shaped modern AI.', 40),
                    ('How Machine Learning Works', 'An intuitive explanation of training data, models, and prediction without the maths.', 55),
                    ('Neural Networks: The Big Picture', 'What neural networks are, how they learn, and why they are so powerful.', 55),
                    ('Natural Language Processing Demystified', 'How AI systems understand and generate text, including large language models.', 55),
                    ('Computer Vision and Its Applications', 'How AI sees the world and where it is used in education and everyday life.', 50),
                    ('AI Limitations and Common Misconceptions', 'What AI cannot do, where it fails, and how to talk about it accurately.', 45),
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
                    ('Unplugged AI: Teaching Without Computers', 'The case for unplugged AI education and a toolkit of screen-free activities.', 40),
                    ('Training a Classifier: Sorting and Labelling Activities', 'Hands-on activities that simulate the training of a machine learning classifier.', 50),
                    ('Decision Trees in the Real World', 'Using everyday decisions to teach students how decision tree algorithms work.', 45),
                    ('Pattern Recognition Games for the Classroom', 'Games and puzzles that build intuition for how AI recognises patterns.', 45),
                    ('Age-Appropriate AI Projects (Primary)', 'Guided project ideas for primary students that introduce AI concepts through play.', 50),
                    ('Age-Appropriate AI Projects (Secondary)', 'Structured project ideas for secondary students that go deeper into AI concepts.', 50),
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
                    ('AI in English and Language Arts', 'Using AI to explore authorship, creativity, and language — with ready-to-use lesson ideas.', 60),
                    ('AI in Mathematics', 'Connecting AI and data science to mathematical concepts students already know.', 60),
                    ('AI in Science and STEM', 'How AI is transforming scientific research and what that means for science education.', 60),
                    ('AI in Humanities and Social Sciences', 'Exploring AI\'s social, historical, and ethical dimensions through Humanities subjects.', 55),
                    ('AI in the Arts', 'AI as a creative collaborator: music, visual art, and writing projects for the classroom.', 55),
                    ('Cross-Curricular AI Projects', 'Frameworks for designing and running AI projects that span multiple subject areas.', 50),
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
                    ('Backwards Design for AI Units', 'Starting with learning outcomes and working backwards to activities and assessments.', 60),
                    ('Inquiry-Based Learning and AI', 'Designing open-ended investigations that put students in the role of AI researchers.', 70),
                    ('Aligning AI Topics to Curriculum Standards', 'Mapping AI content to national and international curriculum frameworks.', 65),
                    ('Assessment Strategies for AI Learning', 'Authentic assessment approaches that capture deep learning about AI.', 65),
                    ('Showcasing Student Work: Exhibitions and Portfolios', 'Designing exhibitions and digital portfolios that celebrate student AI learning.', 60),
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed the database with learning pillars, courses, modules, and a demo user.'

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
                for order, (title, description, duration_minutes) in enumerate(modules_data, start=1):
                    Module.objects.update_or_create(
                        title=title,
                        course=course,
                        defaults={
                            'order':            order,
                            'description':      description,
                            'duration_minutes': duration_minutes,
                        },
                    )
                self.stdout.write(f'    Course: {course.title} ({len(modules_data)} modules)')

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
