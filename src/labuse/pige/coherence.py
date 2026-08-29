"""RADAR-HTML (Lot 2) — RÈGLES DE COHÉRENCE : une annonce dont les champs se contredisent part en
« À QUALIFIER » et n'entre NI dans les statistiques NI dans les veilles. Jamais un fait faux servi.

Les vendeurs catégorisent mal. Cas réel (échantillon ECH-1) : un « Terrain » de 377 m² portant 12
pièces, une année de construction 1942, une surface habitable = surface terrain, et un prix au m² à
deux ordres de grandeur du terrain nu → c'est un DOMAINE BÂTI, pas un terrain.

Deux familles de contrôles :
  · STRUCTURELS (indépendants de toute donnée externe) — un terrain ne porte ni pièces, ni année de
    construction, ni surface habitable ; un bâti n'a pas surface habitable == surface terrain ;
  · RÉFÉRENTIEL — le prix au m² d'un « terrain » très éloigné du terrain nu de la commune trahit un
    bâti mal catégorisé. On lit NOTRE référentiel unique (marche_commune), jamais un chiffre inventé.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

# Écart RETENU pour le garde-fou prix/m² d'un TERRAIN, et POURQUOI (mandat : « dis quel écart »).
# Un terrain nu se négocie dans une fourchette étroite autour de la médiane de zone ; un bâti mal
# catégorisé « terrain » explose ce ratio (cas ECH-1 : ~6600 €/m² vs terrain nu ~300–450 €/m², ≈ 15×).
# On retient un facteur VOLONTAIREMENT LARGE de 4× (et 1/4 en plancher) : au-delà, le prix/m² n'est
# plus celui d'un terrain nu — presque toujours du bâti. Large pour ne PAS jeter un terrain premium
# légitime (vue mer, viabilisé, centre-ville) ; on préfère laisser passer un doute que salir la stat.
FACTEUR_PRIX_TERRAIN = 4.0


def _ref_terrain_commune_eur_m2(db: Session, commune: str) -> float | None:
    """Médiane €/m² du terrain NU de la commune (référentiel UNIQUE `ligne2_terrain_zone`), zone U de
    préférence sinon AU. None si non calculable (n trop faible) → le contrôle prix est alors ÉCARTÉ
    (pas de garde-fou = pas de verdict : on ne flague jamais sur une base absente)."""
    try:
        from ..faisabilite.marche_commune import ligne2_terrain_zone
        par_zone = ((ligne2_terrain_zone(db, commune).get("valeurs") or {}).get("par_zone")) or {}
    except Exception:  # noqa: BLE001 — un référentiel indisponible ne doit jamais casser l'ingestion
        return None
    for fam in ("U", "AU"):
        cell = par_zone.get(fam) or {}
        if cell.get("calculable") and cell.get("median_eur_m2"):
            return float(cell["median_eur_m2"])
    return None


def evaluer(rec: dict, db: Session | None = None) -> list[str]:
    """Retourne la liste des MOTIFS d'incohérence (vide = annonce cohérente). `rec` = enregistrement
    aplati (`html_next.aplatir`). `db` optionnel : sans lui, seuls les contrôles structurels tournent."""
    motifs: list[str] = []
    typ = rec.get("type")
    hab = rec.get("surface_hab")
    terr = rec.get("surface_terrain")
    pieces = rec.get("pieces")
    annee = rec.get("annee_construction")

    if typ == "terrain":
        # Un terrain nu ne porte ni pièces, ni année de construction, ni surface habitable.
        if pieces and pieces > 0:
            motifs.append(f"« terrain » portant {int(pieces)} pièces")
        if annee:
            motifs.append(f"« terrain » portant une année de construction ({int(annee)})")
        if hab and hab > 0:
            motifs.append("« terrain » portant une surface habitable")
        # chauffage renseigné sur un terrain = signe d'un bâti (le mandat citait aussi la piscine).
        if rec.get("chauffage"):
            motifs.append(f"« terrain » portant un mode de chauffage ({rec['chauffage']})")

    if typ in ("maison", "appartement", "immeuble"):
        # surface habitable == surface terrain sur un bien bâti (mandat) — improbable, souvent une
        # recopie où l'un des deux champs est faux.
        if hab and terr and abs(float(hab) - float(terr)) < 1e-6:
            motifs.append("surface habitable == surface terrain (bien bâti)")

    # Garde-fou prix/m² d'un TERRAIN (référentiel). N'ajoute JAMAIS un motif sans référentiel.
    if typ == "terrain" and db is not None and rec.get("prix") and terr and float(terr) > 0:
        ref = _ref_terrain_commune_eur_m2(db, rec.get("commune") or "")
        if ref and ref > 0:
            pm2 = float(rec["prix"]) / float(terr)
            if pm2 > FACTEUR_PRIX_TERRAIN * ref:
                motifs.append(f"prix/m² {pm2:.0f} €/m² > {FACTEUR_PRIX_TERRAIN:g}× le terrain nu de "
                              f"{rec.get('commune')} ({ref:.0f} €/m²) — probable bâti mal catégorisé")
            elif pm2 < ref / FACTEUR_PRIX_TERRAIN:
                motifs.append(f"prix/m² {pm2:.0f} €/m² < ¼ du terrain nu de {rec.get('commune')} "
                              f"({ref:.0f} €/m²) — incohérence à vérifier")
    return motifs
