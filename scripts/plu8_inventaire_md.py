#!/usr/bin/env python3
"""Génère docs/audit-2026-10/plu-calibrage-8/INVENTAIRE.md depuis /tmp/plu8_inv.json (Lot A)."""
import json

d = json.load(open("/tmp/plu8_inv.json"))
Z = d["zones"]


def nature(x):
    c, cm = x["cause"], x["cause_moteur"]
    zl = x["zone"].lower()
    if c == "silence_total":
        return "structurel"
    if c == "forme_non_modelisee":
        if "plage" in cm or "table graphique" in cm or "prospect" in cm:
            return "structurel"
        if "avap" in zl or "aucune hauteur" in cm:
            return "a_verifier"
        return "calibrable"
    if c == "absente_yaml":
        return "structurel" if ("oap" in zl or zl.endswith("fe")) else "calibrable"
    return "calibrable"  # feuille_propose, renvoi_au_u_absent


for x in Z:
    x["nature"] = nature(x)

CAUSE_LBL = {
    "forme_non_modelisee": "forme non modélisée",
    "renvoi_au_u_absent": "renvoi AU→U non résolu",
    "absente_yaml": "zone absente du YAML",
    "silence_total": "silence total du règlement",
    "feuille_propose": "feuille `propose` (non validée)",
}
NAT_LBL = {"calibrable": "✅ calibrable (schéma actuel)",
           "structurel": "⛔ structurel (hors schéma actuel)",
           "a_verifier": "🟡 à vérifier (renvoi AVAP/doc annexe)"}

out = []
w = out.append

w("# PLU-CALIBRAGE-8 (oct. 2026) — Lot A · Inventaire des zones sans gabarit servable\n")
w("Branche `feat/plu-calibrage-8` · worktree `~/Desktop/labuse-plu8` · base main `3f473aa3`. "
  "Lecture seule, aucune écriture. Point de départ : `docs/audit-2026-10/chasse-calculs-1/"
  "LOT5-GABARIT-INCOMPLETS.md` (39 % des Gabarits incomplets = zones PLU non calibrées).\n")

w("## Méthode\n")
w("`scripts/plu8_inventaire.py` (lecture seule) énumère, pour chaque `(commune, zone_lib)` portée par "
  "des parcelles en famille **U/AU** (les seules qui reçoivent un Gabarit), et **reproduit à "
  "l'identique la décision de blocage AU NIVEAU ZONE du moteur `gabarit/builder.py`** — la seule part "
  "« donnée PLU » (E-C2), indépendante de la géométrie par parcelle (façade, limites non qualifiées, "
  "multi-zone, parcelle enclavée : ces causes-là, 47 % du LOT5, ne relèvent PAS de la calibration PLU "
  "et ne figurent donc pas ici).\n")
w("Une zone est **servable** (gabarit non bloqué au niveau zone) ssi : `resolve_zone` ≠ None, pas de "
  "`regle_non_validee` (feuille SDP `propose` portant une valeur), `calibree=True`, pas de silence "
  "total, **hauteur exploitable** (faîtage OU égout chiffré, OU faîtage validé non chiffré) ET "
  "**emprise exploitable** (CES chiffré OU silence prouvé `absent`). Les reculs, eux, ne bloquent "
  "jamais le gabarit (builder.py ne les érige pas en gate).\n")
w(f"« À potentiel » = `sdp_residuelle_m2 > 0` dans le run servi **{d['run']}** (bandes A–D). "
  "Règlements : `data/plu_reglements/` est vide dans le dépôt ; les PDF sont retéléchargeables du GPU "
  "(URL + md5 dans le `meta` de chaque YAML — md5 vérifié sur un échantillon, HTTP 200).\n")

w("## Résultat\n")
w(f"**{d['n_zones_non_servables']} zones** U/AU ne produisent pas de gabarit servable, couvrant "
  f"**{d['n_parcelles_touchees']} parcelles** dont **{d['n_potentiel_touche']} à potentiel**. "
  "La liste dépasse 60 zones → **STOP, Vic choisit le périmètre** (règle du mandat).\n")

# tableau par cause
w("### Par cause (taxonomie du mandat)\n")
w("| Cause | Zones | Parcelles | À potentiel |\n|---|--:|--:|--:|")
pc = d["par_cause"]
for c, v in sorted(pc.items(), key=lambda kv: -kv[1]["potentiel"]):
    w(f"| {CAUSE_LBL.get(c, c)} | {v['zones']} | {v['parcelles']} | {v['potentiel']} |")
