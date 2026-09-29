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

from ..millesime_source import libelle_date_source as _date_source  # RETOUCHES-1 point 7 (repli nommé)

log = logging.getLogger("labuse.servitudes")
router = APIRouter(prefix="/servitudes-invisibles", tags=["servitudes-invisibles"])

# Couches « servitude dormante » lues (kind spatial_layers) → libellé.
# RECETTE-3 (T5, décision Vic) — on ne déclare QUE des couches réellement peuplées (règle
# anti-« couvert-vide »/faux RAS). Vérifié en base au 09/2026 : les six kinds rajoutés ici ont
# tous des lignes intersectables (dpu 202 · dpf 281 · zone_humide 3122 · ens 84 ·
# plu_gpu_prescription 10490 dont ER/EBC · peb 4). Le PEB — retiré à M137-T quand la couche
# était vide — est REMIS : l'ingestion des annexes GPU l'a peuplé depuis (aéroport Roland Garros,
# zones A/B/C/D). Il quitte donc aussi la liste NON_COUVERT.
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
    # RECETTE-3 (T5) — les six couches rajoutées.
    "dpu": "Droit de préemption (DPU)",
    "dpf": "Ravines et reculs (domaine public fluvial)",
    "zone_humide": "Zone humide",
    "ens": "Espace naturel protégé",
    # plu_gpu_prescription porte TOUTES les prescriptions du GPU (~20 typepsc CNIG) — on surface celles
    # qui TOUCHENT LA CONSTRUCTIBILITÉ (filtre au rendu ; PIEGES-RISQUES-2 Lot B en a élargi la liste).
    "plu_gpu_prescription": "Prescription du PLU (constructibilité)",
    "peb": "Plan d'exposition au bruit (PEB, aérodrome)",
    # GEOPF-3 — mesures compensatoires ERC (GéoMCE) : obligation écologique dormante sur la parcelle.
    "mesures_compensatoires": "Mesure compensatoire biodiversité (ERC)",
}

