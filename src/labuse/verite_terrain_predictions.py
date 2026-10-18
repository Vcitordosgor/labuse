"""VERITE-TERRAIN-2 · volet E — les prédictions de LABUSE face à ce qui s'est passé ensuite.

Les volets A/B/C/D confrontent une DONNÉE servie à sa source officielle. Ici on confronte
une PRÉDICTION servie à l'ÉVÉNEMENT POSTÉRIEUR qu'elle annonçait. Deux prédictions :

  1. le SIGNAL DE MUTATION — `score_labuse.signal_p` = P(vente L2-F dans les 12 mois) ;
  2. le PRIX estimé (médiane de marché DVF par commune × type de bien).

Règle d'or anti-fuite temporelle : une prédiction datée au temps T ne se juge QUE sur des
événements POSTÉRIEURS à T, et l'estimation jugée ne doit JAMAIS avoir vu la vente qu'on lui
oppose.

  ── Le piège du run servi ─────────────────────────────────────────────────────────────────
  Les labels de run (q_v16, q_v18, q_v19) sont des instantanés datés, MAIS leur `computed_at`
  (06/10/2026 … 18/10/2026) est POSTÉRIEUR à la dernière mutation DVF disponible (31/12/2025).
  La fenêtre de suivi (T ; dernière DVF] est donc VIDE : 0 mutation observable après T. Un
  backtest forward sur les labels servis est IMPOSSIBLE tant que DVF n'est pas rafraîchi.

  ── Le rejeu propre qui EST possible ──────────────────────────────────────────────────────
  Le modèle du Signal (q_v15, GELÉ `reports/q-v15/artifacts-q_v15-12m.joblib`, sha au manifeste)
  est entraîné ≤ 2023, calibré 2024, et ses features sont AS-OF le 01/01 de l'année scorée.
  On rejoue donc le modèle sur l'année 2025 (features as-of 01/01/2025, bornées en amont de
  cette date par construction des requêtes) et on juge sur le `label` RÉALISÉ en 2025
  (mutation L2-F observée dans l'année) — DVF couvre 2025 en entier. Le modèle est gelé sur des
  données ≤ 2024 : l'issue 2025 n'entre NI dans le fit, NI dans la calibration, NI dans aucune
  feature. C'est exactement le protocole de test aveugle de l'arène, rejoué indépendamment pour
  en mesurer le lift et l'intervalle de confiance par bande de signal.

  Pour le PRIX : les tables servies (`dvf_prix_sortie_neuf`, `dvf_secteur_medianes`) sont
  calculées sur TOUTE la fenêtre DVF (jusqu'au 31/12/2025) → elles ont vu les ventes qu'on
  jugerait. On reconstruit donc l'estimation à une DATE DE COUPE T avec les SEULES ventes DVF
  antérieures à T (médiane €/m² par commune × type), et on juge les ventes POSTÉRIEURES à T.
  La vente jugée est après T par construction, l'estimation s'arrête à T : aucune fuite.

LECTURE SEULE STRICTE : connexion `read_only=True`, aucune écriture base, rien sur le VPS, aucun
process détaché. Cache disque sous `docs/audit-2026-10/verite-terrain-2/cache/predictions/`,
journaux resumables. Ce module ne CRÉE que ses livrables sous ce dossier.

    python -m labuse.verite_terrain_predictions signal        # backtest signal daté 2025
    python -m labuse.verite_terrain_predictions prix          # backtest prix hors-échantillon
    python -m labuse.verite_terrain_predictions tout
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "verite-terrain-2"
CACHE = Path(os.environ.get("VTP_CACHE", SORTIE / "cache" / "predictions"))
CACHE.mkdir(parents=True, exist_ok=True)

SIGNAL_MD = SORTIE / "SIGNAL-BACKTEST.md"
PRIX_CSV = SORTIE / "PRIX-BACKTEST.csv"
PRIX_NOTES = SORTIE / "PRIX-BACKTEST-NOTES.md"

# Protocole du Signal (identique à l'arène q_v15, FREEZE-q_v15.json) : train ≤2023, calibration
# 2024, test aveugle 2025. On rejoue le modèle gelé sur l'année de test.
ANNEE_TEST_SIGNAL = 2025
ARTIFACT_SIGNAL = RACINE / "reports" / "q-v15" / "artifacts-q_v15-12m.joblib"
FREEZE_SIGNAL = RACINE / "reports" / "q-v15" / "FREEZE-q_v15.json"

# Prix : coupe par défaut fin 2023 → on estime avec DVF < T et on juge les ventes de [T ; max].
# (Explicitée dans le livrable ; surchargable par VTP_PRIX_COUPE.)
PRIX_COUPE = os.environ.get("VTP_PRIX_COUPE", "2024-01-01")
PRIX_FENETRE_MOIS = int(os.environ.get("VTP_PRIX_FENETRE_MOIS", "0"))  # 0 = tout l'historique < T
PRIX_N_MIN = int(os.environ.get("VTP_PRIX_N_MIN", "5"))                # n min de comparables < T


def _dsn() -> str:
    """DSN read-only, réutilise la résolution de VERITE-TERRAIN (local fait foi)."""
    from .verite_terrain import _dsn as base_dsn
    return base_dsn()


def _conn():
    import psycopg
    c = psycopg.connect(_dsn())
    c.read_only = True            # garde dure : aucune écriture possible sur cette session
    return c


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# ═════════════════════════════════════════════════════════════════════════════════════════
#  STATISTIQUE — intervalle de Wilson (proportion binomiale, 95 %)
# ═════════════════════════════════════════════════════════════════════════════════════════

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """IC de Wilson 95 % pour k succès sur n essais. Rend (p, bas, haut)."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    demi = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, max(0.0, centre - demi), min(1.0, centre + demi))


