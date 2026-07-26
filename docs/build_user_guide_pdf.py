"""Render docs/user-guide.md into a styled PDF served by the frontend.

Run it with uv so the dependencies stay out of the project environment:

    uv run --with markdown-pdf python docs/build_user_guide_pdf.py

Output: frontend/public/aidea-user-guide.pdf
"""
import re
from pathlib import Path

from markdown_pdf import MarkdownPdf, Section

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "user-guide.md"
LOGO_DIR = ROOT / "frontend" / "public" / "images" / "logos"
OUT = ROOT / "frontend" / "public" / "aidea-user-guide.pdf"

# Cover page — logo + who the project is. Sourced from aideaacademy.eu.
COVER = """
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
"""

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

# The built-in TOC replaces the in-document anchor links, which PyMuPDF cannot
# resolve across sections. Flatten `[text](#anchor)` to plain `text`.
guide = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", GUIDE.read_text(encoding="utf-8"))

pdf = MarkdownPdf(toc_level=2, optimize=True)
pdf.add_section(Section(COVER, root=str(LOGO_DIR)), user_css=CSS)
pdf.add_section(Section(guide), user_css=CSS)
pdf.meta["title"] = "AIDEA User Guide"
pdf.meta["author"] = "AIDEA Academy"
pdf.save(OUT)
print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
