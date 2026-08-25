"""M-U — Agent Prix : assemblage du bloc « Marché » par commune. POINT DE CALCUL UNIQUE.

9 lignes (groupes PRIX / DYNAMIQUE / OFFRE + loyer), toutes Sourcées. CHAQUE ligne porte SA date
amont — le bloc ne prétend JAMAIS à un millésime unique (les lignes DVF bâti, DVF terrain, Sitadel,
DPE, run servi et DHUP ont des dates distinctes). Une ligne non calculable est PRÉSENTE avec son
motif (« n < 30 », « n < 10 »…), jamais omise en silence (doctrine « tout montrer »).

AUCUN nouveau calcul de prix :
- Ligne 1 (prix ancien) APPELLE `bilan.sector_price` (parcelle représentative = centroïde commune) ;
- Ligne 3 (prix neuf) APPELLE `dvf_prix_neuf.resolve_prix_neuf_marche` ;
- Ligne 2 (terrain × zone) ÉTEND la logique terrain (dvf_mutations_parcelle, comme les médianes
  secteur) au croisement commune × zone CALIBRÉE (voie A, arbitrage Vic 08/08 — taux d'attache
  mesuré 97,7 %) ; n ≥ 10 par cellule ;
- Ligne 9 (loyer) APPELLE `loyers.get_loyers`.
Les tendance/liquidité (4/5) sont de NOUVEAUX calculs mais sur la MÊME population que sector_price
(ventes bâti DVF), pas un percentile_cont de plus sur une population différente.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import DPE_DOM_INTERDICTION_LOCATION, Q_A_RUN_LABEL
from ..verdict_servi import TIERS_SERVABLES

#: seuils d'honnêteté (arbitrage Vic 08/08). Sous le seuil : ligne « non calculable », jamais un
#: chiffre inventé (une flèche sur 8 ventes est un mensonge statistique).
SEUIL_TENDANCE_N = 30       # par fenêtre 12 mois (comptage Sitadel/DVF mêlé — pas un seuil DVF pur)


def _seuil_terrain_cellule() -> int:
    """M103 P1 — le seuil d'effectif de la cellule commune × zone est LU de la config
    (seuils_effectif.terrain_cellule_commune, dvf_profils.yaml) — plus jamais en dur ici."""
    from ..marche_service import seuil_effectif_local
    return seuil_effectif_local("terrain_cellule_commune", 10)


#: valeur RÉSOLUE à l'import depuis la config (source unique) — le littéral ci-dessus n'est
#: qu'un repli prudent si la config est absente (base de test), jamais un second critère.
SEUIL_TERRAIN_CELLULE_N = _seuil_terrain_cellule()


def _ligne(cle: str, groupe: str, *, valeurs: dict, source: str, date_amont: str | None,
           fiabilite: str, etiquette: str, calculable: bool = True, motif: str | None = None) -> dict:
    return {"cle": cle, "groupe": groupe, "calculable": calculable, "motif": motif,
            "valeurs": valeurs, "source": source, "date_amont": date_amont,
            "fiabilite": fiabilite, "etiquette": etiquette}


def _repr_parcel(db: Session, commune: str) -> int | None:
    """Parcelle la plus proche du centroïde de la commune → sert de point d'appel aux fonctions
    PARCELLAIRES réutilisées (sector_price, resolve_prix_neuf_marche) dont le rayon adaptatif
    remonte au niveau commune. Aucun nouveau calcul : on RÉUTILISE la fonction existante."""
    return db.execute(text(
        "SELECT id FROM parcels WHERE commune = :c AND geom_2975 IS NOT NULL "
        "ORDER BY centroid <-> (SELECT ST_Centroid(ST_Collect(centroid)) FROM parcels WHERE commune = :c) "
        "LIMIT 1"), {"c": commune}).scalar()


def _dvf_millesime(db: Session, commune: str) -> str | None:
    y = db.execute(text("SELECT max(extract(year FROM date_mutation))::int FROM dvf_mutations WHERE commune = :c"),
                   {"c": commune}).scalar()
    return f"DVF {y}" if y else None


# ── Groupe PRIX ────────────────────────────────────────────────────────────────────────────────

def ligne1_prix_ancien(db: Session, commune: str) -> dict:
    from .bilan import sector_price
    from .engine import Hypotheses
    pid = _repr_parcel(db, commune)
    sp = sector_price(db, pid, Hypotheses.charger()) if pid else {}
    if not sp or not sp.get("fiable") or sp.get("median") is None:
        return _ligne("prix_ancien_median", "PRIX", valeurs={},
                      source="DVF (sector_price)", date_amont=_dvf_millesime(db, commune),
                      fiabilite="insuffisant", etiquette="Sourcé · DVF",
                      calculable=False, motif="échantillon insuffisant (sector_price)")
    return _ligne("prix_ancien_median", "PRIX",
                  valeurs={"median_eur_m2": sp["median"], "q1": sp.get("q1"), "q3": sp.get("q3"),
                           "n": sp.get("n"), "type_prix": sp.get("type_prix")},
                  source="DVF (sector_price)", date_amont=_dvf_millesime(db, commune),
                  fiabilite=sp.get("fiabilite", "moyenne"), etiquette="Sourcé · millésime DVF")


def prix_terrain_nu_zone(db: Session, commune: str | None, zone: str | None) -> dict | None:
    """LE référentiel UNIQUE du prix marché du terrain nu, pour UNE zone (fusion « Étudier un bien »,
    Vic 21/08/2026). Point de calcul unique déjà partagé par la fiche / l'outil Marché / le
    comparateur (M79) — la calculette (/charge) ET le constat servi le lisent ICI, jamais deux
    sources divergentes (l'ancien `score_e.prix_probable` reste vivant pour banquier/argu/PDF/copilote,
    mais n'alimente plus l'outil fusionné). Retourne {eur_m2, fiabilite, n} ou None (zone hors U/AU,
    commune inconnue, ou aucune vente terrain calculable). Réutilise `ligne2_terrain_zone` (mêmes
    chiffres que le bloc Marché) — aucun calcul parallèle."""
    if not commune or not zone:
        return None
    fam = "AU" if str(zone).upper().startswith("AU") else str(zone)[:1].upper()
    if fam not in ("U", "AU"):
        return None
    l = ligne2_terrain_zone(db, commune)
    pz = ((l.get("valeurs") or {}).get("par_zone") or {}).get(fam)
    if pz and pz.get("calculable"):
        return {"eur_m2": pz.get("median_eur_m2"), "fiabilite": l.get("fiabilite"), "n": pz.get("n")}
    return None


def ligne2_terrain_zone(db: Session, commune: str) -> dict:
    """LIGNE EXCLUSIVE — médiane €/m² du terrain NU par zone PLU CALIBRÉE (U vs AU), voie A.
    Source = dvf_mutations_parcelle (ventes terrain nu) × parcel_zone_plu (zonage calibré LABUSE).
    Date amont = millésime de dvf_mutations_parcelle (≠ dvf_mutations des lignes 1/3 — P2-54)."""
    # Dédup comme dvf_marche : une mutation est répétée par parcelle ET par nature_culture. On prend
    # UN terrain par (mutation, parcelle) (max OVER), on SOMME le terrain de la mutation, et le €/m²
    # (valeur / terrain TOTAL de la mutation) est calculé UNE fois — jamais valeur÷un-bout (artefact
    # AU 28 089 €/m² mesuré sur le calcul naïf ; dédupé : ~328 €/m²). Une mutation compte dans chaque
    # zone qu'elle touche.
    rows = db.execute(text("""
        WITH parc AS (
          SELECT DISTINCT m.id_mutation, m.id_parcelle, z.zone_fam, m.valeur_fonciere AS val,
                 m.millesime AS mill,
                 max(COALESCE(m.surface_terrain,0)) OVER (PARTITION BY m.id_mutation, m.id_parcelle) AS terr_parc
          FROM dvf_mutations_parcelle m
          JOIN parcels p ON p.idu = m.id_parcelle AND p.commune = :c
          JOIN parcel_zone_plu z ON z.idu = m.id_parcelle
          WHERE m.nature_mutation = 'Vente' AND COALESCE(m.surface_reelle_bati,0) = 0
            AND m.surface_terrain > 0 AND z.zone_fam IN ('U','AU')),
        tot AS (SELECT id_mutation, sum(terr_parc) AS terr_tot, max(val) AS val, max(mill) AS mill
                FROM parc GROUP BY id_mutation),
        muz AS (SELECT DISTINCT id_mutation, zone_fam FROM parc)
        SELECT muz.zone_fam,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY tot.val / NULLIF(tot.terr_tot,0)) AS med,
               count(*) AS n, max(tot.mill) AS mill
        FROM muz JOIN tot USING (id_mutation)
        WHERE tot.terr_tot > 0
        GROUP BY muz.zone_fam"""), {"c": commune}).mappings().all()
    par_zone = {r["zone_fam"]: r for r in rows}
    mill = max((r["mill"] for r in rows), default=None)
    cellules = {}
    for zone in ("U", "AU"):
        r = par_zone.get(zone)
        if r and r["n"] >= SEUIL_TERRAIN_CELLULE_N and r["med"] is not None:
            cellules[zone] = {"median_eur_m2": round(r["med"]), "n": r["n"], "calculable": True}
        else:
            cellules[zone] = {"calculable": False, "n": (r["n"] if r else 0),
                              "motif": f"n < {SEUIL_TERRAIN_CELLULE_N}"}
    ok = any(c["calculable"] for c in cellules.values())
    return _ligne("prix_terrain_nu_par_zone", "PRIX",
                  valeurs={"par_zone": cellules},
                  source="DVF terrains (dvf_mutations_parcelle) × zonage calibré LABUSE",
                  date_amont=(f"DVF terrain {mill}" if mill else None),
                  fiabilite="moyenne" if ok else "insuffisant",
                  etiquette="Sourcé · millésime DVF terrain · zonage calibré",
                  calculable=ok, motif=None if ok else f"aucune cellule U/AU ≥ {SEUIL_TERRAIN_CELLULE_N}")


def ligne3_prix_neuf(db: Session, commune: str) -> dict:
    from ..ingestion.dvf_prix_neuf import niveau_prix_label, resolve_prix_neuf_marche
    pid = _repr_parcel(db, commune)
    prix, niveau, n, motif = resolve_prix_neuf_marche(db, pid) if pid else (None, None, None, "commune inconnue")
    if prix is None:
        return _ligne("prix_sortie_neuf", "PRIX", valeurs={},
                      source="DVF neuf (dvf_prix_sortie_neuf)", date_amont=_dvf_millesime(db, commune),
                      fiabilite="insuffisant", etiquette="Sourcé · DVF neuf",
                      calculable=False, motif=motif or "non calculable")
    return _ligne("prix_sortie_neuf", "PRIX",
                  valeurs={"prix_eur_m2": round(prix), "niveau": niveau, "n": n},
                  source="DVF neuf (dvf_prix_sortie_neuf)", date_amont=_dvf_millesime(db, commune),
                  fiabilite="bonne" if niveau == "secteur" else "moyenne",
                  etiquette="Sourcé · " + niveau_prix_label(niveau, n))


# ── Groupe DYNAMIQUE ─────────────────────────────────────────────────────────────────────────

def ligne4_tendance(db: Session, commune: str) -> dict:
    """Médiane €/m² bâti sur 12 m. vs 12 m. précédents (même population que sector_price : ventes
    bâti). n ≥ 30 par fenêtre, sinon « non calculable » — jamais une flèche sur 8 ventes."""
    # MÊME population que sector_price (bornes + type appart/maison + dédup par mutation réelle
    # mutation_id) pour ne pas fabriquer une deuxième médiane divergente ; on FENÊTRE seulement.
    r = db.execute(text("""
        WITH ref AS (SELECT max(date_mutation) mx FROM dvf_mutations WHERE commune = :c),
        d AS (SELECT DISTINCT ON (mutation_id) mutation_id, date_mutation,
                     valeur_fonciere / NULLIF(surface_reelle_bati,0) AS eur_m2
              FROM dvf_mutations
              WHERE commune = :c AND nature_mutation ILIKE '%vente%' AND surface_reelle_bati >= 20
                AND valeur_fonciere > 20000 AND type_local ILIKE ANY(ARRAY['%APPARTEMENT%','%MAISON%'])
                AND date_mutation > (SELECT mx FROM ref) - interval '24 months'),
        f AS (SELECT date_mutation > (SELECT mx FROM ref) - interval '12 months' AS recent, eur_m2 FROM d)
        SELECT count(*) FILTER (WHERE recent) n12,
               count(*) FILTER (WHERE NOT recent) nprev,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY eur_m2) FILTER (WHERE recent) med12,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY eur_m2) FILTER (WHERE NOT recent) medprev,
               (SELECT extract(year FROM mx)::int FROM ref) yr
        FROM f"""), {"c": commune}).mappings().first()
    if not r or (r["n12"] or 0) < SEUIL_TENDANCE_N or (r["nprev"] or 0) < SEUIL_TENDANCE_N \
            or not r["med12"] or not r["medprev"]:
        return _ligne("tendance_12m", "DYNAMIQUE", valeurs={"n12": r["n12"] if r else 0,
                      "nprev": r["nprev"] if r else 0},
                      source="DVF", date_amont=(f"DVF {r['yr']}" if r and r["yr"] else None),
                      fiabilite="insuffisant", etiquette="Sourcé · DVF",
                      calculable=False, motif=f"tendance non calculable — n < {SEUIL_TENDANCE_N} par fenêtre")
    delta = (r["med12"] - r["medprev"]) / r["medprev"] * 100
    # M144 Lot 5.1 — seuil resserré à ±2 % : « stable −4,2 % » (mot ⟂ chiffre) était faux. Sous ±2 %/an
    # (bruit de la médiane DVF communale) = stable ; au-delà, hausse/baisse, cohérent avec le signe.
    sens = "hausse" if delta >= 2 else "baisse" if delta <= -2 else "stable"
    return _ligne("tendance_12m", "DYNAMIQUE",
                  valeurs={"delta_pct": round(delta, 1), "sens": sens,
                           "median_12m": round(r["med12"]), "median_prec": round(r["medprev"]),
                           "n12": r["n12"], "nprev": r["nprev"]},
                  source="DVF", date_amont=f"DVF {r['yr']}", fiabilite="bonne",
                  etiquette="Sourcé · fenêtres 12 m. glissantes affichées")


def ligne5_liquidite(db: Session, commune: str) -> dict:
    """Mutations/trimestre (4 derniers) + delta vs même trimestre N-1. Le tempo du marché."""
    rows = db.execute(text("""
        SELECT to_char(date_trunc('quarter', date_mutation), 'YYYY"T"Q') AS trim, count(*) n
        FROM dvf_mutations
        WHERE commune = :c AND nature_mutation = 'Vente' AND surface_reelle_bati >= 20
          AND valeur_fonciere > 20000
        GROUP BY 1 ORDER BY 1 DESC LIMIT 8"""), {"c": commune}).mappings().all()
    if len(rows) < 4:
        return _ligne("liquidite", "DYNAMIQUE", valeurs={"trimestres": [dict(r) for r in rows]},
                      source="DVF", date_amont=_dvf_millesime(db, commune),
                      fiabilite="faible", etiquette="Sourcé · DVF",
                      calculable=False, motif="historique trimestriel insuffisant")
    derniers = [dict(r) for r in rows[:4]]
    n_dernier = derniers[0]["n"]
    n_an_avant = rows[4]["n"] if len(rows) >= 5 else None
    delta = (round(100 * (n_dernier - n_an_avant) / n_an_avant) if n_an_avant else None)
    return _ligne("liquidite", "DYNAMIQUE",
                  valeurs={"trimestres": derniers, "mutations_dernier_trim": n_dernier,
                           "delta_pct_an": delta},
                  source="DVF", date_amont=_dvf_millesime(db, commune), fiabilite="bonne",
                  etiquette="Sourcé · DVF (mutations/trimestre)")


# ── Groupe OFFRE ─────────────────────────────────────────────────────────────────────────────

def ligne6_offre_engagee(db: Session, commune: str) -> dict:
    """Logements AUTORISÉS (Sitadel) sur 12 mois glissants — l'offre engagée."""
    r = db.execute(text("""
        WITH ref AS (SELECT max(date) mx FROM sitadel_permits)
        SELECT count(*) permis, max(date)::date dernier,
               sum(CASE WHEN raw->>'nb_lgt' ~ '^[0-9]+$' THEN (raw->>'nb_lgt')::int ELSE 0 END) logements
        FROM sitadel_permits
        WHERE commune = :c AND date > (SELECT mx FROM ref) - interval '12 months'"""),
        {"c": commune}).mappings().first()
    if not r or not r["permis"]:
        return _ligne("offre_engagee", "OFFRE", valeurs={"logements_12m": 0, "permis_12m": 0},
                      source="Sitadel (SDES)", date_amont=None, fiabilite="moyenne",
                      etiquette="Sourcé · Sitadel", calculable=False,
                      motif="aucun permis autorisé sur 12 mois")
    return _ligne("offre_engagee", "OFFRE",
                  valeurs={"logements_12m": int(r["logements"] or 0), "permis_12m": r["permis"]},
                  source="Sitadel (SDES)", date_amont=(f"dernier permis {r['dernier']}" if r["dernier"] else None),
                  fiabilite="bonne", etiquette="Sourcé · date dernier permis")


