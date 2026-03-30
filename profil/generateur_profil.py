"""
generateur_profil.py — Génération de profil.yaml depuis un CV
==============================================================

Envoie le texte du CV à Claude avec un prompt structuré.
Claude retourne un profil YAML complet exploitable par tous les modules.
"""

import os
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    raise ImportError("pip install anthropic")

from logger import get_logger

log = get_logger("profil.generateur")

PROFIL_PATH = Path(__file__).parent.parent / "qualification" / "profil.yaml"


def generer_profil(
    texte_cv: str,
    metier: str = "",
    ville: str = "",
    api_key: str = "",
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """
    Analyse un CV et génère un profil YAML structuré.

    Args:
        texte_cv: texte brut extrait du CV
        metier: type de poste recherché (ex: "développeur Python", "data analyst")
        ville: zone géographique de recherche
        api_key: clé API Anthropic
        model: modèle Claude à utiliser

    Returns:
        Contenu du profil en format YAML (string)
    """
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Clé API Anthropic manquante")

    prompt = _construire_prompt(texte_cv, metier, ville)

    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)

    log.info("Analyse du CV par Claude en cours...")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        yaml_content = response.content[0].text.strip()

        # Nettoyer si Claude a ajouté des backticks markdown
        if yaml_content.startswith("```"):
            lines = yaml_content.split("\n")
            yaml_content = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            )

        log.info(f"Profil généré : {len(yaml_content)} caractères")
        return yaml_content

    except Exception as e:
        log.error(f"Erreur API Claude : {e}")
        raise


def sauvegarder_profil(contenu_yaml: str, chemin: Path = PROFIL_PATH) -> Path:
    """
    Sauvegarde le profil YAML sur le disque.

    Crée un backup de l'ancien profil si il existe.
    """
    # Backup de l'ancien
    if chemin.exists():
        backup = chemin.with_suffix(".yaml.bak")
        chemin.rename(backup)
        log.info(f"Ancien profil sauvegardé : {backup.name}")

    chemin.write_text(contenu_yaml, encoding="utf-8")
    log.info(f"Nouveau profil sauvegardé : {chemin}")
    return chemin


def charger_profil(chemin: Path = PROFIL_PATH) -> Optional[str]:
    """Charge le profil actuel si il existe."""
    if not chemin.exists():
        return None
    return chemin.read_text(encoding="utf-8")


def _construire_prompt(texte_cv: str, metier: str, ville: str) -> str:
    """Construit le prompt d'extraction de profil."""

    context_recherche = ""
    if metier:
        context_recherche += f"\nLe candidat recherche un poste de : {metier}"
    if ville:
        context_recherche += f"\nZone géographique : {ville}"

    return f"""Tu es un expert en recrutement tech. Analyse ce CV et génère un profil structuré en YAML.

CV DU CANDIDAT :
{texte_cv}

CONTEXTE DE RECHERCHE :{context_recherche or " Non précisé (déduis du CV)"}

CONSIGNES :
Extrais TOUTES les informations du CV et structure-les en YAML.
- Ne change PAS les informations, ne les invente PAS
- Si une info est absente du CV, ne l'invente pas — omets le champ
- Pour les compétences, déduis le niveau (débutant/intermédiaire/avancé) depuis le contexte
- Sois précis sur les dates et les intitulés

Réponds UNIQUEMENT avec du YAML valide, sans backticks ni commentaire :

nom: "Prénom NOM"
email: "email@exemple.com"
telephone: "+33 X XX XX XX XX"
localisation: "Ville ou Région"
linkedin: "URL ou pseudo"
github: "URL ou pseudo"

titre: "Titre professionnel adapté au poste recherché"

formation:
  - diplome: "Intitulé du diplôme"
    etablissement: "Nom de l'école/université"
    periode: "20XX — 20XX"
    details: "Mentions, spécialités, projets notables"

experience:
  - poste: "Intitulé du poste"
    entreprise: "Nom"
    periode: "Mois 20XX — Mois 20XX"
    missions:
      - "Mission 1 avec technologies utilisées"
      - "Mission 2"

competences:
  langages:
    - nom: "Python"
      niveau: "avancé"
    - nom: "JavaScript"
      niveau: "intermédiaire"
  frameworks:
    - "React"
    - "Node.js"
  bases_de_donnees:
    - "PostgreSQL"
    - "MongoDB"
  outils:
    - "Git"
    - "Docker"
    - "VS Code"
  methodes:
    - "Agile"
    - "MVC"

projets:
  - titre: "Nom du projet"
    technologies: "Tech1, Tech2"
    description: "Ce que fait le projet (1-2 phrases)"

langues:
  - langue: "Français"
    niveau: "natif"
  - langue: "Anglais"
    niveau: "avancé"

interets:
  - "Centre d'intérêt 1"
  - "Centre d'intérêt 2"

recherche:
  type: "alternance"
  rythme: "Déduis du contexte ou laisse vide"
  duree: "Déduis du contexte ou laisse vide"
  domaines:
    - "Domaine 1 recherché"
    - "Domaine 2 recherché"
  localisation: "{ville or 'Déduis du CV'}"

points_forts:
  - "Point fort 1 concret"
  - "Point fort 2 concret"
  - "Point fort 3 concret" """
