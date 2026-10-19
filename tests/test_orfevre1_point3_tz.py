"""FIX-ORFEVRE-1 (point 3) — ORF-17 / ANGLE-D : plus un seul « aujourd'hui » au fuseau du PROCESS.

62 sites `date.today()` / `datetime.now()` nus supposaient process = Réunion — faux si la branche
serveur-UTC de deploy.sh est empruntée (bascule de jour à 04:00 Réunion au lieu de minuit). Tout le
runtime passe par `tz.today_reunion()` / `tz.now_reunion()` (fuseau EXPLICITE Indian/Reunion).

Quatre verrous ici :
1. le helper rend le jour RÉUNION quel que soit le fuseau du process (cas 22:00 UTC = 02:00 Réunion
   le LENDEMAIN — l'instant où le naïf UTC et le métier divergent) ;
2. la borne mensuelle du quota dossiers (D-03) est posée sur le jour Réunion (cohérente avec
   `protection._aujourdhui` qui POSE les compteurs) ;
3. le « dimanche = intégrale banc2 » (D-02) est décidé sur le jour Réunion, plus sur le process ;
4. GARDE DE CLASSE (AST) : aucun `date.today()` / `datetime.now()` nu / `utcnow()` ne revient dans
   src/labuse — le registre refuse, pas la relecture humaine.
"""
from __future__ import annotations

import ast
import inspect
from datetime import date, datetime, timezone
from pathlib import Path

from labuse import tz

SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


class _HorlogeFigee(datetime):
    """now(tz) rend TOUJOURS le même instant : 2026-10-17 22:00 UTC (= 2026-10-18 02:00 Réunion)."""

    @classmethod
    def now(cls, tz=None):  # noqa: A002 — signature datetime
        instant = datetime(2026, 10, 17, 22, 0, tzinfo=timezone.utc)
        return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)


def test_today_reunion_a_22h_utc_cest_deja_demain(monkeypatch):
    """22:00 UTC un vendredi = 02:00 Réunion le samedi : le helper dit SAMEDI (jour métier), là où
    tout « aujourd'hui » naïf d'un process UTC dirait encore vendredi."""
    monkeypatch.setattr(tz, "datetime", _HorlogeFigee)
    # le même instant, vu naïvement en UTC : encore le 17 — c'est LA divergence que ORF-17 ferme.
    assert _HorlogeFigee.now(timezone.utc).date() == date(2026, 10, 17)
    assert tz.today_reunion() == date(2026, 10, 18)
    quand = tz.now_reunion()
    assert (quand.hour, quand.minute) == (2, 0)
    assert str(quand.tzinfo) == "Indian/Reunion"


def test_quota_dossiers_borne_du_mois_au_jour_reunion(monkeypatch):
    """D-03 — `_quota_mois` calcule « le 1er du mois » sur le jour RÉUNION (celui des compteurs),
    plus sur la date locale du process (qui reprenait tout le mois écoulé à la bascule de mois)."""
    from labuse.api import dossier

    # 1er mars (Réunion) à 01:00 : une machine CEST/UTC est encore le 28/29 février en local.
    monkeypatch.setattr(dossier, "today_reunion", lambda: date(2026, 3, 1))
    vu = {}

    class _Res:
        def scalar(self):
            return 4

    class _DB:
        def execute(self, stmt, params=None):
            vu.update(params or {})
            return _Res()

    assert dossier._quota_mois(_DB(), "sujet-test") == 4
    assert vu["p"] == date(2026, 3, 1)   # borne = 1er du mois RÉUNION, pas du mois local


def test_banc2_dimanche_decide_au_jour_reunion():
    """D-02 — le mode `tout`/`nuit` de coherence_banc lit `today_reunion().weekday()`. Sur serveur
    UTC, l'ancien `datetime.now().weekday()` décalait l'intégrale hebdo d'une nuit, silencieusement."""
    from labuse import jobs_impl

    src = inspect.getsource(jobs_impl.coherence_banc)
    assert "today_reunion().weekday() == 6" in src
    assert "datetime.now().weekday()" not in src


def _appels_naifs(path: Path) -> list[str]:
    """Les appels d'horloge NAÏFS d'un fichier : `date.today()` (y c. `_dt.date.today()`),
    `datetime.now()` SANS argument (avec tz = aware, légitime) et `utcnow()` (déprécié).
    `func.now()` (SQLAlchemy, server-side en session Réunion) n'est pas visé."""
    arbre = ast.parse(path.read_text(encoding="utf-8"))
    sorties = []
    for node in ast.walk(arbre):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        a = node.func
        porteur = a.value
        nom = porteur.id if isinstance(porteur, ast.Name) else (
            porteur.attr if isinstance(porteur, ast.Attribute) else None)
        if a.attr == "today" and not node.args and not node.keywords and nom in ("date", "_date"):
            sorties.append(f"{path.relative_to(SRC)}:{node.lineno} date.today()")
        if (a.attr == "now" and not node.args and not node.keywords
                and nom in ("datetime", "_datetime", "dt", "_dt")):
            sorties.append(f"{path.relative_to(SRC)}:{node.lineno} datetime.now() nu")
        if a.attr == "utcnow":
            sorties.append(f"{path.relative_to(SRC)}:{node.lineno} utcnow()")
    return sorties


def test_garde_de_classe_aucune_horloge_naive_dans_src_labuse():
    """ORF-17 fermé STRUCTURELLEMENT : tout retour d'un « aujourd'hui » au fuseau du process dans
    src/labuse casse ce test (liste blanche : vide — tz.py lui-même passe un tz explicite)."""
    fautifs: list[str] = []
    for p in sorted(SRC.rglob("*.py")):
        fautifs += _appels_naifs(p)
    assert not fautifs, "horloges naïves réintroduites (utiliser labuse.tz) : " + " · ".join(fautifs)
