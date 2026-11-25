"""OUTIL-PLU-FIX-8 — LOT 0 : FILET DE NON-RÉGRESSION de l'outil PLU.

Un test par CAS cité dans les relectures 1 à 6 et les deux rapports externes (01-PLU-ASTRA / -2).
Chaque test affirme une VALEUR PRÉCISE (texte, zone, article, page) servie par l'API réelle
(`search_reglement` / `count_reglement` / `plu_annuaire_communes`), pas une propriété vague.

Les sept tours précédents ont chacun recassé un cas du tour d'avant. Ce fichier est le garde-fou :
il DOIT rester vert à chaque réingestion. Il lit le CORPUS réellement servi (base `labuse` réingérée),
pas la base de test vide — DSN via `LABUSE_PLU_CORPUS_DSN` (défaut : openclaw@localhost/labuse). Si le
corpus est injoignable ou vide, les tests sont SKIPPÉS (jamais un faux vert).

Repère historique : écrit AVANT le correctif LOT 1, le test `test_u2e_article13_*` ÉCHOUE sur la base
FIX-7 (l'article 13 y est un moignon p.99 sans le seuil 20 %, détaché dans un extrait « Définition »
sans zone). S'il passe sur FIX-7, c'est que le test est faux.
"""
from __future__ import annotations

import os
import re

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from labuse.ingestion import plu_ingest as P

# Ces tests lisent le CORPUS RÉEL servi (base `labuse` réingérée) : famille `reel`, hors CI (base vide)
# et hors filet « unitaire sans base » du pre-push — rejoués à la main / au banc de nuit (cf. pyproject).
pytestmark = pytest.mark.reel

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")


@pytest.fixture(scope="module")
def sess():
    try:
        eng = create_engine(_DSN)
        s = sessionmaker(bind=eng)()
        n = s.execute(text("SELECT count(*) FROM plu_reglement_extrait")).scalar()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"corpus PLU injoignable ({_DSN}) : {e}")
    if not n or n < 2000:
        pytest.skip(f"corpus PLU vide/partiel ({n}) — réingérer avant de lancer le filet")
    yield s
    s.close()


def _refs(rows):
    return [(r["article_ref"], r["zone"], r.get("page_match") or r.get("page_debut")) for r in rows]


# ─────────────────────────── LOT 1 — U2e article 13 (le cas-phare) ───────────────────────────

def test_u2e_article13_entier_avec_seuil_20pct(sess):
    """RELECTURE-6 §A.4 / 01-PLU-ASTRA-2 §3-4 p.100 : l'article 13 de Saint-Paul U2e est ENTIER sous le
    filtre U2e et contient le seuil « 20 % » d'espaces libres perméables (p.99-100). Sur FIX-7 il était
    un moignon p.99 (143 car.) sans le 20 %, le corps étant détaché en « Définition » SANS zone."""
    rows = P.search_reglement(sess, "espaces libres perméables", insee="97415", zone="U2e",
                              terms=["espaces", "libres", "perméables"], limit=50)
    a13 = [r for r in rows if (r["article_ref"] or "").startswith("Article 13") and r["zone"] == "U2E"]
    assert a13, "aucun 'Article 13-' servi en zone U2E"
    e = a13[0]
    txt = e["texte_verbatim"] or ""
    assert ("20 %" in txt or "20%" in txt), "le seuil 20 % n'est pas dans l'article 13 U2E"
    assert "perméables" in txt and "Perméabilité" in txt, "le corps 'Perméabilité' manque (article tronqué)"
    assert len(txt) > 2000, f"article 13 U2E trop court ({len(txt)} car.) — probablement un moignon"
    assert e["page_debut"] <= 99 <= e["page_fin"] and e["page_fin"] >= 100


def test_u2e_article13_pas_de_moignon_definition_sans_zone(sess):
    """Corollaire : plus aucun extrait « Définition » zone NULL à Saint-Paul (les ex-moignons détachés
    des articles 13 des zones U1/U2e/U3e/AU5e sont réintégrés)."""
    n = sess.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97415' "
                          "AND article_ref ILIKE 'Défin%' AND zone IS NULL")).scalar()
    assert n == 0, f"{n} extrait(s) 'Définition' zone NULL subsistent à Saint-Paul"


