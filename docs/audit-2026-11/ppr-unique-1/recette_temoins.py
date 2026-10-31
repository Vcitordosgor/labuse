"""PPR-UNIQUE-1 — six témoins, AVANT / APRÈS (écran = liste de risques servie + compteur ; Étude =
zone d'implantation + rouge retranché).

AVANT = comportement d'origine reconstitué : classement PPR par SOUS-CHAÎNE (« interdict »/« rouge »)
pour l'Étude (le code `i` n'était NI rouge NI bleu → zone rouge jamais retranchée), et requête d'aléas
filtrée `subtype IN ('INTERDICTION','PRESCRIPTION')` + un seul niveau par aléa (best[typ]) pour l'écran.
APRÈS = classification unique `labuse.ppr` (`labuse_ppr_couleur`).
"""
import json

from shapely import wkt as shp_wkt
from shapely.ops import unary_union
from sqlalchemy import text

from labuse.db import session_scope
from labuse.implantation import terrain

TEMOINS = [
    ("97421000AB0133", "Salazie — PPR rouge 15 % + bleu 21 % + aléas"),
    ("97417000AH0053", "Saint-Philippe — D-001, 100 % code `i` (non classé)"),
    ("97424000AE0050", "Cilaos — PPR rouge 58 % + bleu 42 %"),
    ("97411000EY0173", "Saint-Denis — grande, PPR rouge partiel"),
    ("97415000BR0025", "Saint-Paul — PPR + bande littorale"),
    ("97411000IE0241", "Saint-Denis — maison, PPR bleu 100 %"),
]


def _rouge_bleu(session, aw, mode):
    """mode='avant' (sous-chaîne) ou 'apres' (labuse_ppr_couleur). Rend (rouge_m2, bleu_m2)."""
    rows = session.execute(text(
        "SELECT subtype, attrs->>'code_degre' cd, attrs->>'code_risque' cr, "
        "ST_AsText(ST_Intersection(geom_2975, ST_GeomFromText(:g,2975))) w "
        "FROM spatial_layers WHERE kind='ppr' AND ST_Intersects(geom_2975, ST_GeomFromText(:g,2975))"),
        {"g": aw}).fetchall()
    rouges, bleues = [], []
    for sub, cd, cr, w in rows:
        if not w:
            continue
        g = shp_wkt.loads(w)
        if g.is_empty:
            continue
        if mode == "avant":                       # ancien classement par sous-chaîne
            s = (sub or "").lower()
            if "interdict" in s or "rouge" in s:
                rouges.append(g)
            elif "prescript" in s or "bleu" in s:
                bleues.append(g)
            # `i` et tout code court : NI rouge NI bleu → IGNORÉ (le bug D-001)
        else:                                     # classification unique
            from labuse import ppr
            (rouges if ppr.est_interdit_ligne(sub, cd, cr) else bleues).append(g)
    r = unary_union(rouges).area if rouges else 0.0
    b = unary_union(bleues).area if bleues else 0.0
    return round(r, 1), round(b, 1)


def _aleas_avant(session, idu):
    """Reconstitution de l'ancienne liste d'aléas : PPR filtré INTERDICTION/PRESCRIPTION (→ `i` DROPPÉ),
    un seul niveau par aléa (le plus fort)."""
    out = []
    rows = session.execute(text(
        """WITH p AS (SELECT geom_2975 g, ST_Area(geom_2975) a FROM parcels WHERE idu=:i)
           SELECT upper(sl.subtype) z,
                  round((100*ST_Area(ST_Union(ST_Intersection(sl.geom_2975,p.g)))/NULLIF(min(p.a),0))::numeric)::int pct
           FROM spatial_layers sl CROSS JOIN p WHERE sl.kind='ppr' AND ST_Intersects(sl.geom_2975,p.g)
             AND upper(sl.subtype) IN ('INTERDICTION','PRESCRIPTION') GROUP BY 1"""), {"i": idu}).fetchall()
    for z, pct in rows:
        if (pct or 0) > 0:
            out.append(f"PPR {'rouge' if z == 'INTERDICTION' else 'bleue'} {pct}%")
    rank = {"faible": 1, "moyen": 3, "modere": 3, "eleve": 4, "fort": 5, "tres_fort": 6}
    best = {}
    for typ, niv, pct in session.execute(text(
        """WITH p AS (SELECT geom_2975 g, ST_Area(geom_2975) a FROM parcels WHERE idu=:i)
           SELECT COALESCE(sl.attrs->>'type',sl.subtype) t, lower(sl.attrs->>'niveau') n,
                  round((100*ST_Area(ST_Union(ST_Intersection(sl.geom_2975,p.g)))/NULLIF(min(p.a),0))::numeric)::int pct
           FROM spatial_layers sl CROSS JOIN p WHERE sl.kind='georisque_alea' AND ST_Intersects(sl.geom_2975,p.g)
           GROUP BY 1,2"""), {"i": idu}).fetchall():
        if (pct or 0) <= 0:
            continue
        r = rank.get(niv or "moyen", 3)
        if typ not in best or r > best[typ][0]:
            best[typ] = (r, f"Aléa {typ} {niv} {pct}%")
    out += [v[1] for v in best.values()]
    return out


def main():
    from labuse.api import servitudes
    rapport = []
    with session_scope() as s:
        for idu, desc in TEMOINS:
            t = terrain.charger(s, [idu], recul_voie_m=4.0, recul_separative_m=3.0,
                                inset_m=0.0, avec_pente=False)
            aw = t.assiette.wkt
            r_av, b_av = _rouge_bleu(s, aw, "avant")
            r_ap, b_ap = _rouge_bleu(s, aw, "apres")
            al_apres = [a["libelle"] for a in servitudes.aleas_parcelle(s, idu)]
            al_avant = _aleas_avant(s, idu)
            rapport.append({
                "idu": idu, "description": desc,
                "ecran_AVANT": {"n_lignes_risque": len(al_avant), "lignes": al_avant},
                "ecran_APRES": {"n_lignes_risque": len(al_apres), "lignes": al_apres},
                "etude_AVANT": {"ppr_rouge_m2": r_av, "ppr_bleu_m2": b_av,
                                "rouge_retranche": r_av > 0},
                "etude_APRES": {"ppr_rouge_m2": r_ap, "ppr_bleu_m2": b_ap,
                                "rouge_retranche": r_ap > 0, "zone_implantation_m2": round(t.aire_zone_m2, 1)},
            })
    out = "docs/audit-2026-11/ppr-unique-1/recette_temoins_resultat.json"
    with open(out, "w") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    print(json.dumps(rapport, indent=2, ensure_ascii=False))
    print(f"\nécrit → {out}")


if __name__ == "__main__":
    main()
