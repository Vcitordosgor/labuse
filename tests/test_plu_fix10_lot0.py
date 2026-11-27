"""OUTIL-PLU-FIX-10 — LOT 0 : FILET DES TÉMOINS de l'audit 01-PLU-ASTRA-3 (liste « C'est faux », 8 points).

Nouveau critère (le SEUL qui compte) : pour une zone ET un article, l'outil sert l'article PROPRE à la
zone s'il existe dans le PDF ; il ne sert celui d'une AUTRE zone que si le texte de la zone y renvoie
EXPRESSÉMENT pour CET article — et il le dit. L'ancien critère « chaque zone donne au moins un résultat »
(retiré de test_plu_cas_valides) est précisément ce qui a produit les erreurs : des zones renvoyées en
bloc vers le règlement d'une autre alors qu'elles ont leur propre article.

Chaque test affirme une VALEUR PRÉCISE (article, page, chiffre) lue au PDF officiel (~/Desktop/labuse/
data/plu_reglements), pas une propriété vague. Écrits AVANT correction → ROUGES sur la base actuelle.

Lit le CORPUS RÉEL servi (base `labuse` réingérée) ; SKIP si le corpus est injoignable/vide (jamais un
faux vert). DSN via LABUSE_PLU_CORPUS_DSN (défaut openclaw@localhost/labuse).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from labuse.ingestion import plu_ingest as P

pytestmark = pytest.mark.reel

_DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")


@pytest.fixture(scope="module")
def sess():
    try:
        s = sessionmaker(bind=create_engine(_DSN))()
        n = s.execute(text("SELECT count(*) FROM plu_reglement_extrait")).scalar()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"corpus PLU injoignable ({_DSN}) : {e}")
    if not n or n < 2000:
        pytest.skip(f"corpus PLU vide/partiel ({n}) — réingérer avant le filet")
    yield s
    s.close()


def _pages(rows, r):
    return set(r.get("pages_match") or []) | ({r.get("page_match")} if r.get("page_match") else set())


# ─────────────── Point 1 (bloquant) — Trois-Bassins AUt : hauteur = l'article PROPRE (p.69) ───────────────

def test_p1_trois_bassins_AUt_hauteur_est_son_propre_article_p69(sess):
    """AUindicée 10.2, p.69, fixe pour AUt 8 m à l'égout/acrotère et 10 m au faîtage. L'outil doit servir
    CET article (p.69), jamais étendre à la hauteur le renvoi vers Ub (p.32-33, 12 m au faîtage)."""
    for plan in ("AUt", "1AUt"):
        rows = P.search_reglement(sess, "hauteur", insee="97423", zone=plan, terms=["hauteur"], limit=30)
        zoned = [r for r in rows if r["zone"]]
        assert zoned, f"{plan} : aucun article de hauteur servi"
        # l'article propre (AUINDICEE 10, p.69, 8 m / 10 m) est servi et vient EN PREMIER
        propre = [r for r in zoned if 69 in _pages(rows, r)
                  and "8 mètres" in (r["texte_verbatim"] or "") and "10 mètres" in (r["texte_verbatim"] or "")]
        assert propre, f"{plan} : l'article AUindicée 10 (p.69, 8 m/10 m) n'est pas servi"
        assert 69 in _pages(rows, zoned[0]), f"{plan} : le 1er résultat zoné n'est pas la p.69 ({zoned[0]['article_ref']})"
        # le renvoi vers Ub (p.32-33) ne doit PAS être servi pour la hauteur (AUt a son article propre)
        assert not any(("UB" == (r["zone"] or "")) and (_pages(rows, r) & {32, 33}) for r in zoned), \
            f"{plan} : la hauteur Ub p.32-33 est servie à tort"


# ─────────────── Point 2 (bloquant) — Bras-Panon AUec : hauteur propre (p.80, 18 m) ───────────────

def test_p2_bras_panon_AUec_hauteur_18m_p80(sess):
    """AUindicée 10, p.80 : « Pour la zone AUec, la hauteur absolue … ne doit pas excéder 18 mètres ».
    L'outil doit servir cet article (p.80), jamais UE 10 (p.70-71, 12 m/16 m)."""
    rows = P.search_reglement(sess, "hauteur", insee="97402", zone="AUec", terms=["hauteur"], limit=30)
    zoned = [r for r in rows if r["zone"]]
    assert zoned, "AUec : aucun article de hauteur servi"
    propre = [r for r in zoned if 80 in _pages(rows, r) and "18 mètres" in (r["texte_verbatim"] or "")]
    assert propre, "AUec : l'article de hauteur propre (p.80, 18 m) n'est pas servi"
    assert 80 in _pages(rows, zoned[0]), f"AUec : 1er résultat zoné pas p.80 ({zoned[0]['article_ref']})"
    assert not any((r["zone"] == "UE") and (_pages(rows, r) & {70, 71}) for r in zoned), \
        "AUec : la hauteur UE p.70-71 est servie à tort"


