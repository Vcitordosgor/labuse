"""RADAR-HTML (Lot 4) — SIGNAUX CROISÉS commune/zone. Ce qu'aucune pige concurrente ne produit, parce
que ça sort de NOTRE référentiel calibré. Ils fonctionnent AU NIVEAU COMMUNE/ZONE → ils ne dépendent
PAS du rattachement parcellaire (rare, cf. Lot 0).

DOCTRINE : un signal est un ÉCART CONSTATÉ entre DEUX SOURCES DATÉES (le prix AFFICHÉ du Radar,
Sourcé portail ; le prix ACTÉ DVF, Sourcé cadastre), JAMAIS une estimation de valeur ni une
prévision. Aucun verdict. Chaque côté porte son millésime et son n ; sous SEUIL_N, on ne sert pas.

Trois usages :
  1. « prix affiché vs référentiel de zone » — par annonce (terrain) et par commune ;
  2. « écart demandé / acté » par commune — médiane Radar (demandé) vs médiane DVF (acté) ;
  3. alimentation de l'Étude de zone (« annonces actives ») et de Communes (onglet Marché).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SEUIL_N = 5   # même honnêteté statistique que l'onglet Marché : sous 5, pas de médiane servie

# RADAR-DEPOT-2 (D4) — SEUIL du badge « sous le marché ». JUSTIFICATION (mandat : « ne le sors pas du
# chapeau ») : le référentiel est la MÉDIANE DVF actée de la zone. Par construction, la moitié des
# ventes réelles sont sous leur médiane → un simple « sous la médiane » flaguerait ~50 % (inutile). Or,
# dans ce corpus, le PRIX DEMANDÉ dépasse presque toujours l'ACTÉ (mesure du Lot 4 : St-Denis bâti
# +31,9 % demandé / acté). Un prix AFFICHÉ qui tombe SOUS l'acté est donc déjà notable. La marge de
# négociation ordinaire (~5–10 %) plus la dispersion intra-zone (qualité variable) forment un bruit
# qu'il faut dépasser : on retient −15 %. L'ÉCART EXACT reste affiché quel que soit le seuil (le seuil
# filtre, il ne juge pas) ; `distribution_ecarts()` permet de le retuner sur base peuplée.
SEUIL_SOUS_MARCHE_PCT = -15.0
PERIMETRE_BATI = "maisons + appartements"   # D5 — le bâti servi aux signaux inclut les copros embasées


def _radar_medianes(db: Session, commune: str) -> dict:
    """Médianes des prix AFFICHÉS du Radar (demandé) pour une commune : terrain €/m² et bâti €/m².
    Exclut les annonces à qualifier et les non validées — jamais un fait faux dans une stat."""
    r = db.execute(text("""
        SELECT
          percentile_cont(0.5) WITHIN GROUP (ORDER BY f.prix / f.surface_terrain)
            FILTER (WHERE b.type_bien = 'terrain' AND f.prix IS NOT NULL AND f.surface_terrain > 0) AS med_terrain,
          count(*) FILTER (WHERE b.type_bien = 'terrain' AND f.prix IS NOT NULL AND f.surface_terrain > 0) AS n_terrain,
          percentile_cont(0.5) WITHIN GROUP (ORDER BY f.prix / f.surface_hab)
            FILTER (WHERE b.type_bien IN ('maison','appartement','immeuble') AND f.prix IS NOT NULL AND f.surface_hab > 0) AS med_bati,
          count(*) FILTER (WHERE b.type_bien IN ('maison','appartement','immeuble') AND f.prix IS NOT NULL AND f.surface_hab > 0) AS n_bati,
          count(*) FILTER (WHERE b.statut = 'active') AS actives
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false
          AND b.statut IN ('active','en_vente_longue') AND b.commune = :c"""),
        {"c": commune}).mappings().first() or {}
    return dict(r)


def _dvf_terrain(db: Session, commune: str) -> dict:
    """DVF acté terrain nu (référentiel UNIQUE) — médiane commune = zone U de préférence sinon AU."""
    try:
        from ..faisabilite.marche_commune import ligne2_terrain_zone
        l = ligne2_terrain_zone(db, commune)
    except Exception:  # noqa: BLE001
        return {"eur_m2": None, "n": 0, "millesime": None}
    par_zone = ((l.get("valeurs") or {}).get("par_zone")) or {}
    for fam in ("U", "AU"):
        cell = par_zone.get(fam) or {}
        if cell.get("calculable") and cell.get("median_eur_m2"):
            return {"eur_m2": float(cell["median_eur_m2"]), "n": int(cell.get("n") or 0),
                    "millesime": l.get("date_amont"), "zone": fam}
    return {"eur_m2": None, "n": 0, "millesime": l.get("date_amont")}


def _dvf_bati(db: Session, commune: str) -> dict:
    """DVF acté bâti ancien (référentiel UNIQUE `ligne1_prix_ancien` / sector_price)."""
    try:
        from ..faisabilite.marche_commune import ligne1_prix_ancien
        l = ligne1_prix_ancien(db, commune)
    except Exception:  # noqa: BLE001
        return {"eur_m2": None, "n": 0, "millesime": None}
    v = l.get("valeurs") or {}
    if v.get("median_eur_m2"):
        return {"eur_m2": float(v["median_eur_m2"]), "n": int(v.get("n") or 0),
                "millesime": l.get("date_amont")}
    return {"eur_m2": None, "n": 0, "millesime": l.get("date_amont")}


def _ecart(demande: float | None, n_dem: int, acte: dict) -> dict | None:
    """Un écart CONSTATÉ demandé/acté, servi seulement si les DEUX côtés tiennent le seuil. Porte les
    deux valeurs, les deux n, le millésime DVF, et le signe (« au-dessus »/« sous le marché »)."""
    acte_v, n_acte = acte.get("eur_m2"), int(acte.get("n") or 0)
    if demande is None or acte_v is None or n_dem < SEUIL_N or n_acte < SEUIL_N:
        return {"calculable": False, "demande_eur_m2": round(demande) if demande else None,
                "n_demande": n_dem, "acte_eur_m2": round(acte_v) if acte_v else None,
                "n_acte": n_acte, "millesime_dvf": acte.get("millesime"),
                "motif": "échantillon insuffisant d'un des deux côtés (< 5)"}
    ecart_pct = round(100.0 * (demande - acte_v) / acte_v, 1)
    return {"calculable": True, "demande_eur_m2": round(demande), "n_demande": n_dem,
            "acte_eur_m2": round(acte_v), "n_acte": n_acte, "millesime_dvf": acte.get("millesime"),
            "ecart_pct": ecart_pct,
            "sens": "au-dessus du marché acté" if ecart_pct > 0 else "sous le marché acté"}


def ecart_demande_acte(db: Session, commune: str) -> dict:
    """SIGNAL #2 — médiane des prix AFFICHÉS du Radar (demandé) contre médiane DVF (acté), par commune.
    C'est la marge de négociation du moment. Terrain ET bâti, chacun avec ses deux millésimes/n."""
    radar = _radar_medianes(db, commune)
    return {
        "commune": commune,
        # D5 — chaque famille DIT son périmètre : un chiffre sans périmètre n'est pas un fait. Le bâti
        # recouvre maisons + appartements (les copros sont embasées et comptent ici, même si elles ne
        # sont jamais servies comme annonces individuelles).
        "perimetre_terrain": "terrain nu", "perimetre_bati": PERIMETRE_BATI,
        "terrain": _ecart(radar.get("med_terrain"), int(radar.get("n_terrain") or 0), _dvf_terrain(db, commune)),
        "bati": _ecart(radar.get("med_bati"), int(radar.get("n_bati") or 0), _dvf_bati(db, commune)),
    }