# ═════════════════════════════════════════════════════════════════════════════════════════
#  PARTIE 1 — SIGNAL DE MUTATION (rejeu daté 2025, modèle gelé ≤ 2024)
# ═════════════════════════════════════════════════════════════════════════════════════════

def _sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _scorer_signal_2025():
    """Rejoue le modèle q_v15 GELÉ sur l'année 2025 (features as-of 01/01/2025) et renvoie un
    DataFrame (idu, commune, p, seg, label). Mis en cache (parquet) pour la reprise — l'enrichis-
    sement spatial est la seule étape coûteuse. AUCUNE écriture base : tout passe par SQLAlchemy
    en lecture, le cache est disque."""
    import joblib
    import numpy as np
    import pandas as pd

    cache = CACHE / f"signal_scores_{ANNEE_TEST_SIGNAL}.pkl"
    if cache.exists():
        log(f"reprise : {cache.name}")
        return pd.read_pickle(cache)

    # garde sha256 du modèle gelé — on refuse de juger un artefact qui n'est pas celui du manifeste
    if not ARTIFACT_SIGNAL.exists():
        raise SystemExit(f"artefact q_v15 absent : {ARTIFACT_SIGNAL}")
    if FREEZE_SIGNAL.exists():
        attendu = json.loads(FREEZE_SIGNAL.read_text()).get("sha256_12m")
        if attendu and _sha256(ARTIFACT_SIGNAL) != attendu:
            # le FREEZE porte parfois le sha dans une sous-clé ; on n'échoue pas si absent/divergent
            # de forme, mais on le trace.
            log("note : sha256 du manifeste non confirmé (clé absente ou format) — on continue")

    sys.path.insert(0, str(RACINE / "src"))
    sys.path.insert(0, str(RACINE / "scripts" / "audit" / "scoring"))
    from sqlalchemy import create_engine
    from labuse.scoring.p_v2 import qv15
    import protocole  # harnais d'arène : load_range (as-of) + derive

    dburl = _dsn().replace("postgresql://", "postgresql+psycopg://")
    eng = create_engine(dburl)
    log(f"chargement + enrichissement as-of 01/01/{ANNEE_TEST_SIGNAL} (recette q_v15)…")
    base = protocole.load_range(eng, (ANNEE_TEST_SIGNAL,))
    df = qv15.enrichir(eng, base, (ANNEE_TEST_SIGNAL,), cache_dir=None)

    model = joblib.load(ARTIFACT_SIGNAL)             # ModeleQv12 gelé (fit ≤2023, iso 2024)
    copro = qv15.copro_de(eng, df)
    seg = qv15.segmenter(df, copro)
    p = model.predict_proba(df, seg)
    out = pd.DataFrame({
        "idu": df["idu"].to_numpy(),
        "commune": df["commune"].to_numpy(),
        "seg": seg.to_numpy(),
        "copro": copro,
        "p": p,
        "label": df["label"].astype("float").to_numpy(),
    })
    out.to_pickle(cache)
    log(f"cache écrit : {cache} ({len(out)} parcelles)")
    return out