# ─────────────── Point 3 (bloquant) — Sainte-Marie U8 entier + le 2e U8 hors UA ───────────────

def test_p3_sainte_marie_UA_U8_entier_avec_valeurs_p22(sess):
    """Sous UA, l'Article U8 (hauteur) doit être ENTIER : la p.22 donne, pour UA, 15 m à l'égout,
    18 m au faîtage, 16 m à l'acrotère. L'extrait est aujourd'hui coupé juste après « limitée à : • »."""
    rows = P.search_reglement(sess, "hauteur", insee="97418", zone="UA", terms=["hauteur"], limit=40)
    u8 = [r for r in rows if "U8" in (r["article_ref"] or "")]
    assert u8, "UA : aucun Article U8 servi"
    # L'U8 qui gouverne UA (p.21-22) doit porter les 3 valeurs de la zone UA
    gouverne_ua = [r for r in u8 if "15,00" in (r["texte_verbatim"] or "")
                   and "18,00" in (r["texte_verbatim"] or "") and "16,00" in (r["texte_verbatim"] or "")]
    assert gouverne_ua, "UA : l'Article U8 est tronqué — 15,00/18,00/16,00 m absents de l'extrait"
    assert any(r["page_fin"] >= 22 for r in gouverne_ua), "UA : l'U8 ne va pas jusqu'à la p.22"


def test_p3_sainte_marie_second_U8_pas_sous_UA(sess):
    """Le second U8 (p.34-35) concerne UEa/UEm/UEp/UR/UEc/UT — il ne doit PAS sortir sous le filtre UA."""
    rows = P.search_reglement(sess, "hauteur", insee="97418", zone="UA", terms=["hauteur"], limit=40)
    mauvais = [r for r in rows if "U8" in (r["article_ref"] or "")
               and (r["page_debut"] or 0) >= 34 and "UEa" in (r["texte_verbatim"] or "")]
    assert not mauvais, "UA : le second U8 (UEa/UEm/…, p.34-35) est servi à tort sous UA"


# ─────────────── Point 4 (bloquant) — Saint-Paul U2e : l'article propre d'ABORD ───────────────

def test_p4_saint_paul_U2e_espaces_article_propre_premier(sess):
    """U2e + « espaces » : le PREMIER résultat de ZONE doit être l'article 13 de U2e (p.99-100, seuil
    20 %), pas l'article 13 des pages 83-87 que le PDF réserve à U2a/U2b/U2c/U2d/U2h."""
    rows = P.search_reglement(sess, "espaces", insee="97415", zone="U2e", terms=["espaces"], limit=30)
    zoned = [r for r in rows if r["zone"]]
    assert zoned, "U2e : aucun article zoné servi"
    first = zoned[0]
    assert first["zone"] == "U2E" and (first["page_debut"] or 0) <= 99 <= (first["page_fin"] or 0), \
        f"U2e : 1er résultat zoné = {first['zone']} p.{first['page_debut']}-{first['page_fin']} (attendu U2E p.99-100)"
    # les pages 83-87 (U2a..U2h) ne doivent pas être servies sous le filtre U2e
    assert not any((r["page_debut"] or 0) <= 84 <= (r["page_fin"] or 999) for r in zoned), \
        "U2e : l'article des pages 83-87 (autres secteurs) est servi sous U2e"


# ─────────────── Point 5 (à corriger) — Saint-Paul Usdu : art 10 ≠ art 11, livrets accessibles ───────────────