def ligne7_gisement(db: Session, commune: str) -> dict:
    """LIGNE EXCLUSIVE — l'offre POTENTIELLE : SDP résiduelle des parcelles en tiers SERVABLES,
    RUN SERVI épinglé (jamais les écartées, jamais « le dernier run calculé »)."""
    r = db.execute(text("""
        SELECT round(sum(r.sdp_residuelle_m2)) sdp, count(*) parcelles, max(r.computed_at)::date maj
        FROM parcel_residuel r
        JOIN parcels p ON p.id = r.parcel_id AND p.commune = :c
        JOIN parcel_p_score_v2 s ON s.parcelle_id = p.idu AND s.run_id = :run
        WHERE s.tier = ANY(:tiers) AND r.sdp_residuelle_m2 > 0"""),
        {"c": commune, "run": Q_A_RUN_LABEL, "tiers": list(TIERS_SERVABLES)}).mappings().first()
    if not r or not r["sdp"]:
        return _ligne("gisement_constructible", "OFFRE", valeurs={"sdp_residuelle_m2": 0, "parcelles": 0},
                      source="LABUSE — SDP résiduelle, tiers servables", date_amont=None,
                      fiabilite="moyenne", etiquette="Sourcé LABUSE", calculable=False,
                      motif="aucune parcelle servable avec SDP résiduelle")
    return _ligne("gisement_constructible", "OFFRE",
                  valeurs={"sdp_residuelle_m2": int(r["sdp"]), "parcelles": r["parcelles"]},
                  source="LABUSE — SDP résiduelle, tiers servables",
                  date_amont=f"run {Q_A_RUN_LABEL} · {r['maj']}", fiabilite="bonne",
                  etiquette=f"Sourcé LABUSE · run {Q_A_RUN_LABEL}")