def test_u2e_article13_famille_toutes_zones_portent_le_20pct(sess):
    """La même sous-découpe tronquait l'article 13 de 4 zones (U1, U2E, U3E, AU5E) : chacune doit de
    nouveau porter le 20 %."""
    zones = sess.execute(text("SELECT DISTINCT zone FROM plu_reglement_extrait WHERE insee='97415' "
                              "AND article_ref='Article 13-' AND (texte_verbatim ~ '20 ?%') "
                              "AND zone = ANY(ARRAY['U1','U2E','U3E','AU5E'])")).scalars().all()
    assert set(zones) == {"U1", "U2E", "U3E", "AU5E"}, f"zones portant le 20 % : {sorted(zones)}"


def test_u2e_article6_reste_entier(sess):
    """RELECTURE-6 cas 6 / 01-PLU-ASTRA-2 : l'article 6 U2e reste entier (6.3 + saillies) p.91-92."""
    rows = P.search_reglement(sess, "saillie", insee="97415", zone="U2e", terms=["saillie"], limit=50)
    a6 = [r for r in rows if (r["article_ref"] or "").startswith("Article 6") and r["zone"] == "U2E"]
    assert a6, "article 6 U2E absent"
    txt = a6[0]["texte_verbatim"] or ""
    assert "6.3" in txt and "saillie" in txt.lower()


# ─────────────────────────── LOT 2 — doublons ───────────────────────────

def test_zero_doublon_octet_meme_zone(sess):
    """RELECTURE-6 §3 : 0 doublon octet-pour-octet (à blancs normalisés) sous une même (insee,doc,zone).
    Les textes DISTINCTS partageant une (réf,zone) — règles de bassins différents — sont légitimes."""
    rows = sess.execute(text("SELECT insee,document,zone,"
                             "md5(regexp_replace(texte_verbatim,'\\s+',' ','g')) h "
                             "FROM plu_reglement_extrait")).all()
    from collections import Counter
    c = Counter((r.insee, r.document, r.zone, r.h) for r in rows)
    extra = sum(v - 1 for v in c.values() if v > 1)
    assert extra == 0, f"{extra} doublon(s) octet-pour-octet (même zone) subsistent"


def test_saintpaul_hauteur_pas_de_doublon_identique(sess):
    """RELECTURE-6 §3 : sous « hauteur » à Saint-Paul, aucun couple (réf,zone) ne contient 2 extraits de
    TEXTE identique (les répétitions restantes sont des bassins de vie distincts)."""
    rows = sess.execute(text(
        "SELECT article_ref, zone, count(*) c, "
        "count(DISTINCT md5(regexp_replace(texte_verbatim,'\\s+',' ','g'))) d "
        "FROM plu_reglement_extrait WHERE insee='97415' "
        "AND tsv @@ websearch_to_tsquery('fr_unaccent','hauteur') GROUP BY 1,2 HAVING count(*)>1")).all()
    identiques = [(r.article_ref, r.zone, r.c, r.d) for r in rows if r.c != r.d]
    assert not identiques, f"doublons identiques servis sous hauteur : {identiques}"


# ─────────────────────────── LOT 3 — zones joignables ───────────────────────────

def test_le_port_2AU_article_aspect_servi(sess):
    """RELECTURE-6 §5 : Le Port — « Article 2AU 9 — Aspect extérieur » p.159 servi sous le filtre 2AU."""
    rows = P.search_reglement(sess, "aspect", insee="97407", zone="2AU", terms=["aspect"], limit=20)
    a2au = [r for r in rows if r["zone"] == "2AU"]
    assert a2au, "aucun article de zone 2AU servi"
    assert any(159 in (r.get("pages_match") or []) or r.get("page_match") == 159 for r in a2au), \
        "l'article 2AU p.159 (Aspect extérieur) n'est pas servi"


def test_le_port_1AU_2AU_ont_des_articles_propres(sess):
    """RELECTURE-7 §1 (durci) : Le Port 1AU et 2AU portent chacune EXACTEMENT 15 articles propres."""
    for z in ("1AU", "2AU"):
        n = sess.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97407' AND zone=:z"),
                         {"z": z}).scalar()
        assert n == 15, f"zone {z} : {n} articles propres (attendu exactement 15)"


