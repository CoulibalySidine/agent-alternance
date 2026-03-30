"""
reponses_questions.py — Réponses aux questions de candidature (v3)
===================================================================

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

log = get_logger("candidature.reponses")

PROFIL_PATH = Path(__file__).parent.parent / "qualification" / "profil.yaml"

QUESTIONS_TYPES = [
    {
        "id": "pourquoi_offre",
        "question": "Pourquoi postulez-vous à cette offre ?",
        "consigne": "Réponds en 3-5 phrases. Fais le lien entre les missions du poste et les compétences/projets du candidat. Mentionne au moins 1 projet concret. Ne répète pas le titre du poste mot pour mot.",
        "max_mots": 150,
    },
    {
        "id": "pourquoi_entreprise",
        "question": "Pourquoi souhaitez-vous rejoindre notre entreprise ?",
        "consigne": "Réponds en 3-4 phrases. Montre une connaissance de l'entreprise (secteur, produits, valeurs, culture tech). Fais le lien avec les intérêts du candidat. Pas de flatterie vide.",
        "max_mots": 120,
    },
    {
        "id": "projet_fier",
        "question": "Décrivez un projet dont vous êtes particulièrement fier.",
        "consigne": "Choisis le projet du candidat le PLUS pertinent pour cette offre. Structure : contexte (1 phrase), ce que j'ai fait (2-3 phrases avec technologies), résultat/apprentissage (1 phrase). Sois concret et technique.",
        "max_mots": 180,
    },
    {
        "id": "points_forts",
        "question": "Quels sont vos principaux atouts pour ce poste ?",
        "consigne": "Cite 3 atouts concrets, chacun illustré par un exemple réel du parcours du candidat. Pas de qualités génériques ('motivé', 'rigoureux') sans preuve.",
        "max_mots": 150,
    },
    {
        "id": "disponibilite",
        "question": "Quelle est votre disponibilité ?",
        "consigne": "Réponds en 1-2 phrases. Le candidat cherche une alternance avec un rythme 1 semaine école / 3 semaines entreprise. Mentionne la disponibilité immédiate ou la date de début si connue.",
        "max_mots": 50,
    },
    {
        "id": "pretentions_salariales",
        "question": "Quelles sont vos prétentions salariales ?",
        "consigne": "Réponds en 1-2 phrases. Le candidat est en alternance, donc la rémunération est encadrée par la loi (% du SMIC selon l'âge et l'année). Mentionne que la priorité est la qualité de la formation et des missions.",
        "max_mots": 60,
    },
    {
        "id": "experience_techno",
        "question": "Avez-vous une expérience avec les technologies mentionnées dans l'offre ?",
        "consigne": "Analyse la description de l'offre pour identifier les technologies demandées. Pour chaque techno : soit le candidat la maîtrise (cite le projet), soit il ne la connaît pas encore (montre sa capacité d'apprentissage avec un exemple). Sois honnête sur le niveau.",
        "max_mots": 200,
    },
    {
        "id": "motivation_alternance",
        "question": "Pourquoi choisir l'alternance plutôt qu'un stage ou un emploi ?",
        "consigne": "Réponds en 2-3 phrases. Mets en avant : immersion longue durée, montée en compétences progressive, contribution réelle à l'équipe, équilibre théorie/pratique.",
        "max_mots": 100,
    },
]


def charger_profil(chemin: Path = PROFIL_PATH) -> str:
    if not chemin.exists():
        raise FileNotFoundError(f"Profil introuvable : {chemin}")
    return chemin.read_text(encoding="utf-8")


class ReponsesQuestions:
    """Génère des réponses personnalisées aux questions de formulaire."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.profil = charger_profil()

    def generer_reponses(self, offre: dict, questions: list[dict] = None, questions_custom: list[str] = None) -> Optional[dict]:
        if questions is None:
            questions = QUESTIONS_TYPES

        bloc_questions = ""
        for i, q in enumerate(questions, 1):
            bloc_questions += f"\nQUESTION {i} (id: {q['id']}) :\n« {q['question']} »\nConsigne : {q['consigne']}\nLongueur max : {q['max_mots']} mots\n"

        if questions_custom:
            for j, qc in enumerate(questions_custom, len(questions) + 1):
                q_id = f"custom_{j}"
                bloc_questions += f"\nQUESTION {j} (id: {q_id}) :\n« {qc} »\nConsigne : Réponds de manière personnalisée en te basant sur le profil et l'offre. Sois concret et pertinent. 3-5 phrases max.\nLongueur max : 150 mots\n"

        prompt = f"""Tu es un expert en candidature pour des alternances en informatique en France.

PROFIL DU CANDIDAT :
{self.profil}

OFFRE VISÉE :
- Titre : {offre.get('titre', '')}
- Entreprise : {offre.get('entreprise', '')}
- Lieu : {offre.get('lieu', '')}
- Description : {offre.get('description', '')}
- Score de matching : {offre.get('score', 'N/A')}/100

ANALYSE DU MATCHING :
- Points forts : {', '.join(offre.get('points_forts', []))}
- Points faibles : {', '.join(offre.get('points_faibles', []))}

MISSION : Génère des réponses personnalisées aux questions suivantes.
{bloc_questions}

RÈGLES :
- Ton naturel, professionnel, première personne
- Spécifique à cette offre et entreprise
- INTERDIT : phrases creuses, flatterie, "je suis motivé et dynamique"
- Mentionne des projets concrets quand pertinent
- Respecte la longueur max
- Sois honnête sur les compétences

FORMAT JSON strict :
{{"reponses": [{{"id": "question_id", "question": "La question", "reponse": "Ta réponse"}}]}}

Réponds UNIQUEMENT avec le JSON, sans commentaire ni backticks."""

        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            texte = response.content[0].text.strip()
            return self._parser_reponses(texte)
        except Exception as e:
            log.error(f"Erreur API : {e}")
            return None

    def _parser_reponses(self, texte: str) -> Optional[dict]:
        import re
        for attempt in [
            lambda: json.loads(texte),
            lambda: json.loads(re.search(r'```(?:json)?\s*(\{.*?\})\s*```', texte, re.DOTALL).group(1)),
            lambda: json.loads(re.search(r'\{.*\}', texte, re.DOTALL).group(0)),
        ]:
            try:
                return self._structurer(attempt())
            except (json.JSONDecodeError, AttributeError):
                continue
        log.warning("Impossible de parser la réponse JSON")
        return None

    def _structurer(self, data: dict) -> dict:
        reponses = data.get("reponses", [])
        return {r["id"]: r for r in reponses}

    def sauvegarder_reponses(self, offre: dict, output_dir: Path, questions_custom: list[str] = None) -> Optional[Path]:
        titre = offre.get("titre", "poste")
        entreprise = offre.get("entreprise", "entreprise")

        log.info(f"💬 Réponses formulaire pour : {titre} @ {entreprise}")

        reponses = self.generer_reponses(offre, questions_custom=questions_custom)
        if not reponses:
            return None

        lignes = [
            f"# RÉPONSES FORMULAIRE — {titre} @ {entreprise}", "",
            f"> Généré le {__import__('datetime').datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            f"> Copie-colle ces réponses dans le formulaire de candidature.", "", "---", "",
        ]
        for q_id, r in reponses.items():
            question = r.get("question", q_id)
            reponse = r.get("reponse", "")
            mots = len(reponse.split())
            lignes.extend([f"## {question}", "", reponse, "", f"*({mots} mots)*", "", "---", ""])

        contenu = "\n".join(lignes)
        nom_safe = f"{entreprise}_{titre}".replace(" ", "_").replace("/", "-")
        nom_safe = "".join(c for c in nom_safe if c.isalnum() or c in "_-")[:60]
        chemin = output_dir / f"REPONSES_{nom_safe}.md"
        chemin.write_text(contenu, encoding="utf-8")
        log.info(f"✅ Réponses : {chemin.name} ({len(reponses)} questions)")

        return chemin
