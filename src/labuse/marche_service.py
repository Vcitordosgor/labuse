"""M73-B Volet C — LE point d'appel UNIQUE du marché (DVF + permis) pour les documents.

Un seul endroit où les documents LISENT le marché. Arbitrage Vic (M73-B) : « un point d'appel,
paramètres NOMMÉS » — chaque document garde ses paramètres (via un `profil`), le CALCUL n'est PAS
touché (délégation aux calculs historiques). Écart au « même chiffre » ASSUMÉ par Vic : on préserve
les doctrines M38 (voisinage 100 m) et M79 (prix terrain) plutôt que de fusionner de force.

Ce module est le point que `MANDAT_DVF` éditera : quand le calcul sera corrigé ICI (ou dans les calculs
délégués), les documents suivront automatiquement — ils ne connaissent que `marche_dvf` / `permits`.

Les `profil` sont PROVISOIRES et NOMMÉS (renvoi MANDAT_DVF) : ils encapsulent les trois lectures
historiques distinctes sans les fusionner.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .dvf_fenetre import fenetre_dvf_sql  # E-04 — fenêtre DVF ancrée sur max(date_mutation)

# ── Profils DVF (paramètres provisoires — cf. MANDAT_DVF) ─────────────────────────────────────────
DVF_SECTEUR_DOSSIER = "secteur_dossier"        # 500 m / 3 ans, bâti + terrain nu (flash/_marche)
DVF_BANQUIER_ADAPTATIF = "banquier_adaptatif"  # rayon adaptatif 500→1500→commune, Q1/méd/Q3 (bilan/sector_price)
DVF_VOISINAGE_100M = "voisinage_100m"          # < 100 m / 36 mois, doctrine M38 (site_voisinage)
DVF_NEUF_VEFA = "neuf_vefa"                    # M101 B2 : neuf déclaré par l'acte (VEFA), grain commune

# ── Profils PERMIS (paramètres provisoires — cf. MANDAT_DVF) ──────────────────────────────────────
PERMITS_FLASH_500M = "flash_500m"              # 500 m / 24 mois (ingestion/permits.nearby_permits)
PERMITS_FICHE_36M = "fiche_36m"                # parcelle + secteur, 36 mois (ingestion/permits.depots_recents)
PERMITS_VOISINAGE_100M = "voisinage_100m"      # < 100 m / 36 mois, doctrine M38 (site_voisinage)


def _parcel_id(db: Session, idu: str) -> int | None:
    return db.execute(text("SELECT id FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()


def filtre_ventes(ventes: list[dict], *, cle_prix: str = "prix_m2",
                  cle_type: str | None = None,
                  bornes: tuple[float, float] | None = (1000.0, 12000.0),
                  z_mad: float | None = None, trim_pct: float | None = None,
                  seuil_type_m2: dict | None = None) -> tuple[list[dict], list[dict]]:
    """EXPORTS-1 lot 2 (2.1/2.3) — LE filtre de comparables, UNE implémentation paramétrée pour
    les trois chemins (fiche `comparables`, flash `_marche`, `sector_price`). Renvoie
    (gardées, écartées) — chaque écartée porte son `motif` (jamais une disparition muette).

    Paramètres par profil :
      - `bornes` : domaine €/m² de bon sens (artefacts DVF hors [1000 ; 12000]) ;
      - `z_mad` : z-score modifié médiane/MAD (aberrance statistique, méthode flash M127-D6) ;
      - `trim_pct` : exclusion des extrêmes en fraction (méthode sector_price SECTEUR-2 T1,
        via `trim_extremes_5pct`) — z_mad et trim_pct sont exclusifs par profil ;
      - `seuil_type_m2` : vraisemblance par type ({"appartement": 200}) — un « appartement »
        de 750 m² est une mutation d'immeuble agrégée (2.2/2.3), écarté avec motif tant que
        le ré-étiquetage d'ingestion n'a pas tourné partout."""
    import statistics
    gardees, ecartees = [], []
    for v in ventes:
        p = v.get(cle_prix)
        if p is None:
            gardees.append(v)
            continue
        p = float(p)
        if bornes and not (bornes[0] <= p <= bornes[1]):
            ecartees.append({**v, "motif": f"€/m² hors domaine [{int(bornes[0])} ; {int(bornes[1])}]"})
            continue
        if seuil_type_m2 and cle_type:
            t = (v.get(cle_type) or "").strip().lower()
            seuil = seuil_type_m2.get(t)
            surf = v.get("surface_m2") or v.get("surface_reelle_bati")
            if seuil and surf and float(surf) > float(seuil):
                ecartees.append({**v, "motif": f"surface incompatible avec un {t} "
                                               f"(> {int(seuil)} m²) — agrégat multi-lots probable"})
                continue
        gardees.append(v)
    prix = [float(v[cle_prix]) for v in gardees if v.get(cle_prix) is not None]
    if z_mad is not None and len(prix) >= 4:
        med = statistics.median(prix)
        mad = statistics.median([abs(x - med) for x in prix]) or 1e-9
        aber_ids = {id(v) for v in gardees if v.get(cle_prix) is not None
                    and abs(0.6745 * (float(v[cle_prix]) - med) / mad) > z_mad}
        for v in gardees:
            if id(v) in aber_ids:
                ecartees.append({**v, "motif": "prix/m² aberrant (z-score médiane/MAD > "
                                               f"{z_mad:g}) — mutation atypique probable"})
        gardees = [v for v in gardees if id(v) not in aber_ids]
    if trim_pct is not None and len(prix) >= 4:
        from .faisabilite.bilan import trim_extremes_5pct
        _kept, lo, hi = trim_extremes_5pct(prix)
        if lo is not None:
            aber_ids = {id(v) for v in gardees if v.get(cle_prix) is not None
                        and not (lo <= float(v[cle_prix]) <= hi)}
            for v in gardees:
                if id(v) in aber_ids:
                    ecartees.append({**v, "motif": f"extrême exclu ({trim_pct:.0%} de chaque queue)"})
            gardees = [v for v in gardees if id(v) not in aber_ids]
    return gardees, ecartees


def filtre_params() -> dict:
    """Paramètres du filtre unique, lus de config/dvf_profils.yaml (bloc `filtre_comparables`)."""
    doc = (_profils_doc().get("filtre_comparables") or {})
    return {"bornes": (float(doc.get("borne_min_eur_m2", 1000)),
                       float(doc.get("borne_max_eur_m2", 12000))),
            "z_mad": float(doc.get("z_mad_max", 3.5)),
            "seuil_type_m2": {str(k).lower(): float(v)
                              for k, v in (doc.get("seuil_type_m2") or {"appartement": 200}).items()}}


def phrase_prix_ancien(sp: dict | None) -> str | None:
    """EXPORTS-1 (1.3) — LA phrase client du prix de l'ancien (`sector_price` parcelle), avec n,
    rayon EFFECTIF et période imprimés. Point de formulation UNIQUE partagé par la fiche PDF, le
    Dossier et le Flash — plus jamais « n 11 » d'un côté et « 36 ventes » de l'autre.
    None si l'échantillon est insuffisant (l'appelant omet la ligne, jamais un chiffre fragile)."""
    if not sp or not sp.get("fiable") or sp.get("median") is None:
        return None
    per = sp.get("periode") or []
    periode = f", ventes {per[0]}–{per[1]}" if len(per) == 2 else ""
    rayon = ("commune entière" if sp.get("commune_fallback")
             else f"rayon {int(sp['radius_m'])} m" if sp.get("radius_m") else "secteur")
    med = f"{int(sp['median']):,}".replace(",", " ")
    return (f"Prix ancien médian {med} €/m² ({sp.get('type_prix')}, {sp['n']} ventes, "
            f"{rayon}{periode})")


def marche_dvf(db: Session, idu: str, *, profil: str, avail: set[str] | None = None) -> dict | None:
    """Lecture DVF d'une parcelle, par le point d'appel UNIQUE. `profil` = préset de paramètres nommé
    (provisoire, MANDAT_DVF). Délègue au calcul existant — aucun recalcul, aucun chiffre changé ici."""
    if profil == DVF_SECTEUR_DOSSIER:
        from .flash.data import _marche
        if avail is None:                       # le dossier fournit déjà `avail` ; sinon on le résout
            from .flash.data import _existing_tables, _NEEDED_TABLES
            avail = _existing_tables(db, _NEEDED_TABLES)
        return _marche(db, idu, avail)
    if profil == DVF_BANQUIER_ADAPTATIF:
        from .faisabilite.bilan import sector_price
        from .faisabilite.engine import Hypotheses
        pid = _parcel_id(db, idu)
        if not pid:
            return None
        # FIX-FINAL-1 (NU-A-002 / NU-D-010) — « prix de l'ancien » de la TÊTE DE FICHE : la médiane du
        # BON type de bien. On lit la nature réelle sur la dernière mutation DVF (même règle qu'« Estimer
        # un bien », `_derniere_mutation_dvf`) et on la passe à `sector_price` → plus jamais un prix
        # d'appartement servi en tête d'un dossier de maison. Point d'appel UNIQUE : tous les lecteurs de
        # ce profil (fiche, Dossier, Comparatif, documents, Radar) deviennent type-exacts d'un coup.
        tp = None
        try:
            from .pige.api import _derniere_mutation_dvf
            mut = _derniere_mutation_dvf(db, idu)
            nat = (mut or {}).get("nature")
            tp = nat if nat in ("maison", "appartement") else None
        except Exception:  # noqa: BLE001 — nature indéterminée : comportement historique (sans type)
            tp = None
        return sector_price(db, pid, Hypotheses.charger(), type_prioritaire=tp)
    if profil == DVF_VOISINAGE_100M:
        from .api.site_voisinage import voisinage_proche
        return voisinage_proche(db, idu)
    if profil == DVF_NEUF_VEFA:
        # M101 B2 (arbitrage Vic) — le NEUF que l'acte déclare (VEFA), grain COMMUNE. Le seuil,
        # la grandeur et la raison viennent de la config (un critère, un endroit) ; sous le seuil,
        # AUCUNE médiane — « échantillon insuffisant » AVEC la grandeur, jamais un chiffre fragile.
        from .ingestion.dvf_marche import neuf_vefa_commune
        meta = profil_meta(DVF_NEUF_VEFA)
        seuil = int(meta.get("seuil_effectif") or 8)
        r = neuf_vefa_commune(db, idu[:5])
        suffisant = r["n"] >= seuil and r["mediane_prix_m2_bati"] is not None
        return {
            "grandeur": meta.get("grandeur"),
            "grain": meta.get("grain", "commune"),
            "fenetre_ans": r["fenetre_ans"],
            "n": r["n"], "seuil_effectif": seuil,
            "effectif_suffisant": suffisant,
            "mediane_prix_m2_bati": r["mediane_prix_m2_bati"] if suffisant else None,
            "insuffisant_libelle": (None if suffisant else
                                    f"Échantillon insuffisant ({r['n']} vente{'s' if r['n'] > 1 else ''} "
                                    f"VEFA sur {r['fenetre_ans']} ans, seuil {seuil}) — pas de médiane servie."),
            "reserve": reserve_methode(),
        }
    raise ValueError(f"profil DVF inconnu : {profil!r}")


# ── MANDAT_DVF — la DOCTRINE des profils est figée en config (config/dvf_profils.yaml), lue ICI (point
# unique). Plus aucun rayon/fenêtre « par continuité » : chaque profil porte sa question/rayon/fenêtre/
# grandeur/raison/seuil d'effectif. La réserve de méthode et le facteur du garde-fou 2× vivent aussi là.
COMPARABLES_PREMIUM = "comparables_premium"


def _profils_doc() -> dict:
    from . import config as _cfg
    try:
        return _cfg.load_yaml_config("dvf_profils") or {}
    except Exception:  # noqa: BLE001 — config absente = défauts prudents, jamais un crash
        return {}


def profil_meta(profil: str) -> dict:
    """Métadonnées SERVIES d'un profil (question, rayon_m, fenetre_*, grandeur, seuil_effectif, raison) —
    pour afficher les PARAMÈTRES à côté du chiffre. Source unique config/dvf_profils.yaml."""
    return (_profils_doc().get("profils") or {}).get(profil, {})


def neuf_vefa_seuil() -> int:
    """RETOURS-11F M1 — LE seuil d'effectif VEFA, source unique (profil `neuf_vefa`). La fiche
    (marche_service), la couche carte (`vefa_neuf`) ET le tableau Communes (comparateur) le lisent ICI
    pour que « fiche = table = carte » : même seuil, même fenêtre, même médiane, à l'euro près."""
    try:
        return int(profil_meta("neuf_vefa").get("seuil_effectif") or 8)
    except (TypeError, ValueError):
        return 8


def seuil_effectif_local(nom: str, defaut: int) -> int:
    """M103 P1 — seuils d'effectif DVF hors profils nommés (bloc `seuils_effectif` de la config).
    Un critère, un endroit : plus aucun seuil d'effectif DVF écrit dans le code. `defaut` = repli
    prudent si la config est absente (base de test) — jamais un desserrage."""
    try:
        return int((_profils_doc().get("seuils_effectif") or {}).get(nom, defaut))
    except (TypeError, ValueError):
        return defaut


def reserve_methode() -> str:
    """La réserve de méthode DVF (retard 1-3 ans, récents provisoires, classement fiable) — écrite une
    fois, voyage avec chaque chiffre DVF servi."""
    return str(_profils_doc().get("reserve_methode") or "").strip()


def garde_fou_facteur() -> float:
    """Facteur du garde-fou : projection > facteur × référence → information manquante, jamais une affaire."""
    return float(_profils_doc().get("garde_fou_ecart_facteur") or 2.0)


def garde_fou_signal(projection: float | None, reference: float | None, *,
                     effectif: int | None = None, seuil_effectif: int | None = None) -> dict:
    """MANDAT_DVF — le garde-fou du 2× : si la PROJECTION arithmétique s'écarte de plus du facteur de la
    RÉFÉRENCE de marché, on le signale comme INFORMATION MANQUANTE (jamais une affaire). Il ANNOTE, ne
    bloque ni ne masque rien. Si un terme manque (pas de référence, ou effectif de référence insuffisant),
    il NE se déclenche PAS — un écart non mesurable n'est pas un écart — et le DIT plutôt que de se taire.
    Retourne {declenche, mesurable, note}."""
    fac = garde_fou_facteur()
    if not reference or reference <= 0:
        return {"declenche": False, "mesurable": False,
                "note": "Écart à la référence de secteur non mesurable (pas de référence DVF fiable)."}
    if seuil_effectif and effectif is not None and effectif < seuil_effectif:
        return {"declenche": False, "mesurable": False,
                "note": "Écart à la référence non mesurable (échantillon de référence insuffisant)."}
    if projection and projection > fac * reference:
        return {"declenche": True, "mesurable": True,
                "note": (f"Écart important à la référence de secteur (×{projection / reference:.1f}) — "
                         "donnée probablement incomplète, à vérifier. Pas une opportunité chiffrée.")}
    return {"declenche": False, "mesurable": True, "note": None}


def comparables(db: Session, idu: str, *, profil: str = COMPARABLES_PREMIUM) -> dict:
    """Liste des comparables DVF d'une parcelle — point de lecture UNIQUE (aucun appel DVF hors d'ici).
    SURFAÇAGE de dvf_mutations, PAS un recalcul : chaque vente porte DATE/DISTANCE/SURFACE/PRIX (une
    vente à trous est exclue par la requête). Rayon/fenêtre/seuil LUS de la config (MANDAT_DVF). Le dict
    porte ses PARAMÈTRES (rayon, fenêtre, n), sa GRANDEUR, sa RÉSERVE et `effectif_suffisant` (sous le
    seuil : le document l'écrit, pas un tableau qui paraît solide)."""
    meta = profil_meta(profil)
    rayon_m = float(meta.get("rayon_m") or 500.0)
    fenetre_ans = int(meta.get("fenetre_ans") or 3)
    seuil = int(meta.get("seuil_effectif") or 8)
    n_affiche = int(meta.get("n_affiche") or 12)   # EXPORTS-1 (2.4) : paramètre du profil
    rows = db.execute(text(
        "WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu) "
        "SELECT to_char(dm.date_mutation, 'YYYY-MM-DD') AS date, dm.type_local, "
        "  round(ST_Distance(ST_Transform(dm.geom, 2975), p.geom_2975))::int AS distance_m, "
        "  round(dm.surface_reelle_bati)::int AS surface_m2, "
        "  round(dm.valeur_fonciere)::int AS prix_eur, "
        "  round(dm.valeur_fonciere / NULLIF(dm.surface_reelle_bati, 0))::int AS prix_m2 "
        "FROM dvf_mutations dm, p "
        "WHERE dm.geom IS NOT NULL AND dm.date_mutation IS NOT NULL "
        # CHASSE-INVARIANTS-FIX-1 Lot 5 (E-04) — fenêtre ancrée sur la dernière vente, pas CURRENT_DATE.
        "  AND " + fenetre_dvf_sql("dm.date_mutation", annees_param="ans") + " "
        # MARCHE-UNIQUE-1 (NU-A-012 / NU-E-025) — comparables ANCIENS : vente de gré à gré SEULE
        # (exclut VEFA/neuf, VTB, adjudication, échange, expropriation). (NU-E-023) — la parcelle
        # sujet n'est JAMAIS son propre comparable (ses mutations sont retirées).
        "  AND dm.nature_mutation = 'Vente' AND dm.valeur_fonciere > 0 "
        "  AND dm.mutation_id NOT IN "
        "      (SELECT id_mutation FROM dvf_mutations_parcelle WHERE id_parcelle = :idu) "
        "  AND dm.surface_reelle_bati >= 20 "
        "  AND ST_DWithin(ST_Transform(dm.geom, 2975), p.geom_2975, :r) "
        "ORDER BY dm.date_mutation DESC LIMIT 60"),
        {"idu": idu, "ans": fenetre_ans, "r": rayon_m}).mappings().all()
    # EXPORTS-1 (2.1) : le chemin SANS filtre de la fiche disparaît — mêmes gardes que le
    # dossier (bornes + z-MAD + vraisemblance par type), écartées comptées avec motif.
    fp = filtre_params()
    gardees, ecartees = filtre_ventes([dict(r) for r in rows], cle_prix="prix_m2",
                                      cle_type="type_local", bornes=fp["bornes"],
                                      z_mad=fp["z_mad"], seuil_type_m2=fp["seuil_type_m2"])
    montrees = gardees[:n_affiche]
    n = len(montrees)
    return {"rayon_m": int(rayon_m), "fenetre_ans": fenetre_ans, "n": n,
            "n_retenues": len(gardees), "n_ecartees": len(ecartees), "n_affiche": n_affiche,
            "ecartees_motifs": sorted({e["motif"] for e in ecartees}),
            "comparables": montrees,
            "seuil_effectif": seuil, "effectif_suffisant": n >= seuil,   # sous le seuil : « échantillon insuffisant »
            "grandeur": meta.get("grandeur"), "question": meta.get("question"),
            "reserve": reserve_methode()}


# ── ANNONCE-5 — le comparateur UNIQUE de l'outil « Analyser une annonce » ─────────────────────────
#: Point d'appel UNIQUE pour l'estimation, la valeur indicative ET le tableau de comparables de
#: l'annonce : À PARTIR D'UNE SEULE requête DVF ancrée sur la parcelle, on sort l'AGRÉGAT (médiane,
#: Q1/Q3, n retenues, rayon effectif, période, fiabilité) ET les ventes LES PLUS PROCHES retenues. Ainsi
#: l'estimation « 34 ventes · rayon 1 000 m », la valeur indicative et le tableau des « 8 ventes les
#: plus proches » ne divergent JAMAIS (même échantillon, même filtre). `marche_service.py` est déjà un
#: lecteur DÉCLARÉ de dvf_mutations (robinet pdf_financier) — aucune nouvelle arête à déclarer.
_CMP_RAYONS = (500.0, 1000.0, 1500.0)   # rayon ADAPTATIF : on élargit jusqu'au seuil d'effectif

# ── ESTIMER-PRECISION-1 — médiane PONDÉRÉE par la ressemblance (poids RÉGLÉS sur les ventes 2024,
# ANNONCÉS sur 2025, banc docs/audit-2026-11/estimer-precision-1/). Chaque comparable compte selon :
# sa DISTANCE (gaussien), son écart de SURFACE bâtie (laplacien), pour les MAISONS son écart de TAILLE
# de TERRAIN, et son ANCIENNETÉ (demi-vie). Les prix sont RAMENÉS À AUJOURD'HUI par un indice local de
# dérive (médiane €/m² de la commune, 2019-2024, figé). L'écart d'ALTITUDE (Hauts/littoral) a été mesuré
# via la distance au trait de côte (le MNT RGE ALTI n'est pas chargé island-wide) : contribution 0,1 pt
# → NON servie (ne justifie pas un index spatial au serve-time). Gain mesuré 2025 : appartement/copro
# €/m² 17,2 % → 14,4 % (objectif < 15 % atteint, surface connue) ; maison ~27 % (plancher donnée DVF,
# confirmé par un test gradient boosting à 27,8 % — aucune méthode ne descend sous 20 %).
_POIDS_SEGMENT = {
    "appartement": {"h_dist": 500.0, "h_surf": 160.0, "halflife": 2.0, "drift": True, "h_terr": None},
    "maison":      {"h_dist": 900.0, "h_surf": 120.0, "halflife": 4.0, "drift": True, "h_terr": 1500.0},
}
_POIDS_DEFAUT = {"h_dist": 900.0, "h_surf": 120.0, "halflife": 4.0, "drift": True, "h_terr": None}
_DRIFT_ANS = (2019, 2024)            # indice local estimé sur ≤2024 et FIGÉ
_DRIFT_MIN, _DRIFT_MAX = -0.04, 0.12


def _annee_decimale(d: str | None) -> float | None:
    """'YYYY-MM-DD' → année décimale (ex. 2024-07-02 ≈ 2024,5). None si illisible."""
    if not isinstance(d, str) or len(d) < 10:
        return None
    try:
        import datetime as _dt
        dd = _dt.date.fromisoformat(d[:10])
        deb = _dt.date(dd.year, 1, 1).toordinal()
        fin = _dt.date(dd.year + 1, 1, 1).toordinal()
        return dd.year + (dd.toordinal() - deb) / (fin - deb)
    except ValueError:
        return None


def _drift_commune(db: Session, commune: str | None) -> float:
    """Dérive géométrique annuelle du €/m² bâti de la commune (médianes 2019-2024, FIGÉES). Repli île si
    assise mince. Bornée [−4 % ; +12 %]/an (garde-fou contre les communes à faible effectif)."""
    import statistics as _st
    rows = db.execute(text(
        "SELECT extract(year FROM date_mutation)::int AS annee, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur_fonciere/surface_reelle_bati) AS med, "
        "  count(*) AS n "
        "FROM dvf_mutations "
        "WHERE surface_reelle_bati >= 20 AND valeur_fonciere > 0 AND nature_mutation = 'Vente' "
        "  AND valeur_fonciere/surface_reelle_bati BETWEEN 1000 AND 12000 "
        "  AND extract(year FROM date_mutation) BETWEEN :a AND :b "
        "  AND (commune = :c OR :c IS NULL) "
        "GROUP BY annee"), {"a": _DRIFT_ANS[0], "b": _DRIFT_ANS[1], "c": commune}).mappings().all()
    serie = {int(r["annee"]): float(r["med"]) for r in rows if (r["n"] or 0) >= 8 and r["med"]}
    ans = sorted(serie)
    if len(ans) >= 4 and serie.get(ans[0]) and serie.get(ans[-1]):
        d = (serie[ans[-1]] / serie[ans[0]]) ** (1.0 / (ans[-1] - ans[0])) - 1.0
        return max(_DRIFT_MIN, min(_DRIFT_MAX, d))
    return 0.0


def _med_quantiles_pondere(vw: list[tuple[float, float]]) -> tuple[float | None, float | None, float | None]:
    """(q1, médiane, q3) PONDÉRÉS d'une liste (valeur, poids). Quantile pondéré = valeur où le poids
    cumulé franchit 25/50/75 %. None si vide."""
    vw = [(float(v), float(w)) for v, w in vw if w and w > 0]
    if not vw:
        return None, None, None
    vw.sort(key=lambda t: t[0])
    total = sum(w for _, w in vw)
    cum, out, cibles, qs = 0.0, {}, [0.25, 0.5, 0.75], {}
    for v, w in vw:
        cum += w
        for c in cibles:
            if c not in qs and cum >= total * c:
                qs[c] = v
    for c in cibles:
        qs.setdefault(c, vw[-1][0])
    return qs[0.25], qs[0.5], qs[0.75]


def _cle_type(type_bien: str | None) -> str | None:
    """Fragment ILIKE du type_local DVF pour un type de bien, ou None (bâti combiné)."""
    if type_bien == "maison":
        return "maison"
    if type_bien == "appartement":
        return "appart"
    return None