def test_preambule_saint_pierre_ucv_rattache(sess):
    """RELECTURE-6 §6 : le préambule « La zone Ucv correspond au centre-ville » (Saint-Pierre p.59) porte
    la zone UCV (était NULL, injoignable au filtre Ucv)."""
    rows = P.search_reglement(sess, "centre-ville", insee="97416", zone="Ucv", terms=["centre-ville"], limit=20)
    pre = [r for r in rows if r["zone"] == "UCV" and "Ucv correspond" in (r["texte_verbatim"] or "")]
    assert pre, "préambule Ucv non rattaché à la zone UCV"


def test_preambules_zones_reattaches_count(sess):
    """RELECTURE-7 §1 (durci — n'était plus tautologique) : chaque zone de Saint-Pierre porte EXACTEMENT
    UN préambule (extrait dont le texte commence par « Préambule » ET nomme « La/Les zone(s) <x> ») — le
    test échouerait si un préambule n'était pas rattaché (zone NULL), pas seulement si la zone existe."""
    attendu = {"UCV": "Ucv", "UD": "Ud", "UG": "Ug", "UF": "Uf", "US": "Us", "UP": "Up", "UT": "Ut"}
    for zone, lbl in attendu.items():
        rows = sess.execute(text(
            "SELECT texte_verbatim FROM plu_reglement_extrait WHERE insee='97416' AND zone=:z "
            "AND texte_verbatim ~* '^\\s*Pr.ambule'"), {"z": zone}).scalars().all()
        assert len(rows) == 1, f"zone {zone} : {len(rows)} préambule(s) rattaché(s) (attendu 1)"
        assert re.search(rf"(?i)\b(?:la|les)\s+zones?\s+{lbl}\b", rows[0]), \
            f"le préambule de {zone} ne définit pas « la zone {lbl} »"


def test_couverture_plan_zonage_liste_nominative(sess):
    """RELECTURE-7 §4 (durci) : sur les 21 communes, CHAQUE zone du plan de zonage a ≥1 résultat sous son
    filtre. On affirme la LISTE NOMINATIVE des zones injoignables (et non « ≤ 4 ») : après FIX-9
    (Sainte-Rose 1AUto→AUTO ; Bras-Panon/Trois-Bassins AUt→Ua/Ub ; Le Tampon AUto→Ucto par renvoi texte),
    elle doit être VIDE. Un nouveau trou ferait échouer le test en le NOMMANT."""
    import pathlib

    import yaml
    mil = yaml.safe_load((pathlib.Path(__file__).resolve().parents[1] / "config" / "plu_millesimes.yaml")
                         .read_text())["communes"]
    servables = {k for k, v in mil.items() if v.get("statut") in ("a_jour", "annule_partiel")}
    rows = sess.execute(text("SELECT right(attrs->>'partition',5) insee, attrs->>'libelle' lib "
                             "FROM spatial_layers WHERE kind='plu_gpu_zone' "
                             "AND attrs->>'partition' LIKE 'DU_%' GROUP BY 1,2")).all()
    from collections import defaultdict
    zbyc = defaultdict(set)
    for r in rows:
        if r.insee in servables and r.lib:
            zbyc[r.insee].add(r.lib)
    zeros = sorted((i, z) for i in zbyc for z in zbyc[i] if not P.zones_apparentees(sess, z, i))
    assert zeros == [], f"zones du plan injoignables (devrait être vide) : {zeros}"


def test_renvoi_generique_AUa_vers_U(sess):
    """LOT 3 : une zone AU sans chapitre propre ouvre le règlement de la zone U de même indice."""
    note = P.zone_renvoi_note("AUa", "97401", sess)
    assert note and "zone Ua" in note and "urbaniser" in note.lower()
    assert P.zones_apparentees(sess, "AUa", "97401"), "AUa ne sert aucune zone (renvoi U cassé)"


def test_sainte_rose_1AUto_relie_au_chapitre_AUTO(sess):
    """FIX-9 (point 1) : Sainte-Rose 1AUto (plan) est relié au chapitre « AUTO » du règlement (phasage) —
    la règle existait en base mais était injoignable. On sert bien les articles AUTO (≥10, p.58-63)."""
    assert P.zones_apparentees(sess, "1AUto", "97419") == ["AUTO"], \
        f"1AUto mal relié : {P.zones_apparentees(sess, '1AUto', '97419')}"
    n = sess.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97419' AND zone='AUTO'")).scalar()
    assert n >= 10, f"chapitre AUTO absent ({n} extraits)"
    rows = P.search_reglement(sess, "hauteur", insee="97419", zone="1AUto", terms=["hauteur"], limit=10)
    assert any(r["zone"] == "AUTO" for r in rows), "le filtre 1AUto ne sert pas le chapitre AUTO"


