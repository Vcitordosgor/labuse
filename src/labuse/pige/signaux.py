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

# RADAR-VEILLE-1 (R2a) — RÉFÉRENCE DU MÊME TYPE DE BIEN. Comparer une maison à une médiane « maisons +
# appartements » mélange deux marchés au €/m² différent (mesuré : la référence mixte, tirée vers le bas
# par les appartements sans terrain, sur-évalue les maisons — écart médian +34,8 % vs +5,4 % en médiane
# maisons seule, corpus RADAR-VEILLE-1). On sert la médiane DVF du MÊME type dès qu'elle tient ce seuil ;
# sinon repli sur la référence mixte, dont le périmètre est alors écrit tel quel.
SEUIL_REF_TYPE = 30

# RADAR-VEILLE-1 (R2b) — LE BIAIS DU TERRAIN. Le €/m² d'une maison est calculé sur l'habitable seul, mais
# le prix inclut le terrain : une maison à grand terrain est mécaniquement « au-dessus du marché ». Mesuré
# sur le corpus : la part foncière (surface_terrain × réf. terrain nu / prix) est MAJORITAIRE pour 16 des
# 25 maisons connues (médiane 0,54). Au-delà de ce seuil, le prix au m² habitable n'est PAS comparable au
# bâti — on ne rend alors AUCUN verdict « sous/au-dessus » (le €/m² reste affiché, avec la mention du
# motif). Choix mesuré, pas arbitraire : « la valeur est majoritairement foncière » est le point de bascule.
SEUIL_PART_FONCIERE = 0.5

# FICHE-COMMUNE-2 (C5) — SEUIL de la MÉDIANE LOCALE (autour de la parcelle rattachée). Diagnostic :
# la référence commune-entière (médiane DVF du type sur toute la commune, n = 1000+) est TROP LARGE →
# toutes les maisons paraissent « sous le marché » (−24 à −54 %), tous les appartements « au-dessus »
# (+70 à +231 %), car un bien d'un quartier est comparé à la commune entière. Correctif : quand le bien
# est rattaché à une parcelle, on prend la médiane DVF du MÊME TYPE dans un rayon autour d'elle (le
# moteur « Marché et secteur » de la fiche parcelle) ; repli commune SEULEMENT à défaut, et on le DIT.
SEUIL_REF_LOCAL = 8   # sous ce n dans le rayon, le local ne tient pas → on élargit puis on replie commune


def _ref_local(db: Session, idu: str | None, type_bien: str | None) -> dict | None:
    """C5 — MÉDIANE LOCALE du MÊME type autour de la parcelle rattachée (rayon adaptatif 500→1500 m,
    même filtre de retenue que le baromètre). None si pas d'idu, type non bâti, ou n < SEUIL_REF_LOCAL
    à 1500 m (→ repli commune). Sert la médiane secteur, jamais la commune entière (diagnostic C5)."""
    tl = {"maison": "Maison", "appartement": "Appartement", "immeuble": "Maison"}.get(type_bien or "")
    if not idu or not tl:
        return None
    from ..api.moteurs import _BAROMETRE_RETENUE
    for rayon in (500.0, 1000.0, 1500.0):
        r = db.execute(text(
            f"SELECT count(*) n, "
            f"  percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati,0)) m, "
            f"  to_char(max(date_mutation), 'YYYY') AS millesime "
            f"FROM dvf_mutations "
            f"WHERE type_local = :t AND {_BAROMETRE_RETENUE} "
            f"  AND ST_DWithin(geom::geography, "
            f"      (SELECT centroid::geography FROM parcels WHERE idu = :idu), :rad)"),
            {"t": tl, "idu": idu, "rad": rayon}).mappings().first()
        if r and r["m"] and int(r["n"]) >= SEUIL_REF_LOCAL:
            return {"eur_m2": float(r["m"]), "n": int(r["n"]), "millesime": r["millesime"],
                    "perimetre": f"{'maisons' if tl == 'Maison' else 'appartements'} · {int(rayon)} m autour de la parcelle",
                    "meme_type": True, "locale": True, "rayon_m": int(rayon)}
    return None


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

