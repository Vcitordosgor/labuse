"""ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — le barème sait porter les vraies règles du PLU.

Tests unitaires du moteur de barème (`BaremeStationnement.exiger`), sans base : formes typées
(par tranche de m², arrondi lu, visiteurs, seuil d'opération, « la plus exigeante de deux
formules », ligne du logement social), conditions non modélisables remontées, destination lue
dans le type de projet. Les chiffres sont calculés à la main depuis le texte (cf. RAPPORT d'audit).
"""
from types import SimpleNamespace

from labuse.implantation.regles import DESTINATION_PAR_PROJET, _bareme


def _prog(spec):
    """spec = [(pieces, surface_m2, n), …] → liste de logements."""
    out = []
    for p, s, n in spec:
        out += [SimpleNamespace(pieces=p, surface_m2=s) for _ in range(n)]
    return out


# Programme « équilibre » du moteur pour 8 logements : T2×4 (2p, 56 m²), T3×3 (3p, 70), T4×1 (4p, 80).
PROG8 = _prog([(2, 56, 4), (3, 70, 3), (4, 80, 1)])


def test_tampon_collectif_retient_la_regle_operation_la_plus_exigeante():
    """Le Tampon Ud12.2 : habitat collectif par pièces (0,5/1/1,5) ET « opération > 5 logements :
    1,5/logt, arrondi inférieur ». Pour 8 logements, la plus exigeante = 12 (vs 10 par typologie)."""
    b = _bareme({"par_typologie": {
        "statut": "valide", "article": "Ud12.2", "page_pdf": 66, "citation": "…", "retenue": "max",
        "detail": [
            {"destination": "collectif", "pieces_max": 1, "places": 0.5, "role": "base", "tranche": "chambre/studio"},
            {"destination": "collectif", "pieces_min": 2, "pieces_max": 2, "places": 1, "role": "base", "tranche": "2 pièces"},
            {"destination": "collectif", "pieces_min": 3, "places": 1.5, "role": "base", "tranche": "3 pièces+"},
            {"destination": "individuel", "places": 1, "role": "base"},
            {"destination": "collectif", "places": 1.5, "arrondi": "inferieur", "logements_min": 6, "role": "operation"},
        ],
        "conditions": ["dont au moins 0,5 place à l'extérieur des espaces privatisés"]}})
    ex = b.exiger(PROG8, destination="collectif")
    assert ex.couvert is True
    assert ex.places == 12                      # 1,5 × 8 (opération > 5), arrondi inférieur
    assert "opération > 5" in ex.formule
    assert any("= 10" in f for f in ex.formules_ecartees)   # lecture par typologie écartée
    assert ex.conditions == ("dont au moins 0,5 place à l'extérieur des espaces privatisés",)


def test_saint_pierre_par_m2_sdp_tranche_complete_arrondi_inferieur():
    """Saint-Pierre Ud6 : « 1 place par tranche de 75 m² de SP » + « la place est comptabilisée par tranche
    complète » → seules les tranches ENTIÈRES comptent → arrondi INFÉRIEUR. 887,5 m² → 11 places (pas 12)."""
    b = _bareme({"par_m2_sdp": {"statut": "valide", "article": "Ud6", "page_pdf": 93,
                                "citation": "…", "m2_par_place": 75, "arrondi": "inferieur"}})
    ex = b.exiger(_prog([(3, 88.75, 10)]), destination="collectif")   # SDP 887,5
    assert ex.places == 11
    assert "inférieur" in ex.formule
    # 450 m² = 6 tranches entières exactes → 6 quel que soit l'arrondi
    assert b.exiger(_prog([(3, 90, 5)]), destination="collectif").places == 6


def test_tranche_muette_prend_le_plus_exigeant_superieur():
    """Formule « 1 place / 35 m² » sans mention d'arrondi (Les Avirons, ligne alternative) → plus exigeant
    = arrondi SUPÉRIEUR."""
    b = _bareme({"par_typologie": {"statut": "valide", "article": "x", "page_pdf": 1, "retenue": "max",
                 "detail": [{"destination": "collectif", "par_m2": 35, "role": "alt"}]}})
    ex = b.exiger(_prog([(2, 56, 4), (3, 70, 3), (4, 80, 1)]), destination="collectif")   # SDP 514
    assert ex.places == 15          # 514 / 35 = 14,7 → 15 (supérieur)
    assert "supérieur" in ex.formule