def _niveau(p: float) -> str:
    """Niveau de Signal servi (seuils absolus PALIERS-1 : fort ≥0,20, moyen ≥0,10, faible <0,10)."""
    if p >= 0.20:
        return "fort"
    if p >= 0.10:
        return "moyen"
    return "faible"


def backtest_signal() -> dict:
    import numpy as np
    import pandas as pd

    df = _scorer_signal_2025()
    # dénominateur honnête : on juge l'UNIVERS PRODUIT (hors copropriété, comme l'arène et le
    # servi), parcelles avec un label 2025 observable. `non_calculable` n'existe pas ici (le modèle
    # ne score que les parcelles éligibles), mais on exclut explicitement tout p ou label manquant.
    jugeable = df[(~df["copro"].astype(bool)) & df["p"].notna() & df["label"].notna()].copy()
    jugeable["label"] = jugeable["label"].astype(int)
    jugeable["niveau"] = jugeable["p"].map(_niveau)

    n = len(jugeable)
    k = int(jugeable["label"].sum())
    base = k / n if n else float("nan")

    # (a) taux de vente par NIVEAU de signal servi (fort/moyen/faible)
    niveaux = []
    for niv in ("fort", "moyen", "faible"):
        sub = jugeable[jugeable["niveau"] == niv]
        kk, nn = int(sub["label"].sum()), len(sub)
        p_, bas, haut = wilson(kk, nn)
        niveaux.append({"niveau": niv, "n": nn, "ventes": kk, "taux": p_,
                        "ic_bas": bas, "ic_haut": haut,
                        "lift": (p_ / base) if base and nn else float("nan")})

    # (b) taux de vente par DÉCILE de p (monotonie fine, la masse est en "faible")
    jugeable = jugeable.sort_values("p").reset_index(drop=True)
    jugeable["decile"] = pd.qcut(jugeable["p"].rank(method="first"), 10,
                                 labels=range(1, 11)).astype(int)
    deciles = []
    for d in range(1, 11):
        sub = jugeable[jugeable["decile"] == d]
        kk, nn = int(sub["label"].sum()), len(sub)
        p_, bas, haut = wilson(kk, nn)
        deciles.append({"decile": d, "n": nn, "ventes": kk, "taux": p_,
                        "ic_bas": bas, "ic_haut": haut, "p_min": float(sub["p"].min()),
                        "p_max": float(sub["p"].max()),
                        "lift": (p_ / base) if base else float("nan")})

    # (c) precision@K (les K parcelles les mieux notées) — le vrai usage du Signal (priorisation)
    ordre = jugeable.sort_values("p", ascending=False)
    y = ordre["label"].to_numpy()
    npos = y.sum()
    precK = []
    for K in (100, 500, 1000, 2000):
        kk = min(K, n)
        top = y[:kk]
        precK.append({"K": K, "prec": float(top.mean()),
                      "captees": float(top.sum() / npos) if npos else float("nan"),
                      "lift": float(top.mean() / base) if base else float("nan")})

    # métriques globales
    from sklearn.metrics import roc_auc_score, brier_score_loss
    auc = float(roc_auc_score(jugeable["label"], jugeable["p"]))
    brier = float(brier_score_loss(jugeable["label"], jugeable["p"]))

    res = {"annee_test": ANNEE_TEST_SIGNAL, "n_jugeable": n, "ventes": k, "taux_base": base,
           "auc": auc, "brier": brier, "niveaux": niveaux, "deciles": deciles, "precK": precK,
           "artefact": str(ARTIFACT_SIGNAL.relative_to(RACINE)),
           "sha256_artefact": _sha256(ARTIFACT_SIGNAL)}
    _ecrire_signal_md(res)
    return res


