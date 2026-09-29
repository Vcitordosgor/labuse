"""OUTILS-6 — LES BLOCS AJOUTÉS DE LA FICHE COMMUNE (C5) + les compteurs des passerelles (C6).

Doctrine transversale : **un seul moteur, une seule donnée**. Aucune donnée n'est recalculée ici — chaque
bloc CONSOMME le point de calcul EXISTANT de l'outil d'origine (Radar, Pièges & risques, Étude de zone,
veille PLU, Permis, Densifier) et se contente de le présenter à la maille commune. Introuvable = null (le
front affiche « non disponible » sourcé, jamais un zéro menteur). Rien n'entre dans le scoring.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


# ───────────────────────────── C2 — les chiffres COMMUNS au comparateur ─────────────────────────────
def comparable(db: Session, commune: str) -> dict | None:
    """Les chiffres que la fiche PARTAGE avec le comparateur des 24 communes (OUTILS-6 C2) : ils viennent
    de la MÊME source (`comparateur.raw_rows`, même run, mêmes requêtes) → chaque valeur est identique des
    deux côtés, par construction. Le prix ancien est la médiane COMMUNE ENTIÈRE (baromètre DVF), jamais le
    `sector_price` local d'une parcelle représentative."""
    from .comparateur import raw_rows
    r = raw_rows(db).get(commune)
    if not r:
        return None
    velo = r.get("velocite")
    return {
        "ancien_median_eur_m2": r.get("prix_ancien"),
        "ancien_n": r.get("prix_ancien_n"),
        "neuf_eur_m2": r.get("prix_neuf"),
        "permis_5a": r.get("permis"),
        "delai_median_mois": round(float(velo), 1) if velo is not None else None,
        "stock_opportunites_n": r.get("stock"),
        "source": "DVF (baromètre commune entière) + SITADEL (autorisations et délais d'instruction) — "
                  "même moteur que le comparateur des 24 communes.",
    }


# ───────────────────────────── C5 — le marché des annonces (Radar) ─────────────────────────────
def marche_annonces(db: Session, commune: str) -> dict | None:
    """Radar LABUSE, à la maille commune. Même seuil d'affichage que le bloc Communes (OUTILS-2) :
    servi à partir de `SEUIL_N` biens, sinon `sous_seuil=True` (le front replie en une phrase). L'écart
    demandé/acté — le signal exclusif LABUSE — est calculé entre le prix demandé (annonces, bâti) et le
    prix acté commune entière (baromètre DVF, cf. `comparable`). None si Radar ne couvre pas la commune."""
    from ..pige.marche import SEUIL_N, stats
    # COMMUNE-FIX-1 (A2) — le seuil Radar (30) : un prix demandé médian (et donc l'écart demandé/acté)
    # calculé sur moins de 30 biens n'est pas statistiquement robuste (le même seuil que la référence
    # de type du Radar). Sous ce seuil, on ne sert NI le médian NI le pourcentage — la fiche dira
    # « sous le seuil (N biens) », jamais un −31 % tiré de 5 annonces.
    from ..pige.signaux import SEUIL_REF_TYPE
    row = next((c for c in stats(db).get("communes", []) if c.get("commune") == commune), None)
    if not row:
        return None
    demande = (row.get("prix_m2_bati") or {}).get("valeur")
    demande_n = (row.get("prix_m2_bati") or {}).get("n")
    cmp = comparable(db, commune) or {}
    acte = cmp.get("ancien_median_eur_m2")
    biens = int(row.get("actives") or 0)
    robuste = demande is not None and demande_n is not None and demande_n >= SEUIL_REF_TYPE
    ecart = round(100.0 * (demande - acte) / acte, 1) if (robuste and acte) else None
    return {
        "biens": biens,
        "seuil_n": SEUIL_N,
        "sous_seuil": biens < SEUIL_N,
        # COMMUNE-FIX-1 (A2) — seuil de robustesse du prix demandé médian / de l'écart (Radar, 30 biens).
        "demande_seuil_n": SEUIL_REF_TYPE,
        "demande_sous_seuil": demande is not None and not robuste,
        "prix_demande_median_eur_m2": demande if robuste else None,
        "prix_demande_n": demande_n,
        "ecart_demande_acte_pct": ecart,
        "prix_acte_eur_m2": acte,
        "source": "Radar LABUSE (annonces relevées) · écart mesuré contre le baromètre DVF commune entière.",
    }


