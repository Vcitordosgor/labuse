"""COURRIER-2 Lot 2 — résolution du DESTINATAIRE et de l'ADRESSE D'ENVOI d'un pli, par parcelle.

Règles d'adressage (décisions Vic 21/09) — AUCUNE substitution silencieuse, un blocage porte
toujours son motif :
  • PM : pli NOMINATIF à la raison sociale, au siège SIRENE quand il existe
    (« [Raison sociale] — au siège social déclaré » + adresse SIRENE) ; sinon « à l'occupant »
    sur bâti ; sinon bloqué.
  • PP : « À l'occupant » à l'adresse BAN de la parcelle, sur BÂTI seulement.
    Terrain nu → bloqué (« Parcelle non bâtie : aucun destinataire à l'adresse »).
  • Opposition (Lot 1) : une adresse OU une parcelle opposée bloque, motif « Opposition enregistrée ».

C'est la SOURCE UNIQUE de l'adressage : l'écran avant dépôt (front), la garde de dépôt et le PDF
(Lot 3) lisent tous ce résolveur — jamais deux logiques d'adresse.
"""
from __future__ import annotations

from sqlalchemy import text

from . import courrier

MOTIF_NU = "Parcelle non bâtie : aucun destinataire à l'adresse"
MOTIF_SANS_ADRESSE = "Aucune adresse postale connue pour la parcelle"
MOTIF_PM_SANS_CANAL = "Aucune adresse : ni siège déclaré, ni parcelle bâtie adressée"
MOTIF_INCONNUE = "Parcelle inconnue"
MENTION_OCCUPANT = "pli à l'occupant, non nominatif"
MENTION_SIEGE = "au siège social déclaré"

# OUTILS-S2 Lot B — code machine du blocage (le front bloque l'AJOUT sur un terrain sans occupant
# joignable — nu / sans adresse / sans canal / inconnue — et renvoie au Courrier SPF ; l'opposition
# reste traitée au dépôt, motif à part). None = pli résolu, adressable.
CODE_PAR_MOTIF = {
    MOTIF_NU: "nu",
    MOTIF_SANS_ADRESSE: "sans_adresse",
    MOTIF_PM_SANS_CANAL: "sans_canal",
    MOTIF_INCONNUE: "inconnue",
}


def _siege_adresse(payload) -> str | None:
    """Adresse du siège social depuis le payload SIRENE (owner_enrichment). None si absente.

    Le champ `adresse` SIRENE est DÉJÀ dénormalisé (voie + CP + commune sur une ligne) — on le sert
    tel quel ; on ne reconstruit à partir des parts (CP/commune) que s'il est absent."""
    if not isinstance(payload, dict):
        return None
    s = payload.get("siege") or {}
    adr = (s.get("adresse") or "").strip()
    if adr:
        return adr
    parts = [str(s.get(k) or "").strip() for k in ("libelle_voie", "code_postal", "libelle_commune")]
    ligne = " ".join(p for p in parts if p)
    return ligne or None


def resoudre_destinataire(db, idu: str) -> dict:
    """Résout {destinataire, adresse_envoi, bien, type, mention, bloque, motif} pour une parcelle.

    `type` ∈ {'occupant', 'siege', None}. `bloque=True` ⇒ `motif` renseigné (jamais None) et
    `adresse_envoi` peut rester None. `bien` = {reference cadastrale, adresse BAN, commune}."""
    row = db.execute(text("""
        SELECT p.idu, p.section, p.numero, p.commune, p.surface_m2,
               (fb.idu IS NOT NULL) AS batie,
               pm.denomination, pm.siren
        FROM parcels p
        LEFT JOIN parcel_filtre_bati fb ON fb.idu = p.idu
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE p.idu = :i"""), {"i": idu}).mappings().first()
    ban = courrier.adresse_ban_parcelle(db, idu)
    if not row:
        return _bloque({"idu": idu, "bien": {"reference": idu, "adresse": ban, "commune": None},
                        "type": None, "destinataire": None, "adresse_envoi": None,
                        "mention": None}, MOTIF_INCONNUE)
    ref = " ".join(x for x in (row["section"], row["numero"]) if x) or idu
    bien = {"reference": ref, "adresse": ban, "commune": row["commune"]}
    base = {"idu": idu, "bien": bien, "type": None, "destinataire": None,
            "adresse_envoi": None, "mention": None, "bloque": True, "motif": None, "code": None}

    est_pm = bool(row["denomination"])
    if est_pm:
        siege = None
        if row["siren"]:
            payload = db.execute(text(
                "SELECT payload FROM owner_enrichment WHERE siren = :s ORDER BY fetched_at DESC LIMIT 1"),
                {"s": row["siren"]}).scalar()
            siege = _siege_adresse(payload)
        if siege:
            res = {**base, "type": "siege", "destinataire": f"{row['denomination']} — {MENTION_SIEGE}",
                   "adresse_envoi": siege, "mention": MENTION_SIEGE, "bloque": False}
        elif row["batie"] and ban:
            res = {**base, "type": "occupant", "destinataire": "À l'occupant",
                   "adresse_envoi": ban, "mention": MENTION_OCCUPANT, "bloque": False}
        else:
            return _bloque(base, MOTIF_PM_SANS_CANAL)
    else:
        if not row["batie"]:
            return _bloque(base, MOTIF_NU)
        if not ban:
            return _bloque(base, MOTIF_SANS_ADRESSE)
        res = {**base, "type": "occupant", "destinataire": "À l'occupant",
               "adresse_envoi": ban, "mention": MENTION_OCCUPANT, "bloque": False}

    # dernière garde : opposition (Lot 1) — sur l'IDU ou sur l'adresse d'envoi résolue.
    motif_opp = courrier.opposition_motif(
        db, idu=idu, adresse_norm=courrier.normaliser_adresse(res["adresse_envoi"]))
    if motif_opp:
        return {**res, "bloque": True, "motif": motif_opp, "code": "opposition"}
    return res


def _bloque(base: dict, motif: str) -> dict:
    """Marque un blocage avec son motif ET son code machine (CODE_PAR_MOTIF) — OUTILS-S2 Lot B."""
    return {**base, "bloque": True, "motif": motif, "code": CODE_PAR_MOTIF.get(motif)}


def resoudre_plusieurs(db, idus: list[str]) -> list[dict]:
    return [resoudre_destinataire(db, idu) for idu in idus]
