"""O12 — DIVISION EN OR : détecteur conservateur. VALIDÉ (Vic, 28/07/2026) après 2 revues
visuelles exhaustives + verdict de calibrage PLU — EXPOSE=True, pool 35, 0 faux positif connu.

Faux positif = péché mortel : seuils conservateurs codés dans _DETECT ; exclusions de revue
PERMANENTES par IDU (config, INSEE vérifié) ; emprise du lot restant confrontée au plafond PLU
réel (dépendance récurrente o12_emprise_recheck.py).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import division_or as d


def test_expose_false_dormant():
    # M129-C (Vic 19/08/2026) : division_or SORT DU PRODUIT (dormant) — code/table/CLI restent.
    assert d.EXPOSE is False


def test_seuils_conservateurs_dans_detect():
    q = d._DETECT
    assert "BETWEEN {surface_min} AND {surface_max}" in q  # M129-C : seuils en CONFIG (seuils_geometrie.yaml)            # parcelle assez grande pour DEUX lots
    assert "BETWEEN {ratio_min} AND {ratio_max}" in q            # bâti présent mais ne remplit pas
    assert "free_m2 >= {lot_min}" in q and "surface_m2 - {reste_min}" in q   # les deux lots restent viables
    assert "rad >= {rayon_min}" in q                          # pas de lanière (largeur ~18 m)
    assert "facade_free >= {facade_min}" in q                 # accès voirie indépendant


def test_correctifs_o12_ile_dans_detect():
    """Revue O12-ÎLE (20 cartes Entre-Deux + Bras-Panon) — trois défauts corrigés."""
    q = d._DETECT
    # démembrement ≠ division : le lot ne peut pas emporter plus de la moitié de la parcelle
    assert "free_m2 <= surface_m2 * {lot_part_max}" in q
    # division URBAINE : zone dominante du LOT en U/AU ; A et N exclus ; RNU → PAU estimée exigée
    assert "zone = 'U' OR zone LIKE 'AU%'" in q
    assert "zone IS NULL AND ({pau_pred})" in q
    assert "plu_gpu_zone" in q
    # clarté : façade voirie PLAFONNÉE à 30 m (une façade de 465 m = bande linéaire, pas un top candidat)
    assert "LEAST(d.residuel_facade_m, 30)" in d._INSERT


def test_types_de_division_o12_ile_d():
    """O12-ÎLE D — le bâti dans le lot est CLASSÉ (libre / démolition), pas exclu."""
    q = d._DETECT
    # deux variantes : lot nu (tout le bâti retiré) / démolition (seul le PRINCIPAL retiré)
    assert "VALUES ('libre', bat.bgeom), ('demolition', princ.pgeom)" in q
    # le bâtiment principal = plus grande emprise au sol — jamais dans le lot par construction
    assert "ORDER BY id, a DESC" in q
    # garde anti-découpage inversé : bâti à démolir ≤ 1/3 du bâti total (≤ moitié du bâti conservé)
    assert "bati_lot_m2 * 3 <= bat_m2" in q
    # une parcelle qui passe en libre RESTE libre (dédoublonnage, libre prioritaire)
    assert "DISTINCT ON (idu)" in q and "(variante = 'demolition')" in q
    # mono-bâtiment : variante démolition sautée (identique à libre)
    assert "v.variante = 'demolition' AND bat.nb_bat = 1" in q
    # divisions libres prioritaires au tri du dossier de revue
    import inspect
    assert "(type_division = 'demolition'), clarte DESC" in inspect.getsource(d.top_candidates)


def test_correctifs_revue_2_3_4():
    """Revue O12-ÎLE, 2e itération : bâti d'activité, compacité, littoral/domaine public."""
    q = d._DETECT
    # (2) critère ensemble_bati RÉUTILISÉ de la cascade (mêmes constantes que bati.py),
    #     comptage fidèle à stats_batch (intersection ≥ 10 m²)
    from labuse.bati import ENSEMBLE_MIN_BATIMENTS, GRAND_BATIMENT_M2
    assert "nb_bat < {ens_min_bat} AND bat.max_bat_m2 < {grand_bat_m2}" in q
    assert "count(*) FILTER (WHERE a >= 10) AS nb_bat" in q
    assert (ENSEMBLE_MIN_BATIMENTS, int(GRAND_BATIMENT_M2)) == (3, 400)
    # (3) compacité Polsby-Popper du lot, seuil en constante documentée
    assert "4 * pi() * free_m2 / power(ST_Perimeter(free_geom), 2) >= {compacite_min}" in q
    assert d.COMPACITE_MIN == 0.25
    # (4) littoral et domaine public non acquérable : 50 pas, forêt domaniale, cœur du Parc,
    #     et CONTACT du trait de côte (trou de couverture du corridor 50 pas au Barachois)
    for kind in ("cinquante_pas", "foret_publique", "parc_national", "trait_de_cote"):
        assert kind in q