# ───────────────────────────── C5 — les risques (Géorisques / Pièges & risques) ─────────────────────────────
def risques(db: Session, commune: str, insee: str | None) -> dict:
    """Part des parcelles de la commune exposées, par couche Géorisques déjà ingérée (mêmes couches
    `spatial_layers` que l'outil Pièges & risques), + le nombre d'arrêtés CatNat (table `catnat_arretes`)
    et la présence du Parc National. Les libellés restent fidèles à la donnée : la couche `ppr` n'ayant
    pas de sous-type dans nos attributs, on n'invente pas « inondation » — on dit « PPR (risque naturel) »."""
    # CIRCUIT-2 lot 1.6 — la part par couche est calculée par le moteur nommé `commune_compteurs`
    # (id registre ppr_pct) : ce robinet ne calcule plus, il appelle (le total est calculé une fois).
    from ..registre.moteurs.commune import pct_parcelles_couche
    tot = db.execute(text("SELECT count(*) FROM parcels WHERE commune = :c"), {"c": commune}).scalar() or 0

    def _pct_layer(kind: str, subtype: str | None = None) -> float | None:
        return pct_parcelles_couche(db, commune, kind, tot, subtype)

    catnat = (db.execute(text("SELECT count(*) FROM catnat_arretes WHERE insee = :i"),
                         {"i": insee}).scalar() or 0) if insee else 0
    # SOURCES-4 lot 1 — le détail des arrêtés dormait dans `catnat_arretes` (seul le COMPTE était
    # servi). On surface la liste : le péril, les trois dates (début/fin/arrêté) et le code national
    # + la date de publication au JO (jusque-là seulement dans `raw`). 12 plus récents — la fiche dit
    # « et N autres » via le compte total. Chaque champ vient du producteur (GASPAR/Géorisques).
    catnat_detail = [dict(r) for r in db.execute(text(
        "SELECT type_peril, "
        "       to_char(date_debut, 'YYYY-MM-DD') AS date_debut, "
        "       to_char(date_fin, 'YYYY-MM-DD') AS date_fin, "
        "       to_char(date_arrete, 'YYYY-MM-DD') AS date_arrete, "
        "       raw->>'code_national_catnat' AS code_national, "
        "       raw->>'date_publication_jo' AS date_publication_jo "
        "FROM catnat_arretes WHERE insee = :i "
        "ORDER BY date_debut DESC NULLS LAST, date_arrete DESC NULLS LAST LIMIT 12"),
        {"i": insee}).mappings().all()] if insee else []
    parc = db.execute(text(
        "SELECT EXISTS (SELECT 1 FROM parcels p JOIN spatial_layers sl ON sl.kind = 'parc_national' "
        "AND ST_Intersects(p.geom_2975, sl.geom_2975) WHERE p.commune = :c)"), {"c": commune}).scalar()
    # SOURCES-1 lot 2 — le fait AZI/TRI de la commune (GASPAR, table azi_communes) : quels
    # documents inondation couvrent la commune. None si la source n'est pas ingérée.
    azi_tri = None
    if insee:
        try:
            from ..ingestion.azi_tri import azi_tri_commune
            azi_tri = azi_tri_commune(db, insee)
        except Exception:  # noqa: BLE001 — table absente = source non ingérée, jamais un 500
            db.rollback()
            azi_tri = None
    return {
        "ppr_pct": _pct_layer("ppr"),
        # SOURCES-FIX-2 lot A — aléa mouvement de terrain = l'aléa RÉGLEMENTAIRE zoné
        # (kind='georisque_alea' subtype='mouvement_terrain', DEAL PPR/aléas source 30), MÊME
        # donnée que la couche carte `alea_mvt` et la fiche §Pièges & risques. (Avant : kind='mvt'
        # = inventaire d'événements BDMvt Géorisques source 36, une notion distincte non zonée.)
        "mouvement_terrain_pct": _pct_layer("georisque_alea", "mouvement_terrain"),
        "catnat_arretes": int(catnat),
        "catnat_detail": catnat_detail,   # SOURCES-4 lot 1 — arrêtés détaillés (péril, dates, code national)
        "parc_national": bool(parc),
        "azi_tri": azi_tri,
        "source": "DEAL Réunion — PPR / aléas (zones PPR, aléa mouvement de terrain) · GASPAR (arrêtés CatNat, AZI/TRI) · BD TOPO (Parc National).",
    }