def ligne8_pression_dpe(db: Session, commune: str) -> dict:
    """Pression DPE = % F/G sur les DPE CONNUS (parc diagnostiqué, JAMAIS le parc total) + les deux
    échéances DOM (constante partagée M-G, jamais recopiée)."""
    insee = db.execute(text("SELECT left(min(idu),5) FROM parcels WHERE commune = :c"), {"c": commune}).scalar()
    r = db.execute(text("""
        SELECT count(*) connus, count(*) FILTER (WHERE upper(etiquette_dpe) IN ('F','G')) fg
        FROM dpe_records WHERE code_insee = :i AND etiquette_dpe IS NOT NULL"""),
        {"i": insee}).mappings().first()
    ech = f"G interdit à la location au {DPE_DOM_INTERDICTION_LOCATION['G']}, F au {DPE_DOM_INTERDICTION_LOCATION['F']}"
    if not r or not r["connus"]:
        # LOT10 (OUTILS-FINALE) — `date_amont` = « ADEME » seul : le « (DPE connus) » redondant donnait
        # le libellé cassé « Sourcé · sur 0 DPE connu · ADEME (DPE connus) ». Le compte des DPE connus
        # est DÉJÀ porté par l'étiquette ; la fraîcheur n'a qu'à nommer la source.
        return _ligne("pression_dpe", "OFFRE", valeurs={"echeances": ech, "dpe_connus": 0},
                      source="DPE ADEME + calendrier DOM (M-G)", date_amont="ADEME",
                      fiabilite="faible", etiquette="Sourcé · sur 0 DPE connu", calculable=False,
                      motif="aucun DPE connu sur la commune")
    pct = round(100 * r["fg"] / r["connus"], 1)
    return _ligne("pression_dpe", "OFFRE",
                  valeurs={"pct_fg": pct, "fg": r["fg"], "dpe_connus": r["connus"], "echeances": ech},
                  source="DPE ADEME + calendrier DOM (M-G)", date_amont="ADEME",
                  fiabilite="moyenne", etiquette=f"Sourcé · sur {r['connus']} DPE connus · {ech}")