def test_viabilite_lot_restant():
    """Revue O12-ÎLE, 4e itération : la division ne doit pas rendre la parcelle du
    PROPRIÉTAIRE non conforme — emprise bâtie du lot restant plafonnée."""
    q = d._DETECT
    assert "(bat_m2 - bati_lot_m2) / NULLIF(surface_m2 - free_m2, 0) <= ({emprise_max})" in q
    assert d.EMPRISE_RESTANTE_MAX == 0.60          # plancher prudent hors zone calibrée
    # PLU calibré : le plafond de zone prime (CASE sur zone_lib) ; sans yaml → plancher seul
    assert d._emprise_max_sql("Commune-Sans-Plu") == "0.6"
    case_sd = d._emprise_max_sql("Saint-Denis")    # 20 zones chiffrées dans plu_saint_denis.yaml
    assert case_sd.startswith("CASE zone_lib WHEN ") and case_sd.endswith("ELSE 0.6 END")
    assert "WHEN 'Ud' THEN 0.80" in case_sd and "WHEN 'Uh' THEN 0.30" in case_sd


def test_metrique_bati_invalidee_pas_filtrante():
    # la métrique façade du lot bâti est NULL (invalidée — finding), jamais un filtre sur un chiffre faux
    assert "NULL::numeric AS bati_facade_m" in d._DETECT
    assert "(facade_parcelle - facade_free) >= 5" not in d._DETECT


def test_lot_decoupe_o12_partiel():
    """O12-PARTIEL : lot DÉCOUPÉ (bande de façade) — aucun critère validé assoupli."""
    q = d._DETECT_PARTIEL
    # univers : écartées par le SEUL ratio > 50 % ; filtres parcelle inchangés (surface, bâti, activité)
    assert "ST_Area(lg.geom) > c.surface_m2 * 0.5" in q
    assert "BETWEEN {surface_min} AND {surface_max}" in q  # M129-C : seuils en CONFIG (seuils_geometrie.yaml) and "BETWEEN 0.08 AND 0.45" in q
    assert "nb_bat < {ens_min_bat} AND bat.max_bat_m2 < {grand_bat_m2}" in q
    # bande ancrée sur le plus long segment CONTIGU de façade (LineMerge), bouts droits
    assert "ST_LineMerge" in q and "endcap=flat" in q and "ST_LineSubstring" in q
    # cible 600-900 m², compacité ≥ 0.28 (plancher OBSERVÉ du pool validé), cercle ≥ 9 m
    assert (d.LOT_DECOUPE_MIN_M2, d.LOT_DECOUPE_MAX_M2) == (600, 900)
    assert d.COMPACITE_MIN_DECOUPE >= d.COMPACITE_MIN     # 0.28 à l'origine, relevé en revue 2
    assert "BETWEEN {lot_min} AND {lot_max}" in q and ">= {compacite_min_dec}" in q
    assert ".radius >= 9" in q
    # façade du LOT revérifiée (contiguë ≥ 12), zonage, littoral, emprise restante : mêmes gardes
    assert "facade_lot >= 12" in q
    # ANTI-ENCLAVEMENT : le lot RESTANT garde ≥ 12 m de façade contiguë, mesurée DIRECTEMENT
    # sur sa géométrie (jamais par soustraction de longueurs — finding O12) ; parcelle
    # traversante acceptée naturellement (mesure contre toutes les voiries)
    assert "facade_reste >= 12" in q
    assert "ST_Difference(c.geom_2975, c.lot_geom)" in q
    assert "zone = 'U' OR zone LIKE 'AU%'" in q and "{pau_pred}" in q and "{emprise_max}" in q
    for kind in ("cinquante_pas", "foret_publique", "parc_national", "trait_de_cote"):
        assert kind in q
    # famille DISTINCTE, jamais fusionnée : type 'decoupe', géométrie du lot STOCKÉE
    assert "'decoupe' AS type_division" in q and "lot_geom" in d._INSERT_PARTIEL