# ───────────────────────────── C5 — population & revenu (Étude de zone / Filosofi) ─────────────────────────────
def population(db: Session, commune: str, insee: str | None) -> dict:
    """Habitants, ménages et niveau de vie moyen. COMMUNE-FIX-1 (A1) — les HABITANTS sont désormais la
    POPULATION LÉGALE INSEE (population municipale du recensement, `sudocuh_procedures.pop_mun`), plus
    l'agrégat Filosofi (carreaux fiscaux) qui SOUS-ESTIMAIT la population (Saint-Paul 96 786 Filosofi vs
    105 240 légaux) et qu'on présentait à tort comme « INSEE ». Filosofi ne sert plus QUE le NIVEAU DE VIE
    (revenu, sa vocation). Les ménages viennent des résidences principales du RP (`commune_insee_logement`,
    base cohérente avec la population légale), plus des ménages fiscaux Filosofi. `ind_snv/ind` reste un
    niveau de vie MOYEN, pas une médiane. Mémoïsé 1 h (l'agrégat spatial Filosofi est coûteux)."""
    from .app import _mem_cached

    def _c():
        r = db.execute(text(
            "SELECT round(sum(f.ind_snv) / NULLIF(sum(f.ind), 0)) niveau_vie_moyen "
            "FROM filosofi_carreaux_200m f WHERE EXISTS ("
            "  SELECT 1 FROM parcels p WHERE p.commune = :c "
            "  AND ST_Intersects(p.geom_2975, ST_Centroid(f.geom)))"), {"c": commune}).mappings().first()
        return dict(r) if r else {}
    demo = _mem_cached(("fiche-pop", commune), 3600.0, _c)
    # COMMUNE-FIX-1 (A1) — population LÉGALE INSEE (population municipale du recensement).
    # COHERENCE-FIX-1 (lot E) — le MILLÉSIME LE PLUS RÉCENT d'abord : `population_legale`
    # (populations légales en vigueur, geo.api.gouv/INSEE, année affichée), repli Sudocuh
    # (fichier DGALN, recensement plus ancien — 10 communes sur 24 servies 5-8 % sous la
    # population en vigueur, FAUX-CLIENT n° 6 de l'audit) avec SON millésime affiché.
    from ..ingestion.population_legale import lire as _pop_legale
    pl = _pop_legale(db, insee) if insee else None
    poplegale = db.execute(text(
        "SELECT pop_mun, pop_tot, to_char(millesime_date, 'DD/MM/YYYY') AS millesime "
        "FROM sudocuh_procedures WHERE insee = :i"), {"i": insee}).mappings().first() if insee else None
    if pl is not None:
        habitants = pl["pop_mun"]
    else:
        habitants = int(poplegale["pop_mun"]) if poplegale and poplegale["pop_mun"] is not None else None
    log = db.execute(text("SELECT logements, vacants, res_principales, millesime FROM commune_insee_logement "
                          "WHERE insee = :i"), {"i": insee}).mappings().first() if insee else None
    logements = int(log["logements"]) if log and log["logements"] is not None else None
    vacants = int(log["vacants"]) if log and log["vacants"] is not None else None
    # COMMUNE-FIX-1 (A1) — ménages = résidences principales du RP (base légale), et non les ménages
    # FISCAUX Filosofi (qui sous-comptent), pour ne garder Filosofi QUE sur le niveau de vie.
    menages = int(log["res_principales"]) if log and log.get("res_principales") is not None else None
    # CIRCUIT-2 lot 1.6 — le taux de vacance est calculé par le moteur nommé `commune_compteurs`
    # (id registre vacance_pct) : même arithmétique, un seul chemin.
    from ..registre.moteurs.commune import vacance_pct
    # SOURCES-1 lot 6 — l'affinage par QUARTIER (IRIS RP2022) : n IRIS, vacance min/méd/max.
    # Maille DITE ; commune_insee_logement reste la vérité communale. None si non ingéré.
    quartiers = None
    if insee and db.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'iris_rp'")).first():
        from ..ingestion.iris_rp import quartiers_commune
        quartiers = quartiers_commune(db, insee)
    return {
        "quartiers": quartiers,
        "habitants": habitants,                       # COMMUNE-FIX-1 (A1) — population LÉGALE (municipale) INSEE
        # pop_totale : uniquement quand les habitants viennent de la MÊME source (Sudocuh) — jamais
        # deux millésimes mélangés dans la même ligne.
        "habitants_pop_totale": (int(poplegale["pop_tot"])
                                 if (pl is None and poplegale and poplegale["pop_tot"] is not None) else None),
        # COHERENCE-FIX-1 (lot E) — l'ANNÉE au client, partout : « Population légale 2023 (INSEE) ».
        "habitants_millesime": (str(pl["millesime"]) if pl is not None
                                else (poplegale["millesime"] if poplegale else None)),
        "habitants_etiquette": (pl["etiquette"] if pl is not None
                                else (f"Population municipale légale INSEE (Sudocuh, {poplegale['millesime']})"
                                      if poplegale and poplegale["millesime"] else None)),
        "menages": menages,                           # COMMUNE-FIX-1 (A1) — résidences principales (RP), base légale
        "menages_millesime": (log or {}).get("millesime"),
        "niveau_vie_moyen_eur": int(demo["niveau_vie_moyen"]) if demo.get("niveau_vie_moyen") is not None else None,
        "logements": logements,
        "vacants": vacants,
        "vacance_pct": vacance_pct(logements, vacants),
        # DONNEES-1 lot 2.4 — ÂGE DU PARC (RP2022, table rp_logement_commune, variable ACHL) :
        # part du parc de logements construit AVANT 1991 (stock ancien = potentiel de rénovation /
        # démolition-reconstruction). Le reste des variables logement de rp_logement_commune (type
        # maison/appartement, tenure, vacance, parc social) est DÉJÀ servi ici via
        # commune_insee_logement / IRIS / RPLS — donc DOUBLON, non rebranché. L'âge du parc, lui,
        # n'était nulle part (seul le millésime médian du parc SOCIAL l'était via RPLS).
        "parc_ancien_pct": _parc_ancien_pct(db, insee),
        "source": "INSEE — population municipale légale (recensement, via Sudocuh) · INSEE RP "
                  "(ménages, logements) · INSEE Filosofi (niveau de vie).",
    }


