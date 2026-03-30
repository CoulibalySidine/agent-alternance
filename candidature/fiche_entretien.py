"""
fiche_entretien.py — Fiche de préparation d'entretien (v3)
============================================================

V3 — Migration vers logger.
"""

import json
import os
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    raise ImportError("pip install anthropic")

from logger import get_logger

log = get_logger("candidature.entretien")

PROFIL_PATH = Path(__file__).parent.parent / "qualification" / "profil.yaml"


def charger_profil(chemin: Path = PROFIL_PATH) -> str:
    if not chemin.exists():
        raise FileNotFoundError(f"Profil introuvable : {chemin}")
    return chemin.read_text(encoding="utf-8")


class FicheEntretien:
    """Génère des fiches de préparation d'entretien."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.profil = charger_profil()

    def generer_fiche(self, offre: dict) -> Optional[str]:
        prompt = f"""Tu es un coach de préparation aux entretiens d'embauche, spécialisé en alternance tech.

PROFIL DU CANDIDAT :
{self.profil}

OFFRE :
- Titre : {offre.get('titre', '')}
- Entreprise : {offre.get('entreprise', '')}
- Lieu : {offre.get('lieu', '')}
- Description : {offre.get('description', '')}
- Score de matching : {offre.get('score', 'N/A')}/100

ANALYSE DU SCORING :
- Points forts : {', '.join(offre.get('points_forts', []))}
- Points faibles : {', '.join(offre.get('points_faibles', []))}
- Conseil : {offre.get('conseil', '')}

Génère une fiche de préparation d'entretien structurée exactement comme suit :

# FICHE DE PRÉPARATION — [Titre du poste] @ [Entreprise]

## 1. Résumé de l'offre (3-4 phrases)
## 2. Pourquoi je suis le bon candidat (4-5 arguments concrets)
## 3. Mes projets à mettre en avant
## 4. Points faibles à anticiper
## 5. Questions à poser au recruteur (5 questions)
## 6. Vocabulaire technique à maîtriser

Réponds directement avec le contenu en Markdown, sans commentaire."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            log.error(f"Erreur API : {e}")
            return None

    def sauvegarder_fiche(self, offre: dict, output_dir: Path) -> Optional[Path]:
        titre = offre.get("titre", "poste")
        entreprise = offre.get("entreprise", "entreprise")

        log.info(f"📋 Fiche entretien pour : {titre} @ {entreprise}")

        contenu = self.generer_fiche(offre)
        if not contenu:
            return None

        nom_safe = f"{entreprise}_{titre}".replace(" ", "_").replace("/", "-")
        nom_safe = "".join(c for c in nom_safe if c.isalnum() or c in "_-")[:60]

        chemin = output_dir / f"ENTRETIEN_{nom_safe}.md"
        chemin.write_text(contenu, encoding="utf-8")
        log.info(f"✅ Fiche : {chemin.name}")

        return chemin
