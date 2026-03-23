# Courses assigned to demo_creator for analytics population.
CREATOR_COURSE_TITLES = [
    'Introduction to AI Tools for Teachers',
    'Prompt Engineering for Educators',
    'Teaching AI Ethics and Responsible Use',
    'AI Fundamentals for Educators',
]

# (username, first_name, last_name, initials)
COHORT = [
    ('teacher_sofia',    'Sofia',      'Andreou',        'SA'),
    ('teacher_yannis',   'Yannis',     'Dimitriou',      'YD'),
    ('teacher_elena',    'Elena',      'Papageorgiou',   'EP'),
    ('teacher_kostas',   'Kostas',     'Stavrou',        'KS'),
    ('teacher_maria',    'Maria',      'Nikolaou',       'MN'),
    ('teacher_petros',   'Petros',     'Alexiou',        'PA'),
    ('teacher_anna',     'Anna',       'Christodoulou',  'AC'),
    ('teacher_giorgos',  'Giorgos',    'Papadimitriou',  'GP'),
    ('teacher_katerina', 'Katerina',   'Vassiliadou',    'KV'),
    ('teacher_nikos',    'Nikos',      'Economou',       'NE'),
    ('teacher_thanos',   'Thanos',     'Georgiou',       'TG'),
    ('teacher_ioanna',   'Ioanna',     'Makridou',       'IM'),
    ('teacher_stavros',  'Stavros',    'Tzanetakis',     'ST'),
    ('teacher_dina',     'Dina',       'Papakosta',      'DP'),
    ('teacher_michalis', 'Michalis',   'Koutsouris',     'MK'),
    ('teacher_zoe',      'Zoe',        'Hatzigeorgiou',  'ZH'),
    ('teacher_vasilis',  'Vasilis',    'Sotiropoulos',   'VS'),
    ('teacher_niki',     'Niki',       'Theodorakis',    'NT'),
    ('teacher_spyros',   'Spyros',     'Lambrou',        'SL'),
    ('teacher_chrisa',   'Chrisa',     'Papadaki',       'CP'),
    ('teacher_takis',    'Takis',      'Anagnostopoulos', 'TA'),
    ('teacher_rena',     'Rena',       'Filippidou',     'RF'),
    ('teacher_manolis',  'Manolis',    'Daskalakis',     'MD'),
    ('teacher_olga',     'Olga',       'Karagianni',     'OK'),
    ('teacher_paris',    'Paris',      'Stathopoulos',   'PS'),
]

# Each entry: (teacher_index, stage)
# stage: 'done' = 100%, 'half' = ~50%, 'quarter' = ~25%, 'start' = 0%
COHORT_ENROLLMENTS = {
    'Introduction to AI Tools for Teachers': [
        (0,  'done'), (1,  'done'), (2,  'done'), (3,  'done'), (4,  'done'),
        (5,  'done'), (6,  'done'), (7,  'done'), (8,  'done'), (9,  'done'),
        (10, 'done'), (11, 'done'), (12, 'done'), (13, 'done'), (14, 'done'),
        (15, 'done'), (16, 'done'), (17, 'done'), (18, 'done'), (19, 'done'),
        (20, 'half'), (21, 'half'), (22, 'half'), (23, 'quarter'), (24, 'start'),
    ],
    'Prompt Engineering for Educators': [
        (0,  'done'), (2,  'done'), (4,  'done'), (6,  'done'), (8,  'done'),
        (10, 'done'), (12, 'done'), (14, 'done'), (16, 'done'), (18, 'done'),
        (1,  'half'), (3,  'half'), (5,  'half'), (7,  'half'),
        (9,  'quarter'), (11, 'quarter'), (13, 'start'),
    ],
    'Teaching AI Ethics and Responsible Use': [
        (0,  'done'), (1,  'done'), (2,  'done'), (4,  'done'), (5,  'done'),
        (6,  'done'), (8,  'done'), (10, 'done'), (12, 'done'), (14, 'done'),
        (16, 'done'), (18, 'done'),
        (3,  'half'), (7,  'half'), (9,  'half'), (11, 'half'), (13, 'half'),
        (15, 'quarter'), (17, 'quarter'), (19, 'start'), (20, 'start'),
    ],
    'AI Fundamentals for Educators': [
        (0,  'done'), (3,  'done'), (6,  'done'), (9,  'done'), (12, 'done'),
        (15, 'done'), (18, 'done'), (21, 'done'),
        (1,  'half'), (4,  'half'), (7,  'half'), (10, 'half'),
        (2,  'quarter'), (5,  'quarter'), (8,  'start'), (11, 'start'),
    ],
}