def _parc_ancien_pct(db: Session, insee: str | None) -> float | None:
    """Part (%) du parc de logements construit AVANT 1991, depuis la distribution ACHL (période
    d'achèvement) de rp_logement_commune (RP2022). Codes INSEE : A11 (< 1919), A12 (1919-1945),
    B11 (1946-1970), B12 (1971-1990) = ancien ; C… = 1991 et après. None si table/donnée absente."""
    if not insee or not db.execute(text("SELECT to_regclass('rp_logement_commune')")).scalar():
        return None
    row = db.execute(text("SELECT distributions -> 'ACHL' AS achl FROM rp_logement_commune "
                          "WHERE insee = :i"), {"i": insee}).mappings().first()
    achl = (row or {}).get("achl") if row else None
    if not achl:
        return None
    total = sum(float(v) for v in achl.values())
    ancien = sum(float(v) for k, v in achl.items() if k[:1] in ("A", "B"))
    return round(100.0 * ancien / total, 1) if total > 0 else None


# ───────────────────────────── C5 — le PLU (statut + document d'urbanisme) ─────────────────────────────
_PLU_STATUT = {
    "cloturee": "à jour", "aucune": "à jour",
    "revision_plu": "en révision", "elaboration_plu": "en élaboration",
    "modification_plu": "en modification",
}


def plu_statut(db: Session, insee: str | None, commune: str | None) -> dict:
    """Statut du document d'urbanisme (à jour / en révision / RNU), sa date d'opposabilité et le lien vers
    la recherche verbatim. Statut CALCULÉ (registre `veille_plu` + `rnu`), jamais en dur (correctif A5
    d'OUTILS-1). RNU = pas de PLU opposable ; l'emporte sur toute procédure."""
    from .. import rnu as rnu_mod
    if rnu_mod.is_rnu_insee(insee):
        return {"statut": "RNU", "libelle": "Règlement National d'Urbanisme (pas de PLU opposable)",
                "date_reglement": None, "recherche_verbatim": True,
                "source": "config/rnu_communes.yaml"}
    from .. import veille_plu
    e = veille_plu.entry(insee) or {}
    proc = e.get("procedure")
    # COMMUNE-FIX-1 (D12) — la PROCÉDURE PLU EN COURS au dernier relevé Sudocuh (révision, modification,
    # élaboration…), avec son millésime : le fait producteur brut, daté, à côté du statut déduit.
    procedure_sudocuh = None
    if insee:
        row = db.execute(text(
            "SELECT du_en_cours, etat_detaille, to_char(prescription_proc, 'DD/MM/YYYY') AS prescription, "
            "       to_char(millesime_date, 'DD/MM/YYYY') AS millesime "
            "FROM sudocuh_procedures WHERE insee = :i"), {"i": insee}).mappings().first()
        if row and (row["etat_detaille"] or row["du_en_cours"]):
            procedure_sudocuh = {"document": row["du_en_cours"], "etat": row["etat_detaille"],
                                 "prescription": row["prescription"], "millesime": row["millesime"]}
    return {
        "statut": _PLU_STATUT.get(proc, "document local"),
        "libelle": e.get("stade"),
        "procedure": proc,
        "procedure_sudocuh": procedure_sudocuh,   # COMMUNE-FIX-1 (D12) — révision/modification en cours (Sudocuh)
        "date_reglement": None if e.get("date_acte") in (None, "ABSENT") else e.get("date_acte"),
        "confiance": e.get("confiance"),
        "recherche_verbatim": True,
        "source": e.get("source"),
    }


def scot_commune(db: Session, commune: str) -> dict | None:
    """GEOPF-3 — nom du SCOT et date d'approbation de la commune (spatial_layers kind='scot', GPU).
    Passe-plat : le SCOT dont le PÉRIMÈTRE CONTIENT le centroïde de la commune (le simple « une
    parcelle intersecte » attrapait les débordements de bord — Saint-Denis rattaché à tort au SCOT
    voisin). None si le centroïde n'est dans aucun périmètre (ex. Est/CIREST, SCOT non publié au GPU)."""
    row = db.execute(text(
        "WITH c AS (SELECT ST_Centroid(ST_Collect(geom_2975)) g FROM parcels WHERE commune = :c) "
        "SELECT s.name AS nom, s.attrs->>'date_approbation' AS date_appro, "
        "       s.attrs->>'statut' AS statut, ds.name AS source "
        "FROM spatial_layers s LEFT JOIN data_sources ds ON ds.id = s.data_source_id, c "
        "WHERE s.kind = 'scot' AND s.geom_2975 IS NOT NULL AND c.g IS NOT NULL "
        "  AND ST_Contains(s.geom_2975, c.g) LIMIT 1"), {"c": commune}).mappings().first()
    if not row:
        return None
    return {"nom": row["nom"], "date_approbation": row["date_appro"], "statut": row["statut"],
            "source": row["source"] or "Géoportail de l'urbanisme (GPU)"}