# typepsc CNIG surfacés = ceux qui GRÈVENT LA CONSTRUCTIBILITÉ. PIEGES-RISQUES-2 (Lot B, É3) élargit
# {01 EBC, 05 ER} — chaque ajout justifié en une ligne dans `_PRESCRIPTION_LABEL` ci-dessous.
# LAISSÉS informatifs (ne bornent pas la constructibilité nouvelle, ou déjà servis ailleurs) :
#   07 patrimoine identifié (touche la démolition/modification, pas la constructibilité neuve ; volume
#   élevé) · 16 changement de destination AUTORISÉ (permission, pas contrainte) · 02 secteur d'aléa
#   inondation (déjà servi par la couche risques, Lot B) · 31 ZNIEFF (servi par le kind `znieff`) ·
#   04 zone tendue (fiscal) · 37 non réglementé · 99 renvois du règlement graphique · 24 sentier ·
#   03/45/48 régimes ponctuels (permis de démolir, ZAC, eaux pluviales).
_PRESCRIPTION_PIEGE = {"01", "05", "08", "15", "17", "18", "19", "22"}
# Effet client des typepsc élargis (justif. constructibilité). 01/05 gardent leur libellé dédié.
_PRESCRIPTION_LABEL = {
    "08": "Terrain cultivé/planté à protéger (art. L151-23) — préservation imposée, constructibilité très restreinte",
    "15": "Règle d'implantation / bande de recul portée au règlement graphique — recul à respecter",
    "17": "Clause de logements aidés (mixité sociale, art. L151-15) — part de logements sociaux imposée au programme",
    "18": "Secteur d'orientations d'aménagement (OAP) — le projet doit être compatible avec l'OAP (à consulter)",
    "19": "Secteur protégé (richesse du sol/sous-sol) — constructibilité restreinte",
    "22": "Linéaire commercial/services obligatoire — rez-de-chaussée affecté (usage imposé)",
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
    # RECETTE-3 (T5) — le PEB était ici (couche vide à M137-T) ; il est désormais INGÉRÉ et
    # surfacé comme servitude (kind `peb`), donc retiré des « non couverts ».
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
    # RECETTE-3 (T5) — les six couches rajoutées.
    if kind == "dpu":
        renforce = "renforcé" in st or st == "dpu_renforce"
        return ("Droit de préemption urbain renforcé — la commune peut se substituer à l'acquéreur (bien "
                "et fonds de commerce)" if renforce else
                "Droit de préemption urbain — la commune peut se substituer à l'acquéreur à la vente")
    if kind == "dpf":
        return (f"Domaine public fluvial — {name} : marge de recul imposée le long du cours d'eau/plan d'eau"
                if name else "Domaine public fluvial — marge de recul imposée (ravine / cours d'eau)")
    if kind == "zone_humide":
        return (f"Zone humide — {name} : remblai, drainage et construction fortement encadrés (loi sur l'eau)"
                if name else "Zone humide — remblai, drainage et construction fortement encadrés")
    if kind == "ens":
        return (f"Espace naturel protégé — {name} : réglementation spécifique (autorisation requise)"
                if name else "Espace naturel protégé — réglementation spécifique")
    if kind == "plu_gpu_prescription":
        lib = (attrs or {}).get("libelle") or name
        if st == "01":
            return "Espace boisé classé (EBC) — inconstructible, coupe et abattage soumis à autorisation"
        if st == "05":
            return f"Emplacement réservé — {lib}" if lib and lib.lower() != "emplacement réservé" \
                else "Emplacement réservé — terrain grevé au bénéfice d'un tiers public (préemption/expropriation)"
        if st in _PRESCRIPTION_LABEL:
            base = _PRESCRIPTION_LABEL[st]
            return f"{base} — « {lib} »" if lib and lib.lower() not in base.lower() else base
        return lib or "Prescription PLU"
    if kind == "mesures_compensatoires":
        a = attrs or {}
        projet = a.get("projet") or name
        mesure = a.get("type_mesure") or a.get("classe")
        base = ("Mesure compensatoire biodiversité (séquence ERC) — gestion écologique imposée à un "
                "maître d'ouvrage ; encadre fortement l'usage du sol")
        det = " · ".join([x for x in (projet, mesure) if x])
        return f"{base} — {det}" if det else base
    if kind == "peb":
        z = ((attrs or {}).get("zone") or subtype or "").upper()
        return (f"Zone {z} du plan d'exposition au bruit (aéroport) — isolation acoustique obligatoire, "
                "constructibilité restreinte" if z else
                "Plan d'exposition au bruit (aéroport) — constructibilité restreinte")
    return name or subtype or "parcelle concernée"


AVERTISSEMENT = ("Lecture des couches déjà ingérées — sourcée et datée. L'absence d'une servitude ici "
                 "ne vaut pas absence réelle (couches non exhaustives) ; vérifiez le certificat d'urbanisme.")

# PIEGES-RISQUES-2 (Lot B, É2) — RISQUE GRADUÉ lu EN DIRECT : zonage PPR DEAL (rouge INTERDICTION /
# bleu PRESCRIPTION) + aléas Géorisques par niveau. Jusqu'ici le mode « une parcelle » ne voyait le
# PPR que par l'ASSIETTE SUP `pm1` (périmètre, sans zonage interne) — la carte et la fiche §Pièges &
# risques, elles, montrent le zonage rouge/bleu et le niveau d'aléa. On lit donc les mêmes couches
# (`ppr`, `georisque_alea`) avec le % de la parcelle touché (ST_Union), la source DEAL et le millésime.
# Miroir des seuils/libellés de la cascade `risques` (RisquesLayer + arbitrage M73), mais 100 % lecture.
_CAT_RISQUE = "Risque naturel (PPR / aléa)"
_NIVEAU_RANK = {"faible": 1, "moyen": 3, "modere": 3, "modéré": 3, "eleve": 4, "élevé": 4,
                "fort": 5, "tres_fort": 6, "très fort": 6}


def _risque_seuils(db_unused=None) -> tuple[float, float, float]:
    """Seuils PPR rouge (marginal / exclusion / couverture minimale bleue) LUS DE LA CONFIG partagée
    `cascade_rules.yaml` (couche `risques`) — mêmes valeurs que le moteur, jamais réécrites en dur."""
    try:
        from ..config import cascade_rules
        for l in (cascade_rules().get("layers") or []):
            if l.get("name") == "risques":
                p = l.get("params") or {}
                return (float(p.get("ppr_red_marginal_pct", 2)), float(p.get("ppr_red_exclude_pct", 50)),
                        float(p.get("min_coverage_pct", 10)))
    except Exception:  # noqa: BLE001 — config absente (tests) → valeurs de doctrine
        pass
    return (2.0, 50.0, 10.0)


def _clean_risque(detail: str) -> str:
    """Nettoyage client des libellés techniques (miroir de risques_arbitrage.libelle_client_detail)."""
    try:
        from .risques_arbitrage import libelle_client_detail
        return libelle_client_detail(detail) or detail
    except Exception:  # noqa: BLE001
        return detail


def aleas_parcelle(db: Session, idu: str) -> list[dict]:
    """PIEGES-RISQUES-2 (Lot B/C) — PPR zoné (rouge/bleu) + aléas par niveau, EN DIRECT, avec le % de la
    parcelle touché. Point de vérité partagé : `contraintes_parcelle` en fait des lignes plates (outil)
    et la fiche §Pièges & risques en fait son bloc « aléas ». L'assiette SUP PM1 du PPR reste servie à
    part (catégorie SUP). Retourne `[{nature, niveau, part_pct, libelle, redhibitoire, source, millesime}]`."""
    marg, excl, mincov = _risque_seuils()
    out: list[dict] = []
    # PPR zoné DEAL : INTERDICTION = rouge (3 paliers) / PRESCRIPTION = bleu. % = union sur la parcelle.
    for r in db.execute(text(
        """WITH p AS (SELECT geom_2975 g, ST_Area(geom_2975) a FROM parcels WHERE idu = :idu)
           SELECT upper(sl.subtype) AS zone, sl.attrs->>'risque' AS risque,
                  round((100 * ST_Area(ST_Union(ST_Intersection(sl.geom_2975, p.g))) / NULLIF(min(p.a), 0))::numeric)::int AS pct,
                  max(ds.name) AS source,
                  max(ds.source_millesime) AS source_millesime, max(ds.source_horizon_at) AS source_horizon_at,
                  max(COALESCE(ds.last_sync_at, ds.updated_at)::date)::text AS ingere_le
           FROM spatial_layers sl CROSS JOIN p LEFT JOIN data_sources ds ON ds.id = sl.data_source_id
           WHERE sl.kind = 'ppr' AND sl.geom_2975 IS NOT NULL AND ST_Intersects(sl.geom_2975, p.g)
             AND upper(sl.subtype) IN ('INTERDICTION', 'PRESCRIPTION')
           GROUP BY upper(sl.subtype), sl.attrs->>'risque'"""), {"idu": idu}).mappings().all():
        pct = r["pct"] or 0
        if pct <= 0:   # intersection au bord (aire arrondie à 0 %) → bruit, pas une contrainte
            continue
        # RETOUCHES-1 point 7 — libellé daté nommé selon sa provenance : « millésime <X> » si publié
        # en amont (source_millesime), sinon « ingéré le JJ/MM/AAAA » (repli d'ingestion).
        mill = _date_source(r["source_millesime"], source_horizon_at=r["source_horizon_at"], ingere_le=r["ingere_le"])
        risque = r["risque"] or "risque naturel"
        pctxt = f" (~{pct}% de la parcelle)" if pct < 99 else " (toute la parcelle)"
        if r["zone"] == "INTERDICTION":
            if pct >= excl:
                lib = f"PPR {risque} — zone rouge (inconstructible) sur {pct} % de la surface."
                red = True
            elif pct >= marg:
                lib = (f"PPR {risque} — zone rouge sur {pct} % de la surface : vigilance forte, "
                       "constructibilité à vérifier au règlement (pas d'exclusion automatique).")
                red = False
            else:
                lib = f"PPR {risque} — zone rouge marginale ({pct} %), hors emprise probable."
                red = False
            out.append({"nature": "PPR — zone rouge", "niveau": "rouge", "part_pct": pct,
                        "libelle": _clean_risque(lib), "redhibitoire": red,
                        "source": r["source"] or "DEAL Réunion", "millesime": mill})
        else:   # PRESCRIPTION = zone bleue
            lib = (f"Zone bleue PPR {risque}{pctxt} — constructible SOUS PRESCRIPTIONS (règlement DEAL).")
            out.append({"nature": "PPR — zone bleue", "niveau": "bleu", "part_pct": pct,
                        "libelle": _clean_risque(lib), "redhibitoire": False,
                        "source": r["source"] or "DEAL Réunion", "millesime": mill})
    # Aléas Géorisques : UN niveau (le plus fort) par type d'aléa, avec % touché (arbitrage M73).
    best: dict[str, tuple[int, dict]] = {}
    for a in db.execute(text(
        """WITH p AS (SELECT geom_2975 g, ST_Area(geom_2975) a FROM parcels WHERE idu = :idu)
           SELECT COALESCE(sl.attrs->>'type', sl.subtype) AS type, lower(sl.attrs->>'niveau') AS niveau,
                  round((100 * ST_Area(ST_Union(ST_Intersection(sl.geom_2975, p.g))) / NULLIF(min(p.a), 0))::numeric)::int AS pct,
                  max(ds.name) AS source,
                  max(ds.source_millesime) AS source_millesime, max(ds.source_horizon_at) AS source_horizon_at,
                  max(COALESCE(ds.last_sync_at, ds.updated_at)::date)::text AS ingere_le
           FROM spatial_layers sl CROSS JOIN p LEFT JOIN data_sources ds ON ds.id = sl.data_source_id
           WHERE sl.kind = 'georisque_alea' AND sl.geom_2975 IS NOT NULL AND ST_Intersects(sl.geom_2975, p.g)
           GROUP BY COALESCE(sl.attrs->>'type', sl.subtype), lower(sl.attrs->>'niveau')"""),
            {"idu": idu}).mappings().all():
        if (a["pct"] or 0) <= 0:   # intersection au bord → bruit
            continue
        typ = (a["type"] or "aléa").replace("submersion_marine_cc", "submersion marine (horizon 2100)")
        rank = _NIVEAU_RANK.get(a["niveau"] or "moyen", 3)
        if typ not in best or rank > best[typ][0]:
            best[typ] = (rank, a)
    for typ, (_rank, a) in best.items():
        niveau = a["niveau"] or "moyen"
        pct = a["pct"] or 0
        pctxt = f" (~{pct}% de la parcelle)" if pct < 99 else " (toute la parcelle)"
        mill = _date_source(a["source_millesime"], source_horizon_at=a["source_horizon_at"], ingere_le=a["ingere_le"])
        out.append({"nature": f"Aléa {typ}", "niveau": niveau, "part_pct": pct,
                    "libelle": _clean_risque(f"Aléa {typ} — niveau {niveau}{pctxt}."), "redhibitoire": False,
                    "source": a["source"] or "DEAL Réunion / Géorisques", "millesime": mill})
    return out


def contraintes_parcelle(db: Session, idu: str) -> list[dict]:
    """PIEGES-RISQUES-2 (Lot A) — FONCTION PARTAGÉE, point de vérité unique des contraintes dormantes
    d'UNE parcelle, lues EN DIRECT dans `spatial_layers`. Utilisée par les trois surfaces :
    l'endpoint « une parcelle » (`servitudes_invisibles`), l'outil « un lot » (`/modules/duediligence`,
    qui en fait l'UNION) et la fiche parcelle §Pièges & risques. Même source, même filtrage
    (assainissement → ANC seul ; prescriptions GPU → pièges fonciers seuls), mêmes libellés (`_detail`),
    même millésime par contrainte. Retourne `[{categorie, effet, source, date}]` trié par catégorie
    (`[]` si aucune). Ne vérifie PAS l'existence de la parcelle — l'appelant s'en charge."""
    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu)
           SELECT sl.kind, sl.subtype, sl.name, sl.attrs,
                  ds.name AS source, ds.source_millesime, ds.source_horizon_at,
                  COALESCE(ds.last_sync_at, ds.updated_at)::date AS date_source
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
        # RECETTE-3 (T5) — plu_gpu_prescription : seuls les typepsc « pièges fonciers » sont surfacés.
        if r["kind"] == "plu_gpu_prescription" and (r["subtype"] or "") not in _PRESCRIPTION_PIEGE:
            continue
        detail = _detail(r["kind"], r["subtype"], r["name"], r["attrs"])
        key = (r["kind"], detail)
        if key in seen:
            continue
        seen.add(key)
        # RETOUCHES-1 point 7 — libellé daté nommé : « millésime <X> » si publié en amont
        # (data_sources.source_millesime), sinon « ingéré le JJ/MM/AAAA » (repli d'ingestion).
        mill = _date_source(r["source_millesime"], source_horizon_at=r["source_horizon_at"],
                            ingere_le=r["date_source"])
        items.append({"categorie": _KINDS.get(r["kind"], r["kind"]), "effet": detail,
                      "source": r["source"] or "spatial_layers", "date": mill})
    # PIEGES-RISQUES-2 (Lot B) — RISQUE GRADUÉ (PPR zoné rouge/bleu + aléas par niveau) ajouté aux DEUX
    # modes : la même donnée que la couche carte et que la fiche §Pièges & risques (le mode parcelle ne
    # voyait le PPR que par l'assiette SUP, sans le zonage ni le niveau).
    for al in aleas_parcelle(db, idu):
        items.append({"categorie": _CAT_RISQUE, "effet": al["libelle"],
                      "source": al["source"], "date": al["millesime"]})
    # KELFONCIER-FIX-1 (Lot A) — une zone AU FERMÉE (ou au statut d'ouverture non déterminé) est une
    # contrainte foncière DORMANTE : la parcelle n'est pas constructible tant que le PLU n'a pas ouvert la
    # zone. Ajoutée au crible partagé → visible en mode « une parcelle », en mode « un lot » (N/M) ET en
    # fiche §Pièges & risques. Source unique : parcel_au_statut (moteur d'ouverture AU).
    if db.execute(text("SELECT to_regclass('parcel_au_statut')")).scalar() is not None:
        au = db.execute(text("SELECT classe, zone_lib FROM parcel_au_statut WHERE idu = :i"),
                        {"i": idu}).mappings().first()
        if au and au["classe"] in ("declasse_au_fermee", "declasse_au_statut_inconnu", "générique"):
            ferme = au["classe"] == "declasse_au_fermee"
            zl = f" {au['zone_lib']}" if au["zone_lib"] else ""
            items.append({
                "categorie": "Zone à urbaniser (AU)",
                "effet": (f"Zone AU{zl} FERMÉE — une modification du PLU est requise pour ouvrir la zone "
                          "à l'urbanisation (non constructible en l'état)." if ferme else
                          f"Zone AU{zl} au statut d'ouverture NON DÉTERMINÉ — constructibilité à confirmer "
                          "auprès de la commune (phasage 2AU → 1AU)."),
                "source": "LABUSE — moteur d'ouverture AU (règlement PLU calibré)", "date": None})
    items.sort(key=lambda x: x["categorie"])
    return items


@router.get("/{idu}")
def servitudes_invisibles(idu: str, db: Session = Depends(get_db)) -> dict:
    """IDU → synthèse des servitudes/contraintes dormantes intersectant la parcelle, chacune sourcée + datée."""
    if db.execute(text("SELECT to_regclass('spatial_layers')")).scalar() is None:
        raise HTTPException(503, "Couche spatial_layers absente.")
    exists = db.execute(text("SELECT 1 FROM parcels WHERE idu = :i"), {"i": idu}).first()
    if not exists:
        raise HTTPException(404, "Parcelle inconnue")
    items = contraintes_parcelle(db, idu)
    return {"idu": idu, "n": len(items), "servitudes": items,
            "synthese": (f"{len(items)} servitude(s)/contrainte(s) dormante(s) intersecte(nt) cette parcelle."
                         if items else "Aucune servitude dormante détectée dans les couches ingérées."),
            "non_couvert": _NON_COUVERT,
            "avertissement": AVERTISSEMENT}
