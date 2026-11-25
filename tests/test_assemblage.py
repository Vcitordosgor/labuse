"""Assemblage foncier v1 (Lot C5) — paires contiguës franchissant le seuil, sur PostGIS réel."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import assemblage

pytestmark = pytest.mark.db


def _p(db, idu, wkt, surf):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, geom_2975) VALUES "
        "(:i,'Asmville','S','1', ST_GeomFromText(:w,4326), :s, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326)), ST_Transform(ST_GeomFromText(:w,4326),2975)) RETURNING id"),
        {"i": idu, "w": wkt, "s": surf}).scalar()


def _p2975(db, idu, wkt2975, surf):
    """Insère une parcelle depuis un contour en EPSG:2975 (mètres) — contrôle MÉTRIQUE exact des
    distances/bords (OUTIL-ASSEMBLAGE-FIX-1 LOT 1, les trois verdicts de contiguïté se mesurent en m)."""
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, geom_2975) VALUES "
        "(:i,'Asmville','S','1', ST_Transform(ST_GeomFromText(:w,2975),4326), :s, "
        " ST_Centroid(ST_Transform(ST_GeomFromText(:w,2975),4326)), "
        " ST_Envelope(ST_Transform(ST_GeomFromText(:w,2975),4326)), ST_GeomFromText(:w,2975)) RETURNING id"),
        {"i": idu, "w": wkt2975, "s": surf}).scalar()


def _carre(x0, y0, cote):
    return (f"POLYGON(({x0} {y0},{x0 + cote} {y0},{x0 + cote} {y0 + cote},"
            f"{x0} {y0 + cote},{x0} {y0}))")


def test_paire_contigue_franchit_le_seuil(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    # deux carrés ADJACENTS de ~600 m² chacun (côte à côte) → cumul ~1200 ≥ 1000, chacun < 1000
    a = _p(db_session, "ASM00001", "POLYGON((55.40 -21.00,55.4003 -21.00,55.4003 -20.9997,55.40 -20.9997,55.40 -21.00))", 600)
    _p(db_session, "ASM00002", "POLYGON((55.4003 -21.00,55.4006 -21.00,55.4006 -20.9997,55.4003 -20.9997,55.4003 -21.00))", 600)
    groups = assemblage.find_assemblages(db_session, "Asmville")
    assert any(set(g["parcelles"]) == {"ASM00001", "ASM00002"} and g["surface_cumulee_m2"] >= 1000
               for g in groups)
    u = assemblage.parcel_assemblage(db_session, a)
    assert u["possible"] and u["meilleur_cumul_m2"] >= 1000


def test_parcelle_seule_au_dessus_du_seuil_pas_d_assemblage(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    big = _p(db_session, "ASM00010", "POLYGON((55.50 -21.10,55.5005 -21.10,55.5005 -21.0995,55.50 -21.0995,55.50 -21.10))", 1500)
    u = assemblage.parcel_assemblage(db_session, big)
    assert u["possible"] is False   # déjà au-dessus du seuil seule → pas besoin d'assemblage


def test_parcelles_non_contigues_pas_de_paire(db_session, monkeypatch):
    monkeypatch.setattr(assemblage, "_params", lambda: {"min_surface_m2": 1000.0, "individuel_max_m2": 1000.0})
    _p(db_session, "ASM00020", "POLYGON((55.60 -21.20,55.6003 -21.20,55.6003 -21.1997,55.60 -21.1997,55.60 -21.20))", 600)
    _p(db_session, "ASM00021", "POLYGON((55.70 -21.30,55.7003 -21.30,55.7003 -21.2997,55.70 -21.2997,55.70 -21.30))", 600)
    groups = assemblage.find_assemblages(db_session, "Asmville")
    assert not any(set(g["parcelles"]) == {"ASM00020", "ASM00021"} for g in groups)


def test_endpoint_moteurs_assemblage_ne_leve_pas(db_session):
    """L'ENDPOINT scoré (/moteurs/assemblage) n'était couvert par AUCUN test. Il ne doit pas lever :
    422 si < 2 demandées, 404 si < 2 trouvées, et sur 2 parcelles contiguës il rend la structure —
    base de test SANS faisabilité servie → sans_potentiel, JAMAIS une exception. Les vestiges de
    matrice (opportunity_score / sdp_cumulee_m2 / statut / m2_par_logement) ont disparu du payload."""
    from fastapi import HTTPException

    from labuse.api.moteurs import AssemblageIn
    from labuse.api.moteurs import assemblage as endpoint
    with pytest.raises(HTTPException) as e1:
        endpoint(AssemblageIn(idus=["ASM00099"]), db=db_session)
    assert e1.value.status_code == 422
    with pytest.raises(HTTPException) as e2:
        endpoint(AssemblageIn(idus=["97499000ZZ9998", "97499000ZZ9999"]), db=db_session)
    assert e2.value.status_code == 404
    _p(db_session, "ASM00050", "POLYGON((55.40 -21.00,55.4003 -21.00,55.4003 -20.9997,55.40 -20.9997,55.40 -21.00))", 600)
    _p(db_session, "ASM00051", "POLYGON((55.4003 -21.00,55.4006 -21.00,55.4006 -20.9997,55.4003 -20.9997,55.4003 -21.00))", 600)
    out = endpoint(AssemblageIn(idus=["ASM00050", "ASM00051"]), db=db_session)   # ne lève pas
    assert out["n"] == 2 and out["contigu"] is True
    assert out["sans_potentiel"] is True and out["score_assemblage"] == 0   # aucune faisabilité servie
    # ASSEMBLAGE-2 (RETOUCHES-1 lot B.4) — la note dit désormais que le calcul est sur l'UNION
    # (une assiette, une VRD) ; sans zonage en base de test, la capacité d'union est « aucune ».
    assert "UNION" in out["note_sdp"] and out["ca"] is None and out["charge_fonciere"] is None
    # vestiges retirés (payload + items)
    for k in ("opportunity_score", "sdp_cumulee_m2", "m2_par_logement"):
        assert k not in out
    # CHASSE-FIX-1 (B-2 / SDP-UNIQUE) — l'item porte désormais la SDP brute (`sdp_m2` = terrain libéré)
    # ET la SDP bâti conservé (`sdp_residuelle_m2`, comme la fiche ; None si faisabilité absente).
    for it in out["items"]:
        assert "sdp_m2" in it and "tier_v2" in it
        assert "sdp_residuelle_m2" in it and "sdp_existante_m2" in it
        assert "opportunity_score" not in it and "statut" not in it
    # payload : les deux grandeurs SDP-UNIQUE, jamais la brute seule.
    for k in ("sdp_bati_conserve_m2", "sdp_terrain_libere_m2", "sdp_conserve_estimation"):
        assert k in out
    assert out["sdp_combinee_m2"] == out["sdp_bati_conserve_m2"]   # le défaut = bâti conservé


# ── OUTIL-ASSEMBLAGE-FIX-1 (LOT 1) — contiguïté en TROIS verdicts (bord / point / vide) ──
# Chaque cas chiffré du relecteur (21 paires) devient un test : la contiguïté n'était pas testée.

@pytest.mark.parametrize("dist,bord,attendu,mesure", [
    # 3 vrais bords du relecteur (10,51 à 42,73 m) + le bord réel BZ0824/BZ0381 (26,38 m).
    (0.0, 26.381, "bord", 26.38), (0.0, 10.51, "bord", 10.51), (0.0, 42.73, "bord", 42.73),
    # 3 contacts par un point (bord commun 0 m) : CV0085/CV0876, CV0107/CV1287, CV0157/CV0095.
    (0.0, 0.0, "point", None), (0.0, 0.0, "point", None), (0.0, 0.0, "point", None),
    # petits vides cadastraux 0,315 à 0,322 m (CV0186/CW0182 = 0,315) — PAS un bord commun.
    (0.315, 0.0, "vide", 0.32), (0.320, 0.0, "vide", 0.32), (0.322, 0.0, "vide", 0.32),
])
def test_classer_lien_trois_verdicts(dist, bord, attendu, mesure):
    """`classer_lien` rend un verdict par lien ; seul « bord » est une vraie mitoyenneté."""
    v = assemblage.classer_lien(dist, bord)
    assert v["type"] == attendu
    if attendu == "bord":
        assert v["longueur_bord_m"] == pytest.approx(mesure, abs=0.01) and v["vide_m"] is None
    elif attendu == "point":
        assert v["longueur_bord_m"] == 0.0 and v["vide_m"] is None
    else:
        assert v["vide_m"] == pytest.approx(0.32, abs=0.01) and v["longueur_bord_m"] is None


def _endpoint(db, idus):
    from labuse.api.moteurs import AssemblageIn
    from labuse.api.moteurs import assemblage as endpoint
    return endpoint(AssemblageIn(idus=idus), db=db)


def test_contiguite_bord_commun_est_seule_contigue(db_session):
    """Deux carrés partageant un BORD de 30 m → « contiguës », d'un seul tenant, lien mesuré."""
    _p2975(db_session, "ASMB0001", _carre(0, 0, 30), 900)        # A : [0,30]²
    _p2975(db_session, "ASMB0002", _carre(30, 0, 30), 900)       # B : bord commun x=30 sur 30 m
    out = _endpoint(db_session, ["ASMB0001", "ASMB0002"])
    assert out["relie"] is True and out["tenant_unique"] is True and out["contigu"] is True
    assert out["lien_faible"] is False and out["tenant_avertissement"] is None
    assert len(out["liens"]) == 1 and out["liens"][0]["type"] == "bord"
    assert out["liens"][0]["longueur_bord_m"] == pytest.approx(30.0, abs=0.1)