# ───────────────────────────── C5 — construire ici (permis + point mort) ─────────────────────────────
def permis_bloc(db: Session, commune: str) -> dict:
    """Le bloc « Construire ici » : permis autorisés (12 mois / 5 ans) et délai d'instruction viennent des
    MÊMES sources que le comparateur (SITADEL + m10, cf. `comparable`) ; les permis DORMANTS (au point
    mort) viennent du MÊME moteur/id que l'outil Permis (`permis_point_mort` / point_mort_n)."""
    from ..faisabilite.marche_commune import ligne6_offre_engagee
    from ..registre.moteurs.commune import permis_point_mort
    from .. import runs
    offre = ligne6_offre_engagee(db, commune)
    # OUTILS-FIX-5 L5 — « dormants » de la fiche commune = LE MÊME id que l'outil Permis
    # (point_mort_n = permis_point_mort : PC sans DAACT depuis 36 mois sur parcelle non bâtie au run
    # servi). Avant, la fiche comptait pc_caducs (103 à Saint-Benoît) quand l'outil affichait le point
    # mort (651) sous le même mot « dormants » — un seul id, un seul chiffre désormais (cœur OUTILS-FIX-5).
    point_mort = permis_point_mort(db, commune, months=36, run=runs.cascade())
    cmp = comparable(db, commune) or {}
    # KELFONCIER-FIX-1 (Lot C) — compteurs PC / PA / DP (+ PD) et ANNULÉS sur 12 mois, à la maille
    # commune (Sitadel). L'état ANNULÉ (ETAT_DAU=4) est SÉPARÉ des autorisés (avant, il les gonflait).
    # Purement descriptif : ne touche NI le point mort (Signal) NI les variables pc_*.
    type_rows = db.execute(text(
        """SELECT type,
                  count(*) FILTER (WHERE raw->>'etat' IS DISTINCT FROM '4') AS n,
                  count(*) FILTER (WHERE raw->>'etat' = '4')                 AS n_annules
             FROM sitadel_permits
            WHERE (CAST(:c AS text) IS NULL OR commune = :c)
              AND date >= (CURRENT_DATE - interval '12 months')
            GROUP BY type"""), {"c": commune}).mappings().all()
    par_type = {r["type"]: int(r["n"] or 0) for r in type_rows if int(r["n"] or 0)}
    annules_12m = sum(int(r["n_annules"] or 0) for r in type_rows)
    return {
        "permis_12m": (offre.get("valeurs") or {}).get("permis_12m") or 0,
        "permis_5a": cmp.get("permis_5a"),
        "logements_12m": (offre.get("valeurs") or {}).get("logements_12m"),
        "delai_median_mois": cmp.get("delai_median_mois"),
        "point_mort": int(point_mort),
        # KELFONCIER-FIX-1 (Lot C) — ventilation PC/PA/DP/PD (autorisés, 12 mois) + annulés, servie à
        # la carte « Permis et rythme ». Chaque clé = type Sitadel ; libellés = ingestion.permits._TYPE_LABEL.
        "permis_type_12m": par_type,
        "permis_annules_12m": annules_12m,
        "source": "SITADEL (autorisations) · SITADEL — délais d'instruction · permis au point mort (36 mois sans DAACT, run servi).",
    }


# ───────────────────────────── C5 — densifiables / gisement + loyer sourcé ─────────────────────────────
def densifiables(db: Session, commune: str) -> dict | None:
    """Le gisement de densification (parcelles à capacité résiduelle + SDP), depuis le point de calcul de
    l'outil Densifier (`ligne7_gisement`, tiers servables du run servi). None si non calculable."""
    from ..faisabilite.marche_commune import ligne7_gisement
    g = ligne7_gisement(db, commune)
    if not g.get("calculable"):
        return None
    v = g.get("valeurs") or {}
    return {"parcelles": v.get("parcelles"), "sdp_residuelle_m2": v.get("sdp_residuelle_m2"),
            "source": g.get("etiquette")}