def test_la_plus_exigeante_de_deux_formules():
    """Les Avirons : collectif = « 1,25/logt OU 1 place / 35 m² SDP, la norme produisant le plus de
    places retenue ». Les deux lectures sont calculées, la plus grande retenue."""
    b = _bareme({"par_typologie": {"statut": "valide", "article": "U12.2", "page_pdf": 16, "retenue": "max",
                 "detail": [
                     {"destination": "collectif", "places": 1.25, "role": "alt"},
                     {"destination": "collectif", "par_m2": 35, "role": "alt"}]}})
    ex = b.exiger(PROG8, destination="collectif")
    # SDP = 514 m² → 514/35 = 14,7 → 15 ; 1,25 × 8 = 10 → retient 15
    assert ex.places == 15
    assert any("= 10" in f for f in ex.formules_ecartees)


def test_visiteurs_par_m2_et_par_logements():
    """Le Port : 0,3/logt + 1 visiteur / 100 m² SDP. Saint-Benoît : 1/logt + 1 visiteur / 5 logts."""
    port = _bareme({"par_logement": {"statut": "valide", "article": "Ua12.1", "page_pdf": 30, "places": 0.3,
                                     "visiteurs": {"par_m2_sdp": 100, "places": 1}}})
    ex = port.exiger(PROG8, destination="collectif")
    assert ex.places_residents == 3            # 0,3 × 8 = 2,4 → 3
    assert ex.places_visiteurs == 6            # 514 / 100 = 5,14 → 6
    assert ex.places == 9

    benoit = _bareme({"par_logement": {"statut": "valide", "article": "U12", "page_pdf": 17, "places": 1,
                                       "visiteurs": {"par_logements": 5, "places": 1}}})
    exb = benoit.exiger(PROG8, destination="collectif")
    assert exb.places_residents == 8 and exb.places_visiteurs == 2 and exb.places == 10


def test_arrondi_lu_dans_la_regle_par_logement():
    """Le sens d'arrondi est désormais LU en mode par_logement (avant : toujours supérieur)."""
    inf = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1,
                                    "places": 1.5, "arrondi": "inferieur"}})
    sup = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1,
                                    "places": 1.5, "arrondi": "superieur"}})
    prog5 = _prog([(2, 56, 5)])                 # 1,5 × 5 = 7,5
    assert inf.exiger(prog5, destination="collectif").places == 7     # arrondi inférieur
    assert sup.exiger(prog5, destination="collectif").places == 8     # arrondi supérieur


def test_regle_ne_couvrant_pas_le_programme_reste_non_verifie():
    """Un barème validé dont aucune ligne ne couvre le programme dessiné → couvert=False (le contrôle
    dira « Non vérifié », jamais « Réussi ») — on n'invente rien."""
    b = _bareme({"par_typologie": {"statut": "valide", "article": "x", "page_pdf": 1,
                 "detail": [{"destination": "individuel", "places": 2, "role": "base"}]}})
    ex = b.exiger(PROG8, destination="collectif")   # programme collectif, aucune ligne collectif
    assert ex.couvert is False


def test_destination_dediee_senior_etudiant_gouverne():
    """Règle permanente #4 — un projet senior/étudiant lit SA ligne (0,3 ou 0,2 / hébergement), pas la
    règle collective générale ; sans ligne dédiée la destination reste « Non vérifié » (via le moteur)."""
    b = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1, "places": 1.5,
                                  "senior": {"places": 0.3}, "etudiant": {"places": 0.2}}})
    prog = _prog([(3, 70, 9)])
    assert b.exiger(prog, destination="collectif").places == 14   # 9 × 1,5 = 13,5 → 14
    assert b.exiger(prog, destination="senior").places == 3       # 9 × 0,3 = 2,7 → 3
    assert b.exiger(prog, destination="etudiant").places == 2     # 9 × 0,2 = 1,8 → 2
    assert b.has_destination("senior") and not b.has_destination("social")