def test_les_3_autres_AU_renvoient_par_le_texte(sess):
    """FIX-9 (point 1) : les 3 autres zones ex-« introuvables » ne sont PAS des trous — leur règlement
    renvoie DANS LE TEXTE à une zone U servie (vérifié PDF : Bras-Panon AUt→Ua p.80, Trois-Bassins
    AUt→Ub p.66-70, Le Tampon AUto→Ucto p.86-89). Chacune doit donc servir des articles sous son filtre."""
    cas = [("97402", "1AUt", "UA"), ("97423", "1AUt", "UB"), ("97422", "1AUto", "UC")]
    for insee, plan, attendu in cas:
        app = P.zones_apparentees(sess, plan, insee)
        assert attendu in app, f"{insee} {plan} : apparentées={app}, attendu ⊇ {{{attendu}}}"
        assert P.count_reglement(sess, "hauteur", insee=insee, zone=plan, terms=["hauteur"]) > 0, \
            f"{insee} {plan} ne sert aucun article de hauteur"


def test_le_tampon_pas_de_lignes_doublees(sess):
    """FIX-9 (point 3) : l'artefact d'extraction « fausse graisse » (ligne de titre dessinée 2×) est
    corrigé — AUCUN extrait du Tampon ne contient 2 lignes NON VIDES identiques consécutives (était 521
    lignes sur 116 pages). Témoin : « 10.3 - Règle particulière… » n'apparaît qu'UNE fois dans Uc10."""
    rows = sess.execute(text("SELECT texte_verbatim FROM plu_reglement_extrait WHERE insee='97422'")).scalars().all()
    doubles = 0
    for t in rows:
        lignes = [re.sub(r"\s+", " ", x).strip() for x in (t or "").splitlines()]
        for i in range(1, len(lignes)):
            if lignes[i] and lignes[i] == lignes[i - 1] and len(lignes[i]) > 3:
                doubles += 1
    assert doubles == 0, f"{doubles} ligne(s) doublée(s) consécutive(s) subsistent au Tampon"
    # témoin de la relecture-7 §6 : l'article Uc10 ne double plus son intertitre « 10.3 - Règle particulière »
    uc10 = sess.execute(text("SELECT texte_verbatim FROM plu_reglement_extrait WHERE insee='97422' "
                             "AND zone='UC' AND article_ref ILIKE '%Uc10%' "
                             "AND texte_verbatim ILIKE '%10.3 - Règle particulière%'")).scalars().all()
    assert uc10, "article Uc10 (10.3) introuvable"
    assert all(t.count("10.3 - Règle particulière") == 1 for t in uc10), "le titre 10.3 est encore doublé dans Uc10"


def test_saint_paul_hauteur_sans_filtre_regroupe_les_identiques(sess):
    """FIX-9 (point 4) : « hauteur » à Saint-Paul SANS filtre regroupe les extraits au texte identique
    servis sous des zones AU*ST différentes en UN extrait portant la liste des zones (zones_concernees),
    sans retirer la règle d'aucune zone (le filtre AU3st la ressert seule)."""
    from labuse.api.modules import plu_annuaire_search
    r = plu_annuaire_search(q="hauteur", insee="97415", zone=None, limit=200, offset=0, db=sess)
    # 0 texte strictement identique répété dans la liste affichée
    norm = [re.sub(r"\s+", " ", (x.get("texte_verbatim") or "")).strip() for x in r["resultats"]]
    from collections import Counter
    rep = sum(v - 1 for v in Counter(norm).values() if v > 1)
    assert rep == 0, f"{rep} extrait(s) identique(s) encore répété(s) à l'affichage"
    # le groupe « Article 10- » porte bien les 5 secteurs AU*ST
    g = [x for x in r["resultats"] if set(["AU1", "AU3ST", "AU4ST", "AU5ST", "AU6ST"]).issubset(set(x.get("zones_concernees") or []))]
    assert g, "les 5 zones AU*ST ne sont pas regroupées sur un seul extrait"
    # la règle reste servable pour une zone précise
    rf = plu_annuaire_search(q="hauteur", insee="97415", zone="AU3st", limit=25, offset=0, db=sess)
    assert any(x["zone"] == "AU3ST" for x in rf["resultats"]), "AU3st ne sert plus sa règle"