def _dvf_bati_type(db: Session, commune: str, type_bien: str | None) -> dict:
    """R2a — référence DVF actée du MÊME TYPE (maison → médiane maisons, appartement → médiane appts),
    servie dès `SEUIL_REF_TYPE` ventes ; sinon repli sur la médiane bâti MIXTE (périmètre écrit tel quel).
    Même filtre de retenue que le baromètre `prix_ancien` — un seul moteur de prix acté."""
    from ..api.moteurs import _BAROMETRE_RETENUE
    tl = {"maison": "Maison", "appartement": "Appartement", "immeuble": "Maison"}.get(type_bien or "")
    if tl:
        r = db.execute(text(
            f"SELECT count(*) n, "
            f"  percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati,0)) m, "
            f"  to_char(max(date_mutation), 'YYYY') AS millesime "
            f"FROM dvf_mutations WHERE commune = :c AND type_local = :t AND {_BAROMETRE_RETENUE}"),
            {"c": commune, "t": tl}).mappings().first()
        if r and r["m"] and int(r["n"]) >= SEUIL_REF_TYPE:
            return {"eur_m2": float(r["m"]), "n": int(r["n"]), "millesime": r["millesime"],
                    "perimetre": "maisons" if tl == "Maison" else "appartements", "meme_type": True}
    r2 = db.execute(text(
        f"SELECT count(*) n, "
        f"  percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati,0)) m, "
        f"  to_char(max(date_mutation), 'YYYY') AS millesime "
        f"FROM dvf_mutations WHERE commune = :c AND type_local IN ('Maison','Appartement') AND {_BAROMETRE_RETENUE}"),
        {"c": commune}).mappings().first()
    return {"eur_m2": float(r2["m"]) if r2 and r2["m"] else None, "n": int(r2["n"]) if r2 else 0,
            "millesime": (r2 or {}).get("millesime"), "perimetre": PERIMETRE_BATI, "meme_type": False}


def _referentiel(db: Session, commune: str, type_bien: str | None, idu: str | None = None) -> dict:
    """Le référentiel DVF acté à opposer à une annonce. C5 — pour le BÂTI, on prend d'abord la MÉDIANE
    LOCALE du même type autour de la parcelle rattachée (`_ref_local`) ; repli sur la médiane commune
    (`_dvf_bati_type`) SEULEMENT à défaut, marqué `repli_commune` pour que l'affichage le DISE. Terrain :
    référentiel de zone (déjà plus étroit que la commune entière). Porte toujours son périmètre."""
    if type_bien == "terrain":
        r = _dvf_terrain(db, commune)
        r["perimetre"] = "terrain nu"
        r["locale"] = False
        return r
    if idu:                                          # bien rattaché → médiane secteur d'abord
        loc = _ref_local(db, idu, type_bien)
        if loc:
            return loc
    r = _dvf_bati_type(db, commune, type_bien)
    r["locale"] = False
    r["repli_commune"] = bool(idu)                   # une parcelle était rattachée, mais le local n'a pas tenu
    return r


def _libelle_ecart(ecart_pct: float) -> str:
    """R2c — formulation NON ambiguë. « au-dessus du marché acté (104,4 %) » se lit aussi « à 104,4 % du
    marché » (à peine au-dessus) : faux. On écrit le signe explicite, et le multiple au-delà de +100 %."""
    signe = "+" if ecart_pct > 0 else "−"
    base = f"{signe}{abs(ecart_pct):.1f} %".replace(".", ",")
    if ecart_pct >= 100.0:
        return f"{base} ({1 + ecart_pct / 100:.2f}× le marché acté)".replace(".", ",")
    return base