def ligne9_loyer(db: Session, commune: str) -> dict:
    from ..loyers import get_loyers
    insee = db.execute(text("SELECT left(min(idu),5) FROM parcels WHERE commune = :c"), {"c": commune}).scalar()
    rec = get_loyers(insee=insee, commune=commune)
    seg = (rec or {}).get("appartement") or (rec or {}).get("maison") if rec else None
    if not rec or not seg or seg.get("loyer_m2") is None:
        return _ligne("loyer_median", "LOYER", valeurs={},
                      source="DHUP (carte des loyers)", date_amont=(rec or {}).get("millesime") if rec else None,
                      fiabilite="insuffisant", etiquette="Sourcé · DHUP", calculable=False,
                      motif="commune hors dataset loyers DHUP")
    return _ligne("loyer_median", "LOYER",
                  valeurs={"loyer_eur_m2": seg["loyer_m2"], "type": "appartement" if rec.get("appartement") else "maison"},
                  source="DHUP (carte des loyers)", date_amont=rec.get("millesime"),
                  fiabilite=seg.get("fiabilite", "moyenne"), etiquette="Sourcé · millésime DHUP")


def market_signal(db: Session, commune: str) -> dict:
    """M-U volet B — signal de marché REBRANCHÉ sur les ACTES : label dérivé de la liquidité (DVF,
    ligne 5) et de l'offre engagée future (Sitadel, ligne 6). REPREND la logique du signal Obsimmo
    (score 50 ± composantes → favorable/neutre/prudence + fiabilité) mais SANS aucune lecture du
    JSON Obsimmo. Servi UNIQUEMENT avec ses deux composantes visibles — jamais un mot nu. Source :
    « DVF (actes) + Sitadel (autorisations) ». « Non calculable » si les deux entrées manquent."""
    liq = ligne5_liquidite(db, commune)
    off = ligne6_offre_engagee(db, commune)
    composantes: list[dict] = []
    score = 50  # neutre, ajusté par composante, borné 0–100

    if liq["calculable"] and liq["valeurs"].get("delta_pct_an") is not None:
        d = liq["valeurs"]["delta_pct_an"]           # + : plus de ventes qu'un an avant = plus liquide
        score += round(max(-1.0, min(1.0, d / 40.0)) * 20)
        composantes.append({"cle": "Liquidité (DVF)", "sens": "+" if d > 0 else "−" if d < 0 else "=",
                            "valeur": f"{liq['valeurs']['mutations_dernier_trim']} ventes au dernier "
                                      f"trimestre ({d:+d} % vs an−1)"})
    if off["calculable"]:
        lg = off["valeurs"]["logements_12m"]          # offre engagée forte = concurrence à la revente
        score += 10 if lg == 0 else 4 if lg < 50 else -6 if lg < 200 else -12
        composantes.append({"cle": "Offre engagée (Sitadel)", "sens": "−" if lg >= 50 else "+",
                            "valeur": f"{lg} logements autorisés / 12 mois"})

    if not composantes:
        return {"disponible": False, "source": "DVF (actes) + Sitadel (autorisations)",
                "note": "Signal non calculable — ni liquidité DVF ni offre Sitadel exploitables."}
    score = max(0, min(100, score))
    label = "favorable" if score >= 60 else "prudence" if score < 40 else "neutre"
    fiab = "bonne" if (liq["calculable"] and off["calculable"]) else "moyenne"
    return {"disponible": True, "label": label, "composantes": composantes, "fiabilite": fiab,
            "source": "DVF (actes) + Sitadel (autorisations)",
            "date_amont": {"liquidite": liq["date_amont"], "offre": off["date_amont"]}}


def build_marche_commune(db: Session, commune: str) -> dict:
    """Assemble le bloc « Marché » d'une commune — les 9 lignes, chacune avec sa date amont. Toutes
    les surfaces (outil, fiche, market_signal) lisent CE bloc : point de calcul unique."""
    lignes = [
        ligne1_prix_ancien(db, commune), ligne2_terrain_zone(db, commune),
        ligne3_prix_neuf(db, commune), ligne4_tendance(db, commune),
        ligne5_liquidite(db, commune), ligne6_offre_engagee(db, commune),
        ligne7_gisement(db, commune), ligne8_pression_dpe(db, commune),
        ligne9_loyer(db, commune),
    ]
    return {"commune": commune, "lignes": lignes,
            "market_signal": market_signal(db, commune),
            "note": "Chaque ligne porte SA date de source amont — le bloc ne prétend pas à un "
                    "millésime unique (P2-54). Fraîcheur = date source amont."}
