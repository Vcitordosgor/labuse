"""M86-B — L'ASSAINISSEMENT (ANC / tout-à-l'égout) SERVI à la fiche. POINT DE CALCUL UNIQUE.

Un critère = un seul endroit : ce module sert la fiche écran, le PDF ET l'export — jamais recalculé
ailleurs. Trois états, jamais quatre :
  · Sourcé  — `zone_anc` réglementaire (collectif | ANC) + commune (source amont : zonage GPU) ;
  · Estimé  — zonage absent MAIS proba de SECTEUR (maille IRIS) ≥ seuil → alerte SECTORIELLE
              « à vérifier auprès du SPANC ». JAMAIS « cette parcelle est en ANC », JAMAIS
              « probablement collectif » (le péché mortel : rassurer sur une contrainte à 8-15 k€) ;
  · Absent  — ni l'un ni l'autre → « zonage non disponible » (un NULL n'est PAS un raccordement).

On ne sert JAMAIS l'estimation SOUS le seuil : sous le seuil = Absent, ce qui est exactement vrai.
Asymétrie assumée (mesurée M86-B) : proba ≥ seuil = une alerte (faux positif = une vérif SPANC de trop,
supportable) ; proba < seuil ne devient jamais un feu vert « collectif ». Le seuil vit en config
(`anc.fiche.proba_seuil`, défaut 75 — précision au-dessus du seuil ~34 %, grade SECTEUR, jamais parcellaire).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

_DEFAUT_SEUIL_FICHE = 75


def seuil_fiche() -> int:
    try:
        from .config import load_yaml_config
        cfg = (load_yaml_config("anc_vegetation") or {}).get("anc", {}).get("fiche", {})
        return int(cfg.get("proba_seuil", _DEFAUT_SEUIL_FICHE))
    except Exception:  # noqa: BLE001 — config absente = défaut, jamais un crash de fiche
        return _DEFAUT_SEUIL_FICHE


def statut_anc(db: Session, idu: str) -> dict:
    """L'état ANC SERVI d'une parcelle. Retourne TOUJOURS un dict (Absent est un état, pas un trou)."""
    row = db.execute(text("SELECT zone_anc, source, proba_anc FROM parcel_anc WHERE idu = :idu"),
                     {"idu": idu}).mappings().first()
    commune = db.execute(text("SELECT commune FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()
    seuil = seuil_fiche()

    if row and row["zone_anc"]:                                    # ── SOURCÉ (réglementaire) ──
        est_anc = row["zone_anc"] == "anc"
        return {
            "statut": "source",
            "libelle": "Assainissement non collectif" if est_anc else "Tout-à-l'égout (collectif)",
            "anc": est_anc,
            "phrase": (f"Zonage réglementaire à {commune} : "
                       + ("assainissement non collectif — surface d'épandage et étude de sol requises."
                          if est_anc else "raccordement au tout-à-l'égout (collectif).")),
            "source": "Zonage d'assainissement (Géoportail de l'urbanisme / GPU)",
            "commune": commune,
        }

    if row and row["proba_anc"] is not None and row["proba_anc"] >= seuil:   # ── ESTIMÉ (secteur) ──
        return {
            "statut": "estime",
            "libelle": "Secteur à forte proportion d'ANC",
            "phrase": ("Secteur à forte proportion d'assainissement non collectif — estimation "
                       "statistique de SECTEUR (maille IRIS, non parcellaire). À vérifier auprès du SPANC."),
            "maille": "IRIS (secteur, jamais la parcelle)",
            "methode": "taux de non-raccordement du secteur (INSEE RP2022, agrégé par IRIS)",
        }

    return {                                                        # ── ABSENT ──
        "statut": "absent",
        "libelle": "Zonage non disponible",
        "phrase": ("Zonage d'assainissement non disponible sur cette commune "
                   "(réglementaire absent, secteur non estimé). Ce n'est pas un raccordement présumé."),
    }


def couverture_anc(db: Session) -> dict:
    """Couverture réglementaire = communes ayant un zonage (pour DIRE l'Absent, pas le subir). Calculé,
    jamais en dur : sur 24 communes, le zonage réglementaire SIG n'existe que pour une minorité."""
    avec = db.execute(text("SELECT count(DISTINCT left(idu, 5)) FROM parcel_anc WHERE zone_anc IS NOT NULL")).scalar() or 0
    total = db.execute(text("SELECT count(DISTINCT commune) FROM parcels")).scalar() or 0
    return {"communes_avec_zonage": int(avec), "communes_total": int(total)}