def test_hauteur_pres_des_limites_non_verifiee():
    """Contre-audit — une règle de hauteur près des limites (Le Tampon Ua10.3, bande de 3,60 m) que le
    moteur ne sait pas chiffrer est DÉTECTÉE (→ contrôle « Non vérifié »), jamais traitée comme absente."""
    from labuse.implantation import regles as R
    rz = R.charger("97422", "Ua")
    assert rz.hauteur_bande_limite is not None
    assert rz.hauteur_bande_limite.get("article") == "Ua10.3"
    assert R.charger("97424", "Ua").hauteur_bande_limite is None   # Cilaos : pas de telle règle


def test_saint_louis_condition_chiffree_comptee():
    """Relecture 7 — « opérations > 10 logements : 0,5 place publique/logt » est CHIFFRÉE et comptée dans
    les places à loger (lecture la plus exigeante)."""
    from types import SimpleNamespace
    from labuse.implantation import regles as R
    b = R.charger("97414", "UA").stationnement
    prog = lambda n: [SimpleNamespace(pieces=3, surface_m2=70) for _ in range(n)]
    assert b.exiger(prog(8), destination="collectif").places_visiteurs == 0      # ≤ 10 : rien
    assert b.exiger(prog(20), destination="collectif").places_visiteurs == 10    # 0,5 × 20


def test_colonne_places_integrees_condition_bloquante_au_seuil():
    """Règle permanente #2 — la colonne « places intégrées » : au-delà du seuil de SDP, une part des places
    doit être bâtie → condition bloquante à vérifier (plein air exclu). En dessous : rien."""
    b = _bareme({"par_logement": {"statut": "valide", "article": "x", "page_pdf": 1, "places": 1.0,
                                  "places_integrees": {"pct": 100, "seuil_m2": 1000}}})
    assert b.exiger(_prog([(3, 70, 20)]), destination="collectif").conditions   # 1400 m² > 1000 → condition
    assert not b.exiger(_prog([(3, 70, 5)]), destination="collectif").conditions  # 350 m² < 1000 → aucune


def test_le_tampon_collectif_jamais_le_bareme_individuel():
    """Contre-audit 97422000BW2635 (Le Tampon) — une opération collective ne doit JAMAIS être chiffrée au
    barème de l'habitat individuel (1 place/logt). Le texte Ud/Ua12.2 donne le collectif (1,5 place/logt au
    3 pièces et plus, ou la règle d'opération > 5) : 30 logements → ~45 places, pas 30."""
    from types import SimpleNamespace
    from labuse.implantation import regles as R
    b = R.charger("97422", "Uav").stationnement

    def prog(n, pieces=3, surface=70):
        return [SimpleNamespace(pieces=pieces, surface_m2=surface) for _ in range(n)]
    for n, attendu in [(8, 12), (20, 30), (30, 45)]:
        ex = b.exiger(prog(n), destination="collectif")
        assert ex.places == attendu, f"{n} logts collectif → {ex.places}, attendu {attendu}"
        assert "individuel" not in ex.formule.lower()


def test_etude_refuse_immediatement_parcelle_non_constructible(monkeypatch):
    """Audit écrans (97404000AM0838, zone UE habitat interdit) — l'Étude lit le MÊME verdict de
    constructibilité que les autres documents et REFUSE tout de suite, avec le motif, SANS lancer le
    solveur, pour toute parcelle non constructible (habitat interdit, zone rouge, A/N…)."""
    from labuse.implantation import service, moteur as M

    monkeypatch.setattr(service, "_refus_constructibilite",
                        lambda s, idus: ("UE", "Habitat interdit dans cette zone"))
    monkeypatch.setattr(service, "_payload_hors_perimetre",
                        lambda s, idus, entree, exc: {"hors_perimetre": True, "message": str(exc)})

    def _solveur_interdit(*a, **k):
        raise AssertionError("le solveur ne doit PAS être lancé pour une parcelle non constructible")
    monkeypatch.setattr(M, "etudier_complet", _solveur_interdit)

    p = service.etudier_payload(None, {"idus": ["97404000AM0838"], "type_projet": "collectif"})
    assert p["hors_perimetre"] is True
    assert "Habitat interdit" in p["message"]


