"""OUTIL-COMMUNES-FIX-7 — LE point de lecture UNIQUE du prix d'une SECTION cadastrale pour un type de
bien (`dvf_secteur_medianes`). TOUTE diffusion d'un prix de section passe ICI.

Doctrine (le seuil vit à UN SEUL endroit) : les bornes de prix sont appliquées au BUILD (seul l'acte
dans [50 ; 20 000] €/m² entre dans la médiane ET dans l'effectif `n_ventes`). La LECTURE applique le
SEUIL DE DIFFUSION (`seuil_section()` = 8 ventes utilisées) : sous le seuil, pas de prix (« pas assez de
ventes »), jamais un chiffre fondé sur 1-7 ventes. Avant FIX-7, chaque lecteur (Comparer, fiche parcelle,
Carnet, Bilan) appliquait — ou OUBLIAIT — ce seuil ; il en restait toujours un (Carnet + fiche parcelle
publiaient 133 €/m² sur 1 vente). Désormais aucun lecteur ne lit la table directement pour un prix :
tous appellent `prix_section` / `prix_sections` / `medianes_sections_commune`.

`seuil` paramétrable (défaut = seuil de diffusion) : le Bilan mode B passe son propre seuil de fiabilité
(`mode_b_prix_local` = 3) ; la cascade de scoring passe `seuil=0` (brut, sa propre règle de plancher).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def seuil_section() -> int:
    """LE seuil de diffusion d'un prix de section (nombre de ventes UTILISÉES). Config
    `dvf_mediane.SEUIL_N` (8), point unique partagé avec Comparer et l'Étude de zone."""
    from .dvf_mediane import SEUIL_N
    return SEUIL_N


def _gate(n_ventes, mediane_prix_m2, mediane_valeur, fenetre, type_bien, seuil) -> dict:
    n = int(n_ventes or 0)
    assez = n >= seuil and mediane_prix_m2 is not None
    return {"type_bien": type_bien, "prix_m2": (int(mediane_prix_m2) if assez else None),
            "n": n, "assez": assez,
            "mediane_valeur": (int(mediane_valeur) if assez and mediane_valeur is not None else None),
            "fenetre": fenetre}


def prix_section(db: Session, secteur: str, type_bien: str, *, seuil: int | None = None) -> dict:
    """LE prix €/m² d'une section cadastrale pour un type de bien, SEUIL appliqué. Renvoie TOUJOURS un
    dict : `{type_bien, prix_m2 (None si < seuil), n, assez, mediane_valeur, fenetre}`. `assez=False` =
    « pas assez de ventes » (prix non diffusable)."""
    s = seuil_section() if seuil is None else seuil
    row = db.execute(text(
        "SELECT n_ventes, mediane_prix_m2, mediane_valeur, fenetre FROM dvf_secteur_medianes "
        "WHERE secteur = :s AND type_bien = :t"), {"s": secteur, "t": type_bien}).mappings().first()
    if not row:
        return {"type_bien": type_bien, "prix_m2": None, "n": 0, "assez": False,
                "mediane_valeur": None, "fenetre": None}
    return _gate(row["n_ventes"], row["mediane_prix_m2"], row["mediane_valeur"], row["fenetre"], type_bien, s)


def prix_sections(db: Session, secteur: str, *, seuil: int | None = None) -> list[dict]:
    """TOUS les types d'une section (terrain / maison / appartement / autre), chacun gaté par le seuil.
    Pour le Carnet de secteur, la fiche parcelle (bloc Marché) et Comparer. Trié par effectif décroissant."""
    s = seuil_section() if seuil is None else seuil
    rows = db.execute(text(
        "SELECT type_bien, n_ventes, mediane_prix_m2, mediane_valeur, fenetre FROM dvf_secteur_medianes "
        "WHERE secteur = :s ORDER BY n_ventes DESC NULLS LAST"), {"s": secteur}).mappings().all()
    out = []
    for r in rows:
        g = _gate(r["n_ventes"], r["mediane_prix_m2"], r["mediane_valeur"], r["fenetre"], r["type_bien"], s)
        out.append({"type_bien": g["type_bien"], "mediane_prix_m2": g["prix_m2"], "n_ventes": g["n"],
                    "assez": g["assez"], "mediane_valeur": g["mediane_valeur"], "fenetre": g["fenetre"]})
    return out


def medianes_sections_commune(db: Session, insee: str, type_biens, *, seuil: int | None = None) -> list[float]:
    """Les médianes €/m² des SECTIONS d'une commune (`left(secteur,5)=insee`) qui passent le seuil — pour
    un repli COMMUNE (percentile). Lecture UNIQUE de la table pour cet agrégat (Bilan mode B)."""
    s = seuil_section() if seuil is None else seuil
    rows = db.execute(text(
        "SELECT mediane_prix_m2 FROM dvf_secteur_medianes WHERE left(secteur, 5) = :c "
        "  AND type_bien = ANY(:types) AND n_ventes >= :n AND mediane_prix_m2 IS NOT NULL"),
        {"c": insee, "types": list(type_biens), "n": s}).scalars().all()
    return [float(x) for x in rows]


#: FIX-7 — score_e (batch de scoring, prix probable) lit le terrain par secteur via CETTE source (pas de
#: `FROM dvf_secteur_medianes` ailleurs). Sous-requête réutilisable : terrain par secteur, seuil `:nt`.
TERRAIN_PAR_SECTEUR_SQL = """SELECT secteur,
         max(mediane_prix_m2) FILTER (WHERE type_bien = 'terrain' AND n_ventes >= :nt) AS terrain
  FROM dvf_secteur_medianes GROUP BY secteur"""
