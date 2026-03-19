from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from hub.models import UserProfile, LearningPillar, Course, Module, Enrollment


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
                'modules': [
                    'What Is AI? A Teacher-Friendly Primer',
                    'The AI Landscape: Tools Worth Knowing',
                    'Evaluating AI Tools for Educational Use',
                    'Getting Started: Your First AI-Assisted Lesson',
                    'Responsible Use and School Policies',
                ],
            },
            {
                'title': 'Prompt Engineering for Educators',
                'description': 'Master the art of writing effective prompts to get the most out of AI assistants for lesson planning, differentiation, and content creation.',
                'modules': [
                    'How Language Models Work (No Maths Required)',
                    'Anatomy of a Good Prompt',
                    'Prompting for Lesson Plans and Unit Outlines',
                    'Differentiation at Scale: Adapting Content with AI',
                    'Iterating and Refining AI Output',
                    'Prompt Templates You Can Use Tomorrow',
                ],
            },
            {
                'title': 'AI-Powered Assessment and Feedback',
                'description': 'Use AI to provide faster, more consistent feedback to students and streamline your assessment workflows without sacrificing quality.',
                'modules': [
                    'The Feedback Gap: Why It Matters',
                    'Generating Rubrics and Marking Criteria with AI',
                    'Drafting Written Feedback with AI Assistance',
                    'Formative Assessment: Exit Tickets and Quizzes',
                    'Academic Integrity in an AI World',
                    'Keeping the Human in the Loop',
                ],
            },
            {
                'title': 'AI for Classroom Differentiation',
                'description': 'Leverage AI to personalise learning materials for diverse classrooms — adapting reading levels, creating extension tasks, and supporting EAL learners.',
                'modules': [
                    'Understanding Your Learners\' Needs',
                    'Adapting Texts and Reading Levels',
                    'Creating Extension and Enrichment Activities',
                    'Supporting EAL and Special Needs Students',
                    'Building a Differentiation Workflow',
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
                'modules': [
                    'Why Data Literacy Matters Now',
                    'Reading Charts, Graphs, and Statistics',
                    'Where Data Comes From and Who Collects It',
                    'Bias in Data: Real-World Examples',
                    'Teaching Data Literacy Across Subjects',
                    'Student Projects: Collecting and Analysing Data',
                ],
            },
            {
                'title': 'Teaching AI Ethics and Responsible Use',
                'description': 'Equip students with the ethical frameworks to navigate AI responsibly — covering bias, privacy, misinformation, and the societal impact of automation.',
                'modules': [
                    'What Are AI Ethics?',
                    'Algorithmic Bias: Case Studies for the Classroom',
                    'Privacy, Surveillance, and Student Rights',
                    'Misinformation, Deepfakes, and Media Literacy',
                    'The Future of Work and Automation',
                    'Facilitating Ethical Discussions with Students',
                ],
            },
            {
                'title': 'Future-Ready Skills: Preparing Students for an AI World',
                'description': 'Understand which skills will matter most in an AI-augmented workforce and how to weave them into your existing curriculum.',
                'modules': [
                    'The Changing Landscape of Work',
                    'Critical Thinking and Problem Solving',
                    'Creativity and Collaboration in the AI Era',
                    'Adaptability and Lifelong Learning',
                    'Embedding Future-Ready Skills in Your Curriculum',
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
                'modules': [
                    'A Brief History of Artificial Intelligence',
                    'How Machine Learning Works',
                    'Neural Networks: The Big Picture',
                    'Natural Language Processing Demystified',
                    'Computer Vision and Its Applications',
                    'AI Limitations and Common Misconceptions',
                ],
            },
            {
                'title': 'Teaching AI Concepts Without Code',
                'description': 'A toolkit of unplugged activities, analogies, and project ideas to teach AI concepts to primary and secondary students without requiring programming knowledge.',
                'modules': [
                    'Unplugged AI: Teaching Without Computers',
                    'Training a Classifier: Sorting and Labelling Activities',
                    'Decision Trees in the Real World',
                    'Pattern Recognition Games for the Classroom',
                    'Age-Appropriate AI Projects (Primary)',
                    'Age-Appropriate AI Projects (Secondary)',
                ],
            },
            {
                'title': 'AI Across the Curriculum',
                'description': 'Discover how AI connects to every subject area and find ready-to-use lesson ideas for English, Maths, Science, Humanities, and the Arts.',
                'modules': [
                    'AI in English and Language Arts',
                    'AI in Mathematics',
                    'AI in Science and STEM',
                    'AI in Humanities and Social Sciences',
                    'AI in the Arts',
                    'Cross-Curricular AI Projects',
                ],
            },
            {
                'title': 'Designing AI Learning Experiences',
                'description': 'Learn instructional design principles for creating engaging, inquiry-based AI units that meet curriculum standards and spark student curiosity.',
                'modules': [
                    'Backwards Design for AI Units',
                    'Inquiry-Based Learning and AI',
                    'Aligning AI Topics to Curriculum Standards',
                    'Assessment Strategies for AI Learning',
                    'Showcasing Student Work: Exhibitions and Portfolios',
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
                    defaults={'description': course_data['description']},
                )
                for order, module_title in enumerate(modules_data, start=1):
                    Module.objects.update_or_create(
                        title=module_title,
                        course=course,
                        defaults={'order': order},
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

        # Enroll demo user in one course with some progress
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
