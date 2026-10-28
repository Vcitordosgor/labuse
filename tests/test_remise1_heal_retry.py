"""REMISE-1 (Lot A) — résilience du heal de schéma au démarrage face aux CONFLITS DE VERROU.

Incident DEPLOY-1028b : au (re)démarrage, le heal d'un module (`ALTER TABLE pige_biens ADD COLUMN …`)
percutait un lecteur concurrent (le gros job `fiche-commune-cache` de l'étape 6 du déploiement) → le
verrou ne se libérait pas → le step tombait en échec DÉFINITIF → `app.state.schema_heal.ok=false` →
`/readyz` 503 (~40 % des workers) jusqu'à un restart manuel.

Correctif testé ici (logique PURE, sans base → tourne au hook) : `_run_heal_steps` RÉESSAIE un step
qui lève une `OperationalError` (lock_timeout dépassé / deadlock) — 1 + 2 essais par défaut — et ne le
compte en échec que si le verrou ne lâche JAMAIS. Une vraie erreur de schéma (non-verrou) n'est PAS
réessayée (échec immédiat). Le bout « vrai verrou Postgres tenu → le heal converge → /readyz 200 » est
dans tests/test_gb011_heal.py (marqué `db`, base réelle).
"""
from __future__ import annotations

from sqlalchemy.exc import OperationalError


def _op_err(msg: str = "canceling statement due to lock timeout") -> OperationalError:
    """Fabrique une `sqlalchemy.exc.OperationalError` telle que la lèverait psycopg sur lock_timeout."""
    return OperationalError("ALTER TABLE …", {}, Exception(msg))


def test_reessaie_les_conflits_de_verrou_et_converge():
    """Un step bloqué par un verrou les 2 premières fois PUIS libre réussit : le heal réessaie et
    CONVERGE → aucun échec (pas de `heal_failed` définitif, cœur du correctif DEPLOY-1028b)."""
    from labuse.api.app import _run_heal_steps
    appels = {"n": 0}
    retries: list[tuple[str, int]] = []

    def _verrou_puis_ok():
        appels["n"] += 1
        if appels["n"] < 3:                      # 2 premiers essais : verrou encore tenu
            raise _op_err()
        # 3e essai : le lecteur a relâché le verrou → l'ALTER passe

    fails = _run_heal_steps((("pige", _verrou_puis_ok),), pause_s=0,
                            on_retry=lambda mod, t, _e: retries.append((mod, t)))
    assert appels["n"] == 3, "le step est rejoué jusqu'au succès (1 + 2 réessais)"
    assert fails == [], "convergé → AUCUN échec (readyz restera 200)"
    assert retries == [("pige", 1), ("pige", 2)], "deux réessais notifiés avant le succès"


def test_verrou_persistant_echoue_apres_les_essais_sans_boucle_infinie():
    """Si le verrou ne lâche JAMAIS, le step finit en échec APRÈS exactement `essais` tentatives
    (il ne boucle pas à l'infini) — et /readyz dira alors honnêtement 503."""
    from labuse.api.app import _run_heal_steps
    appels = {"n": 0}

    def _verrou_eternel():
        appels["n"] += 1
        raise _op_err()

    fails = _run_heal_steps((("pige", _verrou_eternel),), essais=3, pause_s=0)
    assert appels["n"] == 3, "exactement 3 tentatives (1 + 2), puis abandon"
    assert [f["module"] for f in fails] == ["pige"]
    assert "OperationalError" in fails[0]["error"]


def test_erreur_non_verrou_echoue_immediatement_sans_retry():
    """Une vraie erreur de schéma (pas un verrou) n'est PAS réessayée : inutile d'attendre 2×2 s pour
    une erreur qui ne se résoudra pas seule. Elle échoue du 1er coup (et reste isolée des autres)."""
    from labuse.api.app import _run_heal_steps
    appels = {"n": 0}

    def _boom():
        appels["n"] += 1
        raise ValueError("column \"n\" does not exist")

    fails = _run_heal_steps((("x", _boom),), essais=3, pause_s=0)
    assert appels["n"] == 1, "aucun réessai sur erreur non-verrou"
    assert [f["module"] for f in fails] == ["x"]


def test_le_retry_n_annule_pas_la_de_cascade_des_echecs():
    """Garde-fou combiné : un step verrou-éternel au milieu épuise ses essais PUIS les suivants
    tournent quand même (isolation FIX-GB-011 préservée par le retry REMISE-1)."""
    from labuse.api.app import _run_heal_steps
    ran: list[str] = []

    def _verrou_eternel():
        raise _op_err()

    fails = _run_heal_steps(
        (("a", lambda: ran.append("a")),
         ("pige", _verrou_eternel),
         ("veilles", lambda: ran.append("veilles"))),
        essais=2, pause_s=0)
    assert ran == ["a", "veilles"], "les steps après le KO tournent toujours (dé-cascade intacte)"
    assert [f["module"] for f in fails] == ["pige"]