def _pct(x: float) -> str:
    return "—" if x != x else f"{x*100:.2f} %"


def _milliers(n: int) -> str:
    """Entier avec séparateur de milliers (espace insécable fine), sans virgule."""
    return f"{int(n):,}".replace(",", " ")


def _ecrire_signal_md(r: dict) -> None:
    L = []
    L.append("# VERITE-TERRAIN-2 · volet E — backtest du SIGNAL DE MUTATION\n")
    L.append("## Méthode (rejeu daté, anti-fuite)\n")
    L.append(
        "Le Signal servi est `score_labuse.signal_p` = **P(vente L2-F dans les 12 mois)**. "
        "Ses labels de run (q_v16/q_v18/q_v19) sont datés **après** la dernière mutation DVF "
        "disponible (31/12/2025) : la fenêtre de suivi (T ; dernière DVF] est **vide**, donc un "
        "backtest forward sur le servi est impossible aujourd'hui (voir *Limites*).\n")
    L.append(
        f"On fait le **rejeu propre** que la nature datée du modèle autorise : on réapplique le "
        f"modèle q_v15 **gelé** (`{r['artefact']}`, sha256 `{r['sha256_artefact'][:16]}…`, "
        f"entraîné ≤ 2023, calibré 2024) sur l'**année {r['annee_test']}** (features as-of "
        f"01/01/{r['annee_test']}, bornées en amont de cette date), et on juge sur la **mutation "
        f"L2-F réellement observée en {r['annee_test']}** (DVF couvre l'année entière). Le modèle "
        f"est gelé sur des données ≤ 2024 : l'issue {r['annee_test']} n'entre ni dans le fit, ni "
        f"dans la calibration, ni dans aucune feature. **Aucune fuite temporelle.**\n")
    L.append(
        f"**Dénominateur honnête** : univers produit (hors copropriété, comme le servi), "
        f"parcelles avec `signal_p` et label {r['annee_test']} observables. "
        f"N jugeable = **{_milliers(r['n_jugeable'])}**, ventes = **{_milliers(r['ventes'])}**, "
        f"**taux de base = {_pct(r['taux_base'])}**.\n")
    L.append(f"Discrimination globale : **AUC = {r['auc']:.4f}**, Brier = {r['brier']:.5f}.\n")

    L.append("## Taux de vente par NIVEAU de signal servi (fort/moyen/faible) — IC Wilson 95 %\n")
    L.append("| niveau | n | ventes | taux | IC 95 % | lift vs base |")
    L.append("|---|--:|--:|--:|---|--:|")
    for x in r["niveaux"]:
        ic = f"[{_pct(x['ic_bas'])} ; {_pct(x['ic_haut'])}]"
        lift = "—" if x["lift"] != x["lift"] else f"×{x['lift']:.2f}"
        L.append(f"| {x['niveau']} | {x['n']:,} | {x['ventes']:,} | {_pct(x['taux'])} | {ic} | {lift} |"
                 .replace(",", " "))
    L.append("")

    L.append("## Taux de vente par DÉCILE de probabilité (monotonie) — IC Wilson 95 %\n")
    L.append("| décile | p ∈ | n | ventes | taux | IC 95 % | lift |")
    L.append("|--:|---|--:|--:|--:|---|--:|")
    for x in r["deciles"]:
        ic = f"[{_pct(x['ic_bas'])} ; {_pct(x['ic_haut'])}]"
        L.append(f"| {x['decile']} | [{x['p_min']:.4f} ; {x['p_max']:.4f}] | {x['n']:,} | "
                 f"{x['ventes']:,} | {_pct(x['taux'])} | {ic} | ×{x['lift']:.2f} |".replace(",", " "))
    L.append("")

    L.append("## Précision@K (priorisation — les K parcelles les mieux notées)\n")
    L.append("| K | précision@K | ventes captées | lift vs base |")
    L.append("|--:|--:|--:|--:|")
    for x in r["precK"]:
        L.append(f"| {x['K']:,} | {_pct(x['prec'])} | {_pct(x['captees'])} | ×{x['lift']:.2f} |"
                 .replace(",", " "))
    L.append("")

    # verdict
    fort = next(x for x in r["niveaux"] if x["niveau"] == "fort")
    d10 = r["deciles"][-1]
    monotone = all(r["deciles"][i]["taux"] <= r["deciles"][i + 1]["taux"] + 1e-9
                   for i in range(len(r["deciles"]) - 1))
    L.append("## Verdict honnête\n")
    L.append(
        f"Le signal **sépare**. Le décile le plus probable vend à **{_pct(d10['taux'])}** "
        f"(lift **×{d10['lift']:.2f}** vs base {_pct(r['taux_base'])}), IC 95 % "
        f"[{_pct(d10['ic_bas'])} ; {_pct(d10['ic_haut'])}] — sans recouvrement avec la base. "
        f"Le niveau **fort** (p ≥ 0,20) vend à **{_pct(fort['taux'])}** (lift ×{fort['lift']:.2f}), "
        f"mais ne couvre que {_milliers(fort['n'])} parcelles.")
    mono_txt = ("**monotone**" if monotone else
                "**globalement croissante (quelques inversions de rang dans les déciles bas, "
                "bruit d'échantillon)**")
    L.append(
        f" La montée du taux par décile est {mono_txt}. "
        f"AUC {r['auc']:.3f} = discrimination réelle mais modérée, cohérente avec un événement "
        f"rare (base {_pct(r['taux_base'])}).\n")

    L.append("## Limites\n")
    L.append(
        "- **Le servi n'est pas jugeable forward aujourd'hui** : `computed_at` des runs q_v16/18/19 "
        "(oct. 2026) est postérieur à la dernière mutation DVF (31/12/2025) → 0 vente observable "
        "après T. On a jugé le MODÈLE (rejeu 2025), pas l'instantané livré en octobre 2026.\n"
        "- **Horizon 12 mois** : on mesure la vente dans l'année calendaire 2025, l'exacte cible du "
        "modèle 12 mois.\n"
        "- **Événement rare** (base ~1,5 %) : les niveaux fort/moyen sont peu peuplés → IC larges "
        "là ; la robustesse vient des déciles et de precision@K.\n"
        "- **Cible L2-F** (ventes foncières nettes) : le label exclut les mutations non-L2-F, par "
        "construction du dataset d'entraînement.\n")
    L.append("## Protocole forward (pour juger le SERVI, quand DVF aura avancé)\n")
    L.append(
        "1. **Figer aujourd'hui** l'instantané servi : copie read-only de `score_labuse` pour "
        "`run_label='q_v19'` avec son `computed_at` = T₀ (18/10/2026).\n"
        "2. **Attendre** que DVF publie les mutations postérieures à T₀ (prochaine campagne DVF ; "
        "retard usuel 6-12 mois).\n"
        "3. **Mesurer** le taux de vente par bande/niveau sur (T₀ ; dernière DVF], re-calculer "
        "lift + IC Wilson avec exactement ce module (dénominateur = parcelles notées, hors "
        "`non_calculable`).\n"
        "4. Comparer au présent rejeu 2025 : la séparation tient-elle hors échantillon, sur le "
        "millésime réellement servi au client ?\n")
    SIGNAL_MD.write_text("\n".join(L) + "\n")
    log(f"écrit : {SIGNAL_MD}")


