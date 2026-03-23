from . import shared

PILLAR =     {
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.IMG,
                            },
                            {
                                'title': 'Machine Learning Quiz',
                                'type': 'quiz', 'duration': 7, 'required': False,
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.IMG,
                            },
                            {
                                'title': 'Application Spotting Quiz',
                                'type': 'quiz', 'duration': 5, 'required': False,
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.IMG,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.IMG,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
        ],
    }
