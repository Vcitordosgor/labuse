"""INJECTION-SOLIDE-1 — l'EFFET d'une source + le résumé « Où en est la mise à jour ? ».

Le tableau de bord doit dire CLAIREMENT, pour chaque source, ce que sa mise à jour change ; et, en
tête de l'onglet, où en est la version servie. Deux fonctions PURES ici (aucune base, aucun git :
l'endpoint leur passe le déjà-calculé), donc testables à l'unité sans fixture
(tests/test_injection_solide_maj.py) :

  1. `effet(dans_le_score)` — la phrase « Effet » d'une source, colonne du même nom de l'onglet
     Sources. Deux cas, deux phrases (mandat INJECTION-SOLIDE-1) :
       · la source NOURRIT le classement (score/cascade — liste fermée `circuit_garanties.
         sources_du_score`) → « entre dans le classement, déclenche un nouveau calcul » ;
       · sinon (référence lue à la volée, injectée la nuit) →
         « lue directement, visible le lendemain matin ».
     La distinction est la MÊME que celle de la propagation : une source du classement n'est visible
     qu'après le calcul de nuit qui la fait entrer dans le run ; une source lue directement se voit
     dès la lecture suivante (le lendemain matin, après l'injection de nuit).

  2. `resume_mise_a_jour(...)` — les TROIS phrases du bloc « Où en est la mise à jour ? » (mandat) :
       (1) la version servie et sa date ;
       (2) les sources qui ont changé depuis, et si elles demandent un nouveau calcul ;
       (3) le prochain calcul prévu — ou « rien à recalculer ».
"""
from __future__ import annotations

#: les deux effets possibles — code stable (front/test) + phrase exacte du mandat.
EFFET_CLASSEMENT = {"code": "classement",
                    "phrase": "entre dans le classement, déclenche un nouveau calcul"}
EFFET_DIRECT = {"code": "direct",
                "phrase": "lue directement, visible le lendemain matin"}


def effet(dans_le_score: bool) -> dict:
    """La phrase « Effet » d'une source. `dans_le_score` = la source est dans la liste fermée
    `circuit_garanties.sources_du_score()` (nourrit le score ou une couche de la cascade)."""
    return dict(EFFET_CLASSEMENT if dans_le_score else EFFET_DIRECT)


def _jour(iso: str | None) -> str | None:
    """La date (AAAA-MM-JJ) d'un horodatage ISO, ou None."""
    if not iso:
        return None
    return str(iso)[:10]


def _apercu(noms: list[str], n: int = 3) -> str:
    """« a, b, c et 2 autres » — un aperçu borné d'une liste de noms."""
    noms = [n_ for n_ in noms if n_]
    if not noms:
        return ""
    tete = noms[:n]
    reste = len(noms) - len(tete)
    txt = ", ".join(tete)
    if reste > 0:
        txt += f" et {reste} autre" + ("s" if reste > 1 else "")
    return txt


def resume_mise_a_jour(*, run_servi: str, run_date: str | None,
                       sources_changees: list[dict], prochain_calcul: str | None,
                       calcul_en_cours: bool = False) -> list[str]:
    """Les TROIS phrases du bloc « Où en est la mise à jour ? » (mandat INJECTION-SOLIDE-1).

    `sources_changees` : les sources dont la version a avancé DEPUIS le calcul du run servi — chacune
    `{"nom": str, "dans_le_score": bool}` (dans_le_score = elle entre dans le classement). `run_date`
    est la date (ISO) à laquelle le run servi a été calculé. `prochain_calcul` est l'heure du prochain
    passage de `calcul-nuit` (déjà formatée, heure Réunion), ou None. Rend TOUJOURS 3 phrases."""
    changees = [s for s in (sources_changees or []) if s.get("nom")]
    du_score = [s for s in changees if s.get("dans_le_score")]
    recalcul_requis = bool(du_score)

    # ── phrase 1 : la version servie et sa date ──
    jour = _jour(run_date)
    p1 = (f"Les clients sont servis en {run_servi}"
          + (f", calculé le {jour}." if jour else " (date de calcul inconnue)."))

    # ── phrase 2 : les sources changées depuis, et si elles demandent un recalcul ──
    if not changees:
        p2 = "Aucune source n'a changé depuis — la version servie est à jour."
    else:
        n = len(changees)
        mot = "source a" if n == 1 else "sources ont"
        if du_score:
            ns = len(du_score)
            verbe = "entre" if ns == 1 else "entrent"
            p2 = (f"{n} {mot} changé depuis ({_apercu([s['nom'] for s in changees])}) ; "
                  f"{ns} {verbe} dans le classement → un nouveau calcul est nécessaire.")
        else:
            p2 = (f"{n} {mot} changé depuis ({_apercu([s['nom'] for s in changees])}), "
                  f"toutes lues directement → visibles sans recalcul.")

    # ── phrase 3 : le prochain calcul prévu, ou « rien à recalculer » ──
    if calcul_en_cours:
        p3 = "Un calcul tourne en ce moment sur le serveur."
    elif recalcul_requis:
        p3 = (f"Prochain calcul prévu : {prochain_calcul}." if prochain_calcul
              else "Prochain calcul prévu : cette nuit.")
    else:
        p3 = "Rien à recalculer."

    return [p1, p2, p3]
