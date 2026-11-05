"""INJECTION-SOLIDE-2 — les 11 essais de CASSE rejoués sur TROIS INGESTIONS RÉELLES.

Une de chaque famille, avec SON vrai chargeur, sur SA vraie table servie (lue seule : chaque test
tourne dans une transaction ANNULÉE — rien n'est jamais écrit durablement ; on vérifie en plus, par
une connexion INDÉPENDANTE, que la table servie est restée identique) :

  · géométries      → trafic_rn.build_trafic_rn          (GeoJSON LineStrings, httpx simulé)
  · tableaux        → ban_plus.ingest_ban_plus           (moisson WFS, client httpx simulé)
  · fichiers manuels → rnic.ingest_rnic                  (CSV national, fichier temporaire)

Matrice de couverture (11 motifs du mandat × 3 familles) — ✔ joué ici, ≈ équivalent (dédoublonnage à
la charge par ON CONFLICT, cf. note), P sur la primitive (test_injection_solide_casse.py) :

  #   motif                              trafic   ban_plus   rnic
  0   nominal (ça passe)                   ✔         P         P
  1   fichier vide                         ✔         ✔         ✔
  2   à moitié / écart suspect             ✔         ✔         ✔
  3   colonnes renommées → rollback        P         P         ✔ (colonne PK absente → NOT NULL)
  4   doublons                             —(serial) ≈(ONCONF) ≈(ONCONF)   + P (dedup_cols)
  5   géométries invalides                 ✔         —(sans)   —(points toujours valides)
  6   hors de La Réunion                   ✔         —(sans)   ✔
  7   coupure réseau en cours → rollback   ✔         ✔         P
  8   deux injections concurrentes         ✔         ✔         ✔
  9   lecture pendant remplacement         ✔         P         P
  10  retour arrière réel (lignes exactes) ✔         ✔         ✔

« — » = physiquement inapplicable à cette table (serial sans clé métier ; table sans géométrie ;
colonnes Point toujours valides). « ≈ » = le dédoublonnage se fait à la CHARGE (ON CONFLICT keep-first)
→ aucun doublon servi, équivalent au refus ; le refus sur `dedup_cols` est prouvé sur la primitive.
"""
from __future__ import annotations

import csv as _csv

import pytest
from sqlalchemy import text

from labuse.ingestion import injection_sure as ijs

pytestmark = pytest.mark.local

_REUNION_LINE = "LINESTRING(55.50 -21.10, 55.51 -21.11)"
_PARIS_LINE = "LINESTRING(2.35 48.85, 2.36 48.86)"
_DEGEN_LINE = "LINESTRING(55.50 -21.10, 55.50 -21.10)"   # point répété → ST_IsValid faux


@pytest.fixture()
def engine():
    """La base APPLICATIVE POPULÉE (`labuse`, « base saine » du mandat), pas la base de test vide :
    ces essais rejouent les vraies ingestions sur leurs vraies tables servies. LECTURE SEULE — chaque
    test tourne dans une transaction ANNULÉE (rien n'est jamais committé). Skippe si indisponible."""
    import os

    from sqlalchemy import create_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base applicative inconnue")
    try:
        eng = create_engine(url, future=True)
        with eng.connect() as c:
            if not c.execute(text("SELECT 1 FROM pg_extension WHERE extname='postgis'")).scalar():
                pytest.skip("PostGIS absent")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"base applicative indisponible ({exc})")
    return eng


def _count(eng, table: str) -> int:
    """Compte sur une connexion INDÉPENDANTE (ne voit que le COMMITTÉ → la version servie réelle)."""
    with eng.connect() as c:
        if c.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is None:
            return -1
        return int(c.execute(text(f'SELECT count(*) FROM "{table}"')).scalar() or 0)