def test_contiguite_contact_ponctuel_relie_mais_pas_un_seul_tenant(db_session):
    """Deux carrés se touchant par un SEUL point (coin commun) → reliées, PAS « contiguës »."""
    _p2975(db_session, "ASMP0001", _carre(0, 0, 30), 900)        # A : [0,30]²
    _p2975(db_session, "ASMP0002", _carre(30, 30, 30), 900)      # C : coin commun (30,30), aucun bord
    out = _endpoint(db_session, ["ASMP0001", "ASMP0002"])
    assert out["relie"] is True and out["tenant_unique"] is False and out["contigu"] is False
    assert out["lien_faible"] is True
    assert out["liens"][0]["type"] == "point" and out["liens"][0]["longueur_bord_m"] == 0.0
    assert out["tenant_avertissement"] and "point" in out["tenant_avertissement"]


def test_contiguite_petit_vide_cadastral_dit_et_reserve(db_session):
    """Deux carrés séparés de 0,32 m (sous la tolérance 0,5 m) → reliées, « petit vide cadastral »."""
    _p2975(db_session, "ASMV0001", _carre(0, 0, 30), 900)        # A : [0,30]²
    _p2975(db_session, "ASMV0002", _carre(30.32, 0, 30), 900)    # D : vide de 0,32 m, aucun bord
    out = _endpoint(db_session, ["ASMV0001", "ASMV0002"])
    assert out["relie"] is True and out["tenant_unique"] is False and out["contigu"] is False
    assert out["liens"][0]["type"] == "vide"
    assert out["liens"][0]["vide_m"] == pytest.approx(0.32, abs=0.02)
    assert out["tenant_avertissement"] and "vide" in out["tenant_avertissement"]