def loyer(db: Session, commune: str) -> dict | None:
    """Loyer médian — SOURCÉ (le seul chiffre de l'ancienne fiche sans source ni millésime). On lit la
    ligne loyer du bloc Marché commune (`build_marche_commune`), qui porte sa source. None = non calculable
    (jamais un chiffre nu)."""
    from ..faisabilite.marche_commune import build_marche_commune
    mc = build_marche_commune(db, commune)
    lg = next((l for l in mc.get("lignes", []) if l.get("cle") == "loyer_median"), None)
    if not lg:
        return None
    v = lg.get("valeurs") or {}
    if v.get("loyer_eur_m2") is None:
        return None
    return {"median_eur_m2": v.get("loyer_eur_m2"), "type": v.get("type"),
            "source": lg.get("etiquette") or lg.get("source") or "DHUP (carte des loyers)"}


def prix_neuf_observe(db: Session, insee: str | None) -> dict | None:
    """COMMUNE-RANGEMENT-2 lot 2 — prix du neuf OBSERVÉ à la maille commune (table dvf_prix_sortie_neuf,
    niveau='commune' ; repli île marqué). Notion SCINDÉE du VEFA à l'acte (prix_neuf_vefa_acte_eur_m2,
    déjà servi) — la maquette (carte Prix) demande les DEUX. La fiche parcelle sert le même id résolu par
    parcelle (cascade secteur>commune>île) ; ici on lit directement le niveau commune. None si absent."""
    if not insee:
        return None
    row = db.execute(text(
        "SELECT prix_m2_neuf, n FROM dvf_prix_sortie_neuf WHERE cle = :i AND niveau = 'commune' "
        "AND prix_m2_neuf IS NOT NULL LIMIT 1"), {"i": insee}).mappings().first()
    if row and row["prix_m2_neuf"] is not None:
        return {"eur_m2": round(float(row["prix_m2_neuf"])), "niveau": "commune",
                "n": int(row["n"]) if row["n"] is not None else None,
                "source": "DVF — prix du neuf observé (ventes ≤ 3 ans après achèvement), grain commune"}
    return None


def parc_social(db: Session, insee: str | None) -> dict | None:
    """COMMUNE-RANGEMENT-1 (lot 2) — le parc social RPLS de la commune (table `rpls_commune`, SDES),
    fait 100 % communal. Il était servi UNIQUEMENT au contexte marché de la fiche PARCELLE (mal rangé :
    une info commune invisible depuis la commune) ; on le sert désormais à la fiche commune (carte
    Population & logement). `pct_qpv` reste NON servi (non discriminant, RETOURS-11F). None si non ingéré."""
    if not insee:
        return None
    r = db.execute(text(
        "SELECT nb_logements, construct_median FROM rpls_commune WHERE insee = :i"),
        {"i": insee}).mappings().first()
    if not r or r["nb_logements"] is None:
        return None
    return {"logements": int(r["nb_logements"]),
            "construct_median": int(r["construct_median"]) if r["construct_median"] is not None else None,
            "millesime": "RPLS 01/01/2025",
            "source": "SDES — Répertoire des logements locatifs sociaux (RPLS)"}


def fiscalite(db: Session, insee: str | None) -> dict | None:
    """SOURCES-1 lot 5 — taux fonciers de la commune (REI DGFiP) : TFPB commune + EPCI, TEOM.
    Passe-plat sourcé + daté ; None si non ingéré (jamais un taux inventé).
    RECETTE-4 U1 — porte un drapeau de FRAÎCHEUR (`perime`) : la donnée dont l'ingestion date de
    plus d'un an est signalée « à rafraîchir » (mêmes gestes que la taxe d'aménagement)."""
    if not insee:
        return None
    from ..ingestion.rei import rei_commune
    r = rei_commune(db, insee)
    if r is None:
        return None
    from ..fiscalite_libelle import lignes_taxe_fonciere
    bloc = {"tfpb_commune_pct": r["tfpb_commune_pct"], "tfpb_epci_pct": r["tfpb_epci_pct"],
            "teom_pct": r["teom_pct"], "millesime": r["millesime"],
            # SOURCES-4 lot 2 — la TFPNB (taxe foncière sur le NON BÂTI, la plus pertinente pour un
            # terrain) était ingérée mais jamais servie ; on l'ajoute au bloc fiscalité (commune + EPCI).
            "tfpnb_commune_pct": r.get("tfpnb_commune_pct"), "tfpnb_epci_pct": r.get("tfpnb_epci_pct"),
            "maj_at": r.get("maj_at"), "perime": _perime(r.get("maj_at")),
            "source": "DGFiP — fichier REI (impositions primitives)"}
    # RETOUCHES-1 point 2 — la (les) ligne(s) canonique(s) « Taxe foncière (bâti/non bâti) — part
    # communale X % · hors part départementale, TEOM et taxes spéciales », producteur UNIQUE partagé
    # par la fiche, le Dossier et le Copilote (jamais recomposé côté écran).
    bloc["lignes"] = lignes_taxe_fonciere(bloc)
    return bloc