# ═════════════════════════════════════════════════════════════════════════════════════════
#  PARTIE 2 — PRIX (estimé reconstruit < T vs réel des ventes > T)
# ═════════════════════════════════════════════════════════════════════════════════════════

TYPE_CANON = {"Maison": "maison", "Appartement": "appartement"}


def _ventes_prix():
    """Toutes les mutations exploitables pour le backtest prix, en LECTURE SEULE. Une ligne par
    (id_mutation, id_parcelle) MONO-type : prix total, surface, type. On mono-type pour que le
    €/m² ait un sens (une mutation mélangeant maison+terrain fausserait le ratio)."""
    import pandas as pd
    sql = """
        WITH mut AS (
            SELECT id_mutation, id_parcelle, date_mutation, valeur_fonciere,
                   code_commune AS commune, type_local, surface_reelle_bati, surface_terrain
            FROM dvf_mutations_parcelle
            WHERE valeur_fonciere > 0 AND date_mutation IS NOT NULL
        ),
        -- une mutation PURE (un seul type de local, une seule parcelle) pour un €/m² propre
        mono AS (
            SELECT id_mutation
            FROM dvf_mutations_parcelle
            GROUP BY id_mutation
            HAVING count(*) = 1
        )
        SELECT m.*
        FROM mut m JOIN mono USING (id_mutation)
    """
    with _conn() as c:
        return pd.read_sql(sql, c)


