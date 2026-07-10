"""Backtest Score V (Phase 5) — le score prédit-il la vente ?

Cohorte : parcelles 974 VENDUES (DVF nature 'Vente', 2023-01 → 2025-12) vs échantillon
NON-VENDUES stratifié par commune (4× les vendues, seed fixe — reproductible). Pour chaque
parcelle, V est RECALCULÉ à T−12 mois avant la vente (vendues) ou à la date médiane des
ventes −12 mois (non-vendues), en ne retenant que les signaux DATÉS ANTÉRIEURS à T.

⚠ Caveats structurels (documentés au rapport, à lire avant tout usage commercial) :
 - DGFiP PM = millésime 2025 (courant) : pour une vente 2023-2025, le fichier peut déjà
   porter l'ACHETEUR → fuite temporelle sur les familles A/B/C (sens de la fuite : elle
   DÉGRADE plutôt le lift, l'acheteur récent n'ayant pas de signaux de détresse).
 - Fenêtre DVF observable 2021+ : la tenure OBS5 à T (2022-2024) est tronquée.
 - Cartofriches / siège : millésime courant (pas d'historique public).

Métrique : LIFT du décile V supérieur = taux de vente (top 10 % V) / taux de vente (cohorte).
Cible ≥ 2×. Si < 1.5× → à noter EN GRAS : poids à retravailler avant usage commercial.

Usage : LABUSE_DATABASE_URL=… .venv/bin/python scripts/score-v/backtest.py
Sorties : reports/score-v/backtest.md, backtest_cohorte.csv, backtest_lift.svg
"""
from __future__ import annotations

import csv
import random
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.scoring import score_v_constants as C  # noqa: E402
from labuse.scoring.score_v import (  # noqa: E402
    _load_denom_lookups,
    _load_enrichments,
    _load_friches,
    _load_owner_links,
    _retain,
    _signal,
    _tenure_qualifiee,
    classify_owner,
    resolve_owner,
)

SEED = 974
SAMPLE_FACTOR = 4          # non-vendues échantillonnées = 4× vendues (par commune)
VENTE_DEBUT, VENTE_FIN = date(2023, 1, 1), date(2025, 12, 31)
OUT = Path(__file__).resolve().parents[2] / "reports" / "score-v"

_RX_CLOTURE = re.compile(r"cl[oô]ture")
_RX_LJ = re.compile(r"liquidation judiciaire")
_RX_RJ = re.compile(r"redressement judiciaire")
_RX_SAUV = re.compile(r"sauvegarde")
_RX_PLAN = re.compile(r"plan de (redressement|sauvegarde|continuation)")


def months_before(d: date, months: int) -> date:
    return d - timedelta(days=round(months * 30.44))


def famille_a_at(annonces: list[dict], t: date) -> int:
    """Points famille A à la date t (signaux datés ≤ t uniquement) — miroir daté du moteur."""
    pcl = [a for a in annonces if a["famille"] == "pcl" and a["date"] and a["date"] <= t]

    def opened(rx, no=()):  # dernière ouverture non suivie d'un événement « no » avant t
        cands = [a for a in pcl if rx.search(a["nature"])
                 and not _RX_CLOTURE.search(a["nature"]) and not _RX_PLAN.search(a["nature"])]
        if not cands:
            return None
        last = max(cands, key=lambda a: a["date"])
        for stop_rx in no:
            if any(stop_rx.search(a["nature"]) and a["date"] > last["date"] for a in pcl):
                return None
        return last

    best = 0
    lj = [a for a in pcl if _RX_LJ.search(a["nature"]) and not _RX_CLOTURE.search(a["nature"])]
    if lj:
        last = max(lj, key=lambda a: a["date"])
        clot = any(_RX_CLOTURE.search(a["nature"]) and a["date"] > last["date"] for a in pcl)
        best = max(best, 30 if clot else 35)
    if opened(_RX_RJ, no=(_RX_CLOTURE, _RX_PLAN, _RX_LJ)):
        best = max(best, 30)
    if opened(_RX_SAUV, no=(_RX_CLOTURE, _RX_PLAN)):
        best = max(best, 20)
    if any(a["famille"] == "radiation" and a["date"]
           and months_before(t, C.RADIATION_WINDOW_MONTHS) <= a["date"] <= t for a in annonces):
        best = max(best, 25)
    if any(a["famille"] == "vente_cession" and a["date"]
           and months_before(t, C.CESSION_FONDS_WINDOW_MONTHS) <= a["date"] <= t for a in annonces):
        best = max(best, 10)
    return best


