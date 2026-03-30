"""
tracker.py — Suivi des candidatures (v4)
=========================================

V4 — Suppression de tous les sys.path.insert (utilise pyproject.toml).
"""

import json
import shutil
import inspect
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from logger import get_logger

log = get_logger("suivi.tracker")

SUIVI_PATH = Path(__file__).parent / "suivi.json"

ETATS = {
    "brouillon":    "📝",
    "envoyee":      "📤",
    "vue":          "👁️",
    "entretien":    "🎤",
    "acceptee":     "✅",
    "refusee":      "❌",
    "sans_reponse": "⏳",
}

DELAI_RELANCE = {
    "envoyee": 7,
    "vue": 5,
    "entretien": 3,
}


class Candidature:
    """Représente le suivi d'UNE candidature."""

    def __init__(
        self,
        offre_id: str,
        titre: str,
        entreprise: str,
        lieu: str = "",
        score: Optional[float] = None,
        url: str = "",
        etat: str = "brouillon",
        historique: list = None,
        notes: list = None,
        date_creation: str = "",
        date_relance: str = "",
        fichiers: dict = None,
    ):
        self.offre_id = offre_id
        self.titre = titre
        self.entreprise = entreprise
        self.lieu = lieu
        self.score = score
        self.url = url
        self.etat = etat
        self.historique = historique or []
        self.notes = notes or []
        self.date_creation = date_creation or datetime.now().isoformat()
        self.date_relance = date_relance
        self.fichiers = fichiers or {}

        if not self.historique:
            self.historique.append({
                "etat": etat,
                "date": self.date_creation,
                "commentaire": "Création du suivi"
            })

    def changer_etat(self, nouvel_etat: str, commentaire: str = ""):
        if nouvel_etat not in ETATS:
            log.warning(f"État inconnu : {nouvel_etat}")
            return

        ancien = self.etat
        self.etat = nouvel_etat
        self.historique.append({
            "etat": nouvel_etat,
            "date": datetime.now().isoformat(),
            "commentaire": commentaire or f"{ancien} → {nouvel_etat}"
        })

        if nouvel_etat in DELAI_RELANCE:
            jours = DELAI_RELANCE[nouvel_etat]
            self.date_relance = (datetime.now() + timedelta(days=jours)).isoformat()
        else:
            self.date_relance = ""

        log.info(f"État changé : {self.entreprise} — {ancien} → {nouvel_etat}")

    def ajouter_note(self, texte: str):
        self.notes.append({"texte": texte, "date": datetime.now().isoformat()})

    def doit_relancer(self) -> bool:
        if not self.date_relance or self.etat in ("acceptee", "refusee"):
            return False
        try:
            return datetime.now() >= datetime.fromisoformat(self.date_relance)
        except ValueError:
            return False

    def jours_depuis_envoi(self) -> Optional[int]:
        for h in self.historique:
            if h["etat"] == "envoyee":
                return (datetime.now() - datetime.fromisoformat(h["date"])).days
        return None

    def to_dict(self) -> dict:
        return {
            "offre_id": self.offre_id, "titre": self.titre,
            "entreprise": self.entreprise, "lieu": self.lieu,
            "score": self.score, "url": self.url, "etat": self.etat,
            "historique": self.historique, "notes": self.notes,
            "date_creation": self.date_creation,
            "date_relance": self.date_relance, "fichiers": self.fichiers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Candidature":
        params = inspect.signature(cls.__init__).parameters
        valid = {name for name, p in params.items() if name != "self"}
        return cls(**{k: v for k, v in data.items() if k in valid})

    def résumé(self) -> str:
        emoji = ETATS.get(self.etat, "❓")
        relance = " 🔔 RELANCER !" if self.doit_relancer() else ""
        jours = self.jours_depuis_envoi()
        jours_str = f" (J+{jours})" if jours is not None else ""
        return f"{emoji} {self.titre} @ {self.entreprise} [{self.etat}]{jours_str}{relance}"


# ===================================================================
# STOCKAGE
# ===================================================================

def charger_suivi(chemin: Path = None) -> list[Candidature]:
    if chemin is None:
        chemin = SUIVI_PATH
    if not chemin.exists():
        return []
    data = json.loads(chemin.read_text(encoding="utf-8"))
    return [Candidature.from_dict(item) for item in data]


def sauvegarder_suivi(candidatures: list[Candidature], chemin: Path = None):
    if chemin is None:
        chemin = SUIVI_PATH
    data = [c.to_dict() for c in candidatures]
    chemin.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"✅ {len(candidatures)} candidatures sauvegardées dans {chemin.name}")