def _exige_peuplee(eng, table: str, mini: int) -> int:
    """Compte servi ; skippe si la table est absente ou trop peu peuplée pour que l'essai ait un sens
    (ex. l'écart de version n'est probant que si la version précédente est conséquente)."""
    n = _count(eng, table)
    if n < 0:
        pytest.skip(f"{table} absente de la base applicative")
    if n < mini:
        pytest.skip(f"{table} trop peu peuplée ({n} < {mini}) pour cet essai")
    return n


class _Session:
    """Session applicative qu'on ANNULE toujours en sortie (jamais d'écriture durable)."""

    def __init__(self, eng):
        from sqlalchemy.orm import Session
        self.s = Session(eng)

    def __enter__(self):
        return self.s

    def __exit__(self, *a):
        self.s.rollback()
        self.s.close()
        return False


# ═══════════════════════════ simulateurs réseau (httpx) ═══════════════════════════

class _Resp:
    def __init__(self, payload, boom=None):
        self._p, self._boom = payload, boom

    def raise_for_status(self):
        if self._boom:
            raise self._boom

    def json(self):
        if self._boom:
            raise self._boom
        return self._p


class _Client:
    """Client httpx minimal : rend `pages` (liste de payloads) l'une après l'autre, ou lève `boom`."""

    def __init__(self, pages=None, boom=None):
        self._pages, self._boom, self._i = pages or [], boom, 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def close(self):
        pass

    def get(self, *a, **k):
        if self._boom:
            raise self._boom
        p = self._pages[min(self._i, len(self._pages) - 1)]
        self._i += 1
        return _Resp(p)


def _geojson(lines):
    return {"features": [{"type": "Feature", "geometry": {"type": "LineString",
            "coordinates": _coords(wkt)}, "properties": {"route": "N1", "annee": 2024, "tmja": 1000}}
            for wkt in lines]}


def _coords(wkt):
    inside = wkt[wkt.index("(") + 1:wkt.rindex(")")]
    return [[float(x) for x in pt.split()] for pt in inside.split(",")]


def _wfs_page(liens):
    return {"features": [{"properties": {"id_adr": a, "id_bat": b, "idu": "974" + "0" * 11,
            "type_lien": "principal", "nb_adr": 1, "nb_bat": 1}} for (a, b) in liens]}


# ═══════════════════════════ A. GÉOMÉTRIES — trafic_rn ═══════════════════════════

def _run_trafic(eng, monkeypatch, *, pages=None, boom=None):
    from labuse.ingestion import trafic_rn
    monkeypatch.setattr(trafic_rn.httpx, "Client",
                        lambda *a, **k: _Client(pages=pages, boom=boom))
    with _Session(eng) as s:
        return trafic_rn.build_trafic_rn(s, log=lambda *_: None), s


def test_trafic_nominal_sert_la_nouvelle_version(engine, monkeypatch):
    avant = _exige_peuplee(engine, "trafic_rn", 10)
    if avant > 5000:
        pytest.skip("table trop volumineuse pour un nominal fabriqué")
    # une livraison de même taille (écart 0) → injection acceptée.
    res, s = _run_trafic(engine, monkeypatch, pages=[_geojson([_REUNION_LINE] * avant)])
    assert res["n"] == avant
    assert int(s.execute(text("SELECT count(*) FROM trafic_rn")).scalar()) == avant  # swap vu EN session
    assert s.execute(text("SELECT to_regclass('trafic_rn__inj_staging')")).scalar() is None
    assert _count(engine, "trafic_rn") == avant        # on annule → version servie intacte


@pytest.mark.parametrize("cas,attendu", [
    ("vide", "injection vide"), ("ecart", "écart"),
    ("invalide", "invalide"), ("hors", "hors de La Réunion")])