def taxe_amenagement(db: Session, insee: str | None) -> dict | None:
    """COMMUNE-FIX-1 (D10) — le taux communal de la taxe d'aménagement, servi sur la carte Fiscalité.
    MÊME source que l'outil Taxe (`taxe_amenagement.taux_communal_public`, table taxe_amenagement_taux,
    DGFiP/DELTA). Il n'y a pas de taux SECTORIEL à La Réunion dans la source (aucun inventé). None si non
    ingéré (le front dit « non déterminé »)."""
    if not insee:
        return None
    from ..taxe_amenagement import taux_communal_public
    t = taux_communal_public(db, insee)
    if t is None:
        return None
    return {"part_communale_pct": t["part_communale_pct"], "millesime": t.get("millesime"),
            "delib_date": t.get("delib_date"), "perime": t.get("perime"),
            "source": "DGFiP — taxe d'aménagement (application DELTA), délibération communale"}


def _perime(maj_at_iso: str | None, jours: int = 365) -> bool:
    """RECETTE-4 U1 — True si la donnée date de plus de `jours` (fraîcheur > 1 an). Best-effort :
    une date illisible n'est jamais signalée périmée (on ne crie pas au loup sur un doute)."""
    if not maj_at_iso:
        return False
    try:
        from datetime import datetime, timezone
        d = datetime.fromisoformat(maj_at_iso)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days > jours
    except Exception:  # noqa: BLE001 — date illisible : pas de fausse alerte
        return False


def ort(db: Session, insee: str | None) -> dict | None:
    """SOURCES-1 lot 5 — statut ACV/PVD/ORT + condition communale Denormandie (table DGALN).
    None si non ingéré ; « hors » est un état servi (table peuplée, commune hors dispositif)."""
    if not insee:
        return None
    from ..ingestion.ort import ort_commune
    o = ort_commune(db, insee)
    if o is None:
        return None
    o["source"] = "DGALN — communes ORT (table vivante) ; périmètres conventionnés non publiés"
    return o


def zfang_frr(db: Session, insee: str | None) -> dict | None:
    """COUCHES-2 point 4 — ZFANG / FRR de la commune. UNE SEULE SOURCE : territoire_fiscal.
    attributs_commune (la même donnée qui peint la carte via dispositifs.py et qui filtre les
    parcelles). Deux lignes : régime ZFANG (renforcé/standard) et classement FRR (totalité/en
    partie/hors). None si la table n'est pas peuplée."""
    if not insee:
        return None
    from ..territoire_fiscal import attributs_commune
    a = attributs_commune(db, insee)
    if a is None:
        return None
    return {"zfang": a["zfang"], "frr": a["frr"], "avertissement": a.get("avertissement")}


def zonage_abc(db: Session, insee: str | None) -> dict | None:
    """SOURCES-1 lot 1 — zone A/B/C de la commune (arrêté DHUP, passe-plat sourcé + daté).
    None si non ingérée (jamais devinée) — le front dit « non déterminée »."""
    if not insee:
        return None
    from ..ingestion.zonage_abc import zonage_commune
    z = zonage_commune(db, insee)
    if z is None:
        return None
    return {"zone": z["zone"], "millesime": z["millesime"],
            "source": "DHUP — zonage ABC (arrêté du 1er août 2014 modifié, D. 304-1 CCH)"}


# ───────────────────────────── C6 — les compteurs des passerelles ─────────────────────────────
def outils_counters(db: Session, commune: str, insee: str | None,
                    blocs: dict) -> dict:
    """Le chiffre que porte chaque passerelle (C6) : un lien qui annonce ce qu'il contient se clique. On
    réutilise les compteurs DÉJÀ calculés pour les blocs (aucune requête en double) ; on n'ajoute que ceux
    qui manquent (piscines pour le Solaire, acquisitions PM pour le Scan). Un outil dont le compteur vaut 0
    n'apparaît pas (le front l'omet) — jamais un lien grisé à zéro."""
    piscines = db.execute(text(
        "SELECT count(*) FROM parcel_equipements e JOIN parcels p ON p.idu = e.idu "
        "WHERE p.commune = :c AND e.piscine"), {"c": commune}).scalar() or 0
    scan_pm = 0
    if insee:
        scan_pm = db.execute(text(
            "SELECT count(DISTINCT idu) FROM parcelle_personne_morale "
            "WHERE left(idu, 5) = :i"), {"i": insee}).scalar() or 0
    permis = blocs.get("permis") or {}
    dens = blocs.get("densifiables") or {}
    radar = blocs.get("marche_annonces") or {}
    return {
        "permis_en_cours": permis.get("permis_12m") or 0,
        "permis_point_mort": permis.get("point_mort") or 0,
        "densifiables": dens.get("parcelles") or 0,
        "radar_biens": radar.get("biens") or 0,
        "scan_pm": int(scan_pm),
        "solaire_piscines": int(piscines),
    }


import logging

log = logging.getLogger("labuse.fiche_commune")