def test_p5_saint_paul_usdu_article10_separe_de_11(sess):
    """L'« Article 10 – Hauteur » (p.195) de Usdu ne doit PAS incorporer l'article 11 (qui commence
    p.196, avec 11.1 … 11.7 sur les clôtures)."""
    rows = sess.execute(text(
        "SELECT article_ref, page_debut, page_fin, texte_verbatim FROM plu_reglement_extrait "
        "WHERE insee='97415' AND zone='USDU' AND page_debut BETWEEN 195 AND 200 ORDER BY page_debut")).all()
    art10 = [r for r in rows if "10" in (r.article_ref or "")]
    assert art10, "Usdu : Article 10 (p.195) introuvable"
    # l'article 10 ne contient pas l'article 11 (ni ses sous-sections 11.x)
    assert not any("11.1" in (r.texte_verbatim or "") and "11.7" in (r.texte_verbatim or "") for r in art10), \
        "Usdu : l'article 10 (p.195-200) incorpore l'article 11 (11.1 … 11.7)"
    art11 = [r for r in rows if (r.article_ref or "").replace(" ", "").startswith("Article11")]
    assert art11 and any((r.page_debut or 0) <= 196 for r in art11), \
        "Usdu : l'article 11 (p.196) n'est pas un extrait séparé"


def test_p5_saint_paul_usdu_stationnement_livrets_200_246_306(sess):
    """« stationnement » sous Usdu doit citer les articles 12 des livrets La Plaine–Bois de Nèfles (p.200),
    La Saline (p.246) et Guillaume (p.306) — aujourd'hui aucune de ces trois pages n'est citée."""
    rows = P.search_reglement(sess, "stationnement", insee="97415", zone="Usdu",
                              terms=["stationnement"], limit=200)
    pages = {p for r in rows for p in _pages(rows, r)}
    for p in (200, 246, 306):
        assert p in pages, f"Usdu stationnement : la page {p} (article 12 d'un livret) n'est pas citée ; pages={sorted(pages)}"


# ─────────────── Point 6 (à corriger) — barèmes stationnement sur la fiche parcelle ───────────────

def _stat_fiche(sess, idu, commune, zone):
    from labuse.api.app import _reglement_plu_block
    b = _reglement_plu_block(sess, idu, commune)
    z = next(x for x in b["zones"] if x["zone"] == zone)
    return next(r for r in z["regles_valeurs"] if r.get("cle") == "stationnement")


def test_p6_fiche_saint_louis_bareme_article_page(sess):
    """FIX-11 (réécrit, non permissif) — 97414000DK0208 (Saint-Louis, UA) : le barème sert « 2 places /
    logement », la référence contient « UA 12.2 » et le lien profond pointe la p.23."""
    stat = _stat_fiche(sess, "97414000DK0208", "Saint-Louis", "UA")
    assert "2 places" in str(stat.get("valeur")), f"SL : valeur de base ({stat.get('valeur')})"
    assert stat.get("reference") and "UA 12.2" in stat["reference"], f"SL : référence ({stat.get('reference')})"
    assert "#page=23" in (stat.get("url") or ""), f"SL : lien p.23 ({stat.get('url')})"


def test_p6_fiche_saint_louis_ligne_logement_social(sess):
    """FIX-11 point 3 — la fiche de Saint-Louis UA porte EXPLICITEMENT la ligne du tableau p.23
    « logement social : 1 place / logement » dans ses conditions (et non seulement la part publique)."""
    stat = _stat_fiche(sess, "97414000DK0208", "Saint-Louis", "UA")
    conds = [str(c.get("texte", c)).lower() for c in (stat.get("conditions") or [])]
    social = [c for c in conds if ("logement social" in c or "logements sociaux" in c)]
    assert social, f"SL : aucune condition ne nomme le logement social ({stat.get('conditions')})"
    assert any("1 place" in c for c in social), \
        f"SL : la ligne logement social ne porte pas « 1 place » ({social})"