def test_contiguite_vide_au_dela_tolerance_pas_relie(db_session):
    """Un vide > 0,5 m (rue/chemin/ravine du relecteur, 0,68 à 43 m) → isolée, pas d'assemblage."""
    _p2975(db_session, "ASMX0001", _carre(0, 0, 30), 900)
    _p2975(db_session, "ASMX0002", _carre(30.69, 0, 30), 900)    # vide 0,69 m > tolérance
    out = _endpoint(db_session, ["ASMX0001", "ASMX0002"])
    assert out["relie"] is False and out["contigu"] is False
    # aucun lien (vide > tolérance) ; l'autre parcelle (hors du bloc de la 1ʳᵉ) est isolée.
    assert out["liens"] == [] and len(out["isolees"]) == 1
    assert out["isolees"][0] in {"ASMX0001", "ASMX0002"}


# ── OUTIL-ASSEMBLAGE-FIX-1 (LOT 2) — capacité PAR ZONE, reproduite À L'EURO sur les témoins ASTRA ──
# La capacité d'une union multizone n'était pas testée en VALEUR. Ces témoins (base de l'île, lecture
# seule) reproduisent les contrôles indépendants du relecteur : chaque portion reçoit les règles de SA
# zone, puis on additionne. Skippés hors de l'île (CI / base de test sans ce foncier).