def annonce_vs_referentiel(db: Session, bien_id: int) -> dict | None:
    """SIGNAL #1 (par annonce) — pour un TERRAIN, prix affiché €/m² vs terrain nu de la commune. Écart
    constaté, Sourcé des deux côtés, avec les deux millésimes. None si non applicable/non calculable."""
    row = db.execute(text(
        "SELECT b.commune, b.type_bien, f.prix, f.surface_terrain, b.a_qualifier "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id WHERE b.bien_id = :b"),
        {"b": bien_id}).mappings().first()
    if not row or row["type_bien"] != "terrain" or row["a_qualifier"]:
        return None
    if not row["prix"] or not row["surface_terrain"] or float(row["surface_terrain"]) <= 0:
        return None
    affiche = float(row["prix"]) / float(row["surface_terrain"])
    dvf = _dvf_terrain(db, row["commune"])
    if not dvf.get("eur_m2"):
        return {"calculable": False, "affiche_eur_m2": round(affiche),
                "motif": "pas de référentiel terrain nu calculable pour la commune"}
    ecart_pct = round(100.0 * (affiche - dvf["eur_m2"]) / dvf["eur_m2"], 1)
    return {"calculable": True, "affiche_eur_m2": round(affiche),
            "referentiel_eur_m2": round(dvf["eur_m2"]), "n_referentiel": dvf["n"],
            "millesime_dvf": dvf.get("millesime"), "zone": dvf.get("zone"),
            "ecart_pct": ecart_pct,
            "sens": "au-dessus du terrain nu" if ecart_pct > 0 else "sous le terrain nu"}


# ════════════════════════ D4 — badge « SOUS LE MARCHÉ » (par annonce, terrain ET bâti) ════════════════════════

def _referentiel(db: Session, commune: str, type_bien: str | None) -> dict:
    """Le référentiel DVF acté à opposer à une annonce : terrain nu pour un TERRAIN, bâti pour le BÂTI.
    Porte son périmètre (D5) — un bâti = maisons + appartements."""
    if type_bien == "terrain":
        r = _dvf_terrain(db, commune)
        r["perimetre"] = "terrain nu"
    else:
        r = _dvf_bati(db, commune)
        r["perimetre"] = PERIMETRE_BATI
    return r


def _badge(prix, surface, ref: dict) -> dict | None:
    """Le badge d'UNE annonce à partir de son prix, de sa surface pertinente et du référentiel de zone.
    None si non applicable (surface manquante → pas de €/m²). Le badge `sous_le_marche` n'est vrai que
    sous le SEUIL ; l'écart exact est TOUJOURS porté (le seuil filtre, il ne juge pas). Écart CONSTATÉ
    entre deux sources datées — jamais une estimation de valeur."""
    if not prix or not surface or float(surface) <= 0:
        return None                                             # pas de €/m² → pas de badge (mandat D4)
    affiche = float(prix) / float(surface)
    ref_v, n = ref.get("eur_m2"), int(ref.get("n") or 0)
    if not ref_v or n < SEUIL_N:
        return {"calculable": False, "affiche_eur_m2": round(affiche),
                "perimetre": ref.get("perimetre"),
                "motif": "pas de référentiel de zone calculable (échantillon < 5)"}
    ecart_pct = round(100.0 * (affiche - ref_v) / ref_v, 1)
    return {"calculable": True, "affiche_eur_m2": round(affiche), "referentiel_eur_m2": round(ref_v),
            "n_referentiel": n, "millesime_dvf": ref.get("millesime"), "zone": ref.get("zone"),
            "perimetre": ref.get("perimetre"), "ecart_pct": ecart_pct,
            "sous_le_marche": ecart_pct <= SEUIL_SOUS_MARCHE_PCT,
            "sens": "au-dessus du marché acté" if ecart_pct > 0 else "sous le marché acté"}


def badges_pour_biens(db: Session, biens: list[dict]) -> dict[int, dict | None]:
    """D4 — badge « sous le marché » pour un LOT de biens (référentiel calculé une fois par commune×famille).
    `biens` : dicts portant bien_id, commune, type_bien, a_qualifier, prix, surface_hab, surface_terrain.
    Un bien À QUALIFIER (prix suspect par définition) ne porte JAMAIS de badge."""
    cache: dict[tuple, dict] = {}

    def ref(commune, type_bien):
        cle = (commune, "terrain" if type_bien == "terrain" else "bati")
        if cle not in cache:
            cache[cle] = _referentiel(db, commune, type_bien)
        return cache[cle]

    out: dict[int, dict | None] = {}
    for b in biens:
        if b.get("a_qualifier"):
            out[b["bien_id"]] = None
            continue
        surface = b.get("surface_terrain") if b.get("type_bien") == "terrain" else b.get("surface_hab")
        out[b["bien_id"]] = _badge(b.get("prix"), surface, ref(b.get("commune"), b.get("type_bien")))
    return out


def badge_bien(db: Session, bien_id: int) -> dict | None:
    """D4 — le badge « sous le marché » d'UN bien (fiche). None si à qualifier / surface manquante."""
    row = db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien, b.a_qualifier, f.prix, f.surface_hab, f.surface_terrain "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id WHERE b.bien_id = :b"),
        {"b": bien_id}).mappings().first()
    if not row:
        return None
    return badges_pour_biens(db, [dict(row)]).get(bien_id)