def test_logement_de_fonction_refuse_mais_pas_le_logement_conditionnel():
    """Les 52+ zones « habitat secondaire » (correctif relecture) — le logement de FONCTION (employés,
    gardiennage) n'est pas un programme d'habitation → l'Étude refuse ; mais une zone où le logement est
    permis sous condition RÉELLE (opérations d'ensemble, déficit social…) reste étudiée."""
    from labuse.implantation.service import _logement_fonction_seulement as f
    assert f("97405", "UEa") is True      # Petite-Île : « logements des employés »
    assert f("97405", "AUE") is True
    assert f("97404", "AUa") is False     # Étang-Salé : « opérations d'ensemble ≥ 10 logements » (vrai logement)
    assert f("97409", "UB") is False      # Saint-André : « programme de logements > 2 000 m² »


def test_etude_constructible_atteint_le_solveur(monkeypatch):
    """Garde-fou symétrique : une parcelle CONSTRUCTIBLE passe le verdict et atteint bien le solveur."""
    from labuse.implantation import service, moteur as M
    monkeypatch.setattr(service, "_refus_constructibilite", lambda s, idus: None)
    atteint = {}

    def _sentinel(*a, **k):
        atteint["oui"] = True
        raise RuntimeError("arrêt-après-garde")
    monkeypatch.setattr(M, "etudier_complet", _sentinel)
    try:
        service.etudier_payload(None, {"idus": ["97416000HT0538"], "type_projet": "collectif"})
    except RuntimeError:
        pass
    assert atteint.get("oui") is True


def _signature(b):
    """Signature de la RÈGLE appliquée (valeurs, pas le texte) — pour comparer deux zones."""
    lignes = tuple(sorted(
        f"{l.destination}|{l.role}|{l.places}|{l.par_m2}|{l.pieces_min}|{l.pieces_max}|"
        f"{l.sdp_min}|{l.sdp_max}|{l.logements_min}|{l.arrondi}" for l in b.lignes))
    vis = None if b.visiteurs is None else (b.visiteurs.places, b.visiteurs.par_logements,
                                            b.visiteurs.par_m2_sdp, b.visiteurs.logements_min, b.visiteurs.arrondi)
    return (b.mode, b.flat_places, b.m2_par_place, b.arrondi, b.retenue, lignes, vis, tuple(b.conditions))


def test_controle_citation_identique_implique_regle_identique():
    """CONTRÔLE (correctif #3) — aucune citation IDENTIQUE entre deux zones sans que la RÈGLE appliquée soit
    identique. C'est exactement ce qui aurait attrapé le bug « Ucv recopie la citation de Ud » (même phrase,
    mais Ucv applique 0,85 et Ud applique 1 — signatures ≠). Sur les cinq communes pilotes."""
    from labuse.plu import destinations as D
    from labuse.implantation import regles as R
    import glob
    import os
    import re
    communes = sorted({os.path.basename(p)[:5] for p in glob.glob("config/plu_destinations/974??_*.yaml")})
    for insee in communes:
        par_citation = {}
        for r in D.regles_commune(insee):
            z = r["zone"]
            if not re.match(r'^\d*(U|AU)', z, re.I):
                continue
            b = R.charger(insee, z).stationnement
            if not b.validee or not b.citation:
                continue
            par_citation.setdefault(b.citation, []).append((z, _signature(b)))
        for cit, items in par_citation.items():
            sigs = {sig for _z, sig in items}
            zones = [z for z, _s in items]
            if len(sigs) == 1:
                continue
            # citations VERBATIM : un même TABLEAU de page peut légitimement servir plusieurs zones à
            # valeurs différentes (Saint-Paul p.81 : « en zones U2a, U2b : 1,5 ; en zones U2c, U2d : 2 »).
            # Ce n'est une RECOPIE suspecte que si la valeur appliquée d'une zone est ABSENTE de la citation
            # partagée (le cas Ucv-copie-Ud). On l'autorise donc tant que chaque valeur figure dans la citation.
            import re as _re
            cit_n = _re.sub(r'\s+', '', cit.lower().replace("’", "'"))
            def _fr(x):
                return str(int(round(x))) if abs(x - round(x)) < 1e-9 else ("%g" % x).replace(".", ",")
            manque = []
            for z in zones:
                bz = R.charger(insee, z).stationnement
                for v in (bz.flat_places, bz.m2_par_place):
                    if v is not None and _fr(v) not in cit_n:
                        manque.append((z, _fr(v)))
            assert not manque, (
                f"{insee} : citation partagée entre zones de règle différente {zones}, et une valeur "
                f"appliquée est ABSENTE de la citation {manque[:4]} (citation « {cit[:50]}… ») — recopie probable.")