def test_p6_fiche_saint_pierre_bareme_article_page(sess):
    """FIX-11 (réécrit, non permissif) — 97416000HT0538 (Saint-Pierre, Ud) : barème « 1 place / 75 m² »,
    référence « Ud6 », lien profond p.93."""
    stat = _stat_fiche(sess, "97416000HT0538", "Saint-Pierre", "Ud")
    assert "75 m²" in str(stat.get("valeur")), f"SP : valeur de base ({stat.get('valeur')})"
    assert stat.get("reference") and "Ud6" in stat["reference"].replace(" ", ""), f"SP : référence ({stat.get('reference')})"
    assert "#page=93" in (stat.get("url") or ""), f"SP : lien p.93 ({stat.get('url')})"


def test_p6_fiche_saint_pierre_ligne_logement_locatif_social(sess):
    """FIX-11 point 3 — la fiche de Saint-Pierre Ud porte EXPLICITEMENT la ligne p.93 du logement locatif
    social (« 1 place pour les logements locatifs sociaux ») dans ses conditions."""
    stat = _stat_fiche(sess, "97416000HT0538", "Saint-Pierre", "Ud")
    conds = [str(c.get("texte", c)).lower() for c in (stat.get("conditions") or [])]
    social = [c for c in conds if ("locatif" in c and "social" in c) or "logements sociaux" in c
              or "logement social" in c]
    assert social, f"SP : aucune condition ne nomme le logement (locatif) social ({stat.get('conditions')})"
    # FIX-12 (relecture-9 §2) — ratio EXACT « 1 place » (symétrie avec Saint-Louis), pas un vague « place » :
    # un ratio erroné (p.ex. « 2 places ») ne doit plus passer.
    assert any("1 place" in c for c in social), f"SP : la ligne sociale ne porte pas « 1 place » ({social})"


# ─────────────── Points 7-8 (à corriger) — dates & avertissements ───────────────

def test_p7_dates_approbation_ecrite_couverture(sess):
    """La date « approuvé le » servie = la date ÉCRITE sur la couverture ; une couverture sans jour est
    dite telle quelle (pas de jour inventé). Le Tampon couverture = 08/12/2018 (pas le lot 11/08/2023) ;
    Saint-Denis couverture = février 2024 sans jour (pas 05/08/2026)."""
    from labuse.api.modules import plu_annuaire_communes
    by = {c["insee"]: c for c in plu_annuaire_communes(sess)["communes"]}
    assert by["97422"]["date_approbation"] == "2018-12-08", f"Le Tampon : {by['97422']['date_approbation']}"
    # Saint-Denis : mois connu, jour inconnu → pas de jour inventé
    assert str(by["97411"]["date_approbation"]).startswith("2024-02"), f"Saint-Denis : {by['97411']['date_approbation']}"


def test_p8_badges_procedure_liste_egale_detail(sess):
    """Les procédures signalées dans le détail doivent l'être aussi dans la liste servie (mêmes badges) :
    Saint-Benoît, La Possession, Saint-Pierre, Le Tampon."""
    from labuse.api.modules import plu_annuaire_communes
    by = {c["insee"]: c for c in plu_annuaire_communes(sess)["communes"]}
    for insee in ("97410", "97408", "97416", "97422"):
        c = by[insee]
        assert c.get("procedures_inventaire") or c.get("modifications") or c.get("note_doc"), \
            f"{insee} : aucune procédure/évolution servie dans la liste alors que le détail en porte une"


def test_p8_beauvallon_evolution_non_integree_signalee(sess):
    """Saint-Benoît : l'évolution de Beauvallon (30/06/2026) absente du lot GPU 2020 doit être SIGNALÉE
    (le texte servi est le lot de 2020, pas l'état applicable aujourd'hui à Beauvallon)."""
    from labuse.api.modules import plu_annuaire_communes
    by = {c["insee"]: c for c in plu_annuaire_communes(sess)["communes"]}
    note = (by["97410"].get("note_doc") or "") + " " + str(by["97410"].get("modifications") or "")
    assert "beauvallon" in note.lower(), f"Saint-Benoît : évolution Beauvallon non signalée ({note!r})"


# ═══════════════ RELECTURE-PLU-8 (FIX-11) — liste fermée (3 points) ═══════════════

# ─── Point 1 (bloquant) — Saint-Denis Up.10 : les valeurs de hauteur sont DANS l'article 10 ───