def test_correctifs_o12_partiel_2():
    """Mandat O12-PARTIEL-2 (NO-GO de revue) : connexité, lot nu strict, zonage activité,
    voirie qualifiée en RNU, gain estimé retiré des fiches."""
    q = d._DETECT_PARTIEL
    # C2 : le reste D'UN SEUL TENANT — composantes > 1 m² (tolérance anti-slivers cadastraux)
    assert "nb_reste = 1" in q and "WHERE ST_Area(g.geom) > 1) AS nb_reste" in q
    # C3 : lot NU strict — bâti ∩ lot ≤ 1 m², mesuré contre TOUS les bâtiments (voisins compris)
    assert "aire_bati_dans_lot_m2 <= 1" in q
    assert "aire_bati_dans_lot_m2" in d._INSERT_PARTIEL      # rendu dans la table → CSV
    # C4 : zonages exclus, liste en CONFIG (jamais devinée) + motifs AU fermées (2AU*/3AU*)
    assert "({activite_pred})" in q
    # M-C (F6) : le prédicat passe désormais par des VALEURS LIÉES (:activite_libs / :activite_pats),
    # plus de littéraux concaténés. On teste (a) que le fragment utilise bien les binds, (b) que les
    # VALEURS (par commune + motifs) sont correctes côté source.
    p = d._activite_pred_sql("Petite-Île")
    assert ":activite_libs" in p and ":activite_pats" in p and "'" not in p
    libs_pi = d._zones_activite("Petite-Île")
    assert "UEa" in libs_pi and "UT" in libs_pi and "UZ" in libs_pi   # activité + arbitrés (touristique, ZAC)
    assert "^2AU" in d._activite_pats() and "^3AU" in d._activite_pats()
    assert "U1e" in d._zones_activite("Saint-Paul")            # PLU calibré : habitat interdit
    # C4-libellé (finding BP0363) : mots-clés d'activité dans le DESCRIPTIF, appliqué aux
    # DEUX familles ; descriptions mixtes habitat/proximité protégées
    for sql in (q, d._DETECT):
        assert "zone_descr ~* '{descr_re}'" in sql and "{descr_protege}" in sql
    assert "zone d.activit" in d.ACTIVITE_DESCR_RE and "proximit" in d.ACTIVITE_DESCR_PROTEGE_RE
    # C5 ÉTENDU (GO Vic) : façade sur voirie QUALIFIÉE PARTOUT (plus seulement RNU)
    assert "AND facade_lot_route >= 12" in q
    assert "'Route à 1 chaussée', 'Route à 2 chaussées', 'Rond-point'" in q
    # C2-érosion (GO Vic) : rétréci de 2 m (couloir < 4 m ≠ accès), composantes > 25 m²
    assert d.EROSION_RESTE_M == 2 and "nb_reste_erode <= 1" in q
    # C3.3 (GO Vic, option b) : lot à ≥ 1 m de TOUT bâti — cohérence géométrique, pas urbanisme
    assert d.DIST_BATI_MIN_M == 1 and "ST_DWithin(bd.geom_2975, zon.lot_geom, {dist_bati_min})" in q
    # C1 : plus de « Gain estimé » sur les fiches de revue
    import inspect

    from labuse.api import division_review
    src = inspect.getsource(division_review)
    assert "Gain estimé" not in src


