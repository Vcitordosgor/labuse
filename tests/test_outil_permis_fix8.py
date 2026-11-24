"""OUTIL-PERMIS-FIX-8 — LOT 0 : le FILET, écrit AVANT les correctifs (il doit échouer maintenant).

Un test par témoin du contre-audit (`~/Desktop/audit-outils/02-PERMIS-ASTRA-4.md`), valeur précise :

  1. 97441626E0304 (DP, AN_DEPOT=2026, DR_DEPOT=01/06/2020, autorisé 03/08/2026) n'a de date de dépôt
     NI dans la fiche du permis, NI dans l'historique de la parcelle 97416000IE1348 (ni, par voie de
     conséquence, dans son Dossier — chaîne historique_site → _r_permis_liste).
  2. Aucune date d'autorisation n'est jamais affichée sous le libellé « déposé » (quand le dépôt est
     écarté ou absent, rien n'est écrit à sa place — on ne recopie pas l'autorisation).
  3. 97440226G0018 (dépôt 15/02/2026 → autorisation 13/03/2026) n'affiche AUCUNE durée d'instruction ;
     les deux dates restent servies, sans calcul entre elles.
  4. Le score composite du comparateur de communes ne contient plus d'axe de délai (vélocité).

Les tests 1 et 3 vivent sur base (`labuse_test`, permis SEEDÉ avec les valeurs exactes du témoin) ; les
tests 2 et 4 sont unitaires (renderer du Dossier / registre d'indicateurs), dans le lot pre-push.
"""
from __future__ import annotations

import inspect
import json

import pytest
from sqlalchemy import text


def _seed_permit(db, pid, *, typ, aut, dep, an_depot, idus, etat=None):
    """Seed un permis Sitadel avec les valeurs EXACTES d'un témoin (DR_DEPOT = colonne date_depot,
    AN_DEPOT = raw.an_depot, autorisation = colonne date)."""
    raw = {"an_depot": an_depot}
    if etat is not None:
        raw["etat"] = etat
    db.execute(text("DELETE FROM sitadel_permits WHERE permit_id = :p"), {"p": pid})
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, idu_codes, commune, geom, raw) "
        "VALUES (:pid, :t, :aut, :dep, CAST(:i AS jsonb), 'Saint-Témoin', NULL, CAST(:r AS jsonb))"),
        {"pid": pid, "t": typ, "aut": aut, "dep": dep, "i": json.dumps(idus), "r": json.dumps(raw)})


@pytest.mark.db
def test_lot0_temoin1_97441626E0304_depot_absent_fiche_et_historique(db_session):
    """Témoin 1 (BLOQUANT) — l'historique de 97416000IE1348 renvoie aujourd'hui la DATE BRUTE
    01/06/2020 (DR_DEPOT), dont l'année (2020) CONTREDIT l'AN_DEPOT publié (2026). La fiche l'écarte
    déjà ; l'historique doit l'écarter aussi (date_depot = None). ÉCHOUE maintenant (historique = 2020)."""
    from labuse.api import modules, site_voisinage
    _seed_permit(db_session, "97441626E0304", typ="DP", aut="2026-08-03", dep="2020-06-01",
                 an_depot="2026", idus=["97416000IE1348"])
    fiche = modules.permis_fiche("97441626E0304", db_session)
    assert fiche["date_depot"] is None, "fiche : dépôt non affichable (année 2020 ≠ AN_DEPOT 2026)"
    h = site_voisinage.historique_permis(db_session, "97416000IE1348")
    pm = next(p for p in h["permis"] if p["permit_id"] == "97441626E0304")
    assert pm["date_depot"] is None, "historique parcellaire : même validation que la fiche (dépôt écarté)"
    # l'autorisation, elle, reste servie telle quelle
    assert pm["date_autorisation"] == "2026-08-03"