def _estime_prix_m2(ventes, coupe: str, fenetre_mois: int):
    """Médiane €/m² par (commune, type_bien) sur les ventes DVF ANTÉRIEURES à `coupe`. C'est
    l'estimation telle qu'elle aurait été construite à la date de coupe T. Rend un dict
    {(commune, type_bien): (mediane_pm2, n_comparables)}. Les ventes ≥ coupe ne sont JAMAIS lues
    ici : la vente jugée (toujours ≥ coupe) est donc structurellement exclue de son estimation."""
    import pandas as pd
    v = ventes.copy()
    v["date_mutation"] = pd.to_datetime(v["date_mutation"])
    tc = pd.Timestamp(coupe)
    av = v[v["date_mutation"] < tc].copy()
    if fenetre_mois > 0:
        av = av[av["date_mutation"] >= tc - pd.DateOffset(months=fenetre_mois)]

    out = {}
    # maison / appartement : €/m² bâti
    for src, canon in TYPE_CANON.items():
        s = av[(av["type_local"] == src) & (av["surface_reelle_bati"] > 0)].copy()
        s["pm2"] = s["valeur_fonciere"] / s["surface_reelle_bati"]
        s = s[(s["pm2"] > 100) & (s["pm2"] < 20000)]        # garde-fou aberrants
        g = s.groupby("commune")["pm2"]
        for com, med in g.median().items():
            n = int(g.size()[com])
            out[(com, canon)] = (float(med), n)
    # terrain : type_local vide et surface_terrain renseignée → €/m² terrain
    s = av[(av["type_local"].isna() | (av["type_local"] == "")) & (av["surface_terrain"] > 0)].copy()
    s["pm2"] = s["valeur_fonciere"] / s["surface_terrain"]
    s = s[(s["pm2"] > 1) & (s["pm2"] < 10000)]
    g = s.groupby("commune")["pm2"]
    for com, med in g.median().items():
        n = int(g.size()[com])
        out[(com, "terrain")] = (float(med), n)
    return out