def distribution_ecarts(db: Session) -> dict:
    """D4 — DISTRIBUTION des écarts prix affiché / référentiel de zone sur les biens en base (pour
    justifier / retuner le seuil). Renvoie n + percentiles (p10..p90) de l'écart %, terrain et bâti
    confondus. Purement descriptif — ne sert aucun verdict."""
    biens = [dict(r) for r in db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien, b.a_qualifier, f.prix, f.surface_hab, f.surface_terrain "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false").mappings())]
    ecarts = sorted(x["ecart_pct"] for x in badges_pour_biens(db, biens).values()
                    if x and x.get("calculable"))
    def _pct(q):
        if not ecarts:
            return None
        i = min(len(ecarts) - 1, int(q * (len(ecarts) - 1)))
        return ecarts[i]
    return {"n": len(ecarts), "seuil_retenu_pct": SEUIL_SOUS_MARCHE_PCT,
            "p10": _pct(0.10), "p25": _pct(0.25), "median": _pct(0.50),
            "p75": _pct(0.75), "p90": _pct(0.90),
            "n_sous_le_marche": sum(1 for e in ecarts if e <= SEUIL_SOUS_MARCHE_PCT)}


def annonces_actives_zone(db: Session, commune: str) -> dict:
    """SIGNAL #3 — alimente l'Étude de zone (case « annonces actives ») et Communes (onglet Marché) :
    nombre d'annonces Radar actives + médiane affichée. À qualifier et non validées exclues."""
    r = _radar_medianes(db, commune)
    n_terr = int(r.get("n_terrain") or 0)
    n_bati = int(r.get("n_bati") or 0)
    return {
        "commune": commune,
        "actives": int(r.get("actives") or 0),
        # D5 — le périmètre est DIT à côté de chaque chiffre (bâti = maisons + appartements).
        "perimetre_terrain": "terrain nu", "perimetre_bati": PERIMETRE_BATI,
        "prix_m2_terrain": {"valeur": round(float(r["med_terrain"])) if r.get("med_terrain") and n_terr >= SEUIL_N else None,
                            "n": n_terr, "insuffisant": n_terr < SEUIL_N, "perimetre": "terrain nu"},
        "prix_m2_bati": {"valeur": round(float(r["med_bati"])) if r.get("med_bati") and n_bati >= SEUIL_N else None,
                        "n": n_bati, "insuffisant": n_bati < SEUIL_N, "perimetre": PERIMETRE_BATI},
        "ecart_demande_acte": ecart_demande_acte(db, commune),
    }