def importer_offres_qualifiees(score_minimum: int = 60) -> list[Candidature]:
    from sourcing.models import charger_offres

    offres = charger_offres()
    existantes = charger_suivi()
    ids_existants = {c.offre_id for c in existantes}

    nouvelles = []
    for offre in offres:
        if offre.score is not None and offre.score >= score_minimum:
            if offre.id not in ids_existants:
                candidature = Candidature(
                    offre_id=offre.id, titre=offre.titre,
                    entreprise=offre.entreprise, lieu=offre.lieu,
                    score=offre.score, url=offre.url,
                )
                nouvelles.append(candidature)

    if nouvelles:
        toutes = existantes + nouvelles
        sauvegarder_suivi(toutes)
        log.info(f"📥 {len(nouvelles)} nouvelles candidatures importées (score ≥ {score_minimum})")
    else:
        log.info(f"Aucune nouvelle offre à importer")

    return existantes + nouvelles


# ===================================================================
# NETTOYAGE
# ===================================================================

def nettoyer_offres(mode: str = "traitees") -> dict:
    """Supprime de offres.json les offres déjà présentes dans suivi.json."""
    from sourcing.models import charger_offres, sauvegarder_offres, FICHIER_OFFRES

    offres = charger_offres()
    candidatures = charger_suivi()

    if not candidatures:
        log.info("Aucune candidature dans le suivi — rien à nettoyer.")
        return {"avant": len(offres), "supprimees": 0, "apres": len(offres)}

    if mode == "traitees":
        ids_a_supprimer = {c.offre_id for c in candidatures}
        label = "déjà dans le suivi"
    elif mode == "refusees":
        ids_a_supprimer = {c.offre_id for c in candidatures if c.etat == "refusee"}
        label = "refusées"
    elif mode == "terminees":
        ids_a_supprimer = {c.offre_id for c in candidatures if c.etat in ("acceptee", "refusee")}
        label = "terminées (acceptées/refusées)"
    else:
        log.warning(f"Mode inconnu : {mode}. Modes valides : traitees, refusees, terminees")
        return {"avant": len(offres), "supprimees": 0, "apres": len(offres)}

    backup_path = FICHIER_OFFRES.parent / "offres_backup.json"
    shutil.copy2(FICHIER_OFFRES, backup_path)

    avant = len(offres)
    offres_nettoyees = [o for o in offres if o.id not in ids_a_supprimer]
    supprimees = avant - len(offres_nettoyees)

    if supprimees > 0:
        sauvegarder_offres(offres_nettoyees)
        log.info(f"🧹 {supprimees} offres {label} supprimées de offres.json")
        log.info(f"   Avant : {avant} → Après : {len(offres_nettoyees)}")
        log.info(f"   💾 Sauvegarde créée : {backup_path.name}")
    else:
        log.info(f"Aucune offre {label} à supprimer.")

    return {"avant": avant, "supprimees": supprimees, "apres": len(offres_nettoyees)}


def dedupliquer_offres(dry_run: bool = False) -> dict:
    """Détecte et supprime les doublons dans offres.json."""
    from sourcing.models import charger_offres, sauvegarder_offres, FICHIER_OFFRES

    offres = charger_offres()
    avant = len(offres)

    if not offres:
        log.info("Aucune offre dans offres.json.")
        return {"avant": 0, "doublons_id": 0, "doublons_titre": 0, "apres": 0}

    vus_ids = {}
    uniques_apres_id = []
    doublons_id = 0
    for o in offres:
        if o.id in vus_ids:
            doublons_id += 1
            if dry_run:
                log.info(f"  🔴 Doublon ID : {o.id} → «{o.titre}» @ {o.entreprise}")
        else:
            vus_ids[o.id] = o
            uniques_apres_id.append(o)

    groupes = {}
    for o in uniques_apres_id:
        cle = (o.titre.strip().lower(), o.entreprise.strip().lower())
        groupes.setdefault(cle, []).append(o)

    uniques_final = []
    doublons_titre = 0
    for (titre, ent), group in groupes.items():
        if len(group) == 1:
            uniques_final.append(group[0])
        else:
            group.sort(key=lambda o: (
                o.score is not None, o.score or 0, o.date_collecte or "",
            ), reverse=True)
            kept = group[0]
            doublons_titre += len(group) - 1
            if dry_run:
                log.info(f"  🟡 Doublon titre+entreprise : «{kept.titre}» @ {kept.entreprise} "
                         f"({len(group)} exemplaires → garde {kept.source}/{kept.id})")
            uniques_final.append(kept)

    total_doublons = doublons_id + doublons_titre

    if dry_run:
        log.info(f"📊 Simulation : {avant} offres, {total_doublons} doublons → {len(uniques_final)} après nettoyage")
    elif total_doublons > 0:
        backup_path = FICHIER_OFFRES.parent / "offres_backup.json"
        shutil.copy2(FICHIER_OFFRES, backup_path)
        sauvegarder_offres(uniques_final)
        log.info(f"🧹 Déduplication : {doublons_id} doublons ID + {doublons_titre} titre+ent. supprimés")
        log.info(f"   Avant : {avant} → Après : {len(uniques_final)}")
        log.info(f"   💾 Sauvegarde : {backup_path.name}")
    else:
        log.info(f"Aucun doublon détecté dans les {avant} offres.")

    return {"avant": avant, "doublons_id": doublons_id, "doublons_titre": doublons_titre, "apres": len(uniques_final)}