def _badge(prix, type_bien, surface_hab, surface_terrain, ref: dict,
           terrain_ref_eur_m2: float | None) -> dict | None:
    """Le badge « sous le marché » d'UNE annonce (écart CONSTATÉ entre deux sources datées, jamais une
    estimation). None si pas de €/m² calculable. R2b : pour une maison dont la valeur est MAJORITAIREMENT
    foncière (`part_fonciere ≥ SEUIL`), le €/m² habitable n'est pas comparable au bâti → on rend le €/m²
    et le motif, mais AUCUN verdict « sous/au-dessus » (jamais un faux positif structurel)."""
    surface = surface_terrain if type_bien == "terrain" else surface_hab
    if not prix or not surface or float(surface) <= 0:
        return None                                             # pas de €/m² → pas de badge (mandat D4)
    affiche = float(prix) / float(surface)
    base = {"calculable": None, "affiche_eur_m2": round(affiche), "perimetre": ref.get("perimetre")}

    # R2b — garde-fou du biais terrain (maisons seulement : l'appartement n'a pas de terrain).
    part_fonciere = None
    if type_bien in ("maison", "immeuble") and surface_terrain and terrain_ref_eur_m2 and float(prix) > 0:
        part_fonciere = round(float(surface_terrain) * float(terrain_ref_eur_m2) / float(prix), 2)
    if part_fonciere is not None and part_fonciere >= SEUIL_PART_FONCIERE:
        return {**base, "calculable": False, "part_fonciere": part_fonciere, "sous_le_marche": False,
                "motif": "valeur surtout foncière — le prix au m² habitable n'est pas comparable au bâti"}

    ref_v, n = ref.get("eur_m2"), int(ref.get("n") or 0)
    if not ref_v or n < SEUIL_N:
        return {**base, "calculable": False, "part_fonciere": part_fonciere,
                "motif": "pas de référentiel de zone calculable (échantillon < 5)"}
    ecart_pct = round(100.0 * (affiche - ref_v) / ref_v, 1)
    # C5 — le VERDICT « sous le marché » n'est porté que par une référence FIABLE : le terrain (référence
    # de ZONE, déjà étroite) ou le bâti à référence LOCALE (médiane secteur autour de la parcelle). Le
    # bâti à référence COMMUNE entière (repli) est trop large (diagnostic : faux « sous le marché »
    # systématiques) → on montre l'écart SANS badge (« pas de badge sous le seuil » sur repli commune).
    reference_locale = bool(ref.get("locale"))
    reference_fiable = type_bien == "terrain" or reference_locale
    return {**base, "calculable": True, "referentiel_eur_m2": round(ref_v), "n_referentiel": n,
            "millesime_dvf": ref.get("millesime"), "zone": ref.get("zone"),
            "meme_type_reference": bool(ref.get("meme_type")), "part_fonciere": part_fonciere,
            "reference_locale": reference_locale, "repli_commune": bool(ref.get("repli_commune")),
            "ecart_pct": ecart_pct, "ecart_libelle": _libelle_ecart(ecart_pct),
            "sous_le_marche": reference_fiable and ecart_pct <= SEUIL_SOUS_MARCHE_PCT,
            # R2c — le sens n'est plus une phrase ambiguë : signe explicite + multiple.
            "sens": ("sous le marché acté" if ecart_pct <= SEUIL_SOUS_MARCHE_PCT
                     else "au niveau du marché" if abs(ecart_pct) < 15
                     else "au-dessus du marché acté")}


def badges_pour_biens(db: Session, biens: list[dict]) -> dict[int, dict | None]:
    """D4 — badge « sous le marché » pour un LOT de biens (référentiel calculé une fois par commune×famille).
    `biens` : dicts portant bien_id, commune, type_bien, a_qualifier, prix, surface_hab, surface_terrain.
    Un bien À QUALIFIER (prix suspect par définition) ne porte JAMAIS de badge."""
    cache: dict[tuple, dict] = {}
    terrain_cache: dict[str, float | None] = {}

    def ref(commune, type_bien, idu):
        # clé PAR TYPE (R2a) ET par idu (C5 : la médiane locale est propre à la parcelle rattachée).
        # Terrain : pas de local → clé commune seule. Bâti rattaché : clé incluant l'idu.
        fam = "terrain" if type_bien == "terrain" else (type_bien or "bati")
        cle = (commune, fam, idu if (idu and fam != "terrain") else None)
        if cle not in cache:
            cache[cle] = _referentiel(db, commune, type_bien, idu)
        return cache[cle]

    def terrain_ref(commune):
        if commune not in terrain_cache:
            terrain_cache[commune] = _dvf_terrain(db, commune).get("eur_m2")
        return terrain_cache[commune]

    out: dict[int, dict | None] = {}
    for b in biens:
        if b.get("a_qualifier"):
            out[b["bien_id"]] = None
            continue
        out[b["bien_id"]] = _badge(
            b.get("prix"), b.get("type_bien"), b.get("surface_hab"), b.get("surface_terrain"),
            ref(b.get("commune"), b.get("type_bien"), b.get("idu")), terrain_ref(b.get("commune")))
    return out


def badge_bien(db: Session, bien_id: int) -> dict | None:
    """D4 — le badge « sous le marché » d'UN bien (fiche). None si à qualifier / surface manquante."""
    row = db.execute(text(
        "SELECT b.bien_id, b.commune, b.type_bien, b.a_qualifier, b.idu, "
        "       f.prix, f.surface_hab, f.surface_terrain "
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
        "WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false")).mappings()]
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