def test_fix11_p1_saint_denis_Up10_contient_16m_11m(sess):
    """RELECTURE-8 §1 — sous UP, « hauteur » sert l'Article Up.10 (p.34) qui DOIT contenir les hauteurs
    maximales du secteur : Upr 16 m et Upi 11 m. Sur FIX-10 l'extrait s'arrêtait à « …dans le secteur : »
    (530 car.) sans aucune valeur — elles étaient rattachées à tort à l'article SUIVANT Up.11."""
    rows = P.search_reglement(sess, "hauteur", insee="97411", zone="Up", terms=["hauteur"], limit=30)
    a10 = [r for r in rows if "Up.10" in (r["article_ref"] or "")]
    assert a10, "UP : Article Up.10 (hauteur) absent des résultats"
    txt = a10[0]["texte_verbatim"] or ""
    assert "16 m" in txt and "11 m" in txt, \
        f"Up.10 ne contient pas 16 m / 11 m (len={len(txt)}) — valeurs toujours détachées"
    assert "Upr" in txt and "Upi" in txt, "Up.10 ne nomme pas les secteurs Upr/Upi"


def test_fix11_p1_saint_denis_Up11_ne_contient_pas_les_hauteurs(sess):
    """Corollaire : les 16 m / 11 m ne doivent PLUS figurer dans l'Article Up.11 (Aspect extérieur, p.35),
    où ils avaient migré."""
    rows = sess.execute(text(
        "SELECT texte_verbatim FROM plu_reglement_extrait WHERE insee='97411' "
        "AND article_ref ILIKE 'Article Up.11%'")).scalars().all()
    assert rows, "Up.11 introuvable"
    for t in rows:
        assert not ("16 m" in (t or "") and "11 m" in (t or "")), \
            "Up.11 contient encore les hauteurs 16 m / 11 m (elles appartiennent à Up.10)"


# ─── Point 2 — l'article PROPRE à la zone passe avant celui d'une zone sœur ───

def _premier_zone(sess, insee, zone, q):
    rows = P.search_reglement(sess, q, insee=insee, zone=zone, terms=[q], limit=20)
    zoned = [r for r in rows if r["zone"]]
    return zoned[0] if zoned else None


def test_fix11_p2_avirons_UE_stationnement_article_propre_premier(sess):
    """RELECTURE-8 §2 — Les Avirons UE : « stationnement » doit servir EN PREMIER l'Article UE 12 (p.24),
    propre à UE, et non l'Article U 12 (p.16) du chapitre mutualisé « ZONES UA, UB, UC et UD »."""
    r = _premier_zone(sess, "97401", "UE", "stationnement")
    assert r and r["zone"] == "UE" and "UE 12" in (r["article_ref"] or ""), \
        f"Avirons UE : 1er résultat = {r and (r['zone'], r['article_ref'], r['page_debut'])} (attendu UE 12 p.24)"


def test_fix11_p2_salazie_UT_stationnement_article_propre_premier(sess):
    """RELECTURE-8 §2 — Salazie UT : « stationnement » doit servir EN PREMIER l'Article UT 12 (p.26),
    et non l'Article U 12 (p.17) du chapitre « ZONES UA, UB et UC »."""
    r = _premier_zone(sess, "97421", "UT", "stationnement")
    assert r and r["zone"] == "UT" and "UT 12" in (r["article_ref"] or ""), \
        f"Salazie UT : 1er résultat = {r and (r['zone'], r['article_ref'], r['page_debut'])} (attendu UT 12 p.26)"


def test_fix11_p2_petite_ile_UEa_hauteur_article_propre_premier(sess):
    """RELECTURE-8 §2 — Petite-Île UEa : « hauteur » doit servir EN PREMIER l'Article UEa.10 (p.62, 7 m),
    propre à UEa, et non l'Article UE.10 (p.56) de la zone UE."""
    r = _premier_zone(sess, "97405", "UEa", "hauteur")
    assert r and r["zone"] == "UEA" and "UEa.10" in (r["article_ref"] or ""), \
        f"Petite-Île UEa : 1er résultat = {r and (r['zone'], r['article_ref'], r['page_debut'])} (attendu UEa.10 p.62)"


# ═══════════════ RELECTURE-PLU-9 → FIX-13 — La Plaine : dossiers de modification concaténés ═══════════════