def test_revue_2_solidite_et_gardes():
    """Revue 2 : branche 2 de la règle de décision + gardes validés (reste ≥ 400,
    fraîcheur Sitadel, exclusions de revue traçables)."""
    q = d._DETECT_PARTIEL
    # solidité (aire/enveloppe convexe) ≥ 0.85 — le seuil qui préserve TOUTES les validées ;
    # compacité relevée à 0.55 (branche 2)
    assert d.SOLIDITE_MIN_DECOUPE == 0.85 and d.COMPACITE_MIN_DECOUPE == 0.55
    assert "ST_Area(lot.geom) / ST_Area(ST_ConvexHull(lot.geom)) >= {solidite_min}" in q
    assert "solidite" in d._INSERT_PARTIEL
    # reste ≥ 400 m², aligné sur la famille résiduelle
    assert "ST_Area(lot.geom) <= f.surface_m2 - 400" in q
    # fraîcheur : PC Sitadel ≥ 2023-01-01 sur la parcelle → exclu (fenêtre justifiée au rapport)
    assert d.PC_FRAIS_DEPUIS == "2023-01-01" and "({pc_pred})" in q
    # exclusions de revue TRAÇABLES (config), appliquées aux DEUX familles — jamais silencieuses
    assert "({revue_pred})" in q and "({revue_pred})" in d._DETECT
    # revue 3 : exclusion PERMANENTE par IDU (liee_geometrie abandonnée — s'auto-annulait) ;
    # tous les IDU exclus sont dans le prédicat des DEUX familles, sans comparaison de tracé
    # M-C (F6) : exclusion par VALEUR LIÉE (:revue_idus) — plus de concaténation de littéraux.
    for fam in (d._revue_pred_sql(decoupe=True), d._revue_pred_sql(decoupe=False)):
        assert ":revue_idus" in fam and "'" not in fam
        assert "ST_SymDifference" not in fam and "snapshot" not in fam
    assert "97416000CX0214" in d._revue_idus() and "97411000AV0203" in d._revue_idus()


def test_exclusions_revue_idu_coherents():
    """VERROU de la revue 3 : chaque exclusion porte une commune connue dont l'INSEE est le
    préfixe de l'idu (interdit l'IDU-fantôme qui a laissé passer le U de Saint-Denis). Une
    parcelle exclue ne doit jamais reparaître : exclusion PERMANENTE par IDU + IDU vérifié."""
    assert d.check_exclusions_revue() == []                    # config actuelle cohérente
    # le vrai U de Saint-Denis (préfixe 97411, pas le fantôme 97416) est exclu, permanent
    assert "97411000AV0203" in d._revue_idus("permanente")
    assert "97416000AV0203" not in d._revue_idus()             # l'IDU-fantôme a disparu
    # revue 3 : TOUTES les exclusions sont permanentes (3 U + AV0573 + 4 FP + 2 douteux tranchés)
    perm = set(d._revue_idus("permanente"))
    assert d._revue_idus("liee_geometrie") == []
    assert {"97409000AT0650", "97422000CX0720", "97411000AV0203", "97422000AV0573",
            "97404000AX0324", "97415000CR0776", "97416000HX1065", "97418000AP3270",
            "97416000CX0214", "97415000CM0143", "97418000AO0805"} == perm
    # fail-safe : une entrée au préfixe INSEE faux est DÉTECTÉE (et serait écartée au chargement)
    faux_insee = d._insee_par_commune()["Saint-Denis"]
    assert "97416000AV0203"[:5] != faux_insee                  # 97416 ≠ 97411 : incohérent


def test_detect_indexe_par_nom_jamais_left_idu():
    """M50-SUITE-2 : le détecteur filtre parcels.commune (NOM, indexé ix_parcels_commune) et JAMAIS
    left(idu,5) — expression non indexable (btree idu sous collation ≠ C) qui forçait un Parallel Seq
    Scan de 431 k lignes à chaque commune (~3 min → île >1 h → interrompue → rien commité)."""
    for sql in (d._DETECT, d._DETECT_PARTIEL):
        assert "p.commune = :commune" in sql
        assert "left(p.idu" not in sql       # plus de prédicat non indexable dans le détecteur