import os as _os
from types import SimpleNamespace as _SNS

from sqlalchemy import create_engine as _ce
from sqlalchemy.orm import Session as _S

_APP = _os.environ.get("LABUSE_APP_DATABASE_URL")


def _app_session():
    if not _APP:
        pytest.skip("base de l'île indisponible (LABUSE_APP_DATABASE_URL) — témoins de valeur skippés")
    return _S(_ce(_APP))


@pytest.mark.parametrize("idus,commune,sdp_attendu,tol", [
    (["97415000DH0076", "97415000DH0119", "97415000DH0120"], "Saint-Paul", 32174, 5),   # U2b/U2h
    (["97411000BZ0088", "97411000BZ0550"], "Saint-Denis", 1460, 3),                      # Um/Uj
    (["97411000BZ0246", "97411000BZ1488"], "Saint-Denis", 1007, 3),                      # Uj/Uh
    (["97415000CV0724", "97415000CV1506", "97415000CV1507"], "Saint-Paul", 3060, 5),     # mono AU3c (inchangé)
    (["97411000BZ0824", "97411000BZ0381"], "Saint-Denis", 159, 3),                       # mono Uh (inchangé)
])
def test_capacite_union_par_zone_valeurs_astra(idus, commune, sdp_attendu, tol):
    """La SDP de l'union = somme PAR ZONE (chaque portion avec ses règles), aux chiffres du relecteur."""
    from labuse.assemblage import _capacite_union
    with _app_session() as s:
        rows = s.execute(text("SELECT id, COALESCE(contenance_m2, surface_m2) sfc, idu, commune "
                              "FROM parcels WHERE idu = ANY(:i)"), {"i": idus}).mappings().all()
        if len(rows) < len(idus):
            pytest.skip(f"parcelles témoins absentes ({len(rows)}/{len(idus)})")
        ps = [_SNS(id=r["id"], surface_m2=float(r["sfc"]), idu=r["idu"], commune=r["commune"]) for r in rows]
        u = _capacite_union(s, ps)
        assert u is not None, "capacité union None"
        assert abs(u["sdp_m2"] - sdp_attendu) <= tol, (u["sdp_m2"], sdp_attendu, u["zones_detail"])
        # multizone : la somme des SDP par zone == SDP totale (règle de chaque portion appliquée à sa surface)
        if len([z for z in u["zones_detail"] if z["constructible"]]) > 1:
            assert sum(z["sdp_m2"] for z in u["zones_detail"]) == u["sdp_m2"]