def test_lot0_temoin2_aucune_autorisation_sous_le_libelle_depose():
    """Témoin 2 — quand le dépôt est écarté/absent, le Dossier ne RECOPIE PAS l'autorisation sous
    « déposé » (le renderer `_r_permis_liste` tombait sur l'autorisation). ÉCHOUE maintenant."""
    from labuse.exports.miroir import _r_permis_liste
    txt = _r_permis_liste([{"type": "DP", "date_depot": None, "date_autorisation": "2026-08-03"}])
    assert "déposé 03/08/2026" not in txt, "l'autorisation ne doit jamais être écrite sous « déposé »"
    assert "autorisé 03/08/2026" in txt, "l'autorisation reste dite sous son propre libellé"
    # garde front : le fallback « déposé = autorisation » d'autour.tsx est retiré
    from pathlib import Path
    autour = (Path(__file__).resolve().parents[1]
              / "frontend/src/components/fiche/autour.tsx").read_text(encoding="utf-8")
    assert "pm.date_autorisation ? fmtDateNum(pm.date_autorisation) : '?'" not in autour


@pytest.mark.db
def test_lot0_temoin3_97440226G0018_aucune_duree(db_session):
    """Témoin 3 — 97440226G0018 (dépôt 15/02/2026 → autorisation 13/03/2026) affiche aujourd'hui
    « 1 mois entre dépôt et autorisation » (26 jours réels, mois calendaires soustraits). Plus aucune
    durée : les DEUX dates restent, sans calcul entre elles. ÉCHOUE maintenant (délai = 1 mois)."""
    from labuse.api import modules
    _seed_permit(db_session, "97440226G0018", typ="DP", aut="2026-03-13", dep="2026-02-15",
                 an_depot="2026", idus=["97402000AK2164"])
    f = modules.permis_fiche("97440226G0018", db_session)
    assert f["date_depot"] == "2026-02-15" and f["date_autorisation"] == "2026-03-13"  # les deux dates
    assert f.get("delai_instruction") is None, "plus aucune durée d'instruction, même sur la fiche"


@pytest.mark.db
def test_fix9_alerte_de_zone_ne_montre_pas_de_depot_brut(db_session):
    """OUTIL-PERMIS-FIX-9 (canal 1) — l'alerte « Permis déposé dans votre zone » n'écrit plus la date de
    dépôt BRUTE sous « déposé le » : le témoin 97441626E0304 (DR_DEPOT 2020, AN_DEPOT 2026) écarte le
    dépôt et dit « autorisé le 2026-08-03 ». La clé d'arrivée (géocodé en zone, ON CONFLICT) ne change
    pas : une seconde évaluation n'émet aucune alerte."""
    from labuse import alertes
    s = db_session
    commune = "Zonetemoin9"
    lon, lat = 55.491, -20.881
    zone = {"type": "Polygon", "coordinates": [[
        [lon - 0.002, lat - 0.002], [lon + 0.002, lat - 0.002], [lon + 0.002, lat + 0.002],
        [lon - 0.002, lat + 0.002], [lon - 0.002, lat - 0.002]]]}
    s.execute(text("DELETE FROM alertes WHERE source_ref = '97441626E0304'"))
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id = '97441626E0304'"))
    alertes.create_watch_zone(s, "Témoin FIX-9", commune, zone, None)
    alertes.compute_alertes(s, commune, None)   # photo initiale — rien à signaler
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, commune, geom, raw, idu_codes) "
        "VALUES ('97441626E0304','DP','2026-08-03','2020-06-01', :c, "
        "ST_SetSRID(ST_MakePoint(:lon,:lat),4326), CAST('{\"an_depot\":\"2026\"}' AS jsonb), '[]'::jsonb)"),
        {"c": commune, "lon": lon, "lat": lat})
    out = alertes.compute_alertes(s, commune, None)
    assert out["permis_in_zone"] == 1
    detail = s.execute(text(
        "SELECT payload->>'detail' FROM alertes WHERE source_ref = '97441626E0304'")).scalar()
    assert "2020" not in detail and "déposé le" not in detail   # la date rejetée n'apparaît pas
    assert "autorisé le 2026-08-03" in detail                   # le bon mot, la date fiable
    again = alertes.compute_alertes(s, commune, None)
    assert again["permis_in_zone"] == 0                         # clé d'arrivée inchangée : pas de doublon