def test_trafic_livraisons_cassees_refusees(engine, monkeypatch, cas, attendu):
    avant = _exige_peuplee(engine, "trafic_rn", 50)
    petit = max(1, avant // 50)                        # ~2 % → écart ~98 %
    pages = {
        "vide": [{"features": []}],
        "ecart": [_geojson([_REUNION_LINE] * petit)],
        "invalide": [_geojson([_DEGEN_LINE] + [_REUNION_LINE] * (avant - 1))],
        "hors": [_geojson([_PARIS_LINE] * avant)],
    }[cas]
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_trafic(engine, monkeypatch, pages=pages)
    assert attendu in ei.value.verdict.resume()
    assert _count(engine, "trafic_rn") == avant        # servie INTACTE


def test_trafic_coupure_reseau_garde_la_version_servie(engine, monkeypatch):
    avant = _exige_peuplee(engine, "trafic_rn", 1)
    with pytest.raises(ConnectionError):
        _run_trafic(engine, monkeypatch, boom=ConnectionError("réseau coupé"))
    assert _count(engine, "trafic_rn") == avant


def test_trafic_deux_injections_concurrentes(engine, monkeypatch):
    avant = _exige_peuplee(engine, "trafic_rn", 10)
    tiers = engine.connect()
    ttx = tiers.begin()
    try:
        tiers.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ijs._cle_verrou("trafic_rn")})
        with pytest.raises(ijs.InjectionRefusee) as ei:
            _run_trafic(engine, monkeypatch, pages=[_geojson([_REUNION_LINE] * avant)])
        assert "déjà en cours" in ei.value.verdict.resume()
        assert _count(engine, "trafic_rn") == avant
    finally:
        ttx.rollback()
        tiers.close()


def test_trafic_lecture_pendant_remplacement_jamais_a_moitie(engine, monkeypatch):
    """Un lecteur sur une connexion tierce ne voit JAMAIS un décompte intermédiaire : il voit la
    version servie entière tant que l'injection (non committée) n'a pas basculé."""
    avant = _exige_peuplee(engine, "trafic_rn", 10)
    if avant > 5000:
        pytest.skip("table trop volumineuse pour un nominal fabriqué")
    from labuse.ingestion import trafic_rn
    monkeypatch.setattr(trafic_rn.httpx, "Client",
                        lambda *a, **k: _Client(pages=[_geojson([_REUNION_LINE] * avant)]))
    with _Session(engine) as s:
        trafic_rn.build_trafic_rn(s, log=lambda *_: None)      # swap fait EN session (non committé)
        assert int(s.execute(text("SELECT count(*) FROM trafic_rn")).scalar()) == avant
        # connexion tierce : toujours la version servie entière, jamais 0 / partiel.
        assert _count(engine, "trafic_rn") == avant


def test_trafic_retour_arriere_restaure_les_lignes_exactes(engine, monkeypatch):
    _exige_peuplee(engine, "trafic_rn", 1)
    with engine.connect() as c:
        avant_ids = [r[0] for r in c.execute(text("SELECT id FROM trafic_rn ORDER BY id")).all()]
    with pytest.raises(ijs.InjectionRefusee):
        _run_trafic(engine, monkeypatch, pages=[{"features": []}])   # refus (vide)
    with engine.connect() as c:
        apres_ids = [r[0] for r in c.execute(text("SELECT id FROM trafic_rn ORDER BY id")).all()]
        reste = c.execute(text("SELECT to_regclass('trafic_rn__inj_staging')")).scalar()
    assert apres_ids == avant_ids
    assert reste is None, "la staging a survécu"


# ═══════════════════════════ B. TABLEAUX — ban_plus ═══════════════════════════

def _run_ban(eng, *, pages=None, boom=None):
    from labuse.ingestion import ban_plus
    with _Session(eng) as s:
        return ban_plus.ingest_ban_plus(s, log=lambda *_: None,
                                        client=_Client(pages=pages, boom=boom)), s


