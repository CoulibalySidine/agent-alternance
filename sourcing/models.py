"""
models.py — Structure de données pour les offres d'alternance (v4)
===================================================================

V4 — Ajout des champs de scoring (raison_score, points_forts, points_faibles, conseil).
     Avant : seul le champ 'score' existait, les données d'analyse étaient perdues.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json
from pathlib import Path

from logger import get_logger

log = get_logger("sourcing.models")


@dataclass
class Offre:
    """Représente une offre d'alternance collectée."""

    titre: str
    entreprise: str
    url: str
    source: str

    lieu: str = "Non précisé"
    description: str = ""
    type_contrat: str = "Alternance"
    salaire: Optional[str] = None
    date_publication: Optional[str] = None

    id: str = ""
    date_collecte: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    score: Optional[float] = None

    # --- Champs de scoring (remplis par le module Qualification) ---
    raison_score: Optional[str] = None
    points_forts: Optional[list[str]] = field(default=None)
    points_faibles: Optional[list[str]] = field(default=None)
    conseil: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            unique = f"{self.titre}-{self.entreprise}-{self.url}"
            self.id = f"{self.source}_{abs(hash(unique)) % 0xFFFFFF:06x}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Offre":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def résumé(self) -> str:
        score_str = f" [Score: {self.score:.0f}/100]" if self.score else ""
        return f"📌 {self.titre} @ {self.entreprise} — {self.lieu}{score_str}"


# ---------------------------------------------------------------------------
# STOCKAGE
# ---------------------------------------------------------------------------

FICHIER_OFFRES = Path(__file__).parent / "offres.json"


def sauvegarder_offres(offres: list[Offre], fichier: Path = None):
    if fichier is None:
        fichier = FICHIER_OFFRES
    data = [o.to_dict() for o in offres]
    fichier.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    log.info(f"✅ {len(offres)} offres sauvegardées dans {fichier.name}")


def charger_offres(fichier: Path = None) -> list[Offre]:
    if fichier is None:
        fichier = FICHIER_OFFRES
    if not fichier.exists():
        return []
    data = json.loads(fichier.read_text(encoding="utf-8"))
    return [Offre.from_dict(item) for item in data]


def dédupliquer(nouvelles: list[Offre], existantes: list[Offre]) -> list[Offre]:
    ids_existants = {o.id for o in existantes}
    uniques = [o for o in nouvelles if o.id not in ids_existants]
    log.info(f"🔍 {len(nouvelles)} trouvées, {len(uniques)} nouvelles, {len(nouvelles) - len(uniques)} doublons ignorés")
    return uniques
