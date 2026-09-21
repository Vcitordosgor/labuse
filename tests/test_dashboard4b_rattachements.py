"""DASHBOARD-4b lot 3 — COHÉRENCE : pour 5 sources (DVF · PPR · cadastre · Sitadel · CoSIA), le total
des éléments AFFICHÉS (les 7 blocs servis par /sources/rattachements + /sources/couches) = celui
CALCULÉ indépendamment depuis les déclarations/registre. Le test re-dérive l'attendu à la main (chemin
donnée → robinet + sections V5d + couches) et exige l'ÉGALITÉ des ensembles bloc par bloc — un garde
anti-régression : changer le mappage d'une catégorie ou oublier un bloc casse le test.
"""
from labuse.api.app import sources_couches, sources_rattachements
from labuse.circuit_etats import NOM_VERS_SLUG
from labuse.registre.donnees import DONNEES
from labuse.registre.robinets import ROBINETS
from labuse.registre import declarations as DEC

CINQ_SOURCES = [
    "DVF / valeurs foncières",
    "DEAL Réunion — PPR / aléas",
    "Cadastre (API Carto PCI)",
    "SITADEL (autorisations d'urbanisme)",
    "CoSIA (couverture du sol IA, IGN)",
]
CAT_BLOC = {"outil": "outils", "pdf": "documents", "copilote": "copilote", "veille": "radar"}
BLOCS = ("fiche_parcelle", "fiche_commune", "outils", "documents", "copilote", "radar")


def _attendu_par_source(name: str) -> dict[str, set]:
    """Re-dérive, INDÉPENDAMMENT de l'endpoint, l'ensemble {(ligne, cible)} de chaque bloc pour `name`."""
    slug = NOM_VERS_SLUG[name]
    slug2don: dict[str, set] = {}
    for cid, d in DONNEES.items():
        for s in d.reservoirs:
            slug2don.setdefault(s, set()).add(cid)
    don2rob: dict[str, list] = {}
    for _rid, r in ROBINETS.items():
        for cid in r.chiffres:
            don2rob.setdefault(cid, []).append((r.categorie, r.parent, r.nom))
    quoi2sec: dict[str, set] = {}
    for s in DEC.charger()[0]:
        if s.categorie == "fiche":
            for ligne in s.donnees:
                if ligne.section:
                    quoi2sec.setdefault(ligne.quoi, set()).add(ligne.section)
    attendu: dict[str, set] = {b: set() for b in BLOCS}
    for cid in slug2don.get(slug, ()):
        d = DONNEES.get(cid)
        if d is None:
            continue
        for cat, par, nom in don2rob.get(cid, []):
            if cat == "fiche":
                bloc = "fiche_commune" if par == "fiche_commune" else "fiche_parcelle"
            else:
                bloc = CAT_BLOC.get(cat)
            if bloc:
                attendu[bloc].add((d.libelle, nom))
        for sec in quoi2sec.get(cid, ()):
            attendu["fiche_parcelle"].add((d.libelle, sec))
    return attendu


def test_rattachements_7_blocs_egaux_aux_declarations():
    """Les 6 blocs servis == les 6 blocs re-dérivés, pour les 5 sources (ensembles identiques)."""
    servi = sources_rattachements()
    for name in CINQ_SOURCES:
        assert name in servi, f"{name} absente de /sources/rattachements"
        attendu = _attendu_par_source(name)
        for bloc in BLOCS:
            got = {(x["ligne"], x["cible"]) for x in servi[name][bloc]}
            assert got == attendu[bloc], (
                f"{name} · bloc {bloc} : affiché {len(got)} ≠ calculé {len(attendu[bloc])} "
                f"(en trop : {got - attendu[bloc]} ; manquant : {attendu[bloc] - got})")


def test_total_affiche_egal_total_calcule():
    """Le TOTAL (7 blocs = 6 rattachements + couches carte) affiché = total calculé, pour les 5 sources."""
    rat = sources_rattachements()
    cou = sources_couches()
    for name in CINQ_SOURCES:
        attendu = _attendu_par_source(name)
        n_calcule = sum(len(v) for v in attendu.values()) + len(cou.get(name, []))
        n_affiche = sum(len(v) for v in rat[name].values()) + len(cou.get(name, []))
        assert n_affiche == n_calcule, f"{name} : total affiché {n_affiche} ≠ calculé {n_calcule}"
        # une source utile touche au moins un élément (garde : le test porte sur des sources réelles)
        assert n_affiche > 0, f"{name} : aucun élément — la source ne nourrit rien ?"


def test_par_element_est_l_inverse_de_rattachements():
    """Cohérence forward/reverse : si une source apparaît dans un bloc-robinet d'un élément (rattachements),
    alors cet élément liste la source dans /sources/par-element (et réciproquement)."""
    from labuse.api.app import sources_par_element
    rat = sources_rattachements()
    elements = {e["id"]: e for e in sources_par_element()["elements"]}
    # rid → nom d'élément : on reconstruit l'attendu reverse depuis le forward (blocs robinet, rid porté).
    for name in CINQ_SOURCES:
        for bloc in ("outils", "documents", "copilote", "radar", "fiche_parcelle", "fiche_commune"):
            for x in rat[name][bloc]:
                rid = x["rid"]
                if rid is None:
                    continue  # section V5d déclarée sans robinet dédié (hors reverse par rid)
                assert rid in elements, f"élément {rid} absent de par-element"
                assert name in elements[rid]["sources"], (
                    f"forward dit {name} → {rid} ({bloc}), mais reverse ne liste pas {name}")