@__import__("pytest").mark.local  # ouvre une vingtaine de PDF via pymupdf → hors filet rapide (pré-push), tourne en CI/manuel
def test_chaque_chiffre_applique_figure_dans_sa_citation():
    """CONTRÔLE DUR (relecture 3) — chaque chiffre appliqué par un barème doit figurer DANS SA CITATION (pas
    seulement « quelque part sur la page » : un « 1 » s'y trouve partout). Garde-fou contre toute valeur sans
    source citée. Sauté si les PDF officiels ne sont pas présents (CI nue). (La conversion des citations en
    texte VERBATIM sur la page — l'autre moitié du contrôle — est une dette suivie dans le compte-rendu.)"""
    import glob
    import importlib.util
    import os
    pdfdir = os.path.expanduser("~/Desktop/labuse/data/plu_reglements/")
    if not glob.glob(pdfdir + "974*_*.pdf"):
        import pytest
        pytest.skip("PDF officiels absents (data/plu_reglements) — contrôle de pages non exécutable ici")
    spec = importlib.util.spec_from_file_location("ctl_pages", "scripts/stationnement_controle_pages.py")
    ctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ctl)
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        res = ctl.controle()
    fig = res["fig"]
    assert not fig, (f"{len(fig)} règles appliquent un chiffre absent de leur citation : "
                     + ", ".join(f"{i} {z} {h}" for i, z, _pg, h in fig[:10]))


def test_association_secteur_valeur_dans_citation_partagee():
    """Relecture 6 — quand un tableau sert plusieurs secteurs à valeurs différentes (« U2a, U2b : 1,5 ;
    U2c, U2d : 2 »), la valeur appliquée doit être celle ASSOCIÉE à ce secteur dans la citation (pas juste
    présente quelque part). Les cas où l'association ne se lit pas vont en relecture image. Ici : 0."""
    import glob
    import importlib.util
    import os
    import re
    spec = importlib.util.spec_from_file_location("ctl_assoc", "scripts/stationnement_controle_pages.py")
    ctl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ctl)
    from labuse.implantation import regles as R
    from labuse.plu import destinations as D
    a_relire = []
    for p in sorted(glob.glob("config/plu_destinations/974??_*.yaml")):
        insee = os.path.basename(p)[:5]
        for r in D.regles_commune(insee):
            z = r["zone"]
            if not re.match(r'^\d*(U|AU)', z, re.I):
                continue
            b = R.charger(insee, z).stationnement
            if b.validee and ctl.association_secteur(b, z) == "image":
                a_relire.append(f"{insee}/{z}")
    assert not a_relire, f"{len(a_relire)} associations secteur-valeur non lisibles : {a_relire[:10]}"
    # et la bonne association est bien DÉTECTÉE (pas seulement 'ok_simple') sur le cas Saint-Paul
    assert ctl.association_secteur(R.charger("97415", "U2a").stationnement, "U2a") == "ok_associe"
    assert ctl.association_secteur(R.charger("97415", "U2c").stationnement, "U2c") == "ok_associe"


def test_destination_suit_le_type_de_projet():
    """La destination lue dans le barème suit le type de projet (plus de « collectif » codé en dur)."""
    assert DESTINATION_PAR_PROJET["collectif"] == "collectif"
    assert DESTINATION_PAR_PROJET["social"] == "social"
    assert DESTINATION_PAR_PROJET["senior"] == "senior"
    assert DESTINATION_PAR_PROJET["etudiante"] == "etudiant"
    b = _bareme({"par_typologie": {"statut": "valide", "article": "x", "page_pdf": 1,
                 "detail": [
                     {"destination": "collectif", "places": 1.5, "role": "base"},
                     {"destination": "social", "places": 1, "role": "base"}]}})
    # mêmes logements, destination « social » → ligne sociale (1/logt) ; « collectif » → 1,5/logt
    prog = _prog([(3, 70, 4)])
    assert b.exiger(prog, destination="social").places == 4
    assert b.exiger(prog, destination="collectif").places == 6
