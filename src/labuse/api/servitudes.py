"""O5 — SERVITUDES INVISIBLES : la synthèse des couches dormantes qui grèvent une parcelle.

Ce qui ne « crie » pas sur la fiche mais peut tout bloquer : servitudes d'utilité publique (SUP),
50 pas géométriques, classement sonore routier, secteurs d'information sur les sols (SIS/CASIAS),
recul du trait de côte, zonage d'assainissement (ANC obligatoire)…

100 % LECTURE (couche `spatial_layers` déjà ingérée) — zéro donnée nouvelle. Chaque ligne porte sa
**source** (`data_sources`) et sa **date** (dernier sync). Honnêteté : ce que la base n'ingère PAS
(PEB bruit aérien, procédures PLU, canalisations de transport, SUP hors GPU) est listé
comme **non couvert**, jamais faussement « RAS » — un couvert-vide (couche déclarée mais sans donnée)
serait lui aussi un faux RAS, on n'en déclare aucune.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.servitudes")
router = APIRouter(prefix="/servitudes-invisibles", tags=["servitudes-invisibles"])

# Couches « servitude dormante » lues (kind spatial_layers) → libellé.
# M137-T — `peb` RETIRÉ des couvertes : déclaré autrefois mais 0 ligne en base (couvert-vide =
# faux RAS sur le bruit aérien). Passé en NON COUVERT ci-dessous. On ne déclare QUE des couches
# réellement peuplées.
_KINDS = {
    "sup": "Servitude d'Utilité Publique",
    "cinquante_pas": "50 pas géométriques (bande littorale)",
    "bruit_route": "Classement sonore des voies (isolement acoustique)",
    "sol_pollue": "Secteur d'information sur les sols",
    "trait_de_cote": "Recul du trait de côte",
    # audit-risques — SEUL le NON-COLLECTIF (ANC) est une vigilance (dispositif individuel coûteux). Le
    # COLLECTIF (raccordé au tout-à-l'égout) est le cas FAVORABLE → jamais listé (faux positif filtré au
    # rendu). L'état d'assainissement complet vit déjà dans le bloc `anc` de la fiche (M86-B).
    "zonage_assainissement": "Assainissement non collectif (ANC)",
    # M137-U — ZNIEFF (inventaire du patrimoine naturel) : contrainte dormante, subtype = type I/II.
    "znieff": "ZNIEFF — zone naturelle d'intérêt écologique",
}

# Codes SUP normalisés (Géoportail de l'urbanisme) → effet concret.
# audit-risques : ac3/el10/pm2 sortaient bruts (« SUP xxx ») → mappés ici. Sens confirmé sur la donnée
# et le code d'ingestion : el10 = Parc national de La Réunion (sup_gpu.py/etage1.py) ; pm2 = installations
# classées / stockage de déchets ICPE (noms « Stockage_dechets… », layers_ingest.py:316) ; ac3 = réserves
# naturelles (Marine de La Réunion, Étang de Saint-Paul). Vérifié : plus AUCUN sous-type présent en base
# (ac1/ac2/ac3/ac4/el10/pm1/pm2/pm3) ne manque au mapping.
_SUP = {
    "pm1": "Risques naturels (PPR) — prescriptions constructives", "pm3": "Risques technologiques (PPRT)",
    "pm2": "Installation classée / stockage de déchets (ICPE) — périmètre de servitude",
    "ac1": "Abords de Monument historique — avis ABF", "ac2": "Site classé/inscrit — autorisation spéciale",
    "ac3": "Réserve naturelle — protection réglementaire (autorisation spéciale)",
    "ac4": "ZPPAUP/AVAP — prescriptions patrimoniales",
    "el10": "Parc national — réglementation (cœur / aire d'adhésion)",
    "i4": "Ligne électrique — surplomb/ancrage", "i3": "Canalisation de gaz — bande de servitude",
    "i1": "Canalisation d'hydrocarbures", "as1": "Captage d'eau potable — périmètre de protection",
    "el3": "Halage / marchepied (cours d'eau)", "el7": "Alignement de voirie",
    "t1": "Voie ferrée — servitude ferroviaire", "pt1": "Télécoms — protection réception",
    "pt2": "Télécoms — protection contre obstacles", "pt3": "Télécoms — réseaux",
    "int1": "Cimetière — périmètre", "a4": "Cours d'eau non domanial — entretien",
}

_SOL_POLLUE = {"sis": "Secteur d'Information sur les Sols (SIS) — étude de sols obligatoire",
               "casias": "Ancien site industriel (CASIAS)", "instruction": "Site en cours d'instruction"}

# Contraintes attendues mais NON ingérées / partiellement couvertes — À DIRE, jamais un « RAS »
# silencieux (M137-T : liste étendue à tout ce que l'audit a trouvé). Bloc servi à l'entrée
# « une parcelle » ET reporté sur l'entrée « un lot » (outil Risques) — c'est le point critique.
# LOT3 (OUTILS-FINALE) — vérité passée au crible :
#  · RNIC RETIRÉ de la liste : le registre EST ingéré (rnic_coproprietes, 2 220 copropriétés) ET
#    surfacé en fiche (CoproprietesBlock, M125-2). L'annoncer « non couvert » était FAUX (péremption).
#  · SUP : chiffre honnête — 417 SUP ingérées, 8 familles réellement présentes (pm1/pm2/pm3/ac1/ac2/
#    ac3/ac4/el10, toutes décodées). L'ancien « ~17 familles » ne correspondait ni au mapping ni à la base.
NON_COUVERT = [
    "Plan d'Exposition au Bruit (PEB, aérodrome) — couche non ingérée : le bruit aérien n'est pas détecté ici",
    "Procédures PLU en cours (révision/élaboration) — voir l'outil PLU (radar Sudocuh) ; non reprises ici",
    "Canalisations de transport de matières dangereuses (gaz, hydrocarbures) — couche non ingérée",
    "Servitudes d'Utilité Publique hors GPU Réunion — 417 SUP ingérées (8 familles présentes, toutes "
    "décodées) ; une SUP non publiée au Géoportail de l'urbanisme n'est pas vue (certificat d'urbanisme indispensable)",
]
_NON_COUVERT = NON_COUVERT   # rétro-compat (tests + anciens imports)


def get_db():
    from .app import get_db as _g
    yield from _g()


def _detail(kind: str, subtype: str | None, name: str | None, attrs: dict | None) -> str:
    st = (subtype or "").lower()
    if kind == "sup":
        base = _SUP.get(st, f"SUP {subtype or '?'}")
        typeass = (attrs or {}).get("typeass")
        return f"{base}" + (f" — {typeass}" if typeass else "")
    if kind == "sol_pollue":
        return _SOL_POLLUE.get(st, name or "site répertorié")
    if kind == "zonage_assainissement":   # (déjà filtré au non-collectif en amont)
        return "Dispositif individuel à prévoir (coût à anticiper au budget)"
    if kind == "bruit_route":
        return f"catégorie {st.removeprefix('cat')}" if st else (name or "voie classée")
    if kind == "znieff":
        # distingue type I / type II : ils ne pèsent pas pareil en instruction.
        t = subtype or "ZNIEFF"
        return (f"{t} — {name} : contrainte environnementale (études d'impact renforcées, risque de "
                f"recours) ; n'interdit pas de construire" if name else t)
    return name or subtype or "parcelle concernée"


@router.get("/{idu}")
def servitudes_invisibles(idu: str, db: Session = Depends(get_db)) -> dict:
    """IDU → synthèse des servitudes/contraintes dormantes intersectant la parcelle, chacune sourcée + datée."""
    if db.execute(text("SELECT to_regclass('spatial_layers')")).scalar() is None:
        raise HTTPException(503, "Couche spatial_layers absente.")
    exists = db.execute(text("SELECT 1 FROM parcels WHERE idu = :i"), {"i": idu}).first()
    if not exists:
        raise HTTPException(404, "Parcelle inconnue")

    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT sl.kind, sl.subtype, sl.name, sl.attrs,
                  ds.name AS source, COALESCE(ds.last_sync_at, ds.updated_at)::date AS date_source
           FROM spatial_layers sl LEFT JOIN data_sources ds ON ds.id = sl.data_source_id, p
           WHERE sl.kind = ANY(:kinds) AND sl.geom_2975 IS NOT NULL
             AND ST_Intersects(sl.geom_2975, p.geom_2975)"""),
        {"idu": idu, "kinds": list(_KINDS)}).mappings().all()

    # dédup (kind, detail) — une SUP répétée (enveloppes gen1/gen2) = une ligne
    seen, items = set(), []
    for r in rows:
        # audit-risques — zonage d'assainissement : SEUL le non-collectif (ANC) est une vigilance ; le
        # collectif (raccordé) est le cas FAVORABLE et n'est JAMAIS une servitude (faux positif sur
        # 67 208 parcelles avant ce filtre). L'assainissement complet vit dans le bloc `anc` de la fiche.
        if r["kind"] == "zonage_assainissement" and (r["subtype"] or "").lower() != "anc":
            continue
        detail = _detail(r["kind"], r["subtype"], r["name"], r["attrs"])
        key = (r["kind"], detail)
        if key in seen:
            continue
        seen.add(key)
        items.append({"categorie": _KINDS.get(r["kind"], r["kind"]), "effet": detail,
                      "source": r["source"] or "spatial_layers", "date": str(r["date_source"]) if r["date_source"] else None})
    items.sort(key=lambda x: x["categorie"])

    return {"idu": idu, "n": len(items), "servitudes": items,
            "synthese": (f"{len(items)} servitude(s)/contrainte(s) dormante(s) intersecte(nt) cette parcelle."
                         if items else "Aucune servitude dormante détectée dans les couches ingérées."),
            "non_couvert": _NON_COUVERT,
            "avertissement": ("Lecture des couches déjà ingérées — sourcée et datée. L'absence d'une servitude ici "
                              "ne vaut pas absence réelle (couches non exhaustives) ; vérifiez le certificat d'urbanisme.")}
