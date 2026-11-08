"""JOHN-COUT-1 — LE BANC DE COÛT (10 questions types, joué AVANT et APRÈS, 0 réseau, 0 €).

But : mesurer, de façon DÉTERMINISTE et reproductible, ce que coûte une question à John — sans brûler
un centime ni appeler l'API. On pilote le VRAI `chat.repondre` (routeur, boucle d'outils, anti-invention,
garde-fou) avec un appel modèle INSTRUMENTÉ qui :
  · joue un script d'outils réaliste (le bon outil de lecture, puis une réponse SOURCÉE tirée du
    résultat réel de l'outil — donc toujours valide à l'anti-invention) ;
  · compte les jetons réellement envoyés au modèle à CHAQUE appel (system + définitions d'outils +
    historique + résultats d'outils), au tarif du modèle que le routeur a choisi (lu dans `kw["model"]`) ;
  · simule le cache de prompt de l'API par préfixe commun (LCP) quand le code l'active (`chat.CACHE_PROMPT`).

Ce que le banc capte AUTOMATIQUEMENT de mes changements, sans drapeau :
  · le ROUTAGE  → via le `model=` que `repondre` passe à l'appel (Sonnet lecture / Opus diagnostic-action) ;
  · les OUTILS SOBRES → les résultats viennent de `outils.dispatch` réel (plus légers après) ;
  · `jobs_de_la_nuit` → détecté dans la liste `tools` ⇒ 1 appel au lieu de N `lire_job` ;
  · le CACHE → `getattr(chat, "CACHE_PROMPT", False)` (absent = AVANT, présent = APRÈS).

Tarifs €/Mtoken alignés sur `ai.core.PRICE` (indicatifs, cohérents avant/après). Cache : lecture 0,10×,
écriture 1,25× le prix d'entrée (barème Anthropic). Jetons ≈ octets UTF-8 / 4 (heuristique stable : seul
le RAPPORT avant/après compte, et il est le même des deux côtés).

Usage : python docs/audit-2026-11/john-cout-1/bench.py --out docs/audit-2026-11/john-cout-1/avant.json
"""
from __future__ import annotations

import argparse
import json
import os
from types import SimpleNamespace

# Base de test (jamais la base de l'app), comme la recette.
_APP = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://labuse:labuse@localhost:5432/labuse")
_TEST = os.environ.get("LABUSE_TEST_DATABASE_URL") or (_APP.rsplit("/", 1)[0] + "/labuse_test")
os.environ["LABUSE_DATABASE_URL"] = _TEST
os.environ.setdefault("LABUSE_APP_DATABASE_URL", _APP)
os.environ.setdefault("ANTHROPIC_API_KEY", "")   # aucun appel réel de toute façon

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from labuse.john import carnet, chat  # noqa: E402

# ── Tarifs €/Mtoken (= ai.core.PRICE, tier par tier) ────────────────────────────────────────────
PRICE = {
    "claude-opus-5-5": (15.0, 75.0), "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-5-5": (3.0, 15.0), "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-5-5": (1.0, 5.0), "claude-haiku-4-5-20251001": (1.0, 5.0),
}
CACHE_READ_MULT = 0.10
CACHE_WRITE_MULT = 1.25