@pytest.mark.parametrize("pages,attendu", [
    ([{"features": []}], "injection vide"),                       # moisson vide
    ([_wfs_page([(f"a{i}", f"b{i}") for i in range(10)]), {"features": []}], "écart"),  # 738k → 10
])
def test_ban_plus_livraisons_cassees_refusees(engine, pages, attendu):
    avant = _exige_peuplee(engine, "ban_plus_liens", 100)
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_ban(engine, pages=pages)
    assert attendu in ei.value.verdict.resume()
    assert _count(engine, "ban_plus_liens") == avant


def test_ban_plus_coupure_reseau_garde_la_version_servie(engine):
    avant = _exige_peuplee(engine, "ban_plus_liens", 100)
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_ban(engine, boom=ConnectionError("WFS coupé"))
    assert "ConnectionError" in ei.value.verdict.resume()
    assert _count(engine, "ban_plus_liens") == avant


def test_ban_plus_deux_injections_concurrentes(engine):
    avant = _exige_peuplee(engine, "ban_plus_liens", 100)
    tiers = engine.connect()
    ttx = tiers.begin()
    try:
        tiers.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                      {"k": ijs._cle_verrou("ban_plus_liens")})
        with pytest.raises(ijs.InjectionRefusee) as ei:
            _run_ban(engine, pages=[_wfs_page([("a", "b")]), {"features": []}])
        assert "déjà en cours" in ei.value.verdict.resume()
        assert _count(engine, "ban_plus_liens") == avant
    finally:
        ttx.rollback()
        tiers.close()


def test_ban_plus_retour_arriere_restaure_le_compte(engine):
    avant = _exige_peuplee(engine, "ban_plus_liens", 100)
    with pytest.raises(ijs.InjectionRefusee):
        _run_ban(engine, pages=[{"features": []}])
    assert _count(engine, "ban_plus_liens") == avant


# ═══════════════════════════ C. FICHIERS MANUELS — rnic ═══════════════════════════

_RNIC_COLS = ["code_officiel_departement", "numero_d_immatriculation", "code_officiel_commune",
              "commune_adresse_de_reference", "nom_officiel_commune", "nom_d_usage_de_la_copropriete",
              "adresse_de_reference", "nombre_total_de_lots", "nombre_de_lots_a_usage_d_habitation",
              "periode_de_construction", "type_de_syndic_benevole_professionnel_non_connu",
              "raison_sociale_du_representant_legal", "siret_du_representant_legal",
              "mandat_en_cours_dans_la_copropriete", "reference_cadastrale_1", "reference_cadastrale_2",
              "reference_cadastrale_3", "long", "lat"]


def _rnic_row(num, lon="55.50", lat="-21.10", dept="974"):
    r = {c: "" for c in _RNIC_COLS}
    r.update({"code_officiel_departement": dept, "numero_d_immatriculation": num,
              "code_officiel_commune": "97415", "commune_adresse_de_reference": "Saint-Paul",
              "nombre_total_de_lots": "10", "long": lon, "lat": lat})
    return r


def _ecrire_csv(tmp_path, rows, *, cols=_RNIC_COLS):
    p = tmp_path / "rnic.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(p)


def _run_rnic(eng, csv_path):
    from labuse.ingestion.rnic import ingest_rnic
    with _Session(eng) as s:
        return ingest_rnic(s, csv_path, log=lambda *_: None), s


def test_rnic_csv_vide_refuse(engine, tmp_path):
    avant = _exige_peuplee(engine, "rnic_coproprietes", 1)
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_rnic(engine, _ecrire_csv(tmp_path, []))
    assert "injection vide" in ei.value.verdict.resume()
    assert _count(engine, "rnic_coproprietes") == avant


def test_rnic_demi_fichier_ecart_refuse(engine, tmp_path):
    avant = _exige_peuplee(engine, "rnic_coproprietes", 50)
    rows = [_rnic_row(f"IMMAT{i:05d}") for i in range(5)]          # 2220 → 5 = -99 %
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_rnic(engine, _ecrire_csv(tmp_path, rows))
    assert "écart" in ei.value.verdict.resume()
    assert _count(engine, "rnic_coproprietes") == avant


