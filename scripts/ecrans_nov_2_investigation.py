"""ECRANS-NOV-2 (recette 2, point 7) — investigation : le foncier PUBLIC et les ÉQUIPEMENTS
PUBLICS parmi les parcelles les mieux classées (Excellente / Bonne).

RAPPORT CHIFFRÉ, aucune correction du moteur (la règle sera décidée ensuite). Cas d'école :
97411000DO0049 (3 Allée des Étudiants, Saint-Denis) — classée « Excellente, +112 339 m² » alors
que c'est un CAMPUS DE LYCÉES de la Région. Combien de cas analogues sur l'île ?

Lecture seule. Sorties : un Markdown dans docs/audit-2026-11/ecrans-nov-2/.
"""
from __future__ import annotations

import os

from sqlalchemy import text

from labuse.db import make_engine

RUN = "q_v20"
URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
PUBLIC = (1, 2, 3, 4, 9)   # groupes DGFiP publics (proprietaire_type.PUBLIC_DGFIP_GROUPES)


def main() -> None:
    eng = make_engine(URL)
    with eng.begin() as cx:
        # BPE transformés en 2975 une fois, avec index — le join spatial sur 49 980 parcelles tient.
        cx.execute(text("DROP TABLE IF EXISTS _inv_bpe"))
        cx.execute(text("""
            CREATE TEMP TABLE _inv_bpe AS
            SELECT subtype AS dom, name, attrs->>'typequ' AS typequ,
                   ST_Transform(geom, 2975) AS g
            FROM spatial_layers WHERE kind='amenite_bpe'"""))
        cx.execute(text("CREATE INDEX _inv_bpe_gix ON _inv_bpe USING gist (g)"))
        # Les parcelles Excellente / Bonne (conservation, estimées) de l'île.
        cx.execute(text("DROP TABLE IF EXISTS _inv_ab"))
        cx.execute(text(f"""
            CREATE TEMP TABLE _inv_ab AS
            SELECT s.idu, s.band, p.commune, p.geom_2975 AS g, round(ST_Area(p.geom_2975)) AS surf
            FROM parcel_scenario_v2_runs s JOIN parcels p ON p.idu = s.idu
            WHERE s.run_label=:r AND s.scenario='keep' AND s.status='ESTIMATED' AND s.band IN ('A','B')"""),
            {"r": RUN})
        cx.execute(text("CREATE INDEX _inv_ab_gix ON _inv_ab USING gist (g)"))

        # lycée/collège/université : typequ C2 (collège), C3 (lycée), C4/C5 (supérieur) ; hôpital : D1.
        enssup = "(b.dom='C' AND (b.typequ LIKE 'C2%' OR b.typequ LIKE 'C3%' OR b.typequ LIKE 'C4%' OR b.typequ LIKE 'C5%'))"
        hopital = "(b.dom='D' AND b.typequ LIKE 'D1%')"

        def n(where_bpe: str | None = None, owner_public: bool = False) -> int:
            conds = []
            if owner_public:
                conds.append("EXISTS (SELECT 1 FROM parcelle_personne_morale m "
                             "WHERE m.idu=a.idu AND m.groupe = ANY(:pub))")
            if where_bpe:
                conds.append(f"EXISTS (SELECT 1 FROM _inv_bpe b WHERE {where_bpe} AND ST_Intersects(b.g, a.g))")
            w = " AND ".join(conds) or "TRUE"
            return cx.execute(text(f"SELECT count(*) FROM _inv_ab a WHERE {w}"),
                              {"pub": list(PUBLIC)}).scalar()

        total = n()
        pub = n(owner_public=True)
        any_bpe = n("TRUE")
        ens = n("b.dom='C'")
        sante = n("b.dom='D'")
        lycee = n(enssup)
        hop = n(hopital)
        pub_ou_equip = cx.execute(text(f"""
            SELECT count(*) FROM _inv_ab a WHERE
              EXISTS (SELECT 1 FROM parcelle_personne_morale m WHERE m.idu=a.idu AND m.groupe=ANY(:pub))
              OR EXISTS (SELECT 1 FROM _inv_bpe b WHERE ({enssup} OR {hopital}) AND ST_Intersects(b.g,a.g))
            """), {"pub": list(PUBLIC)}).scalar()

        # exemples : les plus grandes parcelles publiques OU à équipement d'enseignement/santé.
        ex = cx.execute(text(f"""
            SELECT a.idu, a.band, a.commune, a.surf,
                   (SELECT m.denomination FROM parcelle_personne_morale m WHERE m.idu=a.idu
                      AND m.groupe=ANY(:pub) LIMIT 1) AS proprio_public,
                   (SELECT b.name FROM _inv_bpe b WHERE ({enssup} OR {hopital})
                      AND ST_Intersects(b.g,a.g) ORDER BY b.dom LIMIT 1) AS equipement
            FROM _inv_ab a
            WHERE EXISTS (SELECT 1 FROM parcelle_personne_morale m WHERE m.idu=a.idu AND m.groupe=ANY(:pub))
               OR EXISTS (SELECT 1 FROM _inv_bpe b WHERE ({enssup} OR {hopital}) AND ST_Intersects(b.g,a.g))
            ORDER BY a.surf DESC LIMIT 15"""), {"pub": list(PUBLIC)}).fetchall()

        # ventilation du propriétaire public par groupe DGFiP.
        par_groupe = cx.execute(text("""
            SELECT m.groupe, m.groupe_label, count(DISTINCT a.idu)
            FROM _inv_ab a JOIN parcelle_personne_morale m ON m.idu=a.idu AND m.groupe=ANY(:pub)
            GROUP BY m.groupe, m.groupe_label ORDER BY 3 DESC"""), {"pub": list(PUBLIC)}).fetchall()

        # DO0049 : le cas d'école.
        do = cx.execute(text(f"""
            SELECT s.band, s.score, s.additional_m2, round(ST_Area(p.geom_2975)) surf,
                   (SELECT groupe_label||' — '||denomination FROM parcelle_personne_morale WHERE idu=s.idu LIMIT 1) proprio
            FROM parcel_scenario_v2_runs s JOIN parcels p ON p.idu=s.idu
            WHERE s.idu='97411000DO0049' AND s.scenario='keep' AND s.run_label=:r"""), {"r": RUN}).fetchone()
        do_equip = cx.execute(text("""
            SELECT b.name, b.dom FROM _inv_bpe b JOIN parcels p ON p.idu='97411000DO0049'
            WHERE ST_Intersects(b.g, p.geom_2975) AND b.dom IN ('C','D') ORDER BY b.dom LIMIT 8""")).fetchall()

    fr = lambda x: f"{int(x):,}".replace(",", " ")                 # espace fine insécable
    pc = lambda x: f"{x/total*100:.1f} %" if total else "—"
    md = []
    md.append("# ECRANS-NOV-2 (recette 2, point 7) — foncier public & équipements publics parmi les mieux classées\n")
    md.append("**Rapport chiffré, aucune correction du moteur** (la règle sera décidée ensuite). Run servi "
              f"`{RUN}`, conservation (bâti conservé), parcelles **estimées Excellente / Bonne** de l'île.\n")
    md.append("## 1. Le cas d'école — 97411000DO0049 (3 Allée des Étudiants, Saint-Denis)\n")
    if do:
        md.append(f"- Classement : **{do.band} (score {do.score})**, capacité additionnelle **+{fr(do.additional_m2)} m²** "
                  f"de plancher, sur **{fr(do.surf)} m²** (≈ {do.surf/10000:.1f} ha).")
        md.append(f"- Propriétaire : **{do.proprio}** (groupe DGFiP public).")
        if do_equip:
            noms = " · ".join(f"{e.name} ({e.dom})" for e in do_equip)
            md.append(f"- Ce qui l'occupe (BPE sur l'emprise) : {noms}.")
        md.append("- Le calcul ne connaît ni le propriétaire ni l'usage public : il voit une grande parcelle en zone "
                  "U peu bâtie au regard du PLU et en déduit un fort résiduel. **C'est un campus de lycées de la Région, "
                  "pas un terrain à bâtir.**\n")
    md.append("## 2. Combien de cas analogues sur l'île ?\n")
    md.append(f"- Parcelles **Excellente + Bonne** (estimées, conservation) : **{fr(total)}**.")
    md.append(f"- Dont **propriétaire PUBLIC** (État / collectivité / établissement public ; groupes DGFiP 1-4 et 9) : "
              f"**{fr(pub)}** ({pc(pub)}).")
    md.append(f"- Dont portant **≥ 1 équipement BPE** (tous domaines) : **{fr(any_bpe)}** ({pc(any_bpe)}) ; "
              f"enseignement **{fr(ens)}** ; santé **{fr(sante)}**.")
    md.append(f"- Dont portant un **lycée / collège / enseignement supérieur** (BPE C2–C5) : **{fr(lycee)}** ({pc(lycee)}) ; "
              f"un **hôpital** (BPE D1) : **{fr(hop)}** ({pc(hop)}).")
    md.append(f"- **Public OU équipement d'enseignement/santé** (union) : **{fr(pub_ou_equip)}** ({pc(pub_ou_equip)}).\n")
    md.append("### Propriétaire public, par groupe DGFiP\n")
    md.append("| Groupe | Libellé | Parcelles Excellente/Bonne |")
    md.append("|---|---|---:|")
    for g in par_groupe:
        md.append(f"| {g.groupe} | {g.groupe_label} | {fr(g[2])} |")
    md.append("\n### Exemples (les plus grandes) — propriétaire public OU lycée/collège/université/hôpital\n")
    md.append("| IDU | Bande | Commune | Surface m² | Propriétaire public | Équipement |")
    md.append("|---|---|---|---:|---|---|")
    for e in ex:
        md.append(f"| {e.idu} | {e.band} | {e.commune} | {fr(e.surf)} | {e.proprio_public or '—'} | {e.equipement or '—'} |")
    md.append("\n## 3. Lecture\n")
    md.append("Une part non négligeable des parcelles les mieux classées est du **foncier public** ou porte un "
              "**équipement public** : ni l'un ni l'autre n'est un terrain à bâtir pour un promoteur privé. Le moteur "
              "ne lit aujourd'hui ni le propriétaire ni l'usage ; il mesure un résiduel réglementaire. **Décision à "
              "prendre (hors de ce rapport) :** exclure, ou signaler (badge « foncier public » / « équipement public ») "
              "ces parcelles dans l'analyse par scénario.\n")

    out = "docs/audit-2026-11/ecrans-nov-2/INVESTIGATION-FONCIER-PUBLIC.md"
    with open(out, "w") as f:
        f.write("\n".join(md) + "\n")
    print("écrit :", out)
    print("\n".join(md))


if __name__ == "__main__":
    main()