# Replis VALIDES (même forme que la donnée nominale) — une source absente ou une table manquante dégrade
# le bloc concerné SANS casser la fiche entière (« introuvable = null, jamais un zéro menteur »).
_FALLBACK = {
    "comparable": None, "marche_annonces": None, "densifiables": None, "loyer": None,
    "zonage_abc": None, "fiscalite": None, "taxe_amenagement": None, "ort": None, "zfang_frr": None,
    "parc_social": None, "prix_neuf_observe": None, "scot": None,
    "risques": {"ppr_pct": None, "mouvement_terrain_pct": None, "catnat_arretes": 0,
                "catnat_detail": [], "parc_national": False, "azi_tri": None,
                "source": "DEAL Réunion — PPR / aléas · GASPAR · BD TOPO"},
    "population": {"habitants": None, "habitants_pop_totale": None, "habitants_millesime": None,
                   "menages": None, "menages_millesime": None, "niveau_vie_moyen_eur": None,
                   "logements": None, "vacants": None, "vacance_pct": None, "quartiers": None,
                   "parc_ancien_pct": None,
                   "source": "INSEE — population municipale légale · INSEE RP · INSEE Filosofi (niveau de vie)"},
    "plu_statut": {"statut": "document local", "libelle": None, "procedure": None,
                   "procedure_sudocuh": None,
                   "date_reglement": None, "confiance": None, "recherche_verbatim": True, "source": None},
    "permis": {"permis_12m": 0, "permis_5a": None, "logements_12m": None,
               "delai_median_mois": None, "point_mort": 0,
               "source": "SITADEL (autorisations) · SITADEL — délais d'instruction · permis au point mort"},
    "outils": {"permis_en_cours": 0, "permis_point_mort": 0, "densifiables": 0,
               "radar_biens": 0, "scan_pm": 0, "solaire_piscines": 0},
}


def _safe(db: Session, key: str, fn):
    """Exécute un builder ; en cas d'échec (table absente, source manquante), ROLLBACK la session (sinon
    la transaction reste avortée et les blocs suivants échouent en cascade) et rend le repli valide."""
    try:
        return fn()
    except Exception as exc:   # noqa: BLE001 — un bloc défaillant ne doit jamais casser la fiche
        log.warning("fiche_commune: bloc %s indisponible (%s)", key, exc)
        db.rollback()
        return _FALLBACK[key]


def build(db: Session, commune: str, insee: str | None) -> dict:
    """Assemble tous les blocs ajoutés + les compteurs de passerelles, en un seul objet servi à la fiche.
    Chaque bloc est isolé : une source indisponible dégrade CE bloc, pas la fiche."""
    blocs = {
        "comparable": _safe(db, "comparable", lambda: comparable(db, commune)),
        "marche_annonces": _safe(db, "marche_annonces", lambda: marche_annonces(db, commune)),
        "risques": _safe(db, "risques", lambda: risques(db, commune, insee)),
        "population": _safe(db, "population", lambda: population(db, commune, insee)),
        "plu_statut": _safe(db, "plu_statut", lambda: plu_statut(db, insee, commune)),
        "scot": _safe(db, "scot", lambda: scot_commune(db, commune)),
        "permis": _safe(db, "permis", lambda: permis_bloc(db, commune)),
        "densifiables": _safe(db, "densifiables", lambda: densifiables(db, commune)),
        "loyer": _safe(db, "loyer", lambda: loyer(db, commune)),
        # COMMUNE-RANGEMENT-1 lot 2 — parc social RPLS (SDES), fait communal servi à la fiche commune.
        "parc_social": _safe(db, "parc_social", lambda: parc_social(db, insee)),
        # COMMUNE-RANGEMENT-2 lot 2 — prix du neuf OBSERVÉ (commune), aux côtés du VEFA à l'acte (maquette Prix).
        "prix_neuf_observe": _safe(db, "prix_neuf_observe", lambda: prix_neuf_observe(db, insee)),
        # SOURCES-1 lot 1 — zonage A/B/C (DHUP, arrêté national) : passe-plat sourcé + daté.
        "zonage_abc": _safe(db, "zonage_abc", lambda: zonage_abc(db, insee)),
        # SOURCES-1 lot 5 — taux fonciers (REI) + ACV/PVD/ORT (Denormandie).
        "fiscalite": _safe(db, "fiscalite", lambda: fiscalite(db, insee)),
        # COMMUNE-FIX-1 (D10) — taux communal de la taxe d'aménagement (même source que l'outil Taxe).
        "taxe_amenagement": _safe(db, "taxe_amenagement", lambda: taxe_amenagement(db, insee)),
        "ort": _safe(db, "ort", lambda: ort(db, insee)),
        # COUCHES-2 point 4 — ZFANG / FRR (territoire_fiscal, source unique : carte + fiche + filtre).
        "zfang_frr": _safe(db, "zfang_frr", lambda: zfang_frr(db, insee)),
    }
    blocs["outils"] = _safe(db, "outils", lambda: outils_counters(db, commune, insee, blocs))
    return blocs
