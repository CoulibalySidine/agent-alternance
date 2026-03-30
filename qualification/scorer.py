"""
scorer.py — Scoring des offres via l'API Claude
================================================

CONCEPT CLÉ : le prompt engineering structuré.

On envoie à Claude :
1. Ton profil (depuis profil.yaml)
2. Les infos d'une offre
3. Des instructions précises pour obtenir un JSON exploitable

Claude retourne un score 0-100 + une explication.
On parse le JSON et on met à jour l'objet Offre.

POURQUOI CLAUDE ET PAS UN ALGORITHME CLASSIQUE ?
Un matching par mots-clés ("Python" dans l'offre + "Python" dans le CV = match)
est fragile et rate beaucoup de nuances :
- "Expérience en sécurité des systèmes" matche avec "cybersécurité"
- "Développeur fullstack" est pertinent même si tu n'as que "Python + HTML"
- "Startup de 10 personnes" peut être un plus ou un moins selon le profil

Un LLM comprend le SENS, pas juste les mots.
"""

import json
import time
from pathlib import Path
from typing import Optional

# --- Chargement du profil YAML ---
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# --- Import du client Anthropic ---
try:
    import anthropic
except ImportError:
    raise ImportError(
        "❌ Le module 'anthropic' est requis.\n"
        "   Installe-le avec : pip install anthropic"
    )

# --- Import du logger ---
try:
    from logger import get_logger
    log = get_logger("qualification.scorer")
except ImportError:
    import logging
    log = logging.getLogger(__name__)

# Chemin vers le profil (même dossier que ce fichier)
PROFIL_PATH = Path(__file__).parent / "profil.yaml"

# --- Constantes de retry ---
MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]  # secondes — backoff progressif


def charger_profil(chemin: Path = PROFIL_PATH) -> str:
    """
    Charge le profil candidat depuis le fichier YAML.

    Retourne le contenu brut (string) — on l'injecte tel quel
    dans le prompt. Pas besoin de parser le YAML en dict,
    Claude comprend le format directement.
    """
    if not chemin.exists():
        raise FileNotFoundError(
            f"❌ Profil introuvable : {chemin}\n"
            f"   Crée le fichier profil.yaml dans le dossier qualification/"
        )
    return chemin.read_text(encoding="utf-8")


def construire_prompt(profil: str, offre_dict: dict) -> str:
    """
    Construit le prompt envoyé à Claude pour scorer UNE offre.

    PRINCIPES DE PROMPT ENGINEERING appliqués ici :

    1. RÔLE : on donne un rôle précis à Claude ("conseiller expert")
    2. CONTEXTE : on fournit toutes les infos nécessaires
    3. FORMAT : on impose un JSON strict pour parser la réponse
    4. CRITÈRES : on liste les dimensions à évaluer
    5. CONTRAINTES : on force un score numérique et des textes courts

    Pourquoi "UNIQUEMENT en JSON" ?
    → Sans ça, Claude ajoute du texte avant/après le JSON
    → Ce texte casse json.loads() → erreur
    → En insistant, Claude retourne du JSON pur 95%+ du temps
    """
    return f"""Tu es un conseiller expert en recrutement et orientation professionnelle, spécialisé dans l'alternance en France.

PROFIL DU CANDIDAT :
{profil}

OFFRE À ÉVALUER :
- Titre : {offre_dict.get('titre', 'Non précisé')}
- Entreprise : {offre_dict.get('entreprise', 'Non précisé')}
- Lieu : {offre_dict.get('lieu', 'Non précisé')}
- Type de contrat : {offre_dict.get('type_contrat', 'Non précisé')}
- Salaire : {offre_dict.get('salaire', 'Non précisé')}
- Description : {offre_dict.get('description', 'Non précisé')}

CONSIGNES :
Évalue la pertinence de cette offre pour ce candidat sur 5 critères :
1. Adéquation compétences (les skills du candidat matchent-ils ?)
2. Adéquation intérêts (le domaine correspond-il à ses intérêts ?)
3. Localisation (le lieu est-il compatible ?)
4. Type de contrat (alternance = ce qu'il cherche ?)
5. Potentiel d'apprentissage (va-t-il progresser ?)

Réponds UNIQUEMENT avec un objet JSON valide, sans aucun texte avant ou après :
{{
    "score": <nombre entre 0 et 100>,
    "raison": "<une phrase résumant pourquoi ce score>",
    "points_forts": ["<max 3 points>"],
    "points_faibles": ["<max 3 points>"],
    "conseil": "<un conseil concret pour la candidature>"
}}"""