@pytest.mark.db
def test_resolution_insee_vers_nom(db_session):
    """M50-SUITE-2 : l'entrée INSEE est résolue en NOM EN AMONT (réf commune_conso_enaf, O(1)),
    pas dans le SQL. Un nom (ou un code hors réf) passe tel quel."""
    s = db_session
    assert d._resolve_commune(s, "Saint-Paul") == "Saint-Paul"   # déjà un nom → inchangé
    assert d._resolve_commune(s, "ZZ") == "ZZ"                    # ni code ni nom connu → inchangé
    if s.execute(text("SELECT to_regclass('commune_conso_enaf')")).scalar() is not None:
        assert d._resolve_commune(s, "97415") == "Saint-Paul"    # code → nom exact de parcels.commune
        assert d._resolve_commune(s, "99999") == "99999"         # code hors réf → tel quel


@pytest.mark.db
def test_all_communes_liste_canonique(db_session):
    """M50-SUITE-2 : --all s'appuie sur all_communes() = la réf canonique de l'île, en NOMS (jamais
    des codes → chemin indexé), pour ne pouvoir en oublier aucune."""
    s = db_session
    noms = d.all_communes(s)
    if s.execute(text("SELECT to_regclass('commune_conso_enaf')")).scalar() is None:
        assert noms == []                                        # réf absente → l'appelant décide
        return
    assert len(noms) == 24                                       # l'île entière
    assert "Saint-Paul" in noms and "Le Port" in noms           # des NOMS, pas des codes INSEE
    assert all(isinstance(n, str) and not n.isdigit() for n in noms)


@pytest.mark.db
def test_purge_commune_avant_reecriture(db_session):
    """M50-SUITE : un rebuild par commune PURGE ses lignes avant réécriture (un rebuild à 0 laisse
    la commune VIDE, pas périmée) ; les tracés REVUS (note_revue) sont PRÉSERVÉS."""
    s = db_session
    d.build_divisions(s, ["Commune-Inexistante"], commit=False, log=lambda *_: None)  # crée la table
    s.execute(text(
        "INSERT INTO division_or_candidates (idu, commune, type_division, run_label, note_revue) VALUES "
        "('97499000ZZ0001','ZZPurge','libre','q_v7_defisc', NULL),"          # périmé non-revu → purgé
        "('97499000ZZ0002','ZZPurge','libre','q_v7_defisc','revu par Vic')," # REVU → préservé
        "('97499000ZZ0003','ZZPurge','decoupe','q_v7_defisc', NULL)"))       # découpe → hors build_divisions
    # rebuild résiduel de la commune (0 détecté en base de test) : la purge doit tourner
    d.build_divisions(s, ["ZZPurge"], commit=False, log=lambda *_: None)
    restant = {r[0]: r[1] for r in s.execute(text(
        "SELECT idu, type_division FROM division_or_candidates WHERE commune='ZZPurge'"))}
    assert "97499000ZZ0001" not in restant                 # périmé non-revu PURGÉ (commune vide, pas périmée)
    assert restant.get("97499000ZZ0002") == "libre"        # REVU préservé
    assert restant.get("97499000ZZ0003") == "decoupe"      # découpe intacte (autre path)