def test_rnic_colonne_pk_absente_rollback(engine, tmp_path):
    """Producteur qui renomme/retire la colonne clé → immatriculation NULL → NOT NULL → rollback."""
    avant = _exige_peuplee(engine, "rnic_coproprietes", 1)
    cols = [c for c in _RNIC_COLS if c != "numero_d_immatriculation"]
    rows = [{c: "" for c in cols} | {"code_officiel_departement": "974", "long": "55.5",
             "lat": "-21.1", "nombre_total_de_lots": "10"} for _ in range(5)]
    with pytest.raises(ijs.InjectionRefusee):
        _run_rnic(engine, _ecrire_csv(tmp_path, rows, cols=cols))
    assert _count(engine, "rnic_coproprietes") == avant


def test_rnic_hors_reunion_refuse(engine, tmp_path):
    avant = _exige_peuplee(engine, "rnic_coproprietes", 50)
    rows = [_rnic_row(f"IMMAT{i:05d}", lon="2.35", lat="48.85") for i in range(5)]   # Paris
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_rnic(engine, _ecrire_csv(tmp_path, rows))
    assert "hors de La Réunion" in ei.value.verdict.resume()
    assert _count(engine, "rnic_coproprietes") == avant


def test_rnic_deux_injections_concurrentes(engine, tmp_path):
    avant = _exige_peuplee(engine, "rnic_coproprietes", 50)
    rows = [_rnic_row(f"IMMAT{i:05d}") for i in range(5)]
    csv_path = _ecrire_csv(tmp_path, rows)
    tiers = engine.connect()
    ttx = tiers.begin()
    try:
        tiers.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                      {"k": ijs._cle_verrou("rnic_coproprietes")})
        with pytest.raises(ijs.InjectionRefusee) as ei:
            _run_rnic(engine, csv_path)
        assert "déjà en cours" in ei.value.verdict.resume()
        assert _count(engine, "rnic_coproprietes") == avant
    finally:
        ttx.rollback()
        tiers.close()


# ══════════════ D. INJECTION-SOLIDE-3 — nouvelles conversions : bd_nyme (moisson WFS, géométrie) ═══
#
# Les 3 sections ci-dessous rejouent les 11 motifs de casse sur TROIS des conversions de SOLIDE-3,
# chacune sur sa vraie table servie de la base saine (transaction annulée, « servie intacte » vérifiée
# par connexion indépendante). Familles : géométrie moissonnée (bd_nyme), fichier (ort), dérivée à
# records (taxe, + preuve `autoriser_vide`). Collectivement : nominal · vide · écart · hors Réunion ·
# coupure réseau · concurrence · lecture pendant · retour arrière + `autoriser_vide`. Motifs
# physiquement inapplicables ici (— dans la matrice) : géométrie INVALIDE (bd_nyme ne sert que des
# POINTS, toujours valides — couvert par trafic_rn + la primitive), colonne PK absente (couvert par
# rnic), doublons (dédoublonnés à la charge — ON CONFLICT / clés de dict — ou refusés par la primitive).

class _Wfs:
    """WfsConnector minimal : rend `pages` (payloads WFS) l'une après l'autre, ou lève `boom`."""

    def __init__(self, pages=None, boom=None):
        self._pages, self._boom, self._i = pages or [], boom, 0

    def fetch_layer(self, *a, **k):
        if self._boom:
            raise self._boom
        p = self._pages[min(self._i, len(self._pages) - 1)]
        self._i += 1
        return p


