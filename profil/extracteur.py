"""
extracteur.py — Extraction de texte depuis un CV (PDF ou Word)
===============================================================

Lit le fichier uploadé et retourne le texte brut.
Supporte : .pdf (via pdfplumber), .docx (via python-docx), .txt
"""

from pathlib import Path
from typing import Optional

from logger import get_logger

log = get_logger("profil.extracteur")


def extraire_texte(chemin: Path) -> str:
    """
    Extrait le texte d'un fichier CV.

    Args:
        chemin: chemin vers le fichier (.pdf, .docx, .txt)

    Returns:
        Texte brut du CV

    Raises:
        ValueError: format non supporté
        FileNotFoundError: fichier introuvable
    """
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    suffix = chemin.suffix.lower()

    if suffix == ".pdf":
        return _lire_pdf(chemin)
    elif suffix == ".docx":
        return _lire_docx(chemin)
    elif suffix in (".txt", ".md"):
        return chemin.read_text(encoding="utf-8")
    else:
        raise ValueError(
            f"Format non supporté : {suffix}. "
            f"Formats acceptés : .pdf, .docx, .txt"
        )


def _lire_pdf(chemin: Path) -> str:
    """Extrait le texte d'un PDF avec pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber est requis pour lire les PDF.\n"
            "   pip install pdfplumber"
        )

    texte_pages = []
    with pdfplumber.open(str(chemin)) as pdf:
        for i, page in enumerate(pdf.pages):
            texte = page.extract_text()
            if texte:
                texte_pages.append(texte)
            else:
                log.warning(f"Page {i+1} : pas de texte extractible (image/scan ?)")

    if not texte_pages:
        raise ValueError(
            "Aucun texte trouvé dans le PDF. "
            "Le fichier est peut-être scanné (image). "
            "Essaie avec un CV au format Word (.docx) ou texte (.txt)."
        )

    resultat = "\n\n".join(texte_pages)
    log.info(f"PDF lu : {len(pdf.pages)} pages, {len(resultat)} caractères")
    return resultat


def _lire_docx(chemin: Path) -> str:
    """Extrait le texte d'un Word .docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx est requis : pip install python-docx")

    doc = Document(str(chemin))
    paragraphes = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    if not paragraphes:
        raise ValueError("Aucun texte trouvé dans le fichier Word.")

    resultat = "\n".join(paragraphes)
    log.info(f"Word lu : {len(paragraphes)} paragraphes, {len(resultat)} caractères")
    return resultat
