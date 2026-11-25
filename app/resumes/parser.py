import pdfplumber
import spacy
from docx import Document
from spacy.matcher import PhraseMatcher

from .skills import ALIASES, SKILLS

_nlp = None
_matcher = None


def _load():
    global _nlp, _matcher
    if _nlp is None:
        _nlp = spacy.blank("en")  # sirf tokenizer, model download ki zaroorat nahi
        _matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
        for skill in SKILLS:
            _matcher.add(skill, [_nlp.make_doc(skill)])
        for alias, canonical in ALIASES.items():
            _matcher.add(canonical, [_nlp.make_doc(alias)])
    return _nlp, _matcher


def extract_text(path, ext):
    if ext == "pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages[:15])
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def extract_skills(text):
    nlp, matcher = _load()
    doc = nlp.make_doc(text[:60000])
    found = {}
    for match_id, start, _ in matcher(doc):
        name = nlp.vocab.strings[match_id]
        found.setdefault(name, start)
    return [name for name, _ in sorted(found.items(), key=lambda kv: kv[1])]