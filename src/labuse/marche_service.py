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
        return sector_price(db, pid, Hypotheses.charger()) if pid else None
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
    rows = db.execute(text(
        "WITH p AS (SELECT geom_2975 FROM parcels WHERE idu = :idu) "
        "SELECT to_char(dm.date_mutation, 'YYYY-MM-DD') AS date, "
        "  round(ST_Distance(ST_Transform(dm.geom, 2975), p.geom_2975))::int AS distance_m, "
        "  round(dm.surface_reelle_bati)::int AS surface_m2, "
        "  round(dm.valeur_fonciere)::int AS prix_eur, "
        "  round(dm.valeur_fonciere / NULLIF(dm.surface_reelle_bati, 0))::int AS prix_m2 "
        "FROM dvf_mutations dm, p "
        "WHERE dm.geom IS NOT NULL AND dm.date_mutation IS NOT NULL "
        "  AND dm.date_mutation >= (CURRENT_DATE - make_interval(years => :ans)) "
        "  AND dm.nature_mutation ILIKE 'vente%' AND dm.valeur_fonciere > 0 "
        "  AND dm.surface_reelle_bati >= 20 "
        "  AND ST_DWithin(ST_Transform(dm.geom, 2975), p.geom_2975, :r) "
        "ORDER BY dm.date_mutation DESC LIMIT 12"),
        {"idu": idu, "ans": fenetre_ans, "r": rayon_m}).mappings().all()
    n = len(rows)
    return {"rayon_m": int(rayon_m), "fenetre_ans": fenetre_ans, "n": n,
            "comparables": [dict(r) for r in rows],
            "seuil_effectif": seuil, "effectif_suffisant": n >= seuil,   # sous le seuil : « échantillon insuffisant »
            "grandeur": meta.get("grandeur"), "question": meta.get("question"),
            "reserve": reserve_methode()}


def permits(db: Session, idu: str, *, profil: str) -> dict | None:
    """Lecture des permis (SITADEL) d'une parcelle, par le point d'appel UNIQUE. `profil` = préset de
    paramètres nommé (provisoire, MANDAT_DVF). Délègue au calcul existant — aucun recalcul."""
    if profil == PERMITS_FLASH_500M:
        from .ingestion.permits import nearby_permits
        pid = _parcel_id(db, idu)
        return nearby_permits(db, pid) if pid else None
    if profil == PERMITS_FICHE_36M:
        from .ingestion.permits import depots_recents
        pid = _parcel_id(db, idu)
        return depots_recents(db, pid) if pid else None
    if profil == PERMITS_VOISINAGE_100M:
        from .api.site_voisinage import voisinage_proche
        return voisinage_proche(db, idu)          # le voisinage porte DVF ET permis dans un seul dict
    raise ValueError(f"profil permis inconnu : {profil!r}")