@pytest.mark.db
def test_ile_resiliente_commune_qui_casse(monkeypatch):
    """M50-SUITE-2 : une commune qui CASSE en cours d'île est ISOLÉE (rollback de sa seule
    transaction) et l'île CONTINUE — les communes AVANT **et APRÈS** sont commitées et persistent
    (vérifié depuis une NOUVELLE connexion). Reproduit le cas réel (Vic : crash 'Les Avirons', île
    avortée alors qu'elle est en tête d'ordre INSEE). Commit=True + session_factory (écritures RÉELLES
    sur communes synthétiques, auto-nettoyées) car la fixture transactionnelle ne prouve pas le
    cross-connexion. La preuve que le commit-par-commune survit à un crash SUIVANT."""
    from labuse.db import session_factory, session_scope
    A, CRASH, C = "ZZ-RESIL-A", "ZZ-RESIL-CRASH", "ZZ-RESIL-C"      # A avant · CRASH casse · C après
    comm = {"a": A, "c": CRASH, "z": C}

    def _wipe():
        sc = session_factory()()
        sc.execute(text("DELETE FROM division_or_candidates WHERE commune IN (:a,:c,:z)"), comm)
        sc.commit(); sc.close()

    try:
        s0 = session_factory()()
        d.build_divisions(s0, ["ZZ-DDL"], commit=False, log=lambda *_: None)   # garantit la DDL
        s0.execute(text("DELETE FROM division_or_candidates WHERE commune IN (:a,:c,:z)"), comm)
        s0.execute(text(
            "INSERT INTO division_or_candidates (idu, commune, type_division, run_label, note_revue) VALUES "
            "('99990000ZR0001', :a, 'libre', 'q_v7_defisc', NULL),"    # A     → doit être PURGÉ+commité
            "('99990000ZR0002', :c, 'libre', 'q_v7_defisc', NULL),"    # CRASH → doit RESTER (rollback)
            "('99990000ZR0003', :z, 'libre', 'q_v7_defisc', NULL)"), comm)  # C → doit être PURGÉ+commité
        s0.commit(); s0.close()

        orig = d._emprise_max_sql
        def boom(commune):
            if commune == CRASH:
                raise RuntimeError("crash simulé en cours d'île")
            return orig(commune)
        monkeypatch.setattr(d, "_emprise_max_sql", boom)

        with session_scope() as s:                     # EXACTEMENT le chemin CLI ; ne DOIT PAS lever
            r = d.build_divisions(s, [A, CRASH, C], commit=True, log=lambda *_: None)
        assert r["failures"] == [CRASH]                # crash isolé ET rapporté (pas avalé en silence)

        s2 = session_factory()()                       # NOUVELLE connexion
        def cnt(name):
            return s2.execute(text("SELECT count(*) FROM division_or_candidates WHERE commune=:x"),
                              {"x": name}).scalar()
        a_rows, c_rows, z_rows = cnt(A), cnt(CRASH), cnt(C)
        s2.close()
        assert a_rows == 0     # A (avant le crash) : purge COMMITÉE, visible malgré le crash suivant
        assert c_rows == 1     # CRASH : purge ROLLBACKÉE, son périmé reste
        assert z_rows == 0     # C (après le crash) : l'île a CONTINUÉ → C purgée+commitée
    finally:
        _wipe()


def test_build_commune_vide_et_table_creee(db_session):
    s = db_session
    r = d.build_divisions(s, ["Commune-Inexistante"], commit=False, log=lambda *_: None)
    assert r["total"] == 0 and r["expose"] is False    # M129-C : dormant
    # la table existe (DDL passé), vide
    assert s.execute(text("SELECT count(*) FROM division_or_candidates")).scalar() == 0
    assert d.top_candidates(s, limit=5) == []
    # le détecteur PARTIEL tourne sur le même socle (SQL valide, 0 candidat)
    r2 = d.build_divisions_partiel(s, ["Commune-Inexistante"], commit=False, log=lambda *_: None)
    assert r2["total"] == 0 and r2["expose"] is False    # M129-C : dormant
    # snapshot des tracés revus + revue exhaustive : SQL valides sur table vide (0 ligne)
    assert d.snapshot_review_lots(s, commit=False) == 0
    assert d.all_candidates_for_review(s) == []


@pytest.mark.db
def test_aucun_candidat_hors_des_35_revus(db_session):
    """Invariant de clôture O12 (exposition 28/07/2026) : TOUT candidat présent en table est
    dans le pool VERSIONNÉ des 35 revus (reports/o12-ile/pool_complet.csv) — un re-run du
    détecteur qui ferait entrer un candidat non revu casse ici (base vide : trivialement vrai,
    l'invariant s'applique partout où la table est peuplée, base servie comprise)."""
    import csv
    from pathlib import Path
    ref = Path(__file__).resolve().parent.parent / "reports" / "o12-ile" / "pool_complet.csv"
    with open(ref, encoding="utf-8") as fh:
        revus = {r["idu"] for r in csv.DictReader(fh)}
    assert len(revus) == 35
    if db_session.execute(text("SELECT to_regclass('division_or_candidates')")).scalar() is None:
        return   # table absente = rien de servi : invariant trivialement tenu
    servis = {r[0] for r in db_session.execute(text("SELECT idu FROM division_or_candidates"))}
    hors = servis - revus
    assert not hors, f"candidat(s) servi(s) HORS des 35 revus : {sorted(hors)}"