# ─────────────────────── Non-régression relectures 1-6 + rapports externes ───────────────────────

def test_renvoi_AU3c_vers_U3c(sess):
    """RELECTURE-5 point 1 / 01-PLU-ASTRA §6 : AU3c (Saint-Paul) renvoie à U3c, sert l'Article 10 U3 p.114."""
    assert P.zone_renvoi_note("AU3c", "97415", sess) == "AU3c : le règlement renvoie à U3c"
    rows = P.search_reglement(sess, "hauteur", insee="97415", zone="AU3c", terms=["hauteur"], limit=25)
    zoned = [r for r in rows if r["zone"]]
    assert zoned and all(r["zone"] in ("U3", "AU3") for r in zoned), \
        f"AU3c sert des zones inattendues : {sorted({r['zone'] for r in zoned})}"
    assert any((r["article_ref"] or "").startswith("Article 10") for r in zoned)


def test_renvoi_2AUd_vers_Ud(sess):
    """RELECTURE-5 point 1 / 01-PLU-ASTRA §6 : 2AUd (Le Tampon) renvoie à Ud, sert l'ARTICLE Ud10."""
    assert P.zone_renvoi_note("2AUd", "97422", sess) == "2AUd : le règlement renvoie à Ud"
    rows = P.search_reglement(sess, "hauteur", insee="97422", zone="2AUd", terms=["hauteur"], limit=25)
    zoned = [r for r in rows if r["zone"]]
    assert zoned and all(r["zone"] == "UD" for r in zoned)


def test_A_ne_ramene_pas_AU(sess):
    """RELECTURE-6 cas 4 : à La Possession, le filtre A ne ramène QUE A (jamais AU)."""
    rows = P.search_reglement(sess, "construction", insee="97408", zone="A", terms=["construction"], limit=50)
    zones = {r["zone"] for r in rows if r["zone"]}
    assert zones <= {"A"}, f"le filtre A ramène aussi {zones - {'A'}}"


def test_piscine_saint_denis_page_22(sess):
    """RELECTURE-6 cas 5 / 01-PLU-ASTRA §3 : « piscine » à Saint-Denis sert « AMÉNAGEMENTS EXTÉRIEURS »
    à la page 22 (plus « Ordures ménagères »)."""
    rows = P.search_reglement(sess, "piscine", insee="97411", terms=["piscine"], limit=50)
    p22 = [r for r in rows if 22 in (r.get("pages_match") or []) or r.get("page_match") == 22]
    assert p22, "aucun extrait piscine servi en page 22"
    assert any("AMÉNAGEMENTS EXTÉRIEURS" in (r["texte_verbatim"] or "").upper() for r in rows)


def test_UBc_possession_cite_UB10(sess):
    """RELECTURE-6 cas 8 : à La Possession, « hauteur » en UBc cite l'ARTICLE UB 10 (pas UB 9)."""
    rows = P.search_reglement(sess, "hauteur", insee="97408", zone="UBc", terms=["hauteur"], limit=25)
    zoned = [r for r in rows if r["zone"]]
    assert zoned, "UBc ne sert aucun article de zone"
    assert any("UB 10" in (r["article_ref"] or "") for r in zoned), \
        f"UB 10 absent ; refs={[r['article_ref'] for r in zoned][:5]}"


def test_casse_accents_cloture_saint_paul(sess):
    """RELECTURE-6 cas 9 : clôture = CLÔTURE = cloture = clotures (même total) à Saint-Paul."""
    vals = {f: P.count_reglement(sess, f, insee="97415", terms=[f])
            for f in ("clôture", "CLÔTURE", "cloture", "clotures")}
    assert len(set(vals.values())) == 1 and next(iter(vals.values())) > 0, f"comptes divergents : {vals}"