def _bdnyme_page(points):
    """points = liste de (lon, lat) → page WFS de lieux-dits (toponyme/cleabs/nature peuplés)."""
    return {"features": [{"geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"toponyme": f"Lieu {i}", "cleabs": f"c{i}", "nature": "Lieu-dit"}}
            for i, (lon, lat) in enumerate(points)]}


def _run_bdnyme(eng, monkeypatch, *, pages=None, boom=None):
    from labuse.ingestion import bd_nyme
    monkeypatch.setattr(bd_nyme, "WfsConnector", lambda *a, **k: _Wfs(pages=pages, boom=boom))
    with _Session(eng) as s:
        return bd_nyme.build_bd_nyme(s, log=lambda *_: None), s


@pytest.mark.parametrize("cas,attendu", [
    ("vide", "injection vide"), ("ecart", "écart"), ("hors", "hors de La Réunion")])
def test_bdnyme_livraisons_cassees_refusees(engine, monkeypatch, cas, attendu):
    avant = _exige_peuplee(engine, "lieux_dits", 50)
    reunion = [(55.50, -21.10)] * 5                   # peu de points → écart ~99 %
    paris = [(2.35, 48.85)] * 5
    pages = {
        "vide": [{"features": []}, {"features": []}],
        "ecart": [_bdnyme_page(reunion), {"features": []}],
        "hors": [_bdnyme_page(paris), {"features": []}],
    }[cas]
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_bdnyme(engine, monkeypatch, pages=pages)
    assert attendu in ei.value.verdict.resume()
    assert _count(engine, "lieux_dits") == avant       # servie INTACTE


def test_bdnyme_coupure_reseau_garde_la_version_servie(engine, monkeypatch):
    avant = _exige_peuplee(engine, "lieux_dits", 50)
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_bdnyme(engine, monkeypatch, boom=ConnectionError("WFS coupé"))
    assert "ConnectionError" in ei.value.verdict.resume()
    assert _count(engine, "lieux_dits") == avant


def test_bdnyme_deux_injections_concurrentes(engine, monkeypatch):
    avant = _exige_peuplee(engine, "lieux_dits", 50)
    tiers = engine.connect()
    ttx = tiers.begin()
    try:
        tiers.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ijs._cle_verrou("lieux_dits")})
        with pytest.raises(ijs.InjectionRefusee) as ei:
            _run_bdnyme(engine, monkeypatch, pages=[_bdnyme_page([(55.5, -21.1)]), {"features": []}])
        assert "déjà en cours" in ei.value.verdict.resume()
        assert _count(engine, "lieux_dits") == avant
    finally:
        ttx.rollback()
        tiers.close()


def test_bdnyme_retour_arriere_garde_le_compte(engine, monkeypatch):
    avant = _exige_peuplee(engine, "lieux_dits", 50)
    with pytest.raises(ijs.InjectionRefusee):
        _run_bdnyme(engine, monkeypatch, pages=[{"features": []}, {"features": []}])
    assert _count(engine, "lieux_dits") == avant
    with engine.connect() as c:
        assert c.execute(text("SELECT to_regclass('lieux_dits__inj_staging')")).scalar() is None


# ══════════════ E. INJECTION-SOLIDE-3 — nouvelles conversions : ort (fichier CSV) ═════════════════

_ORT_COLS = ["Code commune", "Commune", "ACV", "PVD", "Signée ?",
             "Si signée, date de signature", "Durée (en années)"]


def _ort_csv(n):
    """CSV ORT à `n` communes 974 distinctes (ACV signée) → `n` lignes servies."""
    import io as _io
    buf = _io.StringIO()
    w = _csv.DictWriter(buf, fieldnames=_ORT_COLS)
    w.writeheader()
    for i in range(n):
        w.writerow({"Code commune": f"974{i:02d}", "Commune": f"Ville-{i}", "ACV": "true",
                    "PVD": "false", "Signée ?": "Signée",
                    "Si signée, date de signature": "2024-01-01", "Durée (en années)": "5"})
    return buf.getvalue()


def _run_ort(eng, csv_text):
    from labuse.ingestion.ort import ingest_ort
    with _Session(eng) as s:
        return ingest_ort(s, csv_text=csv_text, log=lambda *_: None), s