def test_surface_constructible_est_intersection_directe_uau():
    """ASTRA bloquant 2 — la surface « en zone constructible » = intersection DIRECTE du dessin avec
    U/AU (DH ≈ 21 516 m²), plus une proportion après recul (qui donnait 21 780)."""
    from labuse.assemblage import _capacite_union
    idus = ["97415000DH0076", "97415000DH0119", "97415000DH0120"]
    with _app_session() as s:
        rows = s.execute(text("SELECT id, COALESCE(contenance_m2, surface_m2) sfc, idu, commune "
                              "FROM parcels WHERE idu = ANY(:i)"), {"i": idus}).mappings().all()
        if len(rows) < 3:
            pytest.skip("parcelles DH absentes")
        ps = [_SNS(id=r["id"], surface_m2=float(r["sfc"]), idu=r["idu"], commune=r["commune"]) for r in rows]
        u = _capacite_union(s, ps)
        assert abs(u["surface_constructible_m2"] - 21516) <= 30, u["surface_constructible_m2"]


# ── OUTIL-ASSEMBLAGE-FIX-2 (LOT 0) — filet : un test par point de la relecture. Écouent AVANT les
# correctifs (LOT 1-4), passent après. Preuve que le défaut existe, figée en test. ──

def _endpoint_app(idus):
    """Endpoint /moteurs/assemblage sur la base de l'île (lecture seule), skip si indisponible."""
    from labuse.api.moteurs import AssemblageIn
    from labuse.api.moteurs import assemblage as endpoint
    with _app_session() as s:
        return endpoint(AssemblageIn(idus=idus), db=s)


def test_fix2_cv_affiche_obligation_mixite():
    """Point 1-2 : l'écran Assemblage doit PORTER l'obligation de mixité du trio CV (bande
    intermédiaire) et dire que le +178 261 € est une BORNE HAUTE (accession non chiffrée)."""
    out = _endpoint_app(["97415000CV0724", "97415000CV1506", "97415000CV1507"])
    if out.get("n", 0) < 2:
        pytest.skip("parcelles CV absentes")
    mx = out.get("mixite")
    assert mx is not None, "payload sans champ `mixite`"
    assert mx.get("declenchee") is True and mx.get("regime") == "intermediaire"
    assert mx.get("borne_haute") is True            # CA au prix libre, obligation non chiffrée
    assert "2" in str(mx.get("article") or "") and mx.get("page")


def test_fix2_bande_1500_1800_porte_regle_article_page():
    """Point 1 : une parcelle en bande 1 500–1 800 → la clause porte la RÈGLE (quota %, article, page).
    OUTIL-ASSEMBLAGE-FIX-4 (LOT 1) : la page vient de la ZONE (`zone_mixite`, page du livret) — plus de
    repli commune-wide « pp. 14-15 » ; on fournit donc le `zone_mixite` comme le fait le contexte servi."""
    from labuse.faisabilite.bilan import _clause_mixite
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses.charger("Saint-Paul")
    c = _clause_mixite({"sdp_max_m2": 3000, "sdp_programme_m2": 1600, "logements_estimes": 8,
                        "terrain_m2": 2000,
                        "zone_mixite": {"article": "Art. 2 (zones U1 à U6)", "page": "pp. 106-107"}}, h)
    assert c["regime"] == "intermediaire"
    assert c.get("quota_pct") == 30 and "2" in str(c.get("article") or "") and c.get("page") == "pp. 106-107"


def test_fix2_vingt_logements_sous_1500_declenche():
    """Point 3 : ≥ 20 logements (programme < 1 500 m²) → régime intermédiaire (Art. 2, ligne PC)."""
    from labuse.faisabilite.bilan import _clause_mixite
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses.charger("Saint-Paul")
    c = _clause_mixite({"sdp_max_m2": 2890, "sdp_programme_m2": 1494, "logements_estimes": 20,
                        "terrain_m2": 3000}, h)   # témoin AY1666
    assert c["declenchee"] is True and c["regime"] == "intermediaire"