def test_fix13_laplaine_dossiers_etiquetes(sess):
    """FIX-13 — les extraits des pages 118-217 (3 dossiers de modification collés au PDF) portent une
    étiquette `dossier` « Dossier de modification … (date) » ; ceux du règlement de base (p.1-117) non."""
    base = sess.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97406' "
                             "AND page_debut<=117 AND dossier IS NOT NULL")).scalar()
    assert base == 0, f"{base} article(s) du règlement de base p.1-117 étiqueté(s) dossier à tort"
    dos = sess.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97406' "
                            "AND page_debut>=118 AND dossier IS NULL")).scalar()
    assert dos == 0, f"{dos} extrait(s) de dossier (p.118+) sans étiquette"
    # les 3 dossiers nommés et datés
    labels = {r[0] for r in sess.execute(text("SELECT DISTINCT dossier FROM plu_reglement_extrait "
                                              "WHERE insee='97406' AND dossier IS NOT NULL"))}
    joined = " | ".join(labels)
    assert all(d in joined for d in ("mai 2023", "2019", "2016")), f"dates de dossier manquantes : {joined}"
    assert all("Dossier de modification" in l for l in labels), f"étiquette non conforme : {labels}"


def test_fix13_laplaine_reglement_avant_dossier(sess):
    """FIX-13 — sous un filtre de zone, les articles du règlement de base (p.1-117) passent AVANT les
    extraits de dossier. Témoin : La Plaine UB « hauteur » — aucun extrait de dossier avant un extrait de
    règlement."""
    rows = [r for r in P.search_reglement(sess, "hauteur", insee="97406", zone="UB",
                                          terms=["hauteur"], limit=20) if r["zone"]]
    assert rows, "UB La Plaine : aucun résultat zoné"
    premier_dossier = next((i for i, r in enumerate(rows) if r.get("dossier")), len(rows))
    dernier_regl = max((i for i, r in enumerate(rows) if not r.get("dossier")), default=-1)
    assert dernier_regl < premier_dossier, \
        f"un extrait de dossier précède un article de règlement (regl@{dernier_regl}, dossier@{premier_dossier})"
    assert any(not r.get("dossier") and "Ub 10" in (r["article_ref"] or "") for r in rows), \
        "l'article Ub 10 du règlement de base n'est pas servi en tête"


def test_fix13_laplaine_AUs1_modif_non_integree_signalee(sess):
    """FIX-13 — la modification de mai 2023 (ouverture AUs1) n'est pas intégrée au règlement de base :
    les articles AUs du règlement portent `modif_note` qui la nomme et la date ; le dossier correspondant
    est servi, étiqueté."""
    rows = P.search_reglement(sess, "hauteur", insee="97406", zone="AUs1", terms=["hauteur"], limit=20)
    base_aus = [r for r in rows if r["zone"] == "AUS" and not r.get("dossier")]
    assert base_aus, "aucun article AUs du règlement de base servi sous AUs1"
    note = base_aus[0].get("modif_note") or ""
    assert "mai 2023" in note and "non intégrée" in note.lower(), \
        f"modif_note absente/incomplète sur l'article de base AUs : {note!r}"
    # OUTIL-PLU-FIX-14 (LOT 5) — frontières corrigées : le dossier mai 2023 (p.118-149) modifie en pratique
    # les zones UB/Ur (le volet AUs1 y est RÉDACTIONNEL, pas des articles AUs). On vérifie donc que ce
    # dossier EST servi et étiqueté « mai 2023 » sous une zone qu'il régit réellement (UB), et qu'aucun de
    # ses extraits ne déborde avant p.118 ni après p.149.
    ub = P.search_reglement(sess, "implantation", insee="97406", zone="UB", terms=["implantation"], limit=40)
    dmai = [r for r in ub if (r.get("dossier") or "").find("mai 2023") >= 0]
    assert dmai, "le dossier de modification mai 2023 n'est pas servi/étiqueté (zone UB)"
    for r in dmai:
        assert 118 <= (r["page_debut"] or 0) <= 149, \
            f"extrait du dossier mai 2023 hors de ses frontières p.118-149 : p.{r['page_debut']}"