def toks(s: str) -> int:
    return max(1, (len(s.encode("utf-8")) + 3) // 4)


def _ser(o) -> str:
    return json.dumps(o, ensure_ascii=False, default=str, sort_keys=True)


# ── Les 10 QUESTIONS TYPES du mandat ────────────────────────────────────────────────────────────
# Chaque entrée : (question, [outils préférés par ordre de priorité], est_diagnostic_ou_action).
# `drill` = nombre de `lire_job` à enchaîner AVANT (quand `jobs_de_la_nuit` n'existe pas encore) pour
# couvrir « tous les jobs de la nuit » job par job ; APRÈS, un seul `jobs_de_la_nuit` suffit.
QUESTIONS = [
    {"q": "Fais le point sur tous les jobs de cette nuit.",
     "outils": ["jobs_de_la_nuit", "lire_jobs"], "drill_si_absent": 3},
    {"q": "Où en est le run servi aux clients ?", "outils": ["lire_runs"]},
    {"q": "Montre-moi le journal du job backup-postgres.",
     "outils": ["lire_job"], "args": {"nom": "backup-postgres"}},
    {"q": "Y a-t-il un incident ouvert en ce moment ?", "outils": ["lire_incidents"]},
    {"q": "Combien coûte John ce mois-ci ?", "outils": ["lire_journaux"]},
    {"q": "Est-ce que les sources sont à jour ?", "outils": ["lire_sources"]},
    {"q": "Le banc de cohérence est-il vert ?", "outils": ["lire_controles"]},
    {"q": "La sauvegarde de cette nuit a-t-elle une copie externe ?", "outils": ["lire_sauvegardes"]},
    {"q": "Le Radar a-t-il tourné cette nuit ?", "outils": ["lire_radar"]},
    # une question de DIAGNOSTIC (cause d'un incident) — doit rester sur Opus (routage).
    {"q": "Pourquoi le backup a-t-il échoué cette nuit, quelle est la cause ?",
     "outils": ["lire_journaux", "lire_job"], "args": {"nom": "backup-postgres"}, "diagnostic": True},
]


def _fait_vedette(d) -> float | None:
    """Un fait d'exploitation STABLE et sourcé pour fabriquer la réponse : le compteur d'en-tête `n`
    s'il existe (nombre de jobs/sources/incidents…), sinon la CARDINALITÉ de la 1ʳᵉ collection, sinon le
    plus petit nombre présent. Choisi pour être INVARIANT au dégraissage des outils (le compte survit,
    seul le détail par élément part) → « mêmes faits » avant/après ne dépend pas d'un champ volumineux."""
    if isinstance(d, dict):
        if isinstance(d.get("n"), (int, float)):
            return float(d["n"])
        for v in d.values():
            if isinstance(v, (list, tuple)):
                return float(len(v))
    for n in sorted(chat._nombres_autorises([d])):
        return n
    return None


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


class Instrument:
    """Faux appel modèle : joue le script d'outils de la question et CHIFFRE chaque appel réellement émis."""

    def __init__(self, cache_on: bool):
        self.cache_on = cache_on
        self.prev_in = ""          # entrée (sérialisée) de l'appel précédent → LCP pour le cache
        self.calls: list[dict] = []
        self._script: list = []    # file de blocs à rendre pour la question courante

    def nouvelle_question(self, tools_dispos: set[str], plan: dict, db):
        """Construit la séquence d'outils à jouer pour la question, selon les outils DISPONIBLES."""
        seq = []
        prefs = [o for o in plan["outils"] if o in tools_dispos]
        primaire = prefs[0] if prefs else plan["outils"][0]
        args = plan.get("args", {})
        seq.append(("tool", primaire, args))
        # AVANT : pas de `jobs_de_la_nuit` → on draille job par job pour couvrir « la nuit ».
        if primaire != "jobs_de_la_nuit" and plan.get("drill_si_absent"):
            for nom in ("backup-postgres", "calcul-nuit", "coherence-nuit")[: plan["drill_si_absent"]]:
                seq.append(("tool", "lire_job", {"nom": nom}))
        # diagnostic : une seconde lecture ciblée (journal → job) avant de conclure.
        if plan.get("diagnostic") and "lire_job" in tools_dispos and primaire != "lire_job":
            seq.append(("tool", "lire_job", plan.get("args", {})))
        seq.append(("texte", plan))
        self._script = seq

    def __call__(self, **kw):
        model = kw["model"]
        system = kw["system"]
        tools = kw["tools"]
        msgs = kw["messages"]
        # 1) chiffrage de l'entrée réellement envoyée
        sys_txt = system if isinstance(system, str) else _ser(system)
        full_in = sys_txt + "\x00" + _ser(tools) + "\x00" + "\x00".join(_ser(m) for m in msgs)
        n_in = toks(full_in)
        if self.cache_on and self.prev_in:
            lcp = 0
            m = min(len(full_in), len(self.prev_in))
            while lcp < m and full_in[lcp] == self.prev_in[lcp]:
                lcp += 1
            cached = toks(full_in[:lcp])
            fresh = max(0, n_in - cached)
            in_units = cached * CACHE_READ_MULT + fresh * CACHE_WRITE_MULT
        else:
            cached, fresh, in_units = 0, n_in, float(n_in)
        self.prev_in = full_in

        # 2) prochaine action du script
        bloc = self._script.pop(0)
        if bloc[0] == "tool":
            _, nom, args = bloc
            out_txt = _ser({"tool_use": nom, "input": args})
            reponse = SimpleNamespace(
                content=[SimpleNamespace(type="tool_use", name=nom, input=args, id=f"t{len(self.calls)}")],
                usage=SimpleNamespace(input_tokens=n_in, output_tokens=toks(out_txt)))
        else:
            # réponse finale : SOURCÉE à partir des résultats d'outils déjà présents dans msgs
            dernier = msgs[-1]
            res_dicts = []
            if isinstance(dernier.get("content"), list):
                for b in dernier["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        try:
                            res_dicts.append(json.loads(b["content"]))
                        except Exception:
                            pass
            n = None
            for d in res_dicts:
                n = _fait_vedette(d)
                if n is not None:
                    break
            phrase = ("D'après mes lectures, voici l'état : "
                      + (f"{_fmt(n)} au compteur. " if n is not None else "")
                      + "Rien d'autre d'anormal ne ressort.")
            out_txt = phrase
            reponse = SimpleNamespace(
                content=[SimpleNamespace(type="text", text=phrase)],
                usage=SimpleNamespace(input_tokens=n_in, output_tokens=toks(out_txt)))

        pin, pout = PRICE.get(model, (0.0, 0.0))
        n_out = reponse.usage.output_tokens
        cost = (in_units * pin + n_out * pout) / 1_000_000
        self.calls.append({"model": model, "tokens_in": n_in, "cached": cached, "fresh": fresh,
                           "tokens_out": n_out, "cost_eur": cost})
        return reponse


def _tools_dispos() -> set[str]:
    return {t["name"] for t in chat._tools_modele()}


def run(cache_on: bool) -> dict:
    eng = create_engine(_TEST, future=True)
    db = Session(eng, future=True)
    chat.ensure(db)
    carnet.semer(db)
    db.commit()
    tools_dispos = _tools_dispos()
    instr = Instrument(cache_on)
    resultats = []
    for plan in QUESTIONS:
        instr.nouvelle_question(tools_dispos, plan, db)
        avant = len(instr.calls)
        out = chat.repondre(db, plan["q"], appel=instr)
        db.commit()
        appels = instr.calls[avant:]
        cout = sum(c["cost_eur"] for c in appels)
        modeles = sorted({c["model"] for c in appels})
        faits = sorted(chat._nombres_autorises([{"t": out["texte"]}]))
        resultats.append({
            "question": plan["q"], "appels": len(appels), "cout_eur": round(cout, 6),
            "modeles": modeles, "sources": [s["label"] for s in out.get("sources", [])],
            "faits_cites": faits, "texte": out["texte"]})
    db.close()
    total = sum(r["cout_eur"] for r in resultats)
    n_appels = sum(r["appels"] for r in resultats)
    return {"cache_on": cache_on,
            "code_cache_prompt": bool(getattr(chat, "CACHE_PROMPT", False)),
            "cout_total_eur": round(total, 6), "cout_moyen_eur": round(total / len(resultats), 6),
            "appels_total": n_appels, "appels_moyen": round(n_appels / len(resultats), 2),
            "questions": resultats}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", choices=["auto", "on", "off"], default="auto",
                    help="auto = suit chat.CACHE_PROMPT (défaut) ; on/off pour forcer.")
    a = ap.parse_args()
    if a.cache == "auto":
        cache_on = bool(getattr(chat, "CACHE_PROMPT", False))
    else:
        cache_on = a.cache == "on"
    rep = run(cache_on)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print(f"[bench] cache_on={cache_on}  coût moyen {rep['cout_moyen_eur']*100:.3f} c€/question  "
          f"appels moyen {rep['appels_moyen']}  (écrit {a.out})")


if __name__ == "__main__":
    main()