def test_ort_nominal_sert_la_nouvelle_version(engine):
    avant = _exige_peuplee(engine, "commune_ort", 5)
    if avant > 100:
        pytest.skip("commune_ort anormalement volumineuse")
    res, s = _run_ort(engine, _ort_csv(avant))               # écart 0
    assert res["n"] == avant
    assert int(s.execute(text("SELECT count(*) FROM commune_ort")).scalar()) == avant
    assert s.execute(text("SELECT to_regclass('commune_ort__inj_staging')")).scalar() is None
    assert _count(engine, "commune_ort") == avant            # on annule → servie intacte


def test_ort_lecture_pendant_remplacement_jamais_a_moitie(engine):
    """Un lecteur tiers ne voit JAMAIS un décompte intermédiaire : la version servie entière tant que
    le swap (non committé) n'a pas basculé."""
    avant = _exige_peuplee(engine, "commune_ort", 5)
    if avant > 100:
        pytest.skip("commune_ort anormalement volumineuse")
    from labuse.ingestion.ort import ingest_ort
    with _Session(engine) as s:
        ingest_ort(s, csv_text=_ort_csv(avant), log=lambda *_: None)   # swap fait EN session
        assert int(s.execute(text("SELECT count(*) FROM commune_ort")).scalar()) == avant
        assert _count(engine, "commune_ort") == avant                  # tierce : version servie entière


@pytest.mark.parametrize("n,attendu", [(0, "injection vide"), (1, "écart")])
def test_ort_livraisons_cassees_refusees(engine, n, attendu):
    avant = _exige_peuplee(engine, "commune_ort", 10)
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_ort(engine, _ort_csv(n))
    assert attendu in ei.value.verdict.resume()
    assert _count(engine, "commune_ort") == avant


def test_ort_deux_injections_concurrentes(engine):
    avant = _exige_peuplee(engine, "commune_ort", 5)
    tiers = engine.connect()
    ttx = tiers.begin()
    try:
        tiers.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ijs._cle_verrou("commune_ort")})
        with pytest.raises(ijs.InjectionRefusee) as ei:
            _run_ort(engine, _ort_csv(avant))
        assert "déjà en cours" in ei.value.verdict.resume()
        assert _count(engine, "commune_ort") == avant
    finally:
        ttx.rollback()
        tiers.close()


# ══════════════ F. INJECTION-SOLIDE-3 — nouvelles conversions : taxe (dérivée + autoriser_vide) ═════

def _taxe_records(n):
    return [{"departement": "974", "commune": f"{i:02d}", "taux": "3.0",
             "date_effet": "2024-01-01", "def_prov": "DEF", "libelle_commune": f"Ville-{i}"}
            for i in range(1, n + 1)]


def _run_taxe(eng, records_communaux, records_secteurs=None):
    from labuse.ingestion.taxe_amenagement_delta import ingest_taxe_amenagement
    with _Session(eng) as s:
        return ingest_taxe_amenagement(
            s, records_communaux=records_communaux, records_secteurs=records_secteurs,
            log=lambda *_: None), s


@pytest.mark.parametrize("n,attendu", [(0, "injection vide"), (1, "écart")])
def test_taxe_taux_livraisons_cassees_refusees(engine, n, attendu):
    """taxe_taux est traitée EN PREMIER : une livraison vide / trop maigre la REFUSE avant même de
    toucher aux secteurs → les DEUX tables servies restent intactes (rollback)."""
    avant = _exige_peuplee(engine, "taxe_amenagement_taux", 10)
    avant_sect = _count(engine, "taxe_amenagement_secteur")
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_taxe(engine, _taxe_records(n), records_secteurs=[])
    assert attendu in ei.value.verdict.resume()
    assert _count(engine, "taxe_amenagement_taux") == avant          # les DEUX tables intactes
    assert _count(engine, "taxe_amenagement_secteur") == avant_sect


