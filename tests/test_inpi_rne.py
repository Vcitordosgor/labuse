"""INPI RNE — Vague A3 : parsing dirigeant, calcul d'âge, croisement & signal propension_vendre.

Schéma figé sur un enregistrement RÉEL vérifié le 05/07/2026 (siren 913037362, SCI ALOE).
Les tests DB verrouillent le signal « âge dirigeant » (aîné des dirigeants physiques),
l'ABSENCE de faux signal (dirigeants tous personnes morales = gigogne) et la garde RGPD.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text

from labuse.connectors.inpi_rne import (
    InpiRneConnector,
    compute_age,
    parse_company,
    propension_band,
)
from labuse.ingestion.inpi_rne import (
    SOURCE_NAME,
    eligible_sirens,
    ingest_inpi_rne,
    resolve_gigogne,
    sample_report,
)

# Réponse RÉELLE simplifiée mais fidèle (chemins vérifiés live) : 1 gérant physique + 1 gérant PM.
COMPANY = {
    "siren": "913037362",
    "formality": {
        "siren": "913037362", "diffusionCommerciale": "True", "formeJuridique": "6540",
        "content": {"personneMorale": {
            "identite": {"entreprise": {
                "siren": "913037362", "denomination": "SCI ALOE",
                "formeJuridique": "6540", "dateImmat": "2022-05-02"}},
            "composition": {"pouvoirs": [
                {"roleEntreprise": "30", "typeDePersonne": "INDIVIDU",
                 "representantId": "uuid-techer", "actif": True,
                 "individu": {"descriptionPersonne": {
                     "nom": "TECHER", "prenoms": ["CHRISTIAN", "PHILIPPE"],
                     "dateDeNaissance": "1977-06", "dateDeNaissancePresent": True,
                     "role": "30", "dateEffetRoleDeclarantPresent": False}}},
                {"roleEntreprise": "99", "typeDePersonne": "ENTREPRISE",
                 "representantId": "uuid-fonciere", "actif": True,
                 "entreprise": {"siren": "904178050",
                                "denomination": "FONCIERE DE L'ILE", "formeJuridique": "5710"}},
            ]},
        }},
    },
}


# ───────────────────────── calcul d'âge / bande (pur) ─────────────────────────

def test_compute_age():
    assert compute_age("1977-06", date(2026, 7, 5)) == 49    # anniversaire (mois) passé
    assert compute_age("1977-08", date(2026, 7, 5)) == 48    # anniversaire (mois) à venir → plancher
    assert compute_age("1977-07", date(2026, 7, 5)) == 49    # mois courant → révolu
    assert compute_age(None, date(2026, 7, 5)) is None
    assert compute_age("pas-une-date", date(2026, 7, 5)) is None
    assert compute_age("1977", date(2026, 7, 5)) is None     # jour/mois absents → refusé
    assert compute_age("2030-01", date(2026, 7, 5)) is None  # futur → refusé


def test_propension_band():
    assert propension_band(80) == "tres_eleve"
    assert propension_band(75) == "tres_eleve"
    assert propension_band(70) == "eleve"
    assert propension_band(60) == "modere"
    assert propension_band(40) == "faible"
    assert propension_band(None) is None


# ───────────────────────── parsing (pur, sans réseau) ─────────────────────────

def test_parse_company_reel():
    c = parse_company(COMPANY)
    assert c["siren"] == "913037362"
    assert c["denomination"] == "SCI ALOE"
    assert c["forme_juridique"] == "6540"
    assert c["diffusible"] is True
    assert len(c["dirigeants"]) == 2

    indiv = c["dirigeants"][0]
    assert indiv["type_personne"] == "INDIVIDU"
    assert indiv["nom"] == "TECHER"
    assert indiv["prenoms"] == "CHRISTIAN PHILIPPE"
    assert indiv["date_naissance"] == "1977-06"       # AAAA-MM, mois jamais le jour
    assert indiv["role_entreprise"] == "30"
    assert indiv["date_prise_fonction"] is None        # dateEffetRoleDeclarantPresent=False
    assert indiv["gerant_siren"] is None

    pm = c["dirigeants"][1]
    assert pm["type_personne"] == "ENTREPRISE"
    assert pm["gerant_siren"] == "904178050"           # dirigeant gigogne (personne morale)
    assert pm["date_naissance"] is None


def test_parse_company_rgpd_non_diffusible():
    # Entreprise NON diffusible → on ne conserve PAS l'identité/naissance de la personne physique.
    data = {**COMPANY, "formality": {**COMPANY["formality"], "diffusionCommerciale": "False"}}
    c = parse_company(data)
    assert c["diffusible"] is False
    indiv = c["dirigeants"][0]
    assert indiv["type_personne"] == "INDIVIDU"
    assert indiv["nom"] is None and indiv["date_naissance"] is None   # masqué (RGPD)


def test_parse_company_prise_fonction_presente():
    data = {"siren": "111111118", "formality": {"diffusionCommerciale": "True", "content": {
        "personneMorale": {
            "identite": {"entreprise": {"siren": "111111118", "denomination": "SCI Z", "formeJuridique": "6540"}},
            "composition": {"pouvoirs": [
                {"roleEntreprise": "30", "typeDePersonne": "INDIVIDU", "representantId": "r1", "actif": True,
                 "individu": {"descriptionPersonne": {
                     "nom": "X", "prenoms": ["Y"], "dateDeNaissance": "1960-03", "dateDeNaissancePresent": True,
                     "dateEffetRoleDeclarantPresent": True, "dateEffetRoleDeclarant": "2015-09-01"}}},
            ]}}}}}
    c = parse_company(data)
    assert c["dirigeants"][0]["date_prise_fonction"] == date(2015, 9, 1)


def test_parse_company_sans_siren():
    assert parse_company({"formality": {"content": {}}}) is None
    assert parse_company({}) is None
    assert parse_company("pas un dict") is None


def test_source_name_coherent():
    assert InpiRneConnector.name == SOURCE_NAME


# ───────────────────────── connecteur : jeton (sans réseau) ─────────────────────────

def test_jwt_exp_refresh(monkeypatch):
    # Le connecteur doit re-loginer quand le jeton approche de son expiration.
    conn = InpiRneConnector(username="u", password="p")
    calls = {"n": 0}

    def fake_login():
        calls["n"] += 1
        conn._token = "tok"
        conn._token_exp = 1_000_000  # exp fixe dans le passé/présent contrôlé

    monkeypatch.setattr(conn, "_login", fake_login)
    monkeypatch.setattr("labuse.connectors.inpi_rne.time.time", lambda: 999_000)  # < exp-marge → OK
    conn._ensure_token()
    assert calls["n"] == 1
    conn._ensure_token()                                   # jeton encore valide → pas de re-login
    assert calls["n"] == 1
    monkeypatch.setattr("labuse.connectors.inpi_rne.time.time", lambda: 1_000_000)  # dépassé la marge
    conn._ensure_token()
    assert calls["n"] == 2                                  # re-login déclenché


# ───────────────────────── croisement / signal (DB) ─────────────────────────

def _pm(db, idu, siren, denom="SCI TEST", groupe=0):
    db.execute(text(
        "INSERT INTO parcelle_personne_morale (idu, siren, denomination, groupe, source, date_import) "
        "VALUES (:i,:s,:d,:g,'test',now()) ON CONFLICT (idu) DO NOTHING"),
        {"i": idu, "s": siren, "d": denom, "g": groupe})


def _indiv(rid, dn):
    return {"representant_id": rid, "type_personne": "INDIVIDU", "role_entreprise": "30",
            "actif": True, "diffusible": True, "nom": "NOM_" + rid, "prenoms": "P",
            "date_naissance": dn, "date_prise_fonction": None, "gerant_siren": None,
            "raw": {"representantId": rid}}


def _entreprise(rid, gs):
    return {"representant_id": rid, "type_personne": "ENTREPRISE", "role_entreprise": "99",
            "actif": True, "diffusible": True, "nom": "SCI GERANTE", "prenoms": None,
            "date_naissance": None, "date_prise_fonction": None, "gerant_siren": gs,
            "raw": {"representantId": rid}}


def _parsed(siren, dirigeants, denom="SCI X"):
    return {"siren": siren, "denomination": denom, "forme_juridique": "6540",
            "date_immat": None, "diffusible": True, "dirigeants": dirigeants,
            "url_source": "http://x/" + siren}


class _StubConn:
    """Connecteur factice : rejoue des sociétés pré-parsées, sans réseau."""

    def __init__(self, companies):
        self._c = companies
        self._by_siren = {c["siren"]: c for c in companies}

    def fetch_companies(self, sirens, throttle_s=None):
        import re
        s = {re.sub(r"\D", "", x) for x in sirens}
        for c in self._c:
            if c["siren"] in s:
                yield c

    def fetch_company(self, siren):
        import re
        return self._by_siren.get(re.sub(r"\D", "", siren))


@pytest.mark.db
def test_eligible_sirens_filtre_public_et_commune(db_session):
    _pm(db_session, "97415000AA0001", "913037362", groupe=0)     # marchande → gardée
    _pm(db_session, "97415000AA0002", "", groupe=0)              # SIREN vide → exclu
    _pm(db_session, "97415000AA0003", "12345", groupe=0)         # mal formé → exclu
    _pm(db_session, "97415000AA0004", "200000004", groupe=4)     # Commune (public) → exclu
    _pm(db_session, "97411000AA0001", "999999999", groupe=0)     # autre commune
    db_session.flush()
    sp = eligible_sirens(db_session, "97415")
    assert "913037362" in sp
    assert "200000004" not in sp and "999999999" not in sp       # public exclu, autre commune exclue
    assert all(len(s) == 9 and s.isdigit() for s in sp)
    ile = eligible_sirens(db_session)
    assert "999999999" in ile and "200000004" not in ile


@pytest.mark.db
def test_ingest_signal_aine_et_pas_de_faux_signal(db_session):
    _pm(db_session, "97415000AA0001", "913037362", "SCI AINEE")   # gérant âgé
    _pm(db_session, "97415000AA0002", "111111118", "SCI GIGOGNE") # dirigeants tous PM
    _pm(db_session, "97415000AA0003", "222222229", "SCI JEUNE")   # gérant jeune
    db_session.flush()

    conn = _StubConn([
        _parsed("913037362", [_indiv("r1", "1990-06"), _indiv("r2", "1945-06")]),  # aîné = 1945
        _parsed("111111118", [_entreprise("r3", "904178050")]),                    # aucun individu
        _parsed("222222229", [_indiv("r4", "1992-01")]),                           # jeune
    ])
    res = ingest_inpi_rne(db_session, ["913037362", "111111118", "222222229"], connector=conn)
    assert res["dirigeants"] == 4 and res["sirens_with_dirigeant"] == 3

    sig = {r["siren"]: r for r in db_session.execute(text(
        "SELECT siren, age_max_dirigeant, propension_band, age_source, nb_individus "
        "FROM v_pm_propension_vendre")).mappings().all()}

    # SCI AÎNÉE : l'âge retenu est celui de l'AÎNÉ (né 1945 → >80), signal élevé, source directe.
    assert sig["913037362"]["age_source"] == "direct"
    assert sig["913037362"]["age_max_dirigeant"] >= 79
    assert sig["913037362"]["propension_band"] == "tres_eleve"
    assert sig["913037362"]["nb_individus"] == 2

    # SCI GIGOGNE : aucun dirigeant physique → PAS de faux signal, taux gigogne mesurable.
    assert sig["111111118"]["age_source"] == "aucun_individu"
    assert sig["111111118"]["age_max_dirigeant"] is None
    assert sig["111111118"]["propension_band"] is None

    # SCI JEUNE : gérant jeune → bande faible.
    assert sig["222222229"]["propension_band"] == "faible"

    # Vue parcelle : le flag suit le SIREN.
    parc = {r["idu"]: r for r in db_session.execute(text(
        "SELECT idu, propension_band, age_source FROM v_foncier_propension_vendre")).mappings().all()}
    assert parc["97415000AA0001"]["propension_band"] == "tres_eleve"
    assert parc["97415000AA0002"]["age_source"] == "aucun_individu"


@pytest.mark.db
def test_sample_report_taux_gigogne(db_session):
    _pm(db_session, "97415000AA0001", "913037362", "SCI AINEE")
    _pm(db_session, "97415000AA0002", "111111118", "SCI GIGOGNE")
    db_session.flush()
    conn = _StubConn([
        _parsed("913037362", [_indiv("r1", "1945-06")]),
        _parsed("111111118", [_entreprise("r3", "904178050")]),
    ])
    ingest_inpi_rne(db_session, ["913037362", "111111118"], connector=conn)
    rep = sample_report(db_session, "97415")
    assert rep["sirens_avec_dirigeant"] == 2
    assert rep["n_gigogne"] == 1 and rep["taux_gigogne"] == 0.5
    assert rep["parcelles_gerant_age"] == 1          # la SCI aînée
    assert len(rep["exemples"]) == 1                 # 1 seul SIREN daté


@pytest.mark.db
def test_ingest_idempotent(db_session):
    _pm(db_session, "97415000AA0001", "913037362")
    db_session.flush()
    conn = _StubConn([_parsed("913037362", [_indiv("r1", "1960-06"), _indiv("r2", "1970-06")])])
    ingest_inpi_rne(db_session, ["913037362"], connector=conn)
    ingest_inpi_rne(db_session, ["913037362"], connector=conn)   # re-run
    n = db_session.execute(text("SELECT count(*) FROM pm_dirigeants")).scalar()
    assert n == 2   # ON CONFLICT (siren, representant_id) → aucun doublon


# ───────────────────────── récursion gigogne depth-1 (DB) ─────────────────────────

def _band(db, siren):
    return db.execute(text(
        "SELECT age_max_dirigeant, propension_band, age_source FROM v_pm_propension_vendre "
        "WHERE siren = :s"), {"s": siren}).mappings().first()


@pytest.mark.db
def test_gigogne_resout_gerant_societe(db_session):
    # SCI GIGOGNE (111111118) gérée par la société 904178050, elle-même gérée par un physique âgé.
    _pm(db_session, "97415000AA0001", "111111118", "SCI GIGOGNE")
    db_session.flush()
    depth0 = _StubConn([_parsed("111111118", [_entreprise("rg", "904178050")])])
    ingest_inpi_rne(db_session, ["111111118"], connector=depth0)
    assert _band(db_session, "111111118")["age_source"] == "aucun_individu"   # avant depth-1

    depth1 = _StubConn([_parsed("904178050", [_indiv("rp", "1945-06")])])     # gérant → physique 1945
    res = resolve_gigogne(db_session, connector=depth1, throttle_s=0)
    assert res["cibles"] == 1 and res["cibles_resolues"] == 1 and res["dirigeants_gigogne"] == 1

    row = _band(db_session, "111111118")
    assert row["age_source"] == "gerant_societe"          # résolu par le gérant-société
    assert row["age_max_dirigeant"] >= 79
    assert row["propension_band"] == "tres_eleve"


@pytest.mark.db
def test_gigogne_cycle_auto_reference_saute(db_session):
    # Gérant = la cible elle-même → cycle : aucun appel, aucune résolution, pas de boucle.
    _pm(db_session, "97415000AA0001", "111111118", "SCI CYCLE")
    db_session.flush()
    ingest_inpi_rne(db_session, ["111111118"],
                    connector=_StubConn([_parsed("111111118", [_entreprise("rg", "111111118")])]))
    res = resolve_gigogne(db_session, connector=_StubConn([]), throttle_s=0)
    assert res["cibles"] == 0 and res["dirigeants_gigogne"] == 0      # écarté par d.gerant_siren <> d.siren
    assert _band(db_session, "111111118")["age_source"] == "aucun_individu"


@pytest.mark.db
def test_gigogne_bornee_un_niveau(db_session):
    # Le gérant est LUI AUSSI une holding (que des PM) → on ne redescend pas : cible non résolue.
    _pm(db_session, "97415000AA0001", "111111118", "SCI GIGOGNE 2")
    db_session.flush()
    ingest_inpi_rne(db_session, ["111111118"],
                    connector=_StubConn([_parsed("111111118", [_entreprise("rg", "904178050")])]))
    depth1 = _StubConn([_parsed("904178050", [_entreprise("rg2", "503556110")])])  # gérant = holding
    res = resolve_gigogne(db_session, connector=depth1, throttle_s=0)
    assert res["cibles"] == 1 and res["cibles_resolues"] == 0 and res["dirigeants_gigogne"] == 0
    assert _band(db_session, "111111118")["age_source"] == "aucun_individu"   # borné → non résolu


@pytest.mark.db
def test_gigogne_direct_a_priorite(db_session):
    # Un SIREN qui a DÉJÀ un dirigeant physique direct garde age_source='direct' (COALESCE).
    _pm(db_session, "97415000AA0001", "111111118", "SCI MIXTE")
    db_session.flush()
    ingest_inpi_rne(db_session, ["111111118"], connector=_StubConn([
        _parsed("111111118", [_indiv("rd", "1990-06"), _entreprise("rg", "904178050")])]))
    # même si on résout le gérant (physique âgé), le direct (jeune) prime.
    resolve_gigogne(db_session, connector=_StubConn([
        _parsed("904178050", [_indiv("rp", "1940-06")])]), throttle_s=0)
    row = _band(db_session, "111111118")
    assert row["age_source"] == "direct" and row["propension_band"] == "faible"


@pytest.mark.db
def test_gigogne_gerant_injoignable_saute_sans_crash(db_session):
    # Un gérant qui lève (429 persistant simulé) ne doit PAS tuer la passe : cible sautée, comptée.
    _pm(db_session, "97415000AA0001", "111111118", "SCI ERR")
    _pm(db_session, "97415000AA0002", "222222229", "SCI OK")
    db_session.flush()
    ingest_inpi_rne(db_session, ["111111118", "222222229"], connector=_StubConn([
        _parsed("111111118", [_entreprise("rg", "480998806")]),   # gérant qui va lever
        _parsed("222222229", [_entreprise("rg2", "904178050")]),  # gérant OK
    ]))

    class _FlakyConn(_StubConn):
        def fetch_company(self, siren):
            import re
            if re.sub(r"\D", "", siren) == "480998806":
                raise RuntimeError("HTTP 429")
            return super().fetch_company(siren)

    conn = _FlakyConn([_parsed("904178050", [_indiv("rp", "1945-06")])])
    res = resolve_gigogne(db_session, connector=conn, throttle_s=0)
    assert res["erreurs_gerant"] == 1                     # le gérant en erreur est compté
    assert res["cibles_resolues"] == 1                    # l'autre cible est bien résolue
    assert _band(db_session, "222222229")["age_source"] == "gerant_societe"
    assert _band(db_session, "111111118")["age_source"] == "aucun_individu"  # sautée → réessayable


@pytest.mark.db
def test_gigogne_idempotent(db_session):
    _pm(db_session, "97415000AA0001", "111111118", "SCI GIGOGNE")
    db_session.flush()
    ingest_inpi_rne(db_session, ["111111118"],
                    connector=_StubConn([_parsed("111111118", [_entreprise("rg", "904178050")])]))
    depth1 = _StubConn([_parsed("904178050", [_indiv("rp", "1945-06")])])
    resolve_gigogne(db_session, connector=depth1, throttle_s=0)
    resolve_gigogne(db_session, connector=depth1, throttle_s=0)   # re-run
    n = db_session.execute(text("SELECT count(*) FROM pm_dirigeant_gigogne")).scalar()
    assert n == 1   # ON CONFLICT (siren, gerant_siren, representant_id) → aucun doublon