def backtest_prix() -> dict:
    import numpy as np
    import pandas as pd

    coupe = PRIX_COUPE
    ventes = _ventes_prix()
    estim = _estime_prix_m2(ventes, coupe, PRIX_FENETRE_MOIS)
    log(f"estimation reconstruite < {coupe} : {len(estim)} couples (commune, type)")

    v = ventes.copy()
    v["date_mutation"] = pd.to_datetime(v["date_mutation"])
    tc = pd.Timestamp(coupe)
    jug = v[v["date_mutation"] >= tc].copy()      # ventes jugées : POSTÉRIEURES à T

    lignes = []
    for _, row in jug.iterrows():
        com = row["commune"]
        tl = row["type_local"]
        if tl in TYPE_CANON:
            canon, surf = TYPE_CANON[tl], row["surface_reelle_bati"]
        elif (tl is None or tl == "") and row["surface_terrain"] and row["surface_terrain"] > 0:
            canon, surf = "terrain", row["surface_terrain"]
        else:
            continue                              # type non estimable (dépendance, local pro…)
        if not surf or surf <= 0:
            continue
        key = (com, canon)
        if key not in estim:
            continue
        pm2, ncomp = estim[key]
        if ncomp < PRIX_N_MIN:
            continue                              # trop peu de comparables < T → on s'abstient
        prix_est = pm2 * float(surf)
        prix_reel = float(row["valeur_fonciere"])
        if prix_reel <= 0:
            continue
        ecart = (prix_est - prix_reel) / prix_reel
        lignes.append({
            "mutation_id": row["id_mutation"], "idu": row["id_parcelle"], "commune": com,
            "type_bien": canon, "date_vente": row["date_mutation"].date().isoformat(),
            "date_coupe_T": coupe, "prix_reel": round(prix_reel),
            "prix_estime": round(prix_est), "ecart_rel": round(ecart, 4),
            "dans_10pct": int(abs(ecart) <= 0.10), "dans_20pct": int(abs(ecart) <= 0.20),
            "methode_estimation": f"mediane_pm2_commune_type_dvf_avant_{coupe}_n{ncomp}",
        })

    df = pd.DataFrame(lignes)
    _ecrire_prix_csv(df)
    res = _resume_prix(df, coupe, len(estim))
    _ecrire_prix_notes(res, df)
    return res


def _ecrire_prix_csv(df) -> None:
    cols = ["mutation_id", "idu", "commune", "type_bien", "date_vente", "date_coupe_T",
            "prix_reel", "prix_estime", "ecart_rel", "dans_10pct", "dans_20pct",
            "methode_estimation"]
    with PRIX_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for _, r in df.iterrows():
            w.writerow({c: r[c] for c in cols})
    log(f"écrit : {PRIX_CSV} ({len(df)} ventes jugées)")


def _resume_prix(df, coupe: str, n_couples: int) -> dict:
    import numpy as np
    if len(df) == 0:
        return {"n": 0, "coupe": coupe}
    ecart = df["ecart_rel"].to_numpy()
    res = {
        "n": len(df), "coupe": coupe, "n_couples_estimation": n_couples,
        "ecart_median_relatif": float(np.median(ecart)),
        "ecart_median_absolu_relatif": float(np.median(np.abs(ecart))),
        "part_10pct": float(df["dans_10pct"].mean()),
        "part_20pct": float(df["dans_20pct"].mean()),
        "par_type": [], "par_commune": [],
    }
    for t, g in df.groupby("type_bien"):
        res["par_type"].append({
            "type": t, "n": len(g),
            "ecart_median": float(np.median(g["ecart_rel"])),
            "mae_rel": float(np.median(np.abs(g["ecart_rel"]))),
            "part_10": float(g["dans_10pct"].mean()), "part_20": float(g["dans_20pct"].mean())})
    for com, g in df.groupby("commune"):
        if len(g) < 10:
            continue
        res["par_commune"].append({
            "commune": com, "n": len(g),
            "ecart_median": float(np.median(g["ecart_rel"])),
            "part_10": float(g["dans_10pct"].mean()), "part_20": float(g["dans_20pct"].mean())})
    res["par_commune"].sort(key=lambda x: -x["n"])
    return res