@pytest.mark.db
def test_fix9_veille_parcelle_ne_montre_pas_de_depot_brut(db_session):
    """OUTIL-PERMIS-FIX-9 (canal 2) — la veille « Nouveau permis sur votre parcelle suivie » passe le
    dépôt par la fonction unique : un permis à année de dépôt contradictoire (DR_DEPOT 01/06/2026 mais
    AN_DEPOT 2000) dit « autorisé le … », jamais la date de dépôt brute. La clé d'arrivée
    (`date_depot >= created_at`) et la dédup permanente ne changent pas : aucune notif en double."""
    from labuse.api import events
    s = db_session
    idu = "97416000IE1348"
    s.execute(text("DELETE FROM event_log WHERE idu = :i"), {"i": idu})
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id = 'PERMIS-FIX9-VEILLE'"))
    s.execute(text("DELETE FROM watched_parcels WHERE idu = :i"), {"i": idu})
    s.execute(text("INSERT INTO watched_parcels (idu, compte_id, created_at) "
                   "VALUES (:i, NULL, now() - interval '400 days')"), {"i": idu})
    # DR_DEPOT récent (donc détecté : >= created_at) mais AN_DEPOT contradictoire → dépôt écarté.
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, idu_codes, date, date_depot, raw) "
        "VALUES ('PERMIS-FIX9-VEILLE','DP', to_jsonb(ARRAY[:i]), '2026-06-15','2026-06-01', "
        "CAST('{\"an_depot\":\"2000\"}' AS jsonb))"), {"i": idu})
    out = events.evaluer_suivis(s)
    assert out["permis"] >= 1
    detail = s.execute(text(
        "SELECT detail FROM event_log WHERE idu = :i AND kind = 'parcelle_suivie' AND source = 'Permis'"),
        {"i": idu}).scalar()
    assert "déposé le" not in detail and "2026-06-01" not in detail   # la date de dépôt écartée n'apparaît pas
    assert "autorisé le 2026-06-15" in detail                         # le bon mot, la date d'autorisation
    events.evaluer_suivis(s)                                          # ré-évaluation → dédup
    n = s.execute(text("SELECT count(*) FROM event_log WHERE idu = :i AND kind = 'parcelle_suivie'"),
                  {"i": idu}).scalar()
    assert n == 1                                                     # aucun doublon


def test_lot0_temoin4_composite_sans_axe_de_delai():
    """Témoin 4 (BLOQUANT classement) — l'axe de délai (vélocité) sort du score composite : il n'est
    plus un indicateur du comparateur, ni un poids par défaut de l'endpoint. ÉCHOUE maintenant."""
    from labuse.registre.moteurs.commune import INDICATEURS, composite_communes
    from labuse.api import comparateur
    assert "velocite" not in INDICATEURS, "l'axe délai n'est plus un indicateur du composite"
    params = inspect.signature(comparateur.comparateur_communes).parameters
    assert "w_velocite" not in params, "plus de poids de vélocité à l'endpoint comparateur"
    # le composite calculé ne porte plus d'axe « velocite » dans sa normalisation
    rows = composite_communes([
        {"insee": "1", "commune": "A", "stock": 10, "permis": 100, "deficit_sru": 5.0,
         "pression_zan": 20.0, "prix_neuf": 4000.0},
        {"insee": "2", "commune": "B", "stock": 30, "permis": 300, "deficit_sru": 15.0,
         "pression_zan": 5.0, "prix_neuf": 5000.0},
    ], {k: v[2] for k, v in INDICATEURS.items()})
    assert all("velocite" not in r["normalise"] for r in rows)
