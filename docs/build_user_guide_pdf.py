"""Render the localized user guides into styled PDFs served by the frontend.

Run it with uv so the dependencies stay out of the project environment:

    uv run --with markdown-pdf python docs/build_user_guide_pdf.py

English is the canonical source (docs/user-guide.md); each other language is
docs/user-guide.<lang>.md. Output: frontend/public/aidea-user-guide.<lang>.pdf,
plus aidea-user-guide.pdf as the English fallback the app defaults to.
"""
import re
import shutil
from pathlib import Path

from markdown_pdf import MarkdownPdf, Section

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LOGO_DIR = ROOT / "frontend" / "public" / "images" / "logos"
OUT_DIR = ROOT / "frontend" / "public"

LANGS = ["en", "el", "fr", "es", "it", "fi", "sv", "no", "de"]

# Cover page per language — logo + who the project is. Sourced from aideaacademy.eu.
COVERS = {
    "en": """
![AIDEA](aidea-logo.png)

# AIDEA User Guide

### The AI‑Driven Educators Academy

The AI‑Driven Educators Academy (AIDEA) redefines how artificial intelligence
integrates into European teacher education. Unifying research from leading
Erasmus+ and Horizon Europe initiatives, AIDEA offers a modular,
research‑backed training framework that moves beyond conventional teacher
preparation — treating AI not just as a tool, but as a catalyst for
pedagogical transformation.

**The three pillars**

- **Teaching About AI** — building educator AI literacy and ethical awareness.
- **Teaching With AI** — equipping teachers with AI tools for formative
  assessment and adaptive learning.
- **Teaching For AI** — preparing students for an AI‑driven future through
  critical thinking.

_Funded by the European Union through the Erasmus+ and Horizon Europe
programmes._
""",
    "el": """
![AIDEA](aidea-logo.png)

# Οδηγός Χρήστη AIDEA

### The AI‑Driven Educators Academy

Η Ακαδημία Εκπαιδευτικών με Γνώμονα την ΤΝ (AIDEA) επαναπροσδιορίζει τον τρόπο
με τον οποίο η τεχνητή νοημοσύνη ενσωματώνεται στην ευρωπαϊκή εκπαίδευση
εκπαιδευτικών. Ενοποιώντας έρευνα από κορυφαίες πρωτοβουλίες Erasmus+ και
Horizon Europe, η AIDEA προσφέρει ένα αρθρωτό, ερευνητικά τεκμηριωμένο πλαίσιο
κατάρτισης που ξεπερνά τη συμβατική προετοιμασία εκπαιδευτικών — αντιμετωπίζοντας
την ΤΝ όχι απλώς ως εργαλείο, αλλά ως καταλύτη παιδαγωγικού μετασχηματισμού.

**Οι τρεις πυλώνες**

- **Διδασκαλία για την ΤΝ** — οικοδόμηση ψηφιακού γραμματισμού και ηθικής
  επίγνωσης των εκπαιδευτικών σχετικά με την ΤΝ.
- **Διδασκαλία με την ΤΝ** — εφοδιασμός των εκπαιδευτικών με εργαλεία ΤΝ για
  διαμορφωτική αξιολόγηση και προσαρμοστική μάθηση.
- **Διδασκαλία εν όψει της ΤΝ** — προετοιμασία των μαθητών για ένα μέλλον με
  γνώμονα την ΤΝ μέσα από την κριτική σκέψη.

_Χρηματοδοτείται από την Ευρωπαϊκή Ένωση μέσω των προγραμμάτων Erasmus+ και
Horizon Europe._
""",
    "fr": """
![AIDEA](aidea-logo.png)

# Guide de l'utilisateur AIDEA

### The AI‑Driven Educators Academy

L'Académie des Éducateurs Guidés par l'IA (AIDEA) redéfinit la manière dont
l'intelligence artificielle s'intègre à la formation des enseignants en Europe.
En unifiant les recherches des principales initiatives Erasmus+ et Horizon
Europe, AIDEA propose un cadre de formation modulaire et fondé sur la recherche
qui dépasse la préparation classique des enseignants — en traitant l'IA non pas
seulement comme un outil, mais comme un catalyseur de transformation pédagogique.

**Les trois piliers**

- **Enseigner l'IA** — développer la littératie en IA et la conscience éthique
  des enseignants.
- **Enseigner avec l'IA** — doter les enseignants d'outils d'IA pour
  l'évaluation formative et l'apprentissage adaptatif.
- **Enseigner pour l'IA** — préparer les élèves à un avenir façonné par l'IA
  grâce à l'esprit critique.

_Financé par l'Union européenne dans le cadre des programmes Erasmus+ et Horizon
Europe._
""",
    "es": """
![AIDEA](aidea-logo.png)

# Guía del usuario de AIDEA

### The AI‑Driven Educators Academy

La Academia de Educadores Impulsada por la IA (AIDEA) redefine cómo se integra
la inteligencia artificial en la formación del profesorado en Europa. Unificando
la investigación de las principales iniciativas Erasmus+ y Horizon Europe, AIDEA
ofrece un marco de formación modular y basado en la investigación que va más allá
de la preparación docente convencional, tratando la IA no solo como una
herramienta, sino como un catalizador de transformación pedagógica.

**Los tres pilares**

- **Enseñar sobre la IA** — desarrollar la alfabetización en IA y la conciencia
  ética del profesorado.
- **Enseñar con la IA** — dotar al profesorado de herramientas de IA para la
  evaluación formativa y el aprendizaje adaptativo.
- **Enseñar para la IA** — preparar al alumnado para un futuro marcado por la IA
  mediante el pensamiento crítico.

_Financiado por la Unión Europea a través de los programas Erasmus+ y Horizon
Europe._
""",
    "it": """
![AIDEA](aidea-logo.png)

# Guida utente di AIDEA

### The AI‑Driven Educators Academy

L'Accademia degli Educatori Guidati dall'IA (AIDEA) ridefinisce il modo in cui
l'intelligenza artificiale si integra nella formazione degli insegnanti in
Europa. Unificando la ricerca delle principali iniziative Erasmus+ e Horizon
Europe, AIDEA offre un quadro formativo modulare e basato sulla ricerca che va
oltre la preparazione convenzionale degli insegnanti, trattando l'IA non solo
come uno strumento, ma come un catalizzatore di trasformazione pedagogica.

**I tre pilastri**

- **Insegnare l'IA** — sviluppare l'alfabetizzazione all'IA e la consapevolezza
  etica degli insegnanti.
- **Insegnare con l'IA** — fornire agli insegnanti strumenti di IA per la
  valutazione formativa e l'apprendimento adattivo.
- **Insegnare per l'IA** — preparare gli studenti a un futuro plasmato dall'IA
  attraverso il pensiero critico.

_Finanziato dall'Unione europea tramite i programmi Erasmus+ e Horizon Europe._
""",
    "fi": """
![AIDEA](aidea-logo.png)

# AIDEA-käyttöopas

### The AI‑Driven Educators Academy

Tekoälyvetoinen opettajien akatemia (AIDEA) määrittelee uudelleen sen, miten
tekoäly integroituu eurooppalaiseen opettajankoulutukseen. Yhdistämällä johtavien
Erasmus+- ja Horizon Europe -hankkeiden tutkimusta AIDEA tarjoaa modulaarisen,
tutkimukseen perustuvan koulutuskehyksen, joka ylittää perinteisen
opettajankoulutuksen — kohdellen tekoälyä ei pelkkänä työkaluna vaan pedagogisen
muutoksen katalyyttinä.

**Kolme pilaria**

- **Tekoälystä opettaminen** — opettajien tekoälylukutaidon ja eettisen
  tietoisuuden rakentaminen.
- **Tekoälyn avulla opettaminen** — opettajien varustaminen tekoälytyökaluilla
  formatiivista arviointia ja mukautuvaa oppimista varten.
- **Tekoälyä varten opettaminen** — oppilaiden valmistaminen tekoälyvetoiseen
  tulevaisuuteen kriittisen ajattelun avulla.

_Rahoittaa Euroopan unioni Erasmus+- ja Horizon Europe -ohjelmien kautta._
""",
    "sv": """
![AIDEA](aidea-logo.png)

# AIDEA-användarguide

### The AI‑Driven Educators Academy

AI‑drivna lärarakademin (AIDEA) omdefinierar hur artificiell intelligens
integreras i den europeiska lärarutbildningen. Genom att förena forskning från
ledande Erasmus+- och Horizon Europe-initiativ erbjuder AIDEA ett modulärt,
forskningsbaserat utbildningsramverk som går bortom konventionell lärarutbildning
— och behandlar AI inte bara som ett verktyg, utan som en katalysator för
pedagogisk förändring.

**De tre pelarna**

- **Undervisa om AI** — bygga lärares AI-litteracitet och etiska medvetenhet.
- **Undervisa med AI** — utrusta lärare med AI-verktyg för formativ bedömning
  och adaptivt lärande.
- **Undervisa för AI** — förbereda elever för en AI-driven framtid genom
  kritiskt tänkande.

_Finansieras av Europeiska unionen genom programmen Erasmus+ och Horizon Europe._
""",
    "no": """
![AIDEA](aidea-logo.png)

# AIDEA-brukerveiledning

### The AI‑Driven Educators Academy

AI‑drevne lærerakademiet (AIDEA) omdefinerer hvordan kunstig intelligens
integreres i europeisk lærerutdanning. Ved å forene forskning fra ledende
Erasmus+- og Horizon Europe-initiativer tilbyr AIDEA et modulært,
forskningsbasert opplæringsrammeverk som går utover konvensjonell
lærerutdanning — og behandler KI ikke bare som et verktøy, men som en
katalysator for pedagogisk endring.

**De tre pilarene**

- **Undervise om KI** — bygge læreres KI-kompetanse og etiske bevissthet.
- **Undervise med KI** — utstyre lærere med KI-verktøy for formativ vurdering
  og adaptiv læring.
- **Undervise for KI** — forberede elever på en KI-drevet framtid gjennom
  kritisk tenkning.

_Finansiert av Den europeiske union gjennom programmene Erasmus+ og Horizon
Europe._
""",
    "de": """
![AIDEA](aidea-logo.png)

# AIDEA-Benutzerhandbuch

### The AI‑Driven Educators Academy

Die KI‑gesteuerte Akademie für Lehrkräfte (AIDEA) definiert neu, wie künstliche
Intelligenz in die europäische Lehrkräftebildung integriert wird. Durch die
Bündelung von Forschung aus führenden Erasmus+- und Horizont-Europa-Initiativen
bietet AIDEA einen modularen, forschungsbasierten Ausbildungsrahmen, der über die
herkömmliche Lehrkräftevorbereitung hinausgeht — und KI nicht nur als Werkzeug,
sondern als Katalysator für pädagogische Transformation begreift.

**Die drei Säulen**

- **Über KI unterrichten** — Aufbau von KI-Kompetenz und ethischem Bewusstsein
  der Lehrkräfte.
- **Mit KI unterrichten** — Ausstattung der Lehrkräfte mit KI-Werkzeugen für
  formative Bewertung und adaptives Lernen.
- **Für KI unterrichten** — Vorbereitung der Schülerinnen und Schüler auf eine
  KI-geprägte Zukunft durch kritisches Denken.

_Gefördert von der Europäischen Union über die Programme Erasmus+ und Horizont
Europa._
""",
}