def comparateur_bien(db: Session, idu: str, *, type_bien: str | None = None,
                     fenetre_ans: int = 5, seuil: int | None = None, n_table: int = 8,
                     surface_sujet: float | None = None, terrain_sujet: float | None = None) -> dict | None:
    """Comparateur BÂTI de l'annonce (ventes de maisons / d'appartements), SURFAÇAGE de dvf_mutations.
    `type_bien` ∈ {maison, appartement, bati, None} : None/bati → on DÉDUIT le type dominant du secteur
    (règle de nature de la fiche : une parcelle bâtie en secteur de maisons est comparée aux maisons).
    Rayon ADAPTATIF 500→1000→1500 m jusqu'au seuil d'effectif, repli commune. Renvoie None si la parcelle
    n'a pas de géométrie ; sinon un dict toujours défini (median None si échantillon insuffisant).

    ESTIMER-PRECISION-1 — la médiane servie est PONDÉRÉE par la ressemblance (distance, écart de surface,
    écart de terrain pour les maisons, ancienneté) et les prix sont ramenés à aujourd'hui par un indice
    local de dérive ; `surface_sujet` / `terrain_sujet` (facultatifs) alimentent les poids de surface et
    de terrain. Les 8 comparables affichés sont ceux qui PÈSENT LE PLUS (prix bruts affichés). Poids réglés
    sur 2024, annoncés sur 2025 (`_POIDS_SEGMENT`)."""
    import statistics
    pid = _parcel_id(db, idu)
    if pid is None:
        return None
    seuil = int(seuil if seuil is not None else seuil_effectif_local("comparables_annonce", 8))
    fp = filtre_params()

    def _fetch(rayon_m: float | None) -> list[dict]:
        where_r = ("ST_DWithin(ST_Transform(dm.geom, 2975), p.geom_2975, :r)"
                   if rayon_m is not None else "dm.commune = (SELECT commune FROM parcels WHERE idu = :idu)")
        rows = db.execute(text(
            "WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu) "
            "SELECT to_char(dm.date_mutation, 'YYYY-MM-DD') AS date, dm.type_local, "
            "  round(ST_Distance(ST_Transform(dm.geom, 2975), p.geom_2975))::int AS distance_m, "
            "  round(dm.surface_reelle_bati)::int AS surface_m2, "
            "  round(dm.valeur_fonciere)::int AS prix_eur, "
            "  round(dm.valeur_fonciere / NULLIF(dm.surface_reelle_bati, 0))::int AS prix_m2, "
            "  round(COALESCE(dm.surface_terrain, 0))::int AS terrain_m2, "
            "  extract(year FROM dm.date_mutation)::int AS annee "
            "FROM dvf_mutations dm, p "
            "WHERE dm.geom IS NOT NULL AND dm.date_mutation IS NOT NULL "
            "  AND " + fenetre_dvf_sql("dm.date_mutation", annees_param="ans") + " "
            # MARCHE-UNIQUE-1 — comparateur BÂTI (Estimer) : ancien de gré à gré SEUL (NU-A-012 /
            # NU-E-025) ; la parcelle sujet exclue de ses propres comparables (NU-E-023).
            "  AND dm.nature_mutation = 'Vente' AND dm.valeur_fonciere > 0 "
            "  AND dm.mutation_id NOT IN "
            "      (SELECT id_mutation FROM dvf_mutations_parcelle WHERE id_parcelle = :idu) "
            "  AND dm.surface_reelle_bati >= 20 AND " + where_r + " "
            "ORDER BY distance_m ASC LIMIT 600"),
            {"idu": idu, "ans": fenetre_ans, "r": rayon_m}).mappings().all()
        return [dict(r) for r in rows]

    def _garde(rows: list[dict], typ: str | None) -> list[dict]:
        g, _ = filtre_ventes(rows, cle_prix="prix_m2", cle_type="type_local", bornes=fp["bornes"],
                             z_mad=fp["z_mad"], seuil_type_m2=fp["seuil_type_m2"])
        frag = _cle_type(typ)
        return [v for v in g if frag in (v.get("type_local") or "").lower()] if frag else g

    # type dominant déduit (une seule fois, sur le 1 000 m) si le type n'est pas donné.
    if type_bien in (None, "bati"):
        base = _garde(_fetch(1000.0), None)
        nm = sum(1 for v in base if "maison" in (v.get("type_local") or "").lower())
        na = sum(1 for v in base if "appart" in (v.get("type_local") or "").lower())
        if nm + na > 0 and max(nm, na) / (nm + na) >= 0.55:
            type_bien = "maison" if nm >= na else "appartement"
        else:
            type_bien = None   # bâti combiné (secteur mixte)

    radius: int | None = None
    commune_fallback = False
    kept: list[dict] = []
    for rayon in _CMP_RAYONS:
        kept = _garde(_fetch(rayon), type_bien)
        if len(kept) >= seuil:
            radius = int(rayon)
            break
    else:
        commune = _garde(_fetch(None), type_bien)   # repli commune entière
        if len(commune) > len(kept):
            kept, commune_fallback = commune, True
        elif kept:
            radius = int(_CMP_RAYONS[-1])

    kept = [v for v in kept if v.get("prix_m2") is not None]
    annees = [int(v["annee"]) for v in kept if v.get("annee") is not None]
    n = len(kept)
    # ── ESTIMER-PRECISION-1 — médiane PONDÉRÉE + prix ramenés à aujourd'hui (indice local) ──
    import math as _math
    par = _POIDS_SEGMENT.get(type_bien or "", _POIDS_DEFAUT)
    commune_nom = db.execute(text("SELECT commune FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()
    drift = _drift_commune(db, commune_nom) if par.get("drift") else 0.0
    is_maison = (type_bien == "maison")
    # Référence de dérive = le comparable le PLUS RÉCENT (l'ancre, comme le banc) — on ramène les prix
    # à l'état de marché le plus frais DONT ON A LA DONNÉE, jamais une extrapolation calendaire.
    ycs = [(_annee_decimale(v.get("date")) or float(v.get("annee") or 0)) for v in kept]
    ref_dec = max([y for y in ycs if y] or [0.0])
    vw = []   # (prix ramené à l'ancre, poids)
    for v, yc in zip(kept, ycs):
        p = float(v["prix_m2"])
        if drift and yc:
            fac = (1.0 + drift) ** (ref_dec - yc)
            fac = min(1.6, max(0.7, fac))   # garde-fou : un comparable n'est ré-indexé qu'au plus ±(…)
            p_adj = p * fac
        else:
            p_adj = p
        w = 1.0
        hd = par.get("h_dist")
        if hd and isinstance(v.get("distance_m"), (int, float)):
            w *= _math.exp(-(float(v["distance_m"]) / hd) ** 2)
        hs = par.get("h_surf")
        if hs and isinstance(surface_sujet, (int, float)) and surface_sujet > 0 and v.get("surface_m2"):
            w *= _math.exp(-abs(float(v["surface_m2"]) - float(surface_sujet)) / hs)
        ht = par.get("h_terr")
        if ht and is_maison and isinstance(terrain_sujet, (int, float)) and terrain_sujet > 0 \
                and (v.get("terrain_m2") or 0) > 0:
            w *= _math.exp(-abs(float(v["terrain_m2"]) - float(terrain_sujet)) / ht)
        hl = par.get("halflife")
        if hl:
            w *= 0.5 ** (max(0.0, ref_dec - yc) / hl)
        if not (w > 0) or not _math.isfinite(w):
            w = 1e-12
        v["_poids"] = w
        vw.append((p_adj, w))
    q1f, medf, q3f = _med_quantiles_pondere(vw)
    median = round(medf) if medf is not None else None
    q1 = round(q1f) if (n >= 4 and q1f is not None) else None
    q3 = round(q3f) if (n >= 4 and q3f is not None) else None
    # Les 8 comparables AFFICHÉS = ceux qui PÈSENT LE PLUS (mandat) ; prix BRUTS (non ramenés) affichés.
    proches = sorted(kept, key=lambda v: v.get("_poids", 0.0), reverse=True)[:n_table]
    comparables = [{
        "date": f"{v['date'][5:7]}/{v['date'][0:4]}" if isinstance(v.get("date"), str) and len(v["date"]) >= 7 else None,
        "type": (v.get("type_local") or "").capitalize() or None,
        "surface_m2": v.get("surface_m2"), "prix_eur": v.get("prix_eur"),
        "prix_m2": v.get("prix_m2"), "distance_m": v.get("distance_m"),
    } for v in proches]
    label_pl = {"maison": "maisons", "appartement": "appartements"}.get(type_bien or "", "biens bâtis anciens")
    periode = [min(annees), max(annees)] if annees else None
    # ── CHASSE-FIX-1 (B-3 / CH-B-M3 / MARCHE-UNIQUE) — la MÉDIANE servie à l'écran est celle du POINT
    # DE CALCUL UNIQUE `reference_locale` (le même moteur de secteur que la carte Marché de la fiche et
    # l'Étude de zone). Avant, l'Estimer calculait sa propre médiane (échantillon/fenêtre distincts :
    # « maison 4 747 €/m² · 16 ventes » ici vs « 4 265 €/m² · 13 ventes » sur la fiche). Désormais, pour
    # un type maison/appartement, le chiffre de tête (médiane, quartiles, n, rayon, période) est repris
    # de `reference_locale` → UN SEUL €/m² pour le même bien. Les 8 comparables restent illustratifs
    # (sélectionnés par ressemblance, ESTIMER-PRECISION-1) ; en secteur mixte (type None), pas de
    # référence mono-type → l'Estimer garde sa médiane bâti combinée. ──
    if type_bien in ("maison", "appartement"):
        try:
            from .faisabilite.bilan import reference_locale as _ref_sec
            rl = _ref_sec(db, idu, type_bien, return_echantillon=True)
        except Exception:  # noqa: BLE001 — le marché ne casse jamais l'estimation
            rl = None
        if rl and rl.get("eur_m2") is not None:
            median = round(float(rl["eur_m2"]))
            q1 = rl.get("q1") if rl.get("q1") is not None else q1
            q3 = rl.get("q3") if rl.get("q3") is not None else q3
            n = int(rl.get("n") or n)
            radius = int(rl["rayon_m"]) if rl.get("rayon_m") is not None else radius
            periode = rl.get("periode") or periode
            commune_fallback = False
    return {
        "type_bien": type_bien or "bati", "type_label_pluriel": label_pl,
        "median": median, "q1": q1, "q3": q3, "n": n,
        "radius_m": radius, "commune_fallback": commune_fallback,
        "periode": periode,
        "fiable": n >= seuil, "fiabilite": "fiable" if n >= seuil else "moyen",
        "seuil_effectif": seuil, "comparables": comparables, "n_total": n,
        "reserve": reserve_methode(),
    }


def comparateur_terrain(db: Session, idu: str, *, rayons=(1000.0, 2000.0, 3000.0), n_table: int = 8) -> dict:
    """ANNONCE-5-FIX — les ventes de TERRAIN NU les plus proches (dvf_mutations_parcelle, ventes sans
    bâti), MÊME format que le comparateur bâti : date · surface · prix · €/m² · distance. Agrège par
    mutation (une mutation = une vente ; terrain total = somme des parcelles, distance = la plus proche de
    la parcelle sujet). Rayon adaptatif jusqu'au seuil. `marche_service.py` est déjà lecteur déclaré."""
    pid = _parcel_id(db, idu)
    if pid is None:
        return {"comparables": [], "n_total": 0, "radius_m": None, "periode": None}

    def _fetch(r: float) -> list[dict]:
        rows = db.execute(text(
            "WITH p AS (SELECT geom_2975 g FROM parcels WHERE idu = :idu), "
            # MARCHE-UNIQUE-1 (NU-E-031) — dénominateur TERRAIN dédoublonné : surface = max() par
            # (mutation, parcelle) PUIS somme par mutation, jamais la somme des lignes répétées
            # (nature_culture) qui gonflait le terrain (×146 observé) et faussait le €/m². (NU-E-023) —
            # la parcelle sujet exclue. (NU-E-025) — nature terrain = Vente + Vente terrain à bâtir.
            "parc AS (SELECT DISTINCT dm.id_mutation, dm.id_parcelle, dm.valeur_fonciere AS vf, "
            "           dm.date_mutation AS d, "
            "           max(COALESCE(dm.surface_terrain,0)) OVER (PARTITION BY dm.id_mutation, dm.id_parcelle) AS terr_p, "
            "           round(ST_Distance(pp.geom_2975, p.g))::int AS dist "
            "         FROM dvf_mutations_parcelle dm JOIN parcels pp ON pp.idu = dm.id_parcelle, p "
            "         WHERE dm.nature_mutation IN ('Vente', 'Vente terrain à bâtir') "
            "           AND COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain > 0 "
            "           AND dm.date_mutation IS NOT NULL AND dm.id_parcelle <> :idu "
            "           AND " + fenetre_dvf_sql("dm.date_mutation", annees_param="ans") + " "
            "           AND ST_DWithin(pp.geom_2975, p.g, :r)), "
            "t AS (SELECT id_mutation, to_char(min(d), 'YYYY-MM-DD') AS date, "
            "        extract(year FROM min(d))::int AS annee, "
            "        sum(terr_p) AS surf, max(vf) AS vf, min(dist)::int AS dist "
            "      FROM parc GROUP BY id_mutation) "
            "SELECT date, annee, round(surf)::int AS surface_m2, round(vf)::int AS prix_eur, "
            "       round(vf / NULLIF(surf,0))::int AS prix_m2, dist AS distance_m "
            "FROM t WHERE vf / NULLIF(surf,0) BETWEEN 50 AND 4000 ORDER BY dist ASC LIMIT 200"),
            {"idu": idu, "ans": 5, "r": r}).mappings().all()
        return [dict(x) for x in rows]

    kept: list[dict] = []
    radius = None
    for r in rayons:
        kept = _fetch(r)
        if len(kept) >= 4:
            radius = int(r)
            break
    else:
        radius = int(rayons[-1]) if kept else None
    annees = [k["annee"] for k in kept if k.get("annee")]
    proches = sorted(kept, key=lambda v: (v.get("distance_m") is None, v.get("distance_m")))[:n_table]
    comparables = [{"date": f"{k['date'][5:7]}/{k['date'][0:4]}" if isinstance(k.get("date"), str) and len(k["date"]) >= 7 else None,
                    "type": "Terrain", "surface_m2": k.get("surface_m2"), "prix_eur": k.get("prix_eur"),
                    "prix_m2": k.get("prix_m2"), "distance_m": k.get("distance_m")} for k in proches]
    return {"comparables": comparables, "n_total": len(kept), "radius_m": radius,
            "periode": [min(annees), max(annees)] if annees else None}


def permits(db: Session, idu: str, *, profil: str) -> dict | None:
    """Lecture des permis (SITADEL) d'une parcelle, par le point d'appel UNIQUE. `profil` = préset de
    paramètres nommé (provisoire, MANDAT_DVF). Délègue au calcul existant — aucun recalcul."""
    if profil == PERMITS_FLASH_500M:
        # EXPORTS-1 (4.1) : les paramètres du profil sont TRANSMIS au moteur — l'audit A4 a mesuré
        # que ce chemin exécutait les défauts (300 m · 5 ans) sous un profil nommé « 500 m · 24 mois ».
        from .ingestion.permits import nearby_permits
        pid = _parcel_id(db, idu)
        if not pid:
            return None
        meta = profil_meta(profil)
        rayon = float(meta.get("rayon_m") or 500.0)
        mois = int(meta.get("fenetre_mois") or 24)
        out = nearby_permits(db, pid, radius_m=rayon, fenetre_mois=mois)
        if out is not None:
            # 4.2 : le libellé de définition voyage avec les chiffres (généré du profil, jamais en dur)
            out["fenetre_mois"] = mois
            out["libelle_definition"] = f"≤ {int(rayon)} m · {mois} mois"
        return out
    if profil == PERMITS_FICHE_36M:
        from .ingestion.permits import depots_recents
        pid = _parcel_id(db, idu)
        return depots_recents(db, pid) if pid else None
    if profil == PERMITS_VOISINAGE_100M:
        from .api.site_voisinage import voisinage_proche
        return voisinage_proche(db, idu)          # le voisinage porte DVF ET permis dans un seul dict
    raise ValueError(f"profil permis inconnu : {profil!r}")