def purger_offres_demo() -> dict:
    """Supprime toutes les offres de source 'demo'."""
    from sourcing.models import charger_offres, sauvegarder_offres, FICHIER_OFFRES

    offres = charger_offres()
    avant = len(offres)
    demos = [o for o in offres if o.source == "demo"]
    reelles = [o for o in offres if o.source != "demo"]

    if not demos:
        log.info("Aucune offre demo trouvée.")
        return {"avant": avant, "supprimees": 0, "apres": avant}

    backup_path = FICHIER_OFFRES.parent / "offres_backup.json"
    shutil.copy2(FICHIER_OFFRES, backup_path)
    sauvegarder_offres(reelles)
    log.info(f"🧹 {len(demos)} offres demo supprimées de offres.json")
    log.info(f"   Avant : {avant} → Après : {len(reelles)} (100% offres réelles)")
    log.info(f"   💾 Sauvegarde : {backup_path.name}")

    return {"avant": avant, "supprimees": len(demos), "apres": len(reelles)}


def reinitialiser_suivi() -> None:
    """Vide complètement suivi.json."""
    if SUIVI_PATH.exists():
        backup_path = SUIVI_PATH.parent / "suivi_backup.json"
        shutil.copy2(SUIVI_PATH, backup_path)
        log.info(f"💾 Sauvegarde : {backup_path.name}")
    sauvegarder_suivi([])
    log.info("🗑️  Suivi réinitialisé (0 candidature)")


def archiver_offres_sous_seuil(score_minimum: int = 60) -> dict:
    """Déplace les offres scorées sous le seuil vers offres_archivees.json."""
    from sourcing.models import charger_offres, sauvegarder_offres, FICHIER_OFFRES, Offre

    offres = charger_offres()
    avant = len(offres)

    if not offres:
        log.info("Aucune offre dans offres.json.")
        return {"avant": 0, "archivees": 0, "apres": 0}

    a_garder = []
    a_archiver = []
    for o in offres:
        if o.score is not None and o.score < score_minimum:
            a_archiver.append(o)
        else:
            a_garder.append(o)

    if not a_archiver:
        non_scorees = sum(1 for o in offres if o.score is None)
        log.info(f"Aucune offre sous le seuil de {score_minimum}.")
        if non_scorees:
            log.info(f"   ℹ️  {non_scorees} offres non encore scorées (lance le module Qualification)")
        return {"avant": avant, "archivees": 0, "apres": avant}

    archive_path = FICHIER_OFFRES.parent / "offres_archivees.json"
    archives_existantes = []
    if archive_path.exists():
        try:
            data = json.loads(archive_path.read_text(encoding="utf-8"))
            archives_existantes = [Offre.from_dict(item) for item in data]
        except (json.JSONDecodeError, Exception):
            pass

    ids_archives = {o.id for o in archives_existantes}
    nouvelles_archives = [o for o in a_archiver if o.id not in ids_archives]
    toutes_archives = archives_existantes + nouvelles_archives

    backup_path = FICHIER_OFFRES.parent / "offres_backup.json"
    shutil.copy2(FICHIER_OFFRES, backup_path)

    sauvegarder_offres(a_garder)
    archive_data = [o.to_dict() for o in toutes_archives]
    archive_path.write_text(json.dumps(archive_data, indent=2, ensure_ascii=False), encoding="utf-8")

    non_scorees = sum(1 for o in a_garder if o.score is None)
    qualifiees = sum(1 for o in a_garder if o.score is not None and o.score >= score_minimum)

    log.info(f"📦 {len(a_archiver)} offres archivées (score < {score_minimum})")
    log.info(f"   offres.json      : {avant} → {len(a_garder)} ({qualifiees} qualifiées, {non_scorees} à scorer)")
    log.info(f"   offres_archivees : {len(archives_existantes)} → {len(toutes_archives)} offres")
    log.info(f"   💾 Sauvegarde : {backup_path.name}")

    return {"avant": avant, "archivees": len(a_archiver), "apres": len(a_garder), "total_archives": len(toutes_archives)}