def parser_reponse(texte: str) -> Optional[dict]:
    """
    Parse la réponse JSON de Claude.

    Gestion robuste : parfois Claude ajoute du texte ou des backticks
    autour du JSON. On nettoie avant de parser.

    TECHNIQUE : on cherche le premier '{' et le dernier '}' dans la réponse
    pour extraire le JSON même s'il y a du texte autour.
    """
    try:
        # Cas idéal : la réponse est du JSON pur
        return json.loads(texte)
    except json.JSONDecodeError:
        pass

    # Plan B : extraire le JSON entre les premiers { et derniers }
    try:
        debut = texte.index("{")
        fin = texte.rindex("}") + 1
        json_str = texte[debut:fin]
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError):
        pass

    # Plan C : enlever les backticks markdown (```json ... ```)
    try:
        nettoye = texte.replace("```json", "").replace("```", "").strip()
        return json.loads(nettoye)
    except json.JSONDecodeError:
        log.warning(f"Impossible de parser le JSON : {texte[:100]}...")
        return None


class Scorer:
    """
    Évalue les offres en utilisant l'API Claude.

    Usage :
        scorer = Scorer(api_key="sk-ant-...")
        resultat = scorer.scorer_offre(offre)
        # resultat = {"score": 82, "raison": "...", ...}
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 400,
        delai_entre_appels: float = 1.0,
        timeout: float = 30.0,
    ):
        """
        Args:
            api_key: ta clé API Anthropic (commence par "sk-ant-...")
            model: le modèle Claude à utiliser
                   - claude-sonnet-4-20250514 : bon rapport qualité/prix (recommandé)
                   - claude-haiku-4-5-20251001 : plus rapide et moins cher
            max_tokens: tokens max pour la réponse (400 suffit pour notre JSON)
            delai_entre_appels: pause entre les requêtes (rate limiting)
            timeout: timeout en secondes pour chaque appel API
        """
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_tokens = max_tokens
        self.delai = delai_entre_appels
        self.profil = charger_profil()

        log.info(f"Scorer initialisé (modèle: {model}, timeout: {timeout}s)")
        print(f"✅ Scorer initialisé (modèle: {model})")

    def scorer_offre(self, offre_dict: dict, _tentative: int = 0) -> Optional[dict]:
        """
        Score UNE offre via l'API Claude.

        Args:
            offre_dict: dictionnaire d'une offre (from offre.to_dict())
            _tentative: compteur interne de retry (ne pas passer manuellement)

        Returns:
            dict avec score, raison, points_forts, points_faibles, conseil
            ou None si erreur
        """
        prompt = construire_prompt(self.profil, offre_dict)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extraire le texte de la réponse
            texte = response.content[0].text
            resultat = parser_reponse(texte)

            if resultat and "score" in resultat:
                # S'assurer que le score est un nombre entre 0 et 100
                resultat["score"] = max(0, min(100, int(resultat["score"])))
                return resultat
            else:
                log.warning("Réponse API sans score valide")
                return None

        except anthropic.RateLimitError:
            if _tentative >= MAX_RETRIES:
                log.error(f"Rate limit : {MAX_RETRIES} tentatives échouées, abandon")
                print(f"  ❌ Rate limit persistant après {MAX_RETRIES} tentatives, abandon")
                return None
            delai = RETRY_DELAYS[min(_tentative, len(RETRY_DELAYS) - 1)]
            log.warning(f"Rate limit — tentative {_tentative + 1}/{MAX_RETRIES}, pause {delai}s")
            print(f"  ⏱️  Rate limit — pause {delai}s (tentative {_tentative + 1}/{MAX_RETRIES})")
            time.sleep(delai)
            return self.scorer_offre(offre_dict, _tentative=_tentative + 1)

        except anthropic.AuthenticationError:
            log.error("Clé API invalide")
            print(f"  ❌ Clé API invalide ! Vérifie ta clé Anthropic.")
            return None

        except anthropic.APITimeoutError:
            log.error(f"Timeout API pour {offre_dict.get('titre', '?')}")
            print(f"  ⏱️  Timeout API — offre ignorée")
            return None

        except Exception as e:
            log.error(f"Erreur API : {e}")
            print(f"  ❌ Erreur API : {e}")
            return None

    def scorer_offres(
        self,
        offres: list[dict],
        score_minimum: int = 0,
    ) -> list[dict]:
        """
        Score TOUTES les offres et retourne les résultats triés.

        Args:
            offres: liste de dicts d'offres
            score_minimum: ne garder que les offres au-dessus de ce score

        Returns:
            Liste d'offres enrichies avec le score, triées par score décroissant
        """
        log.info(f"Scoring de {len(offres)} offres")
        print(f"\n{'='*60}")
        print(f"🎯 QUALIFICATION — Scoring de {len(offres)} offres")
        print(f"{'='*60}")

        resultats = []
        erreurs = 0

        for i, offre in enumerate(offres):
            titre = offre.get("titre", "?")
            entreprise = offre.get("entreprise", "?")
            print(f"\n  [{i+1}/{len(offres)}] {titre} @ {entreprise}")

            resultat = self.scorer_offre(offre)

            if resultat:
                offre["score"] = resultat["score"]
                offre["raison_score"] = resultat.get("raison", "")
                offre["points_forts"] = resultat.get("points_forts", [])
                offre["points_faibles"] = resultat.get("points_faibles", [])
                offre["conseil"] = resultat.get("conseil", "")

                emoji = "🟢" if resultat["score"] >= 70 else "🟡" if resultat["score"] >= 40 else "🔴"
                print(f"    {emoji} Score : {resultat['score']}/100 — {resultat.get('raison', '')}")

                resultats.append(offre)
            else:
                erreurs += 1
                log.warning(f"Scoring échoué pour {titre} @ {entreprise}")
                print(f"    ⚠️  Scoring échoué, offre ignorée")

            # Pause entre les appels (rate limiting)
            if i < len(offres) - 1:
                time.sleep(self.delai)

        # Trier par score décroissant
        resultats.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Filtrer par score minimum
        if score_minimum > 0:
            avant = len(resultats)
            resultats = [r for r in resultats if r.get("score", 0) >= score_minimum]
            print(f"\n  🔍 Filtre score ≥ {score_minimum} : {avant} → {len(resultats)} offres")

        # Résumé
        print(f"\n{'='*60}")
        print(f"📊 RÉSULTATS DU SCORING")
        print(f"{'='*60}")
        if resultats:
            scores = [r["score"] for r in resultats]
            print(f"   Offres scorées  : {len(resultats)}")
            print(f"   Erreurs         : {erreurs}")
            print(f"   Score moyen     : {sum(scores) / len(scores):.0f}/100")
            print(f"   Meilleur score  : {max(scores)}/100")
            print(f"   Plus bas score  : {min(scores)}/100")

            log.info(f"Scoring terminé : {len(resultats)} réussies, {erreurs} erreurs, "
                     f"moyenne {sum(scores) / len(scores):.0f}/100")

            print(f"\n🏆 Top 5 :")
            for offre in resultats[:5]:
                emoji = "🟢" if offre["score"] >= 70 else "🟡" if offre["score"] >= 40 else "🔴"
                print(f"   {emoji} {offre['score']}/100 — {offre['titre']} @ {offre['entreprise']}")
        else:
            log.warning("Aucune offre scorée")
            print("   Aucune offre scorée.")

        print(f"{'='*60}\n")

        return resultats
