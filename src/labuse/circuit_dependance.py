"""CIRCUIT-P4 (lot 4) — LA RÈGLE : injection → recalcul.

Le registre sait quelles données lit chaque moteur (`docs/CIRCUIT/inventaire/moteurs.csv`, colonne
`entrees` : les slugs de source cités APRÈS la flèche `→`). On en déduit, pour chaque source, si elle
nourrit **le résiduel** (moteur `residuel`), **le scoring** (moteurs `scoring_p_v2` / `score_e`), ou
aucun. Après toute injection d'une source qui nourrit l'un des deux depuis le run servi — et après
tout commit qui change les règles PLU (`config/plu_destinations/*.yaml`) — une ligne « Calculer »
apparaît dans l'onglet « À faire », avec la LISTE des changements et ce que le recalcul TOUCHE.

Fonction PURE `calculer_ligne` : elle ne lit ni la base ni git ; l'endpoint lui passe la date du run
servi, la liste des règles PLU changées et le signal résiduel existant. Elle est donc testable sans
base (tests/test_circuit_p4_dependance.py) : un cas où une source du scoring a été injectée → la
ligne apparaît ; un cas où une source qui ne nourrit rien a été injectée → rien.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

#: quels moteurs comptent comme « le résiduel » et « le scoring » (familles du mandat).
FAMILLE_MOTEURS: dict[str, set[str]] = {
    "residuel": {"residuel"},
    "scoring": {"scoring_p_v2", "score_e"},
}

#: ce qu'un recalcul TOUCHE, par famille (dérivé des lecteurs aval des moteurs — cf. moteurs.csv /
#: registre) : le résiduel porte la capacité et son affichage/exports ; le scoring porte le score.
TOUCHE_FAMILLE: dict[str, list[str]] = {
    "residuel": ["capacité", "fiche §10", "Dossier", "filtres"],
    "scoring": ["score"],
}

_MOTEURS_CSV = Path(__file__).resolve().parents[2] / "docs" / "CIRCUIT" / "inventaire" / "moteurs.csv"


def _slugs_apres_fleche(entrees: str) -> set[str]:
    """Les slugs de source cités APRÈS un `→` dans la colonne `entrees` (un groupe par `;`)."""
    slugs: set[str] = set()
    for groupe in entrees.split(";"):
        if "→" not in groupe:
            continue
        apres = groupe.split("→", 1)[1]
        # tokens slug : lettres/chiffres/underscore ; on ignore les parenthèses et les « … ».
        for tok in re.findall(r"[a-z][a-z0-9_]+", apres):
            slugs.add(tok)
    return slugs


@lru_cache(maxsize=1)
def _moteurs_entrees() -> dict[str, set[str]]:
    """{moteur_id: set(slugs de source lus)}, lu de moteurs.csv (le registre est la vérité)."""
    out: dict[str, set[str]] = {}
    if not _MOTEURS_CSV.exists():
        return out
    with _MOTEURS_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            mid = (row.get("id") or "").strip()
            if mid:
                out[mid] = _slugs_apres_fleche(row.get("entrees") or "")
    return out


@lru_cache(maxsize=1)
def sources_par_famille() -> dict[str, frozenset[str]]:
    """{'residuel': {slugs…}, 'scoring': {slugs…}} — union des entrées des moteurs de chaque famille."""
    ent = _moteurs_entrees()
    out: dict[str, frozenset[str]] = {}
    for fam, moteurs in FAMILLE_MOTEURS.items():
        acc: set[str] = set()
        for mid in moteurs:
            acc |= ent.get(mid, set())
        out[fam] = frozenset(acc)
    return out


def nourrit(slug: str | None) -> dict:
    """Une source nourrit-elle le résiduel / le scoring ? (par son slug de registre)."""
    par = sources_par_famille()
    return {"residuel": bool(slug and slug in par["residuel"]),
            "scoring": bool(slug and slug in par["scoring"])}


def calculer_ligne(reservoirs: list[dict], *, run_servi_date: str | None = None,
                   plu_changees: list[str] = (), residuel: dict | None = None) -> dict:
    """Construit le contenu de la ligne « Calculer » de l'onglet « À faire » (lot 2). Rend
    `{"actif": False}` s'il n'y a rien à recalculer, sinon `{actif, titre, phrase, touche, changements}`.

    Déclencheurs :
      · une source qui nourrit le résiduel OU le scoring a été injectée DEPUIS le run servi
        (`ingere_le` > `run_servi_date`) ;
      · les règles PLU ont changé (`plu_changees` : communes/fichiers, dérivés d'un commit) ;
      · repli : le signal résiduel existant (`residuel.changees`, entrées PLU/GPU/cadastre/CoSIA)."""
    injectees: list[dict] = []
    for r in reservoirs:
        slug = r.get("slug")
        n = nourrit(slug)
        if not (n["residuel"] or n["scoring"]):
            continue
        ing = r.get("ingere_le")
        if run_servi_date:
            if not ing or ing <= run_servi_date:   # jamais ingérée, ou avant/au run servi
                continue
        injectees.append({"nom": r.get("nom"), "slug": slug,
                          "residuel": n["residuel"], "scoring": n["scoring"], "ingere_le": ing})

    plu = list(plu_changees or ())
    res_signal = bool(residuel and residuel.get("changees"))
    if not (injectees or plu or res_signal):
        return {"actif": False}

    familles: set[str] = set()
    for i in injectees:
        if i["residuel"]:
            familles.add("residuel")
        if i["scoring"]:
            familles.add("scoring")
    if plu or res_signal:
        familles.add("residuel")   # les règles PLU et les entrées résiduel nourrissent la capacité

    touche: list[str] = []
    for fam in ("residuel", "scoring"):
        if fam in familles:
            touche += TOUCHE_FAMILLE[fam]
    if "residuel" in familles and "score" not in touche:
        touche.append("score")   # le scoring LIT le résiduel : un résiduel neuf réclame un score neuf
    touche = list(dict.fromkeys(touche))

    changements = [f"{i['nom']} injectée le {(i['ingere_le'] or '')[:10]}" for i in injectees]
    changements += [f"règles PLU : {c}" for c in plu]
    if res_signal and not injectees and (residuel or {}).get("detail"):
        changements.append(residuel["detail"])

    # le résiduel prime (le score le lit) : un changement résiduel → « Calculer le résiduel » (le
    # score suit, cité dans « Touche ») ; un changement d'entrée SCORING seule → « Calculer le score ».
    titre = "Calculer le résiduel" if "residuel" in familles else "Calculer le score"
    apercu = ", ".join(changements[:4])
    if len(changements) > 4:
        apercu += f" et {len(changements) - 4} autre" + ("s" if len(changements) - 4 > 1 else "")
    phrase = (f"Des entrées ont changé depuis le run servi ({apercu}). "
              f"Touche : {', '.join(touche)}.")
    return {"actif": True, "titre": titre, "phrase": phrase,
            "touche": touche, "changements": changements}


def plu_regles_changees(run_servi_date: str | None) -> list[str]:
    """Les fichiers `config/plu_destinations/*.yaml` changés par un commit DEPUIS le run servi
    (lecture git, best-effort — jamais bloquant). Rend une liste de communes (code INSEE du nom de
    fichier). Sans date de run ou hors dépôt git : liste vide."""
    if not run_servi_date:
        return []
    import subprocess
    racine = Path(__file__).resolve().parents[2]
    try:
        out = subprocess.run(
            ["git", "-C", str(racine), "log", f"--since={run_servi_date}", "--name-only",
             "--pretty=format:", "--", "config/plu_destinations"],
            capture_output=True, text=True, timeout=15)
    except Exception:  # noqa: BLE001 — git indisponible : pas de signal PLU, jamais une erreur
        return []
    communes: list[str] = []
    for ligne in (out.stdout or "").splitlines():
        ligne = ligne.strip()
        if ligne.endswith(".yaml"):
            code = Path(ligne).stem
            if code not in communes:
                communes.append(code)
    return communes