def test_emprise_au_sol_guillemets_vs_sans(sess):
    """RELECTURE-6 cas 10 : "emprise au sol" (expression) < emprise au sol (mots) à Saint-Paul."""
    expr = P.count_reglement(sess, '"emprise au sol"', insee="97415", terms=["emprise", "au", "sol"])
    mots = P.count_reglement(sess, "emprise au sol", insee="97415", terms=["emprise", "au", "sol"])
    assert 0 < expr < mots, f"expression={expr} mots={mots} (l'expression doit être plus restrictive)"


def test_pagination_offset_sans_chevauchement(sess):
    """RELECTURE-6 cas 11 : pagination offset 0 vs 25 (Saint-Paul hauteur) — 0 chevauchement."""
    p0 = P.search_reglement(sess, "hauteur", insee="97415", offset=0, limit=25, terms=["hauteur"])
    p1 = P.search_reglement(sess, "hauteur", insee="97415", offset=25, limit=25, terms=["hauteur"])

    def key(r):
        return (r["zone"], r["article_ref"], r["page_debut"], len(r["texte_verbatim"] or ""))
    k0, k1 = {key(r) for r in p0}, {key(r) for r in p1}
    assert len(p0) == 25, "première page incomplète"
    assert not (k0 & k1), f"chevauchement entre offset 0 et 25 : {k0 & k1}"


def test_dedup_possession_un_seul_idurba(sess):
    """RELECTURE-6 cas 12 : La Possession — un seul idurba servi (doublons clos)."""
    n = sess.execute(text("SELECT count(DISTINCT idurba) FROM plu_reglement_extrait WHERE insee='97408'")).scalar()
    assert n == 1, f"{n} idurba distincts à La Possession"


def test_beauvallon_AUp_joignable(sess):
    """RELECTURE-6 cas 13 : la fiche Beauvallon (Saint-Benoît) est servie sous le filtre AUp (zone AUP)."""
    app = P.zones_apparentees(sess, "AUp", "97410")
    assert "AUP" in app, f"AUp injoignable ; apparentées={app}"
    rows = P.search_reglement(sess, "Beauvallon", insee="97410", zone="AUp", terms=["Beauvallon"], limit=20)
    assert any(r["zone"] == "AUP" for r in rows), "fiche Beauvallon non servie sous AUp"


def test_stecal_saint_benoit_NTA_NTB(sess):
    """RELECTURE-6 cas 14 : les STECAL NTA et NTB de Saint-Benoît sont servis par leur zone."""
    for z in ("NTA", "NTB"):
        n = sess.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97410' AND zone=:z"),
                         {"z": z}).scalar()
        assert n >= 1, f"zone {z} absente (STECAL non servi)"


def test_annexe_NS_NTA_NTB_reste_commune(sess):
    """RELECTURE-6 §A.1 / FIX-7 : le bloc « ANNEXES RELATIVES AUX ZONES NS, NTA ET NTB » (nomme 3 zones)
    reste COMMUN (zone NULL) — il ne doit pas être attribué à NS."""
    rows = sess.execute(text("SELECT zone FROM plu_reglement_extrait WHERE insee='97410' "
                             "AND article_ref ILIKE '%ANNEXES RELATIVES AUX ZONES NS%'")).all()
    assert rows, "bloc annexes NS/NTA/NTB introuvable"
    assert all(r.zone is None for r in rows), f"bloc multi-zone attribué à tort : {[r.zone for r in rows]}"


def test_entre_deux_48_articles_separes(sess):
    """RELECTURE-7 §1 (durci) : Entre-Deux garde EXACTEMENT 48 en-têtes d'article distincts."""
    refs = sess.execute(text("SELECT article_ref FROM plu_reglement_extrait WHERE insee='97403' "
                             "AND article_ref ~* '^article'")).scalars().all()
    assert len(set(refs)) == 48, f"{len(set(refs))} en-têtes d'article distincts à Entre-Deux (attendu 48)"


def test_refs_de_prose_zero(sess):
    """RELECTURE-6 §A.4 : 0 référence « de prose » (phrase prise pour un en-tête d'article)."""
    # motifs EXACTS relevés aux relectures 4-5 (fragments de phrase en minuscules, pas des titres CAPS) :
    # « annexe). Cette disposition ne concerne pas… », « …titre V du présent règlement. »
    rows = sess.execute(text(
        "SELECT insee, article_ref FROM plu_reglement_extrait WHERE "
        "article_ref ~ 'Cette disposition' OR article_ref ~ 'annexe\\)' "
        "OR article_ref ~* 'ne concerne pas les construction' "
        "OR article_ref ~ '[a-zà-ÿ]{3,} du présent règlement\\.'")).all()
    assert not rows, f"références de prose subsistent : {[(r.insee, r.article_ref) for r in rows]}"