def test_fix2_zac_savane_des_tamarins_exclue():
    """Point 4 : une parcelle dans la ZAC Savane des Tamarins → clause NON déclenchée (Art. 2 p.15)."""
    from labuse.faisabilite.bilan import _clause_mixite
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses.charger("Saint-Paul")
    c = _clause_mixite({"sdp_max_m2": 4000, "sdp_programme_m2": 2000, "logements_estimes": 25,
                        "terrain_m2": 7000, "zac_mixite_exclue": True}, h)   # ≥1800 ET terrain>6000
    assert c["declenchee"] is False
    assert "ZAC" in str(c.get("detail") or "") or "Savane" in str(c.get("detail") or "")


def test_fix2_identifiant_introuvable_nomme():
    """Point 6 : 4 identifiants dont 1 introuvable → l'endpoint NOMME l'écarté (comme /compare)."""
    out = _endpoint_app(["97415000CV0724", "97415000CV1506", "97415000CV1507", "97415000ZZ9999"])
    if out.get("n", 0) < 2:
        pytest.skip("parcelles CV absentes")
    assert "97415000ZZ9999" in (out.get("introuvables") or []), "introuvable écarté en silence"


# ── OUTIL-ASSEMBLAGE-FIX-1 (LOT 3) — mixité : déclenchement sur le PROGRAMME chiffré + régime à bandes ──

def test_clause_mixite_regime_a_bandes_saint_paul():
    """Saint-Paul (seuil haut 1 800) : la clause se déclenche sur le PROGRAMME chiffré et distingue
    plein régime (≥ 1 800), bande intermédiaire (1 500–1 800), non déclenchée (< 1 500)."""
    from labuse.faisabilite.bilan import _clause_mixite
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses.charger("Saint-Paul")
    assert h.mixite_sdp_seuil_haut_m2 == 1800.0
    base = {"sdp_max_m2": 5000, "logements_estimes": 8, "terrain_m2": 3778}   # gabarit élevé, < 20 logts
    assert _clause_mixite({**base, "sdp_programme_m2": 2000}, h)["regime"] == "plein"
    assert _clause_mixite({**base, "sdp_programme_m2": 1582}, h)["regime"] == "intermediaire"  # trio CV
    r = _clause_mixite({**base, "sdp_programme_m2": 1200}, h)
    assert r["declenchee"] is False
    # le gabarit élevé (5000) ne déclenche PLUS à lui seul : c'est le programme chiffré (et le nombre
    # de logements du programme, cf. FIX-2 LOT 2 ≥ 20 logts) — pas le gabarit.


def test_clause_mixite_autres_communes_inchangee():
    """Sans seuil haut (défaut / Saint-Denis), le déclenchement reste sur le GABARIT (comportement
    historique inchangé) — la correction est bornée à Saint-Paul (décision 24/11)."""
    from labuse.faisabilite.bilan import _clause_mixite
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses.charger("Saint-Denis")
    assert getattr(h, "mixite_sdp_seuil_haut_m2", 0.0) == 0.0
    # gabarit ≥ 1500 → déclenchée (régime plein), peu importe le programme chiffré.
    r = _clause_mixite({"sdp_max_m2": 1600, "sdp_programme_m2": 800, "logements_estimes": 5, "terrain_m2": 900}, h)
    assert r["declenchee"] is True and r["regime"] == "plein"


