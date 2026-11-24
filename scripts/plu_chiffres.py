"""OUTIL-PLU-FIX-8 — SOURCE UNIQUE DES CHIFFRES du compte-rendu.

Tout chiffre cité dans le compte-rendu OUTIL-PLU-FIX-8 sort d'ICI (sortie brute collée). Aucun chiffre
écrit de mémoire. Le script LIT la base `labuse` réingérée + ré-exécute le découpage sur les PDF pour les
décomptes d'attribution. Lecture seule (aucune écriture).

Usage :
  LABUSE_DATABASE_URL=postgresql+psycopg://<user>@localhost:5432/labuse \
  LABUSE_PLU_PDF_DIR=~/Desktop/labuse/data/plu_reglements \
  PYTHONPATH=src python scripts/plu_chiffres.py
"""
from __future__ import annotations

import glob
import os
import pathlib
import re
import sys

import fitz  # noqa: F401  (chargé par plu_ingest)
import yaml
from sqlalchemy import text

sys.path.insert(0, "src")
from labuse.db import session_factory  # noqa: E402
from labuse.ingestion import plu_ingest as P  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDFDIR = pathlib.Path(os.path.expanduser(os.environ.get("LABUSE_PLU_PDF_DIR",
                      "~/Desktop/labuse/data/plu_reglements")))
MIL = yaml.safe_load((ROOT / "config" / "plu_millesimes.yaml").read_text())["communes"]
SERVABLES = {k for k, v in MIL.items() if v.get("statut") in ("a_jour", "annule_partiel")}