def score_at(t: date, idu: str, owner, fiche, ages_ym: dict[str, str], annonces,
             friches, mutations: list[tuple[date, str]]) -> int | None:
    """V recalculé à la date t. None = non applicable (public/bailleur)."""
    otype = owner["owner_type"] if owner else "pp"
    if otype in ("public", "bailleur"):
        return None
    cands: list[dict] = []
    matched = bool(owner and owner.get("siren") and owner.get("confiance"))
    factor = (C.FALLBACK_AFFECTED_FAMILIES
              if (matched and owner["confiance"] == C.CONF_DENOMINATION) else None)
    m = {"type": "bt", "valeur": idu, "confiance": 1.0}
    # v1.1 : grands groupes (GE/ETI) → familles B et C supprimées (miroir du moteur).
    grand_groupe = bool(fiche and fiche.get("categorie_entreprise") in C.GRANDS_GROUPES_CATEGORIES)
    if matched:
        a_pts = famille_a_at(annonces or [], t)
        if a_pts:  # code porteur du même nombre de points (le détail importe peu au backtest)
            code = {35: "BODACC_LJ", 30: "BODACC_RJ", 25: "BODACC_RADIATION",
                    20: "BODACC_SAUVEGARDE", 10: "BODACC_CESSION_FONDS"}[a_pts]
            cands.append(_signal(code, source="BT", match=m))
        # B — cessation datée ≤ t seulement (une cessation non datée serait de la fuite)
        if grand_groupe:
            pass
        elif fiche and fiche.get("etat_administratif") == "C" and fiche.get("date_fermeture"):
            try:
                if date.fromisoformat(fiche["date_fermeture"]) <= t:
                    cands.append(_signal("RNE_CESSATION", source="BT", match=m))
            except ValueError:
                pass
        ym = ages_ym.get(owner["siren"])
        if ym and not grand_groupe:
            age_t = t.year - int(ym[:4]) - (1 if t.month < int(ym[5:7] or 12) else 0)
            code = ("RNE_DIRIGEANT_75" if age_t >= 75 else "RNE_DIRIGEANT_70" if age_t >= 70
                    else "RNE_DIRIGEANT_65" if age_t >= 65 else None)
            if code:
                cands.append(_signal(code, source="BT", match=m))
        if fiche and fiche.get("date_creation") and not grand_groupe:
            est_sci = str(fiche.get("nature_juridique")) == "6540" or "SCI" in (owner.get("forme") or "")
            try:
                creation = date.fromisoformat(fiche["date_creation"])
                if est_sci and creation <= t.replace(year=t.year - C.SCI_DORMANTE_AGE_ANS):
                    cands.append(_signal("RNE_SCI_DORMANTE", source="BT", match=m))
            except ValueError:
                pass
        # C — siège (millésime courant, caveat fuite documenté)
        if fiche and not grand_groupe:
            siege = fiche.get("siege") or {}
            if siege.get("code_pays_etranger") or (siege.get("departement") and siege["departement"] != "974"):
                cands.append(_signal("GEO_HORS_ILE", source="BT", match=m))
            elif siege.get("commune_insee") and siege["commune_insee"] != idu[:5]:
                cands.append(_signal("GEO_AUTRE_COMMUNE", source="BT", match=m))
    if idu in friches:   # millésime courant (caveat)
        cands.append(_signal("FRICHE", source="BT", match=m))
    antecedentes = [d for d, _ in mutations if d <= t]
    # v1.1 : tenure CONDITIONNELLE (miroir du moteur) — seule = 0 pt.
    if not antecedentes and _tenure_qualifiee(cands):
        cands.append(_signal("DVF_TENURE_OBS5", source="BT", match=m))
    retained, total = _retain(cands, factor)
    if antecedentes and max(antecedentes) >= months_before(t, C.ACHAT_RECENT_WINDOW_MONTHS):
        total += C.MALUS_ACHAT_RECENT[1]   # v1.1 : 0 (neutralisé — contre-prédictif au backtest v1)
    return max(0, min(100, total))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    with session_scope() as s:
        links = {lk["idu"]: lk for lk in _load_owner_links(s)}
        lookups = _load_denom_lookups(s)
        fiches = _load_enrichments(s)
        friches = _load_friches(s)
        # âges : YYYY-MM de l'aîné (recalcul à T possible, contrairement à la vue)
        ages_ym: dict[str, str] = {}
        for siren, ym in s.execute(text(
                "SELECT siren, min(date_naissance) FROM ("
                "  SELECT siren, date_naissance FROM pm_dirigeants "
                "    WHERE type_personne='INDIVIDU' AND date_naissance IS NOT NULL "
                "  UNION ALL SELECT siren, date_naissance FROM pm_dirigeant_gigogne "
                "    WHERE date_naissance IS NOT NULL) x GROUP BY siren")).all():
            ages_ym[siren] = ym
        bodacc: dict[str, list[dict]] = defaultdict(list)
        for siren, fam, nature, d in s.execute(text(
                "SELECT siren, famille, COALESCE(nature,''), date_annonce "
                "FROM bodacc_annonces_owner")).all():
            bodacc[siren].append({"famille": fam, "nature": nature.lower(), "date": d})
        mutations: dict[str, list[tuple[date, str]]] = defaultdict(list)
        for idu, d, nat in s.execute(text(
                "SELECT id_parcelle, date_mutation, nature_mutation FROM dvf_mutations_parcelle "
                "WHERE date_mutation IS NOT NULL")).all():
            mutations[idu].append((d, nat))
        ventes: dict[str, date] = {}   # première vente de la fenêtre par parcelle
        for idu, d in s.execute(text(
                "SELECT id_parcelle, min(date_mutation) FROM dvf_mutations_parcelle "
                "WHERE nature_mutation='Vente' AND date_mutation BETWEEN :a AND :b "
                "GROUP BY id_parcelle"), {"a": VENTE_DEBUT, "b": VENTE_FIN}).all():
            ventes[idu] = d
        all_parcels: dict[str, list[str]] = defaultdict(list)   # insee → idus non vendues
        for (idu,) in s.execute(text("SELECT idu FROM parcels")).all():
            if idu not in ventes:
                all_parcels[idu[:5]].append(idu)

        # échantillon non-vendues STRATIFIÉ commune (même distribution que les vendues)
        sold_by_insee: dict[str, int] = defaultdict(int)
        for idu in ventes:
            sold_by_insee[idu[:5]] += 1
        temoin: list[str] = []
        for insee, n in sold_by_insee.items():
            pool = all_parcels.get(insee, [])
            temoin.extend(rng.sample(pool, min(len(pool), n * SAMPLE_FACTOR)))
        t_ref = months_before(sorted(ventes.values())[len(ventes) // 2], 12)

        owners = {}
        for idu in set(list(ventes) + temoin):
            lk = links.get(idu)
            if lk:
                res = resolve_owner(lk, lookups)
                fiche = fiches.get(res["siren"]) if res["siren"] else None
                owners[idu] = {**res, "owner_type": classify_owner(lk, res["siren"], fiche),
                               "forme": lk["forme"]}

        rows = []
        for idu, d_vente in ventes.items():
            t = months_before(d_vente, 12)
            ow = owners.get(idu)
            fiche = fiches.get(ow["siren"]) if ow and ow.get("siren") else None
            v = score_at(t, idu, ow, fiche, ages_ym, bodacc.get(ow["siren"]) if ow and ow.get("siren") else [],
                         friches, mutations.get(idu, []))
            rows.append({"idu": idu, "vendue": 1, "t": t.isoformat(), "v": v})
        for idu in temoin:
            ow = owners.get(idu)
            fiche = fiches.get(ow["siren"]) if ow and ow.get("siren") else None
            v = score_at(t_ref, idu, ow, fiche, ages_ym, bodacc.get(ow["siren"]) if ow and ow.get("siren") else [],
                         friches, mutations.get(idu, []))
            rows.append({"idu": idu, "vendue": 0, "t": t_ref.isoformat(), "v": v})

    # ── lift par décile (V NULL exclus : non applicables) ──
    # ⚠ ÉGALITÉS MASSIVES : à T, beaucoup de parcelles partagent le même V (ex. 8 = tenure
    # seule). Un tri stable mettrait les vendues en tête des ex æquo (ordre d'assemblage) et
    # fabriquerait un faux lift — on MÉLANGE (seed fixe) avant le tri pour que la coupe des
    # déciles soit neutre dans les blocs d'égalité.
    scored = [r for r in rows if r["v"] is not None]
    rng.shuffle(scored)
    scored.sort(key=lambda r: r["v"], reverse=True)
    base_rate = sum(r["vendue"] for r in scored) / len(scored)
    n10 = max(1, len(scored) // 10)
    deciles = []
    for i in range(10):
        chunk = scored[i * n10:(i + 1) * n10] if i < 9 else scored[9 * n10:]
        rate = sum(r["vendue"] for r in chunk) / max(1, len(chunk))
        deciles.append({"decile": i + 1, "n": len(chunk), "v_min": chunk[-1]["v"] if chunk else 0,
                        "v_max": chunk[0]["v"] if chunk else 0, "taux_vente": rate,
                        "lift": rate / base_rate if base_rate else 0.0})
    lift_top = deciles[0]["lift"]
    # Métrique complémentaire SANS artefact de coupe : lift par BANDE de score (les seuils
    # sont ceux du produit, pas une coupe arbitraire dans des ex æquo).
    bandes = []
    for label, lo, hi in [("V ≥ 50 (fort)", 50, 101), ("V 25-49 (présents)", 25, 50),
                          ("V 9-24 (faible, au-delà de la tenure seule)", 9, 25),
                          ("V = 8 (tenure seule)", 8, 9), ("V 0-7", 0, 8)]:
        grp = [r for r in scored if lo <= r["v"] < hi]
        if not grp:
            continue
        rate = sum(r["vendue"] for r in grp) / len(grp)
        bandes.append({"bande": label, "n": len(grp), "taux": rate,
                       "lift": rate / base_rate if base_rate else 0.0})

    with open(OUT / "backtest_cohorte.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "vendue", "t", "v"])
        w.writeheader()
        w.writerows(rows)

    # graphe de lift (SVG autoporteur, aucune dépendance)
    bw, gap, h0 = 60, 12, 220
    bars = []
    mx = max(d["lift"] for d in deciles) or 1
    for i, d in enumerate(deciles):
        bh = round(d["lift"] / mx * 180)
        x = 40 + i * (bw + gap)
        col = "#FF8A50" if i == 0 else "#5CE6A1"
        bars.append(f'<rect x="{x}" y="{h0 - bh}" width="{bw}" height="{bh}" fill="{col}"/>'
                    f'<text x="{x + bw / 2}" y="{h0 + 16}" text-anchor="middle" font-size="11" fill="#8FA69A">D{d["decile"]}</text>'
                    f'<text x="{x + bw / 2}" y="{h0 - bh - 6}" text-anchor="middle" font-size="11" fill="#C9DCD1">{d["lift"]:.2f}×</text>')
    y2 = h0 - round(2 / mx * 180)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{40 + 10 * (bw + gap) + 20}" height="270" '
           f'style="background:#0B100D;font-family:monospace">'
           f'<text x="40" y="24" font-size="13" fill="#C9DCD1">Lift du taux de vente par décile de Score V '
           f'(D1 = top 10 %) — cible ≥ 2×</text>'
           + (f'<line x1="35" y1="{y2}" x2="{40 + 10 * (bw + gap)}" y2="{y2}" stroke="#E8B44C" '
              f'stroke-dasharray="4 3"/><text x="{45 + 10 * (bw + gap) - 60}" y="{y2 - 4}" font-size="10" '
              f'fill="#E8B44C">cible 2×</text>' if mx >= 2 else "")
           + "".join(bars) + "</svg>")
    (OUT / "backtest_lift.svg").write_text(svg)

    verdict = ("✅ **Cible atteinte** (lift ≥ 2×)." if lift_top >= 2.0 else
               "⚠ Sous la cible 2× mais ≥ 1.5× — signal réel, calibration à affiner." if lift_top >= 1.5 else
               "🔴 **LIFT < 1.5× : poids à retravailler avant tout usage commercial du score.**")
    md = [
        "# Backtest Score V — lift du décile supérieur\n",
        f"- Cohorte : **{sum(r['vendue'] for r in rows)}** parcelles vendues (DVF 'Vente' "
        f"{VENTE_DEBUT} → {VENTE_FIN}) vs **{len(rows) - sum(r['vendue'] for r in rows)}** non-vendues "
        f"(stratifiées commune, ×{SAMPLE_FACTOR}, seed {SEED}).",
        f"- Recalcul V à **T−12 mois** avant vente (signaux datés ≤ T uniquement) ; non-vendues à T réf. "
        f"= {t_ref} (médiane des ventes −12 mois). {len(rows) - len(scored)} parcelles V=NULL exclues "
        "(publics/bailleurs).",
        f"- Taux de vente de base : {base_rate:.3f}.",
        f"\n## Résultat : lift top décile = **{lift_top:.2f}×**\n\n{verdict}\n",
        "| Décile | V min–max | n | Taux de vente | Lift |", "|---|---|---|---|---|",
    ]
    for d in deciles:
        md.append(f"| D{d['decile']} | {d['v_min']}–{d['v_max']} | {d['n']} | {d['taux_vente']:.3f} | "
                  f"**{d['lift']:.2f}×** |")
    md += ["\n## Lift par bande de score (coupe produit, sans artefact d'ex æquo)\n",
           "| Bande | n | Taux de vente | Lift |", "|---|---|---|---|"]
    for b in bandes:
        md.append(f"| {b['bande']} | {b['n']} | {b['taux']:.3f} | **{b['lift']:.2f}×** |")
    md += [
        "\n![lift](backtest_lift.svg)\n",
        "## Caveats (à lire avant tout usage commercial)",
        "- **DGFiP PM = millésime 2025** : pour une vente 2023-2025, le fichier peut déjà porter "
        "l'acheteur → fuite temporelle familles A/B/C (elle joue plutôt CONTRE le lift).",
        "- Fenêtre DVF 2021+ : tenure OBS5 tronquée à T (2-4 ans d'observation).",
        "- Friches et siège : millésimes courants, pas d'historique public.",
        "- Famille E (DPE) non testée à T−12 : 43 F/G sur l'île — volume insuffisant pour peser.",
    ]
    (OUT / "backtest.md").write_text("\n".join(md))
    print(f"lift_top={lift_top:.2f}x  base={base_rate:.3f}  cohorte={len(rows)} "
          f"(vendues {sum(r['vendue'] for r in rows)})")
    print(f"→ {OUT / 'backtest.md'}")


if __name__ == "__main__":
    main()
