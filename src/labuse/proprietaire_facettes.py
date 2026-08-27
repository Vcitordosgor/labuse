"""K1 (rattrapage KelFoncier) — facettes des filtres PROPRIÉTAIRE personne morale.

La donnée est déjà en base (DGFiP « parcelles des personnes morales » millésime 2025 +
INPI RNE dirigeants). Ce module NE FABRIQUE aucune valeur : les listes viennent de `DISTINCT`
réels, avec leur COMPTE. Les libellés d'affichage (forme juridique, code APE) sont un simple
dictionnaire de lecture — la LISTE présentée reste celle des valeurs réellement en base.

Un filtre sans donnée pour une commune renvoie « couvert=False » (l'UI dit « non couvert »),
jamais un zéro silencieux. Le millésime de la source accompagne chaque réponse.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Codes « forme juridique abrégée » DGFiP réellement présents (45 distincts) → libellé lisible.
# La LISTE servie vient du DISTINCT en base ; ce dico ne fait qu'AJOUTER un libellé quand on le
# connaît (les codes inconnus s'affichent tels quels — jamais inventés).
FORME_LABELS: dict[str, str] = {
    "COM": "Commune", "SCI": "Société civile immobilière", "SEM": "Société d'économie mixte",
    "SA": "Société anonyme", "AUPM": "Autre personne morale", "DEPT": "Département",
    "ETAT": "État", "SAS": "Société par actions simplifiée", "SARL": "SARL", "COLL": "Collectivité",
    "EPIC": "Établissement public industriel et commercial", "GFA": "Groupement foncier agricole",
    "SC": "Société civile", "COAG": "Coopérative agricole", "ASS": "Association",
    "SAFR": "SAFER", "SNC": "Société en nom collectif", "REG": "Région", "GIE": "GIE",
    "HLM": "Organisme HLM", "EARL": "Exploitation agricole (EARL)", "EPCI": "Interco (EPCI)",
    "SCP": "Société civile particulière", "SCA": "Société en commandite par actions",
    "SCM": "Société civile de moyens", "GAEC": "GAEC", "SCCV": "SCCV (construction-vente)",
}

# Codes NAF/APE réellement présents (via owner_enrichment) → libellé court. Idem : liste = DISTINCT réel.
APE_LABELS: dict[str, str] = {
    "68.20B": "Location de terrains et logements", "68.20A": "Location de terrains et logements",
    "41.10D": "Promotion immobilière (logements)", "41.10A": "Promotion immobilière",
    "41.10C": "Promotion immobilière (autres bâtiments)", "68.32A": "Administration d'immeubles",
    "68.10Z": "Achat-revente de biens immobiliers", "68.31Z": "Agences immobilières",
    "64.20Z": "Sociétés holding", "70.10Z": "Sièges sociaux", "55.10Z": "Hôtels",
    "55.20Z": "Hébergement touristique", "66.30Z": "Gestion de fonds", "35.11Z": "Production d'électricité",
    "00.00Z": "Activité non renseignée", "94.99Z": "Organisation associative", "94.91Z": "Organisation religieuse",
}

MILLESIME_DEFAUT = "2025"


def _source_millesime(db: Session) -> str:
    m = db.execute(text("SELECT millesime FROM parcelle_personne_morale WHERE millesime IS NOT NULL LIMIT 1")).scalar()
    return str(m or MILLESIME_DEFAUT)


def _commune_scope(commune: str | None):
    """Fragment/where params pour restreindre à une commune (jointure parcels)."""
    if commune:
        return (" JOIN parcels p ON p.idu = pm.idu AND p.commune = :com", {"com": commune})
    return ("", {})


def facettes(db: Session, commune: str | None = None) -> dict:
    """Listes réelles (formes, APE) avec comptes + couverture PM + millésime. Le drapeau RGPD
    `filtre_age_dirigeant` est reflété (l'UI n'affiche le contrôle âge que s'il est ouvert)."""
    from .config import get_settings
    join, prm = _commune_scope(commune)

    formes = [
        {"code": c, "label": FORME_LABELS.get(c, c), "n": int(n)}
        for c, n in db.execute(text(
            f"SELECT pm.forme_juridique, count(*) FROM parcelle_personne_morale pm{join}"
            f" WHERE pm.forme_juridique IS NOT NULL GROUP BY 1 ORDER BY 2 DESC"), prm).all()
    ]
    ape_sql = ("SELECT oe.payload->>'activite_principale' ape, count(DISTINCT pm.idu)"
               " FROM parcelle_personne_morale pm JOIN owner_enrichment oe ON oe.siren = pm.siren"
               + (" JOIN parcels p ON p.idu = pm.idu AND p.commune = :com" if commune else "")
               + " WHERE oe.payload->>'activite_principale' IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 40")
    apes = [
        {"code": c, "label": APE_LABELS.get(c, c), "n": int(n)}
        for c, n in db.execute(text(ape_sql), prm).all()
    ]
    # couverture PM de la commune (ou globale) — pour dire « non couvert » plutôt qu'un zéro muet.
    if commune:
        pm_n = db.execute(text("SELECT count(*) FROM parcelle_personne_morale pm"
                               " JOIN parcels p ON p.idu = pm.idu AND p.commune = :com"), {"com": commune}).scalar()
        tot = db.execute(text("SELECT count(*) FROM parcels WHERE commune = :com"), {"com": commune}).scalar()
    else:
        pm_n = db.execute(text("SELECT count(*) FROM parcelle_personne_morale")).scalar()
        tot = db.execute(text("SELECT count(*) FROM parcels")).scalar()
    return {
        "millesime": _source_millesime(db),
        "source": "DGFiP — parcelles des personnes morales",
        "formes": formes,
        "apes": apes,
        "couverture": {"pm": int(pm_n or 0), "total": int(tot or 0),
                       "couvert": bool(pm_n)},
        "age_dirigeant_actif": bool(get_settings().filtre_age_dirigeant),
    }


def autocomplete(db: Session, q: str, commune: str | None = None, limit: int = 12) -> list[dict]:
    """Suggestions de dénomination sur les noms RÉELS en base (préfixe/inclusion), avec le nombre
    de parcelles portées. Vide si q trop court — jamais de liste inventée."""
    q = (q or "").strip()
    if len(q) < 2:
        return []
    join = " JOIN parcels p ON p.idu = pm.idu AND p.commune = :com" if commune else ""
    prm = {"q": f"%{q}%", "lim": limit}
    if commune:
        prm["com"] = commune
    rows = db.execute(text(
        f"SELECT pm.denomination, pm.siren, count(*) n FROM parcelle_personne_morale pm{join}"
        f" WHERE pm.denomination ILIKE :q GROUP BY 1, 2 ORDER BY n DESC, pm.denomination LIMIT :lim"),
        prm).all()
    return [{"denomination": d, "siren": s, "n": int(n)} for d, s, n in rows]