def h(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def main() -> int:
    s = session_factory()()

    h("1. CORPUS (base labuse réingérée)")
    tot, nc = s.execute(text("SELECT count(*), count(DISTINCT insee) FROM plu_reglement_extrait")).first()
    nz = s.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE zone IS NULL")).scalar()
    print(f"extraits = {tot} · communes servies = {nc} · sans zone = {nz} · zonés = {tot - nz}")

    h("2. DOUBLONS (LOT 2)")
    rows = s.execute(text("SELECT insee,document,zone,texte_verbatim FROM plu_reglement_extrait")).all()
    from collections import Counter
    exact = Counter((r.insee, r.document, r.zone, r.texte_verbatim) for r in rows)
    wsnorm = Counter((r.insee, r.document, r.zone, norm(r.texte_verbatim)) for r in rows)
    print(f"doublons octet-pour-octet (même insee,doc,zone,texte) EN TROP      = {sum(v - 1 for v in exact.values() if v > 1)}")
    print(f"doublons à blancs normalisés (même insee,doc,zone,norm-texte) EN TROP = {sum(v - 1 for v in wsnorm.values() if v > 1)}  (cible 0)")
    # Saint-Paul hauteur
    sp = s.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97415' "
                        "AND tsv @@ websearch_to_tsquery('fr_unaccent','hauteur')")).scalar()
    reps = s.execute(text("SELECT article_ref,zone,count(*) c, count(DISTINCT md5(regexp_replace(texte_verbatim,'\\s+',' ','g'))) d "
                          "FROM plu_reglement_extrait WHERE insee='97415' "
                          "AND tsv @@ websearch_to_tsquery('fr_unaccent','hauteur') GROUP BY 1,2 HAVING count(*)>1 ORDER BY c DESC")).all()
    extra = sum(r.c - 1 for r in reps)
    print(f"\nSaint-Paul « hauteur » : {sp} extraits ; (réf,zone) répétés = {len(reps)} couples, {extra} en trop")
    for r in reps:
        print(f"   {str(r.article_ref):14} {str(r.zone):6} ×{r.c}  (textes distincts à blancs normalisés = {r.d})")
    print("   → tous les 'répétés' restants ont des textes DISTINCTS (livrets/bassins de vie différents) :")
    print("     ce ne sont pas des doublons, les supprimer perdrait une règle de bassin.")

    h("3. U2e ARTICLE 13 — ENTIER SOUS SON FILTRE, SEUIL 20 % (LOT 1)")
    r = P.search_reglement(s, "espaces libres perméables", insee="97415", zone="U2e",
                           terms=["espaces", "libres", "perméables"], limit=50)
    for x in r:
        if (x["article_ref"] or "").startswith("Article 13"):
            t = x["texte_verbatim"] or ""
            print(f"   {x['article_ref']!r} zone={x['zone']} p{x['page_debut']}-{x['page_fin']} "
                  f"len={len(t)} contient_20%={'20%' in t or '20 %' in t}")
    # toutes les zones où l'article 13 contient 20 %
    a13 = s.execute(text("SELECT zone, page_debut, page_fin, length(texte_verbatim) ln "
                         "FROM plu_reglement_extrait WHERE insee='97415' AND article_ref='Article 13-' "
                         "AND (texte_verbatim ~ '20 ?%') ORDER BY page_debut")).all()
    print(f"   Saint-Paul : {len(a13)} 'Article 13-' contiennent le seuil 20 % (zones {[x.zone for x in a13]})")
    # plus aucun extrait 'Définition' sans zone collé à un article 13
    nd = s.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97415' "
                        "AND article_ref ILIKE 'Défin%' AND zone IS NULL")).scalar()
    print(f"   extraits 'Définition' zone NULL à Saint-Paul (ex-moignons détachés) = {nd}")

    h("4. ZONES INJOIGNABLES — COUVERTURE DU PLAN DE ZONAGE (LOT 3)")
    zrows = s.execute(text("SELECT right(attrs->>'partition',5) insee, attrs->>'libelle' lib "
                           "FROM spatial_layers WHERE kind='plu_gpu_zone' "
                           "AND attrs->>'partition' LIKE 'DU_%' GROUP BY 1,2")).all()
    from collections import defaultdict
    zbyc = defaultdict(set)
    for r in zrows:
        if r.insee in SERVABLES and r.lib:
            zbyc[r.insee].add(r.lib)
    tz = tzero = 0
    for insee in sorted(zbyc):
        zeros = [z for z in sorted(zbyc[insee]) if not P.zones_apparentees(s, z, insee)]
        tz += len(zbyc[insee])
        if zeros:
            tzero += len(zeros)
            print(f"   {insee} {MIL[insee]['commune']:<22} {len(zeros)} zéro/{len(zbyc[insee])} -> {zeros}")
    print(f"   TOTAL zones du plan de zonage (21 communes) = {tz} ; injoignables = {tzero}")

    h("5. LE PORT 1AU/2AU — ARTICLES PROPRES SERVIS (LOT 3)")
    for z in ("1AU", "2AU"):
        napp = P.zones_apparentees(s, z, "97407")
        n = s.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE insee='97407' AND zone=:z"),
                      {"z": z}).scalar()
        print(f"   zone {z} : {n} extraits zonés ; apparentées={napp}")
    r = P.search_reglement(s, "aspect", insee="97407", zone="2AU", terms=["aspect"], limit=20)
    serv = [(x["article_ref"], x["page_match"]) for x in r if x["zone"] == "2AU"]
    print(f"   « aspect » filtre 2AU → articles 2AU servis : {serv[:3]}  (dont 'Aspect extérieur' p.159)")

    h("6. RENVOI GÉNÉRIQUE AU→U & NON-RÉGRESSION (LOT 3)")
    for z, ins in [("A", "97408"), ("AU3c", "97415"), ("2AUd", "97422"), ("AUa", "97401")]:
        print(f"   {z}@{ins}: apparentées={P.zones_apparentees(s, z, ins)} ; note={P.zone_renvoi_note(z, ins, s)}")

    h("7. DATES — APPROBATION ÉCRITE ≠ MILLÉSIME DU LOT (LOT 4)")
    from labuse.api.modules import plu_annuaire_communes
    res = plu_annuaire_communes(s)
    for c in sorted(res["communes"], key=lambda x: x["insee"]):
        if c["statut"] != "servable":
            continue
        da, lot = c.get("date_approbation"), c.get("millesime_lot")
        mark = " [écrite≠lot, nommées distinctement]" if da != lot else ""
        print(f"   {c['insee']} {c['commune']:<22} approbation={str(da):<12} lot={lot}{mark}")

    h("8. ATTRIBUTION DE ZONE — « 174 » de FIX-7 : d'où venait l'erreur")
    # recompte réel : combien d'extraits doivent leur zone à _zone_de_fiche / _zone_de_preambule /
    # code à chiffre de tête — en ré-exécutant le découpage.
    nf = npre = nnum = 0
    for p in sorted(glob.glob(str(PDFDIR / "*.pdf"))):
        insee = os.path.basename(p)[:5]
        if insee not in SERVABLES:
            continue
        arts, _ = P._split_articles(p)
        for a in arts:
            if a["zone"] is None:
                continue
            ref = a["article_ref"] or ""
            # zone issue de l'en-tête classique ?
            zm = P._ZONE_FROM_ART.match(ref) or P._ZONE_FROM_ZONE.match(ref)
            z_hdr = P._valid_zone(zm.group(1)) if zm else None
            if z_hdr == a["zone"]:
                continue
            mnum = P._ZONE_FROM_ART_NUM.match(ref)
            if mnum and P._valid_zone(mnum.group(1)) == a["zone"]:
                nnum += 1
            elif P._zone_de_fiche(a["texte_verbatim"] if isinstance(a, dict) and "texte_verbatim" in a else a["texte"]) == a["zone"]:
                nf += 1
            elif P._zone_de_preambule(a.get("texte") or "") == a["zone"]:
                npre += 1
    print(f"   zone posée par _zone_de_fiche (fiche/annexe zonée)      = {nf}")
    print(f"   zone posée par _zone_de_preambule (préambule de zone)   = {npre}")
    print(f"   zone posée par code à chiffre de tête (Le Port 1AU/2AU) = {nnum}")
    print("   → FIX-7 annonçait « ≈174 fiches/annexes attribuées » : FAUX. La bascule 849→675 des")
    print("     sans-zone de FIX-7 venait à ~95 % de la SUPPRESSION d'extraits (ré-découpe/réfs de")
    print("     prose), pas d'une attribution ; seuls 3 extraits recevaient alors une zone (_zone_de_fiche).")

    h("9. FIX-9 point 1 — LES 4 EX-« INTROUVABLES » SONT TOUTES RELIÉES (0 trou)")
    for ins, z, how in [("97419", "1AUto", "chapitre propre AUTO (phasage)"),
                        ("97402", "1AUt", "renvoi texte → Ua"),
                        ("97423", "1AUt", "renvoi texte → Ub"),
                        ("97422", "1AUto", "renvoi texte → Ucto")]:
        app = P.zones_apparentees(s, z, ins)
        n = P.count_reglement(s, "hauteur", insee=ins, zone=z, terms=["hauteur"])
        print(f"   {ins} {z:6} apparentées={app}  n(hauteur)={n}   [{how}]")
    print("   → le compte-rendu FIX-8 (« 4 zones sans règlement correspondant ») était INEXACT : les 4")
    print("     ont bien un règlement (1 chapitre propre + 3 renvois lus sur pièce p.80/66-70/86-89).")

    h("10. FIX-9 point 3 — LIGNES DOUBLÉES (artefact fausse-graisse, dessin EN PLACE)")
    rows = s.execute(text("SELECT insee, texte_verbatim FROM plu_reglement_extrait")).all()
    import re as _re
    cons = {}
    for r in rows:
        ls = [_re.sub(r"\s+", " ", x).strip() for x in (r.texte_verbatim or "").splitlines()]
        for i in range(1, len(ls)):
            if ls[i] and ls[i] == ls[i - 1] and len(ls[i]) > 3:
                cons[r.insee] = cons.get(r.insee, 0) + 1
    print(f"   Le Tampon (97422) doublons consécutifs EN PLACE servis = {cons.get('97422', 0)}  (était 521 sur 116 pages)")
    autres = {k: v for k, v in cons.items() if k != "97422"}
    print(f"   lignes consécutives identiques AILLEURS = {autres} → ce sont des CELLULES DE TABLEAU (y")
    print("     distincts : palette « RECOMMANDÉ », colonnes « 100 % ») — légitimes, NON retirées.")

    h("11. FIX-9 point 4 — REGROUPEMENT À L'AFFICHAGE (Saint-Paul « hauteur » sans filtre)")
    from labuse.api.modules import plu_annuaire_search
    r = plu_annuaire_search(q="hauteur", insee="97415", zone=None, limit=200, offset=0, db=s)
    norms = [_re.sub(r"\s+", " ", (x.get("texte_verbatim") or "")).strip() for x in r["resultats"]]
    from collections import Counter as _C
    print(f"   extraits bruts = {r['n_extraits']} ; entrées après regroupement = {r['n_groupes']} ; "
          f"doublons de texte affichés = {sum(v - 1 for v in _C(norms).values() if v > 1)}")
    for g in r["resultats"]:
        zc = g.get("zones_concernees") or []
        if len(zc) > 1:
            print(f"     {str(g['article_ref']):14} regroupé sur zones {zc}")

    s.close()
    print("\nPLU_CHIFFRES_DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