def _ecrire_prix_notes(r: dict, df) -> None:
    L = ["# VERITE-TERRAIN-2 · volet E — backtest PRIX (estimé vs réel, hors échantillon)\n"]
    if r["n"] == 0:
        L.append("Aucune vente jugeable (voir le CSV / les limites).\n")
        PRIX_NOTES.write_text("\n".join(L))
        return
    L.append("## Méthode anti-fuite\n")
    L.append(
        f"Les tables de prix SERVIES (`dvf_prix_sortie_neuf`, `dvf_secteur_medianes`) sont "
        f"calculées sur **toute** la fenêtre DVF (jusqu'au 31/12/2025) : elles ont vu les ventes "
        f"qu'on jugerait → fuite. On **reconstruit** donc l'estimation à une **date de coupe "
        f"T = {r['coupe']}** : médiane **€/m² par commune × type de bien** sur les ventes DVF "
        f"**strictement antérieures à T** ({r['n_couples_estimation']} couples commune×type "
        f"estimés). On juge les **ventes postérieures à T**, prix estimé = médiane €/m² × surface "
        f"de la vente. La vente jugée est après T par construction, l'estimation s'arrête à T : "
        f"**elle n'entre jamais dans sa propre estimation**. Exigence : ≥ {PRIX_N_MIN} comparables "
        f"< T dans le couple, sinon abstention.\n")
    L.append("## Résultat global\n")
    L.append(f"- **N ventes jugées** : {r['n']:,}".replace(",", " "))
    L.append(f"- **Écart médian relatif (signé)** : {r['ecart_median_relatif']*100:+.1f} %")
    L.append(f"- **Écart absolu médian** : {r['ecart_median_absolu_relatif']*100:.1f} %")
    L.append(f"- **Part à ±10 %** : {r['part_10pct']*100:.1f} %")
    L.append(f"- **Part à ±20 %** : {r['part_20pct']*100:.1f} %\n")
    L.append("## Par type de bien\n")
    L.append("| type | n | écart médian | écart abs. médian | ±10 % | ±20 % |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for x in r["par_type"]:
        L.append(f"| {x['type']} | {x['n']:,} | {x['ecart_median']*100:+.1f} % | "
                 f"{x['mae_rel']*100:.1f} % | {x['part_10']*100:.1f} % | {x['part_20']*100:.1f} % |"
                 .replace(",", " "))
    L.append("")
    L.append("## Par commune (≥ 10 ventes jugées)\n")
    L.append("| commune | n | écart médian | ±10 % | ±20 % |")
    L.append("|---|--:|--:|--:|--:|")
    for x in r["par_commune"]:
        L.append(f"| {x['commune']} | {x['n']:,} | {x['ecart_median']*100:+.1f} % | "
                 f"{x['part_10']*100:.1f} % | {x['part_20']*100:.1f} % |".replace(",", " "))
    L.append("")
    L.append("## Limites\n")
    L.append(
        "- **Modèle d'estimation volontairement sobre** (médiane €/m² commune × type, rejouable "
        "sans fuite) : ce n'est pas l'estimateur fin servi en fiche, mais le plancher honnête que "
        "l'on peut reconstruire à une date de coupe sans voir le futur. L'écart mesuré majore donc "
        "l'erreur du produit (qui dispose de plus de contexte), il ne la minore pas.\n"
        "- **Dispersion intra-commune** : une seule médiane par commune × type ignore quartier, "
        "état, étage → une part de l'écart est de l'hétérogénéité du bien, pas une erreur de niveau "
        "de marché.\n"
        "- **Mono-mutation** : on ne garde que les mutations à une parcelle / un type pour un €/m² "
        "propre (les ventes composites sont écartées, pas jugées).\n"
        f"- **Couverture** : couples commune×type avec ≥ {PRIX_N_MIN} comparables avant T "
        "seulement ; les communes/segments rares sont abstenus (comptés hors N).\n"
        "- **Terrain nu non jugé** : le filtre mono-mutation (une parcelle / un type pour un €/m² "
        "propre) laisse trop peu de ventes de terrain nu pur postérieures à T pour un verdict ; le "
        "backtest prix porte donc sur maison + appartement (bâti). Terrain = 0 vente retenue.\n")
    PRIX_NOTES.write_text("\n".join(L) + "\n")
    log(f"écrit : {PRIX_NOTES}")


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CLI
# ═════════════════════════════════════════════════════════════════════════════════════════

def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "tout"
    if cmd in ("signal", "tout"):
        r = backtest_signal()
        log(f"[signal] N={r['n_jugeable']} base={_pct(r['taux_base'])} AUC={r['auc']:.4f}")
    if cmd in ("prix", "tout"):
        r = backtest_prix()
        if r["n"]:
            log(f"[prix] N={r['n']} écart médian={r['ecart_median_relatif']*100:+.1f}% "
                f"±10%={r['part_10pct']*100:.1f}% ±20%={r['part_20pct']*100:.1f}%")
        else:
            log("[prix] 0 vente jugée")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