@pytest.mark.parametrize("idus,commune,charge_attendu,tol", [
    (["97415000CV0724", "97415000CV1506", "97415000CV1507"], "Saint-Paul", 178261, 2000),  # bande interm. → + (était -349965)
    (["97411000BZ0824", "97411000BZ0381"], "Saint-Denis", -26019, 1500),                    # SD inchangé
])
def test_bilan_union_mixite_reconcilie(idus, commune, charge_attendu, tol):
    """ASTRA bloquant 3 — réconciliation à l'écran : le trio CV (programme ~1 583 m² en bande
    intermédiaire) n'est plus pondéré au plein régime → charge ≈ +178 261 € (cohérent avec la somme
    des fiches), la paire BZ (Saint-Denis, hors régime à bandes) reste −26 019 €."""
    from labuse.assemblage import _capacite_union
    with _app_session() as s:
        rows = s.execute(text("SELECT id, COALESCE(contenance_m2, surface_m2) sfc, idu, commune "
                              "FROM parcels WHERE idu = ANY(:i)"), {"i": idus}).mappings().all()
        if len(rows) < len(idus):
            pytest.skip("parcelles témoins absentes")
        ps = [_SNS(id=r["id"], surface_m2=float(r["sfc"]), idu=r["idu"], commune=r["commune"]) for r in rows]
        u = _capacite_union(s, ps)
        cf = u["charge_fonciere"]
        assert cf is not None and abs(cf["central"] - charge_attendu) <= tol, (cf, charge_attendu)


# ── ASSEMBLAGE-2 (RETOUCHES-1 lot B.4) — l'assiette est l'UNION des géométries, pas la somme ──

def test_aggregate_assiette_calcule_sur_l_union(db_session):
    """Sur un trio de parcelles CONTIGUËS CONSTRUCTIBLES (données réelles), la capacité de
    l'assemblage est calculée sur l'UNION (une assiette, une VRD), pas par somme des résiduels :
    les reculs internes disparaissent → la SDP de l'union est SUPÉRIEURE à la somme par parcelle,
    et la charge foncière est UNE seule (dict unique par_m2_terrain), jamais N VRD additionnées."""
    from types import SimpleNamespace

    # trio mutuellement contigu parmi les parcelles à capacité résiduelle > 0 (contour cadastral).
    cand = db_session.execute(text(
        "SELECT p.id, p.surface_m2, p.idu, p.commune FROM parcels p "
        "JOIN parcel_residuel r ON r.parcel_id = p.id "
        "WHERE r.sdp_residuelle_m2 > 50 AND p.surface_m2 BETWEEN 200 AND 1200 LIMIT 5000")).mappings().all()
    if len(cand) < 3:
        pytest.skip("pas de parcelles à capacité résiduelle en base (run résiduel absent)")
    byid = {c["id"]: c for c in cand}
    ids = list(byid)
    adj: dict[int, set[int]] = {i: set() for i in ids}
    for a, b in db_session.execute(text(
            "SELECT a.id a, b.id b FROM parcels a JOIN parcels b "
            "ON a.id < b.id AND ST_DWithin(a.geom_2975, b.geom_2975, 0.5) "
            "WHERE a.id = ANY(:i) AND b.id = ANY(:i)"), {"i": ids}).all():
        adj[a].add(b)
        adj[b].add(a)
    trio = next(([a, b, next(iter(adj[a] & adj[b]))] for a in ids for b in adj[a] if adj[a] & adj[b]), None)
    if trio is None:
        pytest.skip("aucun trio contigu constructible en base")
    ps = [SimpleNamespace(id=byid[i]["id"], surface_m2=byid[i]["surface_m2"],
                          idu=byid[i]["idu"], commune=byid[i]["commune"]) for i in trio]
    agg = assemblage.aggregate_assiette(db_session, ps)
    assert agg["assiette"] == "union"
    assert agg["emprise_union_m2"] and agg["emprise_union_m2"] > 0
    # SDP de l'union ≥ somme des résiduels par parcelle (reculs internes supprimés à la fusion).
    somme = sum(agg["sdp_par_parcelle"].values())
    assert agg["sdp_m2"] >= somme, (agg["sdp_m2"], somme)
    # charge foncière = UN dict (par_m2_terrain), jamais une somme de N bilans.
    cf = agg["charge_fonciere"]
    assert cf is None or ("par_m2_terrain" in cf and set(cf) >= {"bas", "central", "haut"})