w("")

# tableau par nature
w("### Par nature (calibrable avec le schéma actuel ?)\n")
agg = {}
for x in Z:
    a = agg.setdefault(x["nature"], [0, 0, 0])
    a[0] += 1; a[1] += x["n_parcelles"]; a[2] += x["n_potentiel"]
w("| Nature | Zones | Parcelles | À potentiel | Lecture |\n|---|--:|--:|--:|---|")
LECT = {
    "calibrable": "cible Lot B : renvoi AU→U à câbler, CES à transcrire, feuille `propose` à valider",
    "structurel": "hauteur en table graphique / prospect / silence total / OAP — exigent une **extension "
                  "de schéma** (décision Vic séparée) : hors de ce mandat tel que cadré",
    "a_verifier": "Saint-Denis Uavap : le règlement renvoie INTÉGRALEMENT à l'AVAP annexée (doc patrimonial "
                  "séparé) — rien de chiffré à transcrire depuis le règlement",
}
for n in ("calibrable", "structurel", "a_verifier"):
    if n in agg:
        v = agg[n]
        w(f"| {NAT_LBL[n]} | {v[0]} | {v[1]} | {v[2]} | {LECT[n]} |")
w("")
w("> ⚠️ Nuance sur les 63 « renvoi AU→U non résolu » : une zone AU n'est réellement calibrable que si "
  "sa zone U de rattachement est (ou devient) servable. Celles dont le parent U est structurel "
  "(ex. Saint-Benoît AUb19 → Ub en table graphique) héritent du blocage → à re-trancher zone par zone "
  "en Lot B.\n")

# recommandation périmètre
w("## Périmètre recommandé (à l'arbitrage de Vic)\n")
w(f"1. **Structurel ({agg['structurel'][0]} z / {agg['structurel'][2]} pot.)** — NE PAS calibrer dans ce mandat : table graphique "
  "(Saint-Benoît Ua/Ub/Ue…), prospect, silence total (Le Port Uv/Up…), OAP. Rendement = 0 sans "
  "extension de schéma, que le mandat interdit sans STOP dédié. Rapportées « non calculable : "
  "hauteur hors schéma / silence du règlement ».\n")
w("2. **Uavap (Saint-Denis, 790 pot.)** — renvoi intégral à l'AVAP annexée : rien à transcrire du "
  "règlement, laisser en l'état.\n")
w("3. **Calibrable, par ordre de potentiel décroissant** — cible naturelle de Lot B, concentrée sur "
  "~8 communes (le règlement se lit par commune) : les renvois AU→U dont le parent U est déjà servable, "
  "les zones « CES seule manquante » (hauteur déjà OK), et les 3 feuilles `propose` (dont U1pru = Lot C).\n")

# détail calibrable groupé par commune
w("### Détail « calibrable » par commune\n")
cal = [x for x in Z if x["nature"] == "calibrable"]
by = {}
for x in cal:
    by.setdefault(x["commune"], []).append(x)
w("| Commune | Zones (potentiel) | Σ potentiel |\n|---|---|--:|")
for cm, xs in sorted(by.items(), key=lambda kv: -sum(a["n_potentiel"] for a in kv[1])):
    xs.sort(key=lambda a: -a["n_potentiel"])
    lst = ", ".join(f"{a['zone']} ({a['n_potentiel']})" for a in xs)
    w(f"| {cm} | {lst} | {sum(a['n_potentiel'] for a in xs)} |")
w("")

# table complète
w("## Inventaire complet (111 zones, tri potentiel ↓)\n")
w("| # | Commune | Zone | Fam | Parcelles | À pot. | Nature | Cause | Détail moteur | Règlement (millésime) |")
w("|---|---|---|---|--:|--:|---|---|---|---|")
for i, x in enumerate(Z, 1):
    nat = {"calibrable": "✅", "structurel": "⛔", "a_verifier": "🟡"}[x["nature"]]
    w(f"| {i} | {x['commune']} | {x['zone']} | {x['fam']} | {x['n_parcelles']} | {x['n_potentiel']} | "
      f"{nat} | {CAUSE_LBL.get(x['cause'], x['cause'])} | {x['cause_moteur']} | "
      f"{x['reglement'] or '—'} ({x['millesime'] or '?'}) |")
w("")

open("docs/audit-2026-10/plu-calibrage-8/INVENTAIRE.md", "w", encoding="utf-8").write("\n".join(out))
print("written", len(out), "lines")
