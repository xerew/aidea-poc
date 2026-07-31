# -*- coding: utf-8 -*-
from django.db import migrations

# Translations for the six self-efficacy dimensions and their 24 statements.
# English is the seeded base text; only the 8 other locales are stored here.
# Machine-assisted — recommended to have a native speaker review before using
# the results in research.
DIMENSIONS = {
    'ai-knowledge': {
        'name': {
            'el': 'Γνώση ΤΝ', 'fr': 'Connaissances en IA', 'es': 'Conocimiento de la IA',
            'it': "Conoscenza dell'IA", 'fi': 'Tekoälytietämys', 'sv': 'AI-kunskap',
            'no': 'AI-kunnskap', 'de': 'KI-Wissen',
        },
        'questions': [
            {  # I can distinguish whether a tool is AI-based or not.
                'el': 'Μπορώ να διακρίνω αν ένα εργαλείο βασίζεται σε ΤΝ ή όχι.',
                'fr': "Je peux distinguer si un outil est basé sur l'IA ou non.",
                'es': 'Puedo distinguir si una herramienta se basa en IA o no.',
                'it': "So distinguere se uno strumento è basato sull'IA o no.",
                'fi': 'Osaan erottaa, perustuuko työkalu tekoälyyn vai ei.',
                'sv': 'Jag kan avgöra om ett verktyg är AI-baserat eller inte.',
                'no': 'Jeg kan skille mellom om et verktøy er AI-basert eller ikke.',
                'de': 'Ich kann unterscheiden, ob ein Werkzeug KI-basiert ist oder nicht.',
            },
            {  # I can create content using AI.
                'el': 'Μπορώ να δημιουργώ περιεχόμενο χρησιμοποιώντας ΤΝ.',
                'fr': "Je peux créer du contenu à l'aide de l'IA.",
                'es': 'Puedo crear contenido utilizando IA.',
                'it': "So creare contenuti usando l'IA.",
                'fi': 'Osaan luoda sisältöä tekoälyn avulla.',
                'sv': 'Jag kan skapa innehåll med hjälp av AI.',
                'no': 'Jeg kan lage innhold ved hjelp av AI.',
                'de': 'Ich kann mithilfe von KI Inhalte erstellen.',
            },
            {  # I can explain what artificial intelligence is.
                'el': 'Μπορώ να εξηγήσω τι είναι η τεχνητή νοημοσύνη.',
                'fr': "Je peux expliquer ce qu'est l'intelligence artificielle.",
                'es': 'Puedo explicar qué es la inteligencia artificial.',
                'it': "So spiegare che cos'è l'intelligenza artificiale.",
                'fi': 'Osaan selittää, mitä tekoäly on.',
                'sv': 'Jag kan förklara vad artificiell intelligens är.',
                'no': 'Jeg kan forklare hva kunstig intelligens er.',
                'de': 'Ich kann erklären, was künstliche Intelligenz ist.',
            },
            {  # I know how to choose the right AI tool to complete a task effectively.
                'el': 'Ξέρω πώς να επιλέγω το κατάλληλο εργαλείο ΤΝ για να ολοκληρώσω μια εργασία αποτελεσματικά.',
                'fr': "Je sais choisir le bon outil d'IA pour accomplir une tâche efficacement.",
                'es': 'Sé cómo elegir la herramienta de IA adecuada para completar una tarea de forma eficaz.',
                'it': 'So scegliere lo strumento di IA giusto per completare un compito in modo efficace.',
                'fi': 'Osaan valita oikean tekoälytyökalun tehtävän tehokkaaseen suorittamiseen.',
                'sv': 'Jag vet hur jag väljer rätt AI-verktyg för att utföra en uppgift effektivt.',
                'no': 'Jeg vet hvordan jeg velger riktig AI-verktøy for å utføre en oppgave effektivt.',
                'de': 'Ich weiß, wie ich das richtige KI-Werkzeug auswähle, um eine Aufgabe effektiv zu erledigen.',
            },
        ],
    },
    'ai-pedagogy': {
        'name': {
            'el': 'Παιδαγωγική ΤΝ', 'fr': "Pédagogie de l'IA", 'es': 'Pedagogía de la IA',
            'it': "Pedagogia dell'IA", 'fi': 'Tekoälypedagogiikka', 'sv': 'AI-pedagogik',
            'no': 'AI-pedagogikk', 'de': 'KI-Pädagogik',
        },
        'questions': [
            {
                'el': 'Μπορώ να επιλέξω ένα εργαλείο ΤΝ για την τάξη μου που βελτιώνει το τι διδάσκω, πώς διδάσκω και τι μαθαίνουν οι μαθητές.',
                'fr': "Je peux choisir un outil d'IA pour ma classe qui améliore ce que j'enseigne, comment je l'enseigne et ce que les élèves apprennent.",
                'es': 'Puedo elegir una herramienta de IA para mi aula que mejore qué enseño, cómo enseño y qué aprenden los estudiantes.',
                'it': "So scegliere uno strumento di IA per la mia classe che migliori ciò che insegno, come insegno e ciò che gli studenti imparano.",
                'fi': 'Osaan valita luokkaani tekoälytyökalun, joka parantaa sitä, mitä opetan, miten opetan ja mitä oppilaat oppivat.',
                'sv': 'Jag kan välja ett AI-verktyg för mitt klassrum som förbättrar vad jag undervisar, hur jag undervisar och vad eleverna lär sig.',
                'no': 'Jeg kan velge et AI-verktøy for klasserommet mitt som forbedrer hva jeg underviser i, hvordan jeg underviser, og hva elevene lærer.',
                'de': 'Ich kann für meinen Unterricht ein KI-Werkzeug auswählen, das verbessert, was ich lehre, wie ich lehre und was die Schülerinnen und Schüler lernen.',
            },
            {
                'el': 'Μπορώ να επιλέξω ένα εργαλείο ΤΝ που εμπλουτίζει το γνωστικό περιεχόμενο ενός μαθήματος.',
                'fr': "Je peux choisir un outil d'IA qui enrichit le contenu disciplinaire d'un cours.",
                'es': 'Puedo elegir una herramienta de IA que enriquezca el contenido temático de una lección.',
                'it': "So scegliere uno strumento di IA che arricchisca il contenuto disciplinare di una lezione.",
                'fi': 'Osaan valita tekoälytyökalun, joka rikastuttaa oppitunnin oppiainesisältöä.',
                'sv': 'Jag kan välja ett AI-verktyg som berikar ämnesinnehållet i en lektion.',
                'no': 'Jeg kan velge et AI-verktøy som beriker fagstoffet i en leksjon.',
                'de': 'Ich kann ein KI-Werkzeug auswählen, das den fachlichen Inhalt einer Unterrichtsstunde bereichert.',
            },
            {
                'el': 'Μπορώ να διδάσκω μαθήματα που συνδυάζουν κατάλληλα το γνωστικό περιεχόμενο, τα εργαλεία ΤΝ και τις διδακτικές προσεγγίσεις.',
                'fr': "Je peux enseigner des cours qui combinent de manière appropriée le contenu disciplinaire, les outils d'IA et les approches pédagogiques.",
                'es': 'Puedo impartir lecciones que combinen adecuadamente el contenido temático, las herramientas de IA y los enfoques de enseñanza.',
                'it': "So insegnare lezioni che combinano in modo appropriato il contenuto disciplinare, gli strumenti di IA e gli approcci didattici.",
                'fi': 'Osaan opettaa oppitunteja, joissa oppiainesisältö, tekoälytyökalut ja opetusmenetelmät yhdistyvät tarkoituksenmukaisesti.',
                'sv': 'Jag kan hålla lektioner som på ett lämpligt sätt kombinerar ämnesinnehåll, AI-verktyg och undervisningsmetoder.',
                'no': 'Jeg kan undervise i timer som på en hensiktsmessig måte kombinerer fagstoff, AI-verktøy og undervisningsmetoder.',
                'de': 'Ich kann Unterrichtsstunden halten, die Fachinhalte, KI-Werkzeuge und Lehrmethoden angemessen verbinden.',
            },
            {
                'el': 'Μπορώ να βοηθήσω άλλους εκπαιδευτικούς να συντονίσουν το γνωστικό περιεχόμενο, τα εργαλεία ΤΝ και τις διδακτικές προσεγγίσεις.',
                'fr': "Je peux aider d'autres enseignants à coordonner le contenu disciplinaire, les outils d'IA et les approches pédagogiques.",
                'es': 'Puedo ayudar a otros docentes a coordinar el contenido temático, las herramientas de IA y los enfoques de enseñanza.',
                'it': "So aiutare altri educatori a coordinare il contenuto disciplinare, gli strumenti di IA e gli approcci didattici.",
                'fi': 'Osaan auttaa muita opettajia yhteensovittamaan oppiainesisällön, tekoälytyökalut ja opetusmenetelmät.',
                'sv': 'Jag kan hjälpa andra lärare att samordna ämnesinnehåll, AI-verktyg och undervisningsmetoder.',
                'no': 'Jeg kan hjelpe andre lærere med å samordne fagstoff, AI-verktøy og undervisningsmetoder.',
                'de': 'Ich kann anderen Lehrkräften helfen, Fachinhalte, KI-Werkzeuge und Lehrmethoden aufeinander abzustimmen.',
            },
        ],
    },
    'ai-assessment': {
        'name': {
            'el': 'Αξιολόγηση με ΤΝ', 'fr': "Évaluation par l'IA", 'es': 'Evaluación con IA',
            'it': "Valutazione con l'IA", 'fi': 'Tekoälyavusteinen arviointi', 'sv': 'AI-bedömning',
            'no': 'AI-vurdering', 'de': 'KI-Bewertung',
        },
        'questions': [
            {
                'el': 'Μπορώ να χρησιμοποιώ εργαλεία ΤΝ για να υποστηρίζω την αξιολόγηση για τη μάθηση.',
                'fr': "Je peux utiliser des outils d'IA pour soutenir l'évaluation au service des apprentissages.",
                'es': 'Puedo usar herramientas de IA para apoyar la evaluación para el aprendizaje.',
                'it': "So usare strumenti di IA per sostenere la valutazione per l'apprendimento.",
                'fi': 'Osaan käyttää tekoälytyökaluja oppimista tukevan arvioinnin tukena.',
                'sv': 'Jag kan använda AI-verktyg för att stödja bedömning för lärande.',
                'no': 'Jeg kan bruke AI-verktøy for å støtte vurdering for læring.',
                'de': 'Ich kann KI-Werkzeuge nutzen, um die lernförderliche Beurteilung zu unterstützen.',
            },
            {
                'el': 'Μπορώ να σχεδιάσω μια προσέγγιση αξιολόγησης που βελτιώνει τη μάθηση των μαθητών σε ένα περιβάλλον βασισμένο σε ΤΝ, όπως η μάθηση με το ChatGPT.',
                'fr': "Je peux concevoir une approche d'évaluation qui améliore l'apprentissage des élèves dans un environnement basé sur l'IA, comme l'apprentissage avec ChatGPT.",
                'es': 'Puedo diseñar un enfoque de evaluación que mejore el aprendizaje de los estudiantes en un entorno basado en IA, como aprender con ChatGPT.',
                'it': "So progettare un approccio di valutazione che migliori l'apprendimento degli studenti in un ambiente basato sull'IA, come l'apprendimento con ChatGPT.",
                'fi': 'Osaan suunnitella arviointitavan, joka parantaa oppilaiden oppimista tekoälypohjaisessa ympäristössä, kuten opiskeltaessa ChatGPT:n avulla.',
                'sv': 'Jag kan utforma ett bedömningssätt som förbättrar elevernas lärande i en AI-baserad miljö, till exempel att lära sig med ChatGPT.',
                'no': 'Jeg kan utforme en vurderingsmåte som forbedrer elevenes læring i et AI-basert miljø, for eksempel læring med ChatGPT.',
                'de': 'Ich kann einen Beurteilungsansatz gestalten, der das Lernen der Schülerinnen und Schüler in einer KI-basierten Umgebung verbessert, etwa beim Lernen mit ChatGPT.',
            },
            {
                'el': 'Μπορώ να αξιολογώ τη μάθηση των μαθητών σε ένα περιβάλλον βασισμένο σε ΤΝ.',
                'fr': "Je peux évaluer l'apprentissage des élèves dans un environnement basé sur l'IA.",
                'es': 'Puedo evaluar el aprendizaje de los estudiantes en un entorno basado en IA.',
                'it': "So valutare l'apprendimento degli studenti in un ambiente basato sull'IA.",
                'fi': 'Osaan arvioida oppilaiden oppimista tekoälypohjaisessa ympäristössä.',
                'sv': 'Jag kan bedöma elevernas lärande i en AI-baserad miljö.',
                'no': 'Jeg kan vurdere elevenes læring i et AI-basert miljø.',
                'de': 'Ich kann das Lernen der Schülerinnen und Schüler in einer KI-basierten Umgebung beurteilen.',
            },
            {
                'el': 'Μπορώ να επιλέξω ένα εργαλείο ΤΝ που υποστηρίζει την αυτοαξιολόγηση των μαθητών.',
                'fr': "Je peux choisir un outil d'IA qui soutient l'auto-évaluation des élèves.",
                'es': 'Puedo elegir una herramienta de IA que apoye la autoevaluación de los estudiantes.',
                'it': "So scegliere uno strumento di IA che sostenga l'autovalutazione degli studenti.",
                'fi': 'Osaan valita tekoälytyökalun, joka tukee oppilaiden itsearviointia.',
                'sv': 'Jag kan välja ett AI-verktyg som stödjer elevernas självbedömning.',
                'no': 'Jeg kan velge et AI-verktøy som støtter elevenes egenvurdering.',
                'de': 'Ich kann ein KI-Werkzeug auswählen, das die Selbsteinschätzung der Schülerinnen und Schüler unterstützt.',
            },
        ],
    },
    'ai-ethics': {
        'name': {
            'el': 'Δεοντολογία ΤΝ', 'fr': "Éthique de l'IA", 'es': 'Ética de la IA',
            'it': "Etica dell'IA", 'fi': 'Tekoälyetiikka', 'sv': 'AI-etik',
            'no': 'AI-etikk', 'de': 'KI-Ethik',
        },
        'questions': [
            {
                'el': 'Μπορώ να διδάσκω στους μαθητές για δεοντολογικά ζητήματα που σχετίζονται με την ΤΝ.',
                'fr': "Je peux enseigner aux élèves les questions éthiques liées à l'IA.",
                'es': 'Puedo enseñar a los estudiantes sobre cuestiones éticas relacionadas con la IA.',
                'it': "So insegnare agli studenti le questioni etiche legate all'IA.",
                'fi': 'Osaan opettaa oppilaille tekoälyyn liittyvistä eettisistä kysymyksistä.',
                'sv': 'Jag kan undervisa eleverna om etiska frågor som rör AI.',
                'no': 'Jeg kan undervise elevene om etiske spørsmål knyttet til AI.',
                'de': 'Ich kann Schülerinnen und Schülern ethische Fragen im Zusammenhang mit KI vermitteln.',
            },
            {
                'el': 'Μπορώ να προστατεύω ευαίσθητες πληροφορίες από εργαλεία ΤΝ, όπως εξετάσεις, βαθμούς μαθητών και προσωπικά δεδομένα.',
                'fr': "Je peux protéger les informations sensibles vis-à-vis des outils d'IA, notamment les examens, les notes des élèves et les données personnelles.",
                'es': 'Puedo proteger la información sensible frente a las herramientas de IA, incluidos los exámenes, las calificaciones de los estudiantes y los datos personales.',
                'it': "So proteggere le informazioni sensibili dagli strumenti di IA, compresi esami, voti degli studenti e dati personali.",
                'fi': 'Osaan suojata arkaluontoiset tiedot tekoälytyökaluilta, mukaan lukien kokeet, oppilaiden arvosanat ja henkilötiedot.',
                'sv': 'Jag kan skydda känslig information från AI-verktyg, inklusive prov, elevers betyg och personuppgifter.',
                'no': 'Jeg kan beskytte sensitiv informasjon mot AI-verktøy, inkludert eksamener, elevkarakterer og personopplysninger.',
                'de': 'Ich kann sensible Informationen vor KI-Werkzeugen schützen, einschließlich Prüfungen, Schülernoten und personenbezogener Daten.',
            },
            {
                'el': 'Μπορώ να διατηρώ την υγεία και την ευεξία μου ενώ χρησιμοποιώ εργαλεία ΤΝ.',
                'fr': "Je peux préserver ma santé et mon bien-être tout en utilisant des outils d'IA.",
                'es': 'Puedo mantener mi salud y bienestar mientras uso herramientas de IA.',
                'it': 'So mantenere la mia salute e il mio benessere mentre uso strumenti di IA.',
                'fi': 'Osaan huolehtia terveydestäni ja hyvinvoinnistani käyttäessäni tekoälytyökaluja.',
                'sv': 'Jag kan bevara min hälsa och mitt välbefinnande när jag använder AI-verktyg.',
                'no': 'Jeg kan ivareta min helse og mitt velvære mens jeg bruker AI-verktøy.',
                'de': 'Ich kann meine Gesundheit und mein Wohlbefinden bewahren, während ich KI-Werkzeuge nutze.',
            },
            {
                'el': 'Μπορώ να διδάσκω στους μαθητές πώς να συμπεριφέρονται με ασφάλεια και υπευθυνότητα όταν μαθαίνουν με εργαλεία ΤΝ.',
                'fr': "Je peux apprendre aux élèves à se comporter de manière sûre et responsable lorsqu'ils apprennent avec des outils d'IA.",
                'es': 'Puedo enseñar a los estudiantes a comportarse de forma segura y responsable cuando aprenden con herramientas de IA.',
                'it': 'So insegnare agli studenti a comportarsi in modo sicuro e responsabile quando imparano con strumenti di IA.',
                'fi': 'Osaan opettaa oppilaille, kuinka toimia turvallisesti ja vastuullisesti oppiessaan tekoälytyökalujen avulla.',
                'sv': 'Jag kan lära eleverna att bete sig säkert och ansvarsfullt när de lär sig med AI-verktyg.',
                'no': 'Jeg kan lære elevene å oppføre seg trygt og ansvarlig når de lærer med AI-verktøy.',
                'de': 'Ich kann Schülerinnen und Schülern beibringen, sich beim Lernen mit KI-Werkzeugen sicher und verantwortungsvoll zu verhalten.',
            },
        ],
    },
    'human-centred-education': {
        'name': {
            'el': 'Ανθρωποκεντρική Εκπαίδευση', 'fr': "Éducation centrée sur l'humain",
            'es': 'Educación centrada en el ser humano', 'it': "Educazione centrata sull'essere umano",
            'fi': 'Ihmiskeskeinen opetus', 'sv': 'Människocentrerad utbildning',
            'no': 'Menneskesentrert utdanning', 'de': 'Menschzentrierte Bildung',
        },
        'questions': [
            {
                'el': 'Μπορώ να αξιολογώ τα οφέλη ενός εργαλείου ΤΝ.',
                'fr': "Je peux évaluer les avantages d'un outil d'IA.",
                'es': 'Puedo evaluar los beneficios de una herramienta de IA.',
                'it': 'So valutare i vantaggi di uno strumento di IA.',
                'fi': 'Osaan arvioida tekoälytyökalun hyötyjä.',
                'sv': 'Jag kan bedöma fördelarna med ett AI-verktyg.',
                'no': 'Jeg kan vurdere fordelene ved et AI-verktøy.',
                'de': 'Ich kann den Nutzen eines KI-Werkzeugs bewerten.',
            },
            {
                'el': 'Μπορώ να αξιολογώ τους κινδύνους ενός εργαλείου ΤΝ.',
                'fr': "Je peux évaluer les risques d'un outil d'IA.",
                'es': 'Puedo evaluar los riesgos de una herramienta de IA.',
                'it': 'So valutare i rischi di uno strumento di IA.',
                'fi': 'Osaan arvioida tekoälytyökalun riskejä.',
                'sv': 'Jag kan bedöma riskerna med ett AI-verktyg.',
                'no': 'Jeg kan vurdere risikoene ved et AI-verktøy.',
                'de': 'Ich kann die Risiken eines KI-Werkzeugs bewerten.',
            },
            {
                'el': 'Αναγνωρίζω ότι οι άνθρωποι είναι υπεύθυνοι για τον εντοπισμό και την αντιμετώπιση της μεροληψίας της ΤΝ.',
                'fr': "Je reconnais que ce sont les humains qui ont la responsabilité d'identifier et de corriger les biais de l'IA.",
                'es': 'Reconozco que las personas son responsables de identificar y abordar los sesgos de la IA.',
                'it': "Riconosco che sono gli esseri umani a essere responsabili di individuare e affrontare i pregiudizi (bias) dell'IA.",
                'fi': 'Tunnistan, että ihmiset ovat vastuussa tekoälyn vinoumien tunnistamisesta ja käsittelemisestä.',
                'sv': 'Jag inser att människor är ansvariga för att identifiera och hantera AI-bias.',
                'no': 'Jeg erkjenner at mennesker er ansvarlige for å identifisere og håndtere skjevheter (bias) i AI.',
                'de': 'Ich erkenne an, dass Menschen dafür verantwortlich sind, Verzerrungen (Bias) der KI zu erkennen und zu beheben.',
            },
            {
                'el': 'Μπορώ να εξηγήσω πώς η ΤΝ επηρεάζει την κοινωνία.',
                'fr': "Je peux expliquer comment l'IA affecte la société.",
                'es': 'Puedo explicar cómo la IA afecta a la sociedad.',
                'it': "So spiegare come l'IA influisce sulla società.",
                'fi': 'Osaan selittää, miten tekoäly vaikuttaa yhteiskuntaan.',
                'sv': 'Jag kan förklara hur AI påverkar samhället.',
                'no': 'Jeg kan forklare hvordan AI påvirker samfunnet.',
                'de': 'Ich kann erklären, wie KI die Gesellschaft beeinflusst.',
            },
        ],
    },
    'professional-engagement': {
        'name': {
            'el': 'Επαγγελματική Συμμετοχή', 'fr': 'Engagement professionnel',
            'es': 'Compromiso profesional', 'it': 'Impegno professionale',
            'fi': 'Ammatillinen osallistuminen', 'sv': 'Professionellt engagemang',
            'no': 'Profesjonelt engasjement', 'de': 'Berufliches Engagement',
        },
        'questions': [
            {
                'el': 'Μπορώ να χρησιμοποιώ διαφορετικούς ιστότοπους και στρατηγικές αναζήτησης για να βρίσκω και να επιλέγω κατάλληλα εργαλεία ΤΝ.',
                'fr': "Je peux utiliser différents sites web et stratégies de recherche pour trouver et sélectionner des outils d'IA appropriés.",
                'es': 'Puedo usar diferentes sitios web y estrategias de búsqueda para encontrar y seleccionar herramientas de IA adecuadas.',
                'it': 'So usare diversi siti web e strategie di ricerca per trovare e selezionare strumenti di IA appropriati.',
                'fi': 'Osaan käyttää eri verkkosivustoja ja hakustrategioita löytääkseni ja valitakseni sopivia tekoälytyökaluja.',
                'sv': 'Jag kan använda olika webbplatser och sökstrategier för att hitta och välja lämpliga AI-verktyg.',
                'no': 'Jeg kan bruke ulike nettsteder og søkestrategier for å finne og velge egnede AI-verktøy.',
                'de': 'Ich kann verschiedene Websites und Suchstrategien nutzen, um geeignete KI-Werkzeuge zu finden und auszuwählen.',
            },
            {
                'el': 'Αναζητώ ενεργά δραστηριότητες συνεχούς επαγγελματικής ανάπτυξης εκτός του εκπαιδευτικού μου οργανισμού.',
                'fr': "Je recherche activement des activités de développement professionnel continu en dehors de mon établissement scolaire.",
                'es': 'Busco activamente actividades de desarrollo profesional continuo fuera de mi organización educativa.',
                'it': 'Cerco attivamente attività di sviluppo professionale continuo al di fuori della mia organizzazione educativa.',
                'fi': 'Etsin aktiivisesti jatkuvan ammatillisen kehittymisen toimintaa oman oppilaitokseni ulkopuolelta.',
                'sv': 'Jag söker aktivt efter kontinuerlig kompetensutveckling utanför min utbildningsorganisation.',
                'no': 'Jeg søker aktivt etter aktiviteter for kontinuerlig faglig utvikling utenfor min utdanningsorganisasjon.',
                'de': 'Ich suche aktiv nach Angeboten zur kontinuierlichen beruflichen Weiterentwicklung außerhalb meiner Bildungseinrichtung.',
            },
            {
                'el': 'Μοιράζομαι ενεργά τις εμπειρίες μου από τη διδασκαλία με ΤΝ με συναδέλφους εντός και εκτός του εκπαιδευτικού μου οργανισμού.',
                'fr': "Je partage activement mes expériences d'enseignement avec l'IA avec des collègues au sein et en dehors de mon établissement scolaire.",
                'es': 'Comparto activamente mis experiencias de enseñanza con IA con colegas dentro y fuera de mi organización educativa.',
                'it': "Condivido attivamente le mie esperienze di insegnamento con l'IA con colleghi all'interno e all'esterno della mia organizzazione educativa.",
                'fi': 'Jaan aktiivisesti tekoälyyn liittyviä opetuskokemuksiani kollegoille oman oppilaitokseni sisällä ja ulkopuolella.',
                'sv': 'Jag delar aktivt mina erfarenheter av att undervisa med AI med kollegor inom och utanför min utbildningsorganisation.',
                'no': 'Jeg deler aktivt mine erfaringer med å undervise med AI med kolleger i og utenfor min utdanningsorganisasjon.',
                'de': 'Ich teile meine Erfahrungen beim Unterrichten mit KI aktiv mit Kolleginnen und Kollegen innerhalb und außerhalb meiner Bildungseinrichtung.',
            },
            {
                'el': 'Είμαι πρόθυμος/η να βοηθήσω συναδέλφους να σχεδιάσουν μαθησιακές δραστηριότητες που χρησιμοποιούν ΤΝ.',
                'fr': "Je suis disposé(e) à aider mes collègues à concevoir des activités d'apprentissage utilisant l'IA.",
                'es': 'Estoy dispuesto/a a ayudar a mis colegas a diseñar actividades de aprendizaje que utilicen IA.',
                'it': "Sono disposto/a ad aiutare i colleghi a progettare attività di apprendimento che usano l'IA.",
                'fi': 'Olen valmis auttamaan kollegoita suunnittelemaan tekoälyä hyödyntäviä oppimistoimintoja.',
                'sv': 'Jag är villig att hjälpa kollegor att utforma lärandeaktiviteter som använder AI.',
                'no': 'Jeg er villig til å hjelpe kolleger med å utforme læringsaktiviteter som bruker AI.',
                'de': 'Ich bin bereit, Kolleginnen und Kollegen bei der Gestaltung von Lernaktivitäten zu unterstützen, die KI nutzen.',
            },
        ],
    },
}


def apply(apps, schema_editor):
    Dimension = apps.get_model('hub', 'OnboardingDimension')
    for slug, data in DIMENSIONS.items():
        try:
            dim = Dimension.objects.get(slug=slug)
        except Dimension.DoesNotExist:
            continue
        dim.translations = data['name']
        dim.save(update_fields=['translations'])
        questions = list(dim.questions.filter(is_active=True).order_by('order'))
        for question, translations in zip(questions, data['questions']):
            question.translations = translations
            question.save(update_fields=['translations'])


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0045_userprofile_self_efficacy_draft_and_more'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