def test_famille_stationn_stationner_egale_stationnement(sess):
    """RELECTURE-6 §A.2 : la famille « stationn… » — stationner == stationnement (même total), sans rouvrir
    les « station » d'épuration/mesure."""
    for insee in ("97411", "97422", "97415", "97408"):
        a = P.count_reglement(sess, "stationner", insee=insee, terms=["stationner"])
        b = P.count_reglement(sess, "stationnement", insee=insee, terms=["stationnement"])
        assert a == b, f"{insee}: stationner={a} ≠ stationnement={b}"


def test_station_nue_collisionne_encore_mais_famille_propre(sess):
    """RELECTURE-6 §7 : la requête CANONIQUE (stationnement) est propre ; on vérifie qu'elle ne cite PAS les
    pages de « station d'épuration » de Saint-Denis (p.136/146)."""
    rows = P.search_reglement(sess, "stationnement", insee="97411", terms=["stationnement"], limit=100)
    pages = {p for r in rows for p in (r.get("pages_match") or [])}
    assert not ({136, 146} & pages), f"pages de fausses stations citées : {({136, 146} & pages)}"


def test_barèmes_stationnement_articles_servis(sess):
    """RELECTURE-6 §A.2 : les barèmes de stationnement citent le bon article/page. On vérifie les 3 témoins
    imposés : Saint-Louis UA 12 (p.22-24), Saint-Pierre Ud6 (p.93), Le Tampon Ud12 (p.67)."""
    cas = [("97414", "UA", "UA 12", 22, 24), ("97416", "Ud", "Ud6", 93, 95), ("97422", "Ud", "Ud12", 66, 68)]
    for insee, zone, art, p1, p2 in cas:
        rows = P.search_reglement(sess, "stationnement", insee=insee, zone=zone, terms=["stationnement"], limit=30)
        ok = [r for r in rows if art.lower().replace(" ", "") in (r["article_ref"] or "").lower().replace(" ", "")
              and any(p1 <= p <= p2 for p in (r.get("pages_match") or [r.get("page_match")]))]
        assert ok, f"{insee} {zone}: barème {art} p.{p1}-{p2} non servi ; refs={[r['article_ref'] for r in rows][:6]}"


# ─────────────────────────── LOT 4 — dates ───────────────────────────

def test_dates_approbation_ecrite_distincte_du_lot(sess):
    """RELECTURE-6 §A.3 : pour Saint-Denis, La Plaine, Le Tampon, Cilaos (et L'Étang-Salé), la date
    d'approbation écrite est NOMMÉE et DISTINCTE du millésime du lot (dépôt GPU)."""
    from labuse.api.modules import plu_annuaire_communes
    res = plu_annuaire_communes(sess)
    attendu = {"97411": ("2024-02", "2026-08-05"), "97406": ("2013-05-29", "2023-05-27"),
               "97422": ("2018-12-08", "2023-08-11"), "97424": ("2008-02-06", "2024-02-13"),
               "97404": ("2017-06-22", "2025-09-17")}
    by = {c["insee"]: c for c in res["communes"]}
    for insee, (appro, lot) in attendu.items():
        c = by[insee]
        assert c["date_approbation"] == appro, f"{insee}: approbation={c['date_approbation']} ≠ {appro}"
        assert c["millesime_lot"] == lot, f"{insee}: lot={c['millesime_lot']} ≠ {lot}"
        assert c["date_approbation"] != c["millesime_lot"], f"{insee}: approbation == lot (non distinguées)"


def test_etang_sale_date_2017(sess):
    """RELECTURE-6 §A.3 : L'Étang-Salé affiche l'approbation écrite 22/06/2017 (pas le lot 2025)."""
    from labuse.api.modules import plu_annuaire_communes
    res = plu_annuaire_communes(sess)
    c = next(x for x in res["communes"] if x["insee"] == "97404")
    assert c["date_approbation"] == "2017-06-22"
