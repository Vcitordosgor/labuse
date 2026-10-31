"""COHERENCE-HOOK-1 — un même fait, UNE seule valeur, servie à l'identique par toutes les surfaces.

Sur les 12 parcelles témoins du lot A, pour chaque FAIT (SDP, médiane de marché, nombre d'aléas, zone,
surface, estimation), on extrait la valeur TELLE QU'ELLE EST SERVIE par chaque point de lecture du
produit — fiche, outils, PDF/Docs (mêmes builders), Copilote — en appelant les POINTS D'ENTRÉE réels
en process, et on exige l'ÉGALITÉ à l'euro / au m² près. Le moindre écart fait ÉCHOUER : c'est le filet
qui rend la dérive (« un même fait, plusieurs valeurs ») impossible à passer inaperçue.

Chaque point de lecture appelé ici est celui que sert l'app (pas une reconstitution) :
  • zone        — `zone_servie.zone_dominante` (fiche + Copilote `destination_zone`/`regles_plu_zone`)
                  vs la zone dominante servie dans la fiche (`reglement_plu.zones[0]`).
  • médiane     — `marche_dvf_commune.mediane_commune` (point unique) vs le tableau Radar
                  (`pige.signaux._dvf_bati_type`) vs le bloc commune (`faisabilite.marche_commune_bloc`).
  • estimation  — l'endpoint `radar_annonce_estimation` (outil + PDF « Estimer un bien ») vs la fonction
                  `estimation_annonce` (point unique) : MÊME valeur à l'euro.
  • aléas       — l'endpoint d'estimation (`n_aleas`) vs le point unique `_risques_rows` ; + la cohérence
                  interne du bloc aléas de la fiche (`aleas.n == len(aleas.liste)`).
  • surface     — la surface de terrain servie par la fiche vs le point unique `surface.surface_terrain`.
  • SDP         — en-tête (parcel_residuel) vs verdict (score_labuse) vs scoring (p_score_v2).

Marqueur `reel` : exige la base APPLICATIVE réelle (run servi) — jamais en CI (base vide). Marqueur
`coherence` : jouée au push par le hook quand la base répond, et en entier au banc de nuit.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.coherence_ecrans.conftest import TEMOINS

pytestmark = [pytest.mark.coherence, pytest.mark.reel]

# Tolérance ZÉRO : « un écart d'un euro ou d'un m² fait échouer » (mandat). On compare des entiers
# (valeurs arrondies à l'euro / au m²) en ÉGALITÉ STRICTE — le moindre écart ≥ 1 fait tomber le test.
# (Sur la base réelle les lectures sont rigoureusement identiques — aucun faux rouge d'arrondi.)


def _idus_servis(fiches) -> list[str]:
    return [i for i in TEMOINS if i in fiches]


# ─────────────────────────────────────────────────────────── FAIT 4 : ZONE PLU ───────────────────
def test_zone_identique_fiche_et_moteur_copilote(app_session, fiches):
    """La zone servie par la FICHE (`reglement_plu.zones[0]`) == la zone résolue par le moteur unique
    `zone_servie.zone_dominante` (celui qu'appellent le Copilote `destination_zone`/`regles_plu_zone`
    et l'Étude de zone). Une seule zone dominante partout, label pour label (None des deux côtés OK)."""
    from labuse.faisabilite.zone_servie import zone_dominante
    ecarts = []
    for idu in _idus_servis(fiches):
        pid = app_session.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        zmoteur = zone_dominante(app_session, pid).zone if pid else None
        zones = (fiches[idu].get("reglement_plu") or {}).get("zones") or []
        zfiche = (zones[0].get("zone") if zones and isinstance(zones[0], dict) else None)
        if (zmoteur or None) != (zfiche or None):
            ecarts.append(f"{idu}: moteur={zmoteur!r} fiche={zfiche!r}")
    assert not ecarts, "Zone PLU incohérente fiche ↔ moteur (Copilote/Étude) :\n  " + "\n  ".join(ecarts)


# ─────────────────────────────────────────────────────────── FAIT 5 : SURFACE ────────────────────
def test_surface_terrain_identique_fiche_et_point_unique(app_session, fiches):
    """La surface de terrain servie par la fiche (`surface_terrain_m2`) == le point unique
    `surface.surface_terrain(dessin, contenance)` (contenance si présente, sinon dessin — CONTENANCE-1),
    au m² près. Prouve qu'aucune surface n'est recomposée différemment en aval."""
    from labuse import surface as S
    ecarts = []
    for idu in _idus_servis(fiches):
        raw = app_session.execute(text(
            "SELECT surface_m2, contenance_m2 FROM parcels WHERE idu=:i"), {"i": idu}).mappings().first()
        if not raw:
            continue
        canon = S.surface_terrain(raw["surface_m2"], raw["contenance_m2"]).valeur
        servie = fiches[idu].get("surface_terrain_m2")
        if canon is None and servie is None:
            continue
        if canon is None or servie is None or round(canon) != round(servie):
            ecarts.append(f"{idu}: point_unique={canon} fiche={servie}")
    assert not ecarts, "Surface de terrain incohérente fiche ↔ point unique :\n  " + "\n  ".join(ecarts)


# ─────────────────────────────────────────────────────────── FAIT 2 : MÉDIANE DE MARCHÉ ──────────
def test_mediane_commune_batie_identique_sur_les_trois_lectures(app_session, fiches):
    """Pour chaque commune témoin × type bâti (maison, appartement), la médiane DVF « ancien » servie est
    LA MÊME, à l'euro, sur les trois points de lecture : point unique `mediane_commune`, tableau Radar
    `_dvf_bati_type`, bloc commune `marche_commune_bloc`. (Le terrain n'est pas servi par le tableau
    bâti : hors périmètre de cette égalité — cf. test_marche_unique_1.)"""
    from labuse.faisabilite.marche_commune import marche_commune_bloc
    from labuse.marche_dvf_commune import mediane_commune
    from labuse.pige.signaux import _dvf_bati_type
    communes = sorted({fiches[i].get("commune") for i in _idus_servis(fiches) if fiches[i].get("commune")})
    ecarts = []
    vus = 0
    for commune in communes:
        bloc = marche_commune_bloc(app_session, commune) or {}
        for tb in ("maison", "appartement"):
            mc = (mediane_commune(app_session, commune, tb) or {}).get("eur_m2")
            if mc is None:
                continue
            vus += 1
            dbt = (_dvf_bati_type(app_session, commune, tb) or {}).get("eur_m2")
            blocv = bloc.get("median_maison_eur_m2" if tb == "maison" else "median_appartement_eur_m2")
            if dbt is None or round(mc) != round(dbt):
                ecarts.append(f"{commune}/{tb}: mediane_commune={mc} ≠ tableau_radar={dbt}")
            if blocv is not None and round(blocv) != round(mc):
                ecarts.append(f"{commune}/{tb}: mediane_commune={round(mc)} ≠ bloc_commune={blocv}")
    assert vus, "aucune médiane bâtie servie sur les communes témoins — base réelle incomplète ?"
    assert not ecarts, "Médiane de marché divergente entre les lectures :\n  " + "\n  ".join(ecarts)


# ─────────────────────────────────────────────────────────── FAIT 6 : ESTIMATION ─────────────────
def test_estimation_identique_endpoint_et_point_unique(app_session, fiches):
    """La valeur indicative servie par l'ENDPOINT `radar_annonce_estimation` (outil « Estimer un bien »
    + son PDF + le 9ᵉ doc) == celle du POINT UNIQUE `estimation_annonce`, à l'euro. (Les deux calculent
    sur le MÊME run servi ; l'endpoint n'est qu'un emballage.) Vaut aussi quand il n'y a pas d'estimation
    (copro / terrain sans comparables) : les deux doivent dire « rien » de la même façon."""
    from labuse.pige.api import estimation_annonce, radar_annonce_estimation
    ecarts = []
    for idu in _idus_servis(fiches):
        inner = (estimation_annonce(app_session, idu, fiches[idu]) or {}).get("valeur_indicative") or {}
        endp = (radar_annonce_estimation(idu) or {}).get("valeur_indicative") or {}
        vi, ve = inner.get("valeur_eur"), endp.get("valeur_eur")
        if vi is None and ve is None:
            continue
        if vi is None or ve is None or int(vi) != int(ve):
            ecarts.append(f"{idu}: point_unique={vi} endpoint={ve}")
    assert not ecarts, "Estimation divergente endpoint ↔ point unique :\n  " + "\n  ".join(ecarts)


# ─────────────────────────────────────────────────────────── FAIT 3 : NOMBRE D'ALÉAS ─────────────
def test_nombre_aleas_source_unique(app_session, fiches):
    """Deux garanties, chacune « une source » :
      • le bloc ALÉAS de la fiche est interne-cohérent : `aleas.n == len(aleas.liste)` ;
      • le compteur « Risques et pièges » de l'outil d'estimation (endpoint `n_aleas`) == le POINT
        UNIQUE `_risques_rows(fiche)` — le même dénombrement partout (CHASSE-4-FIX C4-002).
    (Le bloc « aléas naturels » de la fiche et la table « risques et pièges » sont des notions
    DISTINCTES — on ne les confond pas ; chacune est vérifiée contre SA source.)"""
    from labuse.pige.api import _risques_rows, radar_annonce_estimation
    ecarts = []
    for idu in _idus_servis(fiches):
        f = fiches[idu]
        al = f.get("aleas") or {}
        n_decl, liste = al.get("n"), (al.get("liste") or [])
        if (n_decl if n_decl is not None else 0) != len(liste):
            ecarts.append(f"{idu}: fiche aleas.n={n_decl} ≠ len(liste)={len(liste)}")
        n_rr = len(_risques_rows(f, f.get("commune")))
        n_endp = (radar_annonce_estimation(idu) or {}).get("n_aleas")
        if n_endp is not None and n_endp != n_rr:
            ecarts.append(f"{idu}: endpoint n_aleas={n_endp} ≠ _risques_rows={n_rr}")
    assert not ecarts, "Dénombrement d'aléas/risques incohérent :\n  " + "\n  ".join(ecarts)


# ─────────────────────────────────────────────────────────── FAIT 1 : SDP RÉSIDUELLE ─────────────
def _rien(x) -> bool:
    return x is None or x == 0


def test_sdp_residuelle_identique_entete_verdict_scoring(app_session):
    """La SDP résiduelle « restante, bâti conservé » est UNE valeur : en-tête (parcel_residuel) ==
    scoring (p_score_v2) en DONNÉE brute, et en-tête == verdict (score_labuse) en AFFICHAGE (une cause
    d'un côté ⇒ « aucune SDP » des deux). Consolide SDP-UNIQUE-1 sur les 12 témoins (écart > 1 m² = échec)."""
    run = app_session.execute(text("SELECT value FROM mvt_meta WHERE key='run_label'")).scalar() or "q_v20"
    if not app_session.execute(text("SELECT to_regclass('parcel_residuel')")).scalar():
        pytest.skip("parcel_residuel absente — base sans run résiduel servi")
    ecarts = []
    for idu in TEMOINS:
        row = app_session.execute(text(
            """SELECT r.sdp_residuelle_m2 AS r_sdp, r.cause AS r_cause,
                      s.sdp_residuelle_m2 AS s_sdp, s.cause AS s_cause,
                      v.potentiel_sdp_m2 AS v_sdp
                 FROM parcels p
                 LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
                 LEFT JOIN score_labuse s ON s.parcel_id = p.id AND s.run_label = :run
                 LEFT JOIN parcel_p_score_v2 v ON v.parcelle_id = p.idu AND v.run_id = :run
                WHERE p.idu = :idu"""), {"run": run, "idu": idu}).mappings().first()
        if not row or (row["r_sdp"] is None and row["s_sdp"] is None and row["v_sdp"] is None):
            continue
        raw_r = None if row["r_sdp"] is None else int(round(row["r_sdp"]))
        raw_v = None if row["v_sdp"] is None else int(round(row["v_sdp"]))
        if raw_r != raw_v:
            ecarts.append(f"{idu}: DONNÉE en-tête(résiduel)={raw_r} ≠ scoring(p_score_v2)={raw_v}")
        entete = None if (row["r_cause"] is not None or row["s_cause"] is not None) else row["r_sdp"]
        verdict = None if (row["s_cause"] is not None) else row["s_sdp"]
        presentes = [entete, verdict]
        positifs = [int(round(x)) for x in presentes if not _rien(x)]
        if positifs:
            socle = positifs[0]
            if any(_rien(x) for x in presentes) or any(x != socle for x in positifs):
                ecarts.append(f"{idu}: AFFICHAGE en-tête={entete} verdict={verdict}")
    assert not ecarts, "SDP résiduelle incohérente (en-tête/verdict/scoring) :\n  " + "\n  ".join(ecarts)