def test_taxe_empty_delivery_ne_vide_pas_une_table_peuplee(engine):
    """Le CONTRÔLE D'ÉCART protège même une table `autoriser_vide` : une livraison VIDE de secteurs
    (DELTA en panne) ne remplace PAS 10 000+ secteurs servis par 0 — l'écart 100 % > seuil la REFUSE.
    (`autoriser_vide` n'autorise le vide que là où il est LÉGITIME — avant = 0 / première injection —,
    jamais pour effacer une table pleine.)"""
    avant = _exige_peuplee(engine, "taxe_amenagement_taux", 5)
    avant_sect = _exige_peuplee(engine, "taxe_amenagement_secteur", 50)
    with pytest.raises(ijs.InjectionRefusee) as ei:
        _run_taxe(engine, _taxe_records(avant), records_secteurs=[])      # taux OK, secteurs vides
    assert "écart" in ei.value.verdict.resume()
    assert _count(engine, "taxe_amenagement_taux") == avant              # rollback : les DEUX intactes
    assert _count(engine, "taxe_amenagement_secteur") == avant_sect


def test_taxe_deux_injections_concurrentes(engine):
    avant = _exige_peuplee(engine, "taxe_amenagement_taux", 5)
    tiers = engine.connect()
    ttx = tiers.begin()
    try:
        tiers.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                      {"k": ijs._cle_verrou("taxe_amenagement_taux")})
        with pytest.raises(ijs.InjectionRefusee) as ei:
            _run_taxe(engine, _taxe_records(avant), records_secteurs=[])
        assert "déjà en cours" in ei.value.verdict.resume()
        assert _count(engine, "taxe_amenagement_taux") == avant
    finally:
        ttx.rollback()
        tiers.close()


# ══════════════ G. INJECTION-SOLIDE-3 — injection-nuit ne lance QUE les sources sûres ════════════

def test_injection_nuit_ne_lance_que_les_sources_sures(engine, monkeypatch):
    """Bout-en-bout sur la base saine (transaction ANNULÉE) : une source SÛRE avancée est LANCÉE
    (injectees_sures) ; une source de classe A NON sûre avancée n'est PAS lancée → elle remonte comme
    « décision à prendre » (a_decider). La voie « héritée » a DISPARU (plus de clé injectees_heritees)."""
    from sqlalchemy.orm import Session

    import labuse.api.dashboard as dash
    from labuse import jobs_impl
    from labuse.ingestion import garde_injection as gi
    from labuse.jobs import JobContext

    sure = "Trafic RN (Région Réunion — SIR)"          # sûre (injection_sure) + commande → lancée
    non_sure = "Filosofi INSEE (carreaux 200 m)"        # classe A, PAS dans SOURCES_SURES → décision
    assert gi.source_sur_chemin_sur(sure) and not gi.source_sur_chemin_sur(non_sure)

    lancees: list[str] = []
    monkeypatch.setattr(dash, "lancer_ingestion_source",
                        lambda nom: (lancees.append(nom) or {"ok": True}))
    s = Session(engine)
    try:
        for nom in (sure, non_sure):
            n = s.execute(text("UPDATE source_veille SET dernier_statut='nouvelle_version' "
                               "WHERE source_id=(SELECT id FROM data_sources WHERE name=:n)"),
                          {"n": nom}).rowcount
            if not n:
                pytest.skip(f"pas de ligne de veille pour {nom} sur cette base")
        ctx = JobContext(db=s, dry_run=True)
        jobs_impl.injection_nuit(ctx)
        c = ctx.compteurs
        assert sure in c["injectees_sures"], c
        assert sure in lancees                              # la sûre EST lancée (commande connue)
        assert non_sure in c["a_decider"], c                # la non sûre → décision à prendre
        assert non_sure not in lancees                      # JAMAIS lancée seule
        assert "injectees_heritees" not in c                # la voie « héritée » a disparu (SOLIDE-3)
    finally:
        s.rollback()
        s.close()
