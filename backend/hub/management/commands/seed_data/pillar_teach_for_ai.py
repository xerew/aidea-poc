from . import shared

PILLAR =     {
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'content': shared.PDF,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
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
                                'content': shared.VID,
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
                                'quiz_data': shared.SAMPLE_QUIZ,
                            },
                        ],
                    },
                ],
            },
        ],
    }