CSS = """
body { font-family: 'Helvetica', 'Arial', sans-serif; color: #1f2937; line-height: 1.55; }
h1 { color: #1d4ed8; font-size: 26pt; margin: 0.2em 0; }
h2 { color: #1d4ed8; font-size: 16pt; border-bottom: 1px solid #dbeafe; padding-bottom: 4px; margin-top: 1.4em; }
h3 { color: #2563eb; font-size: 13pt; }
img { display: block; margin: 0 auto 1.2em; width: 240px; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0; }
th, td { border: 1px solid #d1d5db; padding: 6px 9px; text-align: left; font-size: 10pt; }
th { background: #eff6ff; }
code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
a { color: #1d4ed8; }
"""


def source_md(lang):
    return DOCS / ("user-guide.md" if lang == "en" else f"user-guide.{lang}.md")


def build(lang):
    # The built-in TOC replaces the in-document anchor links, which PyMuPDF
    # cannot resolve across sections. Flatten `[text](#anchor)` to plain `text`.
    guide = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", source_md(lang).read_text(encoding="utf-8"))

    pdf = MarkdownPdf(toc_level=2, optimize=True)
    pdf.add_section(Section(COVERS[lang], root=str(LOGO_DIR)), user_css=CSS)
    pdf.add_section(Section(guide), user_css=CSS)
    pdf.meta["title"] = "AIDEA User Guide"
    pdf.meta["author"] = "AIDEA Academy"
    out = OUT_DIR / f"aidea-user-guide.{lang}.pdf"
    pdf.save(out)
    print(f"Wrote {out.name} ({out.stat().st_size // 1024} KB)")


for _lang in LANGS:
    build(_lang)

# English is also the default/fallback filename the app serves.
shutil.copyfile(OUT_DIR / "aidea-user-guide.en.pdf", OUT_DIR / "aidea-user-guide.pdf")
print("Copied en -> aidea-user-guide.pdf (fallback)")
