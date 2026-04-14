"""
generateur_profil.py — Génération de profil.yaml depuis un CV (v2)
===================================================================

V2 — Prompt anti-hallucination renforcé :
  - Étape 1 : extraction brute (liste ce qui est dans le CV)
  - Étape 2 : structuration en YAML
  - Template sans valeurs d'exemple (évite le copier-coller par l'IA)
  - Instructions négatives renforcées

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
            max_tokens=3000,
            system=_SYSTEM_PROMPT,
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


def sauvegarder_profil(contenu_yaml: str, chemin: Path = None) -> Path:
    """
    Sauvegarde le profil YAML sur le disque.

    Crée un backup de l'ancien profil si il existe.
    """
    if chemin is None:
        chemin = PROFIL_PATH

    # Backup de l'ancien
    if chemin.exists():
        backup = chemin.with_suffix(".yaml.bak")
        chemin.replace(backup)
        log.info(f"Ancien profil sauvegardé : {backup.name}")

    chemin.write_text(contenu_yaml, encoding="utf-8")
    log.info(f"Nouveau profil sauvegardé : {chemin}")
    return chemin


def charger_profil(chemin: Path = None) -> Optional[str]:
    """Charge le profil actuel si il existe."""
    if chemin is None:
        chemin = PROFIL_PATH
    if not chemin.exists():
        return None
    return chemin.read_text(encoding="utf-8")


# =========================================================================
# PROMPT SYSTEM — contrôle strict du comportement
# =========================================================================

_SYSTEM_PROMPT = """\
Tu es un extracteur de données de CV. Ton rôle est UNIQUEMENT d'extraire \
les informations qui sont EXPLICITEMENT écrites dans le CV fourni.

RÈGLES ABSOLUES :
1. Tu ne dois JAMAIS inventer, deviner, déduire ou compléter une information \
qui n'est pas écrite noir sur blanc dans le CV.
2. Si un champ n'a pas de correspondance dans le CV, tu OMETS le champ \
entièrement. Tu ne mets PAS de valeur vide, de "Non précisé", ou de placeholder.
3. Tu n'ajoutes AUCUNE compétence, technologie, langue ou expérience \
qui n'est pas mentionnée dans le CV.
4. Pour les niveaux de compétence : tu ne les indiques QUE si le CV \
les mentionne explicitement. Sinon, tu omets le champ "niveau".
5. Tu copies les intitulés EXACTS du CV (diplômes, postes, entreprises). \
Tu ne les reformules pas et tu ne les "améliores" pas.
6. Tu ne déduis PAS de centres d'intérêt, de points forts, ou de soft skills \
à partir du contenu du CV. Tu les inclus UNIQUEMENT s'ils sont listés.

En cas de doute sur la présence d'une information : OMETS-LA."""


# =========================================================================
# PROMPT UTILISATEUR — extraction + structuration
# =========================================================================

def _construire_prompt(texte_cv: str, metier: str, ville: str) -> str:
    """Construit le prompt d'extraction de profil."""

    context_recherche = ""
    if metier:
        context_recherche += f"\n- Poste recherché : {metier}"
    if ville:
        context_recherche += f"\n- Zone géographique : {ville}"

    return f"""Voici le texte brut extrait d'un CV. Analyse-le et génère un profil YAML structuré.

=== CV (TEXTE BRUT) ===
{texte_cv}
=== FIN DU CV ===

CONTEXTE DE RECHERCHE (fourni par l'utilisateur, pas extrait du CV) :{context_recherche or " Non précisé"}

ÉTAPE 1 — INVENTAIRE
Avant de générer le YAML, liste mentalement UNIQUEMENT les informations \
que tu as trouvées dans le CV ci-dessus. Si une catégorie entière est absente \
du CV (ex: pas de section langues, pas de projets personnels), tu ne l'incluras \
PAS dans le YAML.

ÉTAPE 2 — GÉNÉRATION YAML
Génère le profil en suivant la structure ci-dessous.
SUPPRIME les sections/champs pour lesquels le CV ne contient AUCUNE information.

Réponds UNIQUEMENT avec du YAML valide, sans backticks, sans commentaire, \
sans explication avant ou après :

nom: "(prénom et nom tels qu'écrits dans le CV)"
email: "(email tel qu'écrit dans le CV)"
telephone: "(tel qu'écrit dans le CV)"
localisation: "(ville/région telle qu'écrite dans le CV)"
linkedin: "(URL ou pseudo tel qu'écrit dans le CV)"
github: "(URL ou pseudo tel qu'écrit dans le CV)"
portfolio: "(URL telle qu'écrite dans le CV)"

titre: "(intitulé professionnel tel qu'écrit dans le CV, ou le poste recherché si fourni)"

formation:
  - diplome: "(intitulé EXACT du diplôme)"
    etablissement: "(nom EXACT)"
    periode: "(dates EXACTES)"
    details: "(mentions ou spécialités SI mentionnées)"

experience:
  - poste: "(intitulé EXACT)"
    entreprise: "(nom EXACT)"
    periode: "(dates EXACTES)"
    missions:
      - "(mission telle que décrite dans le CV)"

competences:
  langages:
    - "(langage mentionné dans le CV)"
  frameworks:
    - "(framework mentionné dans le CV)"
  bases_de_donnees:
    - "(BDD mentionnée dans le CV)"
  outils:
    - "(outil mentionné dans le CV)"
  methodes:
    - "(méthode mentionnée dans le CV)"

projets:
  - titre: "(nom EXACT du projet)"
    technologies: "(technologies mentionnées)"
    description: "(description telle qu'écrite)"

langues:
  - langue: "(langue mentionnée)"
    niveau: "(niveau SI précisé dans le CV)"

interets:
  - "(centre d'intérêt tel qu'écrit dans le CV)"

recherche:
  type: "(type de contrat recherché)"
  rythme: "(rythme SI mentionné)"
  duree: "(durée SI mentionnée)"
  domaines:
    - "(domaine recherché)"
  localisation: "{ville or '(zone SI mentionnée dans le CV)'}"

points_forts:
  - "(point fort UNIQUEMENT s'il est explicitement mentionné dans le CV)"

RAPPEL FINAL : si une section entière est absente du CV, SUPPRIME-LA du YAML. \
Mieux vaut un profil incomplet mais fidèle qu'un profil complet mais inventé."""
