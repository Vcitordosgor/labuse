"""JOHN-COUT-1 — LA RECETTE des quatre leviers de coût (modèle stubé → aucun réseau).

Le mandat : John coûte moins cher sans perdre en qualité. Ce fichier prouve, levier par levier :
  · ROUTAGE invisible — une question de LECTURE part sur Sonnet (`john-lecture`), un DIAGNOSTIC ou une
    ACTION restent sur Opus (`john-chat`) ; un nom (« la sauvegarde ? ») n'est pas pris pour un ordre ;
  · CACHE de prompt — system + outils + dernier message posés derrière des points de cache, sur des
    COPIES (l'historique n'est pas muté) ; le coût du cache (lu 0,10× / écrit 1,25×) arrive au ledger ;
  · OUTILS SOBRES — `lire_jobs` / `lire_sources` ne renvoient que l'essentiel ; `jobs_de_la_nuit` donne
    toute une plage en un appel ;
  · GARDE-FOU — un chiffre non sourcé est RETIRÉ avec la mention « non sourcé », le reste est servi
    (plus de refus en bloc).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from labuse.john import chat, contexte, outils

pytestmark = pytest.mark.db


# ════════════════════════════════ Stubs modèle ════════════════════════════════
def _usage(**kw):
    return SimpleNamespace(input_tokens=kw.get("input_tokens", 10), output_tokens=kw.get("output_tokens", 5),
                           cache_read_input_tokens=kw.get("cache_read", 0),
                           cache_creation_input_tokens=kw.get("cache_write", 0))


def _appel_outil_puis_texte(tool_name, texte, models_vus):
    """1er tour → appelle `tool_name` ; 2e tour (résultat présent) → rend `texte`. Mémorise le modèle."""
    def _appel(**kw):
        models_vus.append(kw["model"])
        dernier = kw["messages"][-1]
        a_res = isinstance(dernier.get("content"), list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in dernier["content"])
        if not a_res:
            return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name=tool_name, input={}, id="t1")],
                                   usage=_usage())
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=texte)], usage=_usage())
    return _appel


# ════════════════════════════════ 1) ROUTEUR ════════════════════════════════
def test_routeur_lecture_vers_sonnet():
    from labuse.ai_models import MODEL_SONNET
    for q in ("Est-ce que tous les jobs tournent ?", "Quel run est servi aux clients ?",
              "Y a-t-il un incident ouvert ?", "Combien coûte John ce mois-ci ?",
              "La sauvegarde de cette nuit a-t-elle une copie externe ?",   # un NOM, pas un ordre
              "Le Radar a-t-il tourné cette nuit ?"):
        kind, model = chat.model_du_tour(q)
        assert (kind, model) == ("john-lecture", MODEL_SONNET), q


def test_routeur_diagnostic_et_action_vers_opus():
    from labuse.ai_models import MODEL_OPUS
    for q in ("Pourquoi le backup a-t-il échoué cette nuit ?", "Quelle est la cause de l'incident ?",
              "Analyse les journaux de calcul-nuit.", "D'où vient cette erreur ?",
              "Relance le job backup-postgres.", "Promeus le run candidat.",
              "Injecte la source BDNB.", "Retire la source périmée.",
              "Lance une sauvegarde."):
        kind, model = chat.model_du_tour(q)
        assert (kind, model) == ("john-chat", MODEL_OPUS), q


def test_repondre_route_une_lecture_sur_sonnet_et_logue_john_lecture(db_session):
    from labuse.ai_models import MODEL_SONNET
    from labuse.john import carnet
    carnet.semer(db_session)
    models = []
    out = chat.repondre(db_session, "Quel run est servi aux clients ?",
                        appel=_appel_outil_puis_texte("lire_runs", "Tout est en ordre côté run.", models))
    assert models and all(m == MODEL_SONNET for m in models)      # routage → Sonnet
    assert out["texte"]
    kinds = db_session.execute(text("SELECT DISTINCT kind FROM ia_log WHERE kind LIKE 'john-%'")).scalars().all()
    assert "john-lecture" in kinds                                # coût imputé à la bonne surface


def test_repondre_route_un_diagnostic_sur_opus(db_session):
    from labuse.ai_models import MODEL_OPUS
    from labuse.john import carnet
    carnet.semer(db_session)
    models = []
    chat.repondre(db_session, "Pourquoi le job backup-postgres a-t-il échoué cette nuit ?",
                  appel=_appel_outil_puis_texte("lire_journaux", "Rien d'anormal ne ressort.", models))
    assert models and all(m == MODEL_OPUS for m in models)


# ════════════════════════════════ 2) CACHE DE PROMPT ════════════════════════════════
def test_poser_cache_pose_les_points_sans_muter_les_originaux():
    system = "SYSTEM"
    tools = [{"name": "a", "input_schema": {}}, {"name": "b", "input_schema": {}}]
    msgs = [{"role": "user", "content": "bonjour"}]
    sys_c, tools_c, msgs_c = chat._poser_cache(system, tools, msgs)
    # system → bloc avec cache_control
    assert sys_c[0]["cache_control"] == {"type": "ephemeral"} and sys_c[0]["text"] == "SYSTEM"
    # dernier outil marqué ; l'original INTACT
    assert tools_c[-1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in tools[-1]
    # dernier message : contenu string → bloc texte avec cache_control ; original INTACT
    assert msgs_c[-1]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert msgs[-1]["content"] == "bonjour"


def test_poser_cache_marque_le_dernier_bloc_dune_liste():
    msgs = [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{}"}]}]
    _, _, msgs_c = chat._poser_cache("S", [{"name": "x"}], msgs)
    assert msgs_c[-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in msgs[-1]["content"][-1]       # original intact


def test_log_cost_facture_le_cache():
    from labuse.ai import core
    from labuse.ai_models import MODEL_SONNET
    pin, pout = core.PRICE[MODEL_SONNET]
    # 0 cache : coût = (tin*pin + tout*pout)/1e6 (compat ascendante, aucun argument cache)
    captured = {}

    class _DB:
        def execute(self, stmt, params=None):
            if params and "c" in params:
                captured.update(params)
            return SimpleNamespace(scalar=lambda: None)

    core._log_cost(_DB(), "john-lecture", MODEL_SONNET, False, 1000, 200)
    base = (1000 * pin + 200 * pout) / 1e6
    assert abs(float(captured["c"]) - base) < 1e-9
    # avec cache : lu 0,10× + écrit 1,25× le prix d'entrée, en plus des jetons frais.
    core._log_cost(_DB(), "john-lecture", MODEL_SONNET, False, 100, 200, cache_read=2000, cache_write=500)
    attendu = (100 * pin + 2000 * pin * core.CACHE_READ_MULT
               + 500 * pin * core.CACHE_WRITE_MULT + 200 * pout) / 1e6
    assert abs(float(captured["c"]) - attendu) < 1e-9
    assert captured["ti"] == 100 + 2000 + 500          # tokens_in journalisé = total d'entrée


# ════════════════════════════════ 3) OUTILS SOBRES + jobs_de_la_nuit ════════════════════════════════
def test_jobs_de_la_nuit_est_un_outil_connu():
    assert "jobs_de_la_nuit" in outils.NOMS
    assert len(outils.NOMS) == len(outils.TOOLS)
    assert "jobs_de_la_nuit" in chat._LECTURE_META and chat._LECTURE_META["jobs_de_la_nuit"][0] == "Jobs"


def test_jobs_de_la_nuit_rend_une_plage_en_un_appel(db_session):
    res = outils.dispatch(db_session, "jobs_de_la_nuit", {"depuis_h": 14})
    assert set(res) >= {"fenetre_h", "n", "en_echec", "passages"} or "indisponible" in res
    if "fenetre_h" in res:
        assert res["fenetre_h"] == 14 and isinstance(res["passages"], list)
    # bornage : une plage absurde est ramenée dans [1, 48].
    res2 = contexte.jobs_nuit(db_session, 999)
    assert "indisponible" in res2 or res2["fenetre_h"] == 48


def test_lire_jobs_est_sobre(db_session):
    res = outils.dispatch(db_session, "lire_jobs", {})
    assert "indisponible" in res or ({"n", "en_echec", "en_retard", "jobs"} <= set(res))
    if res.get("jobs"):
        # un job ne porte QUE l'essentiel (plus de libellé/famille/cadence/cron/prochaine réunion).
        assert set(res["jobs"][0]) == {"nom", "statut", "fin", "bloque", "perime"}


def test_lire_sources_est_sobre(db_session):
    res = outils.dispatch(db_session, "lire_sources", {})
    assert "indisponible" in res or ({"n", "nouvelles_versions", "veille_en_panne", "sources"} <= set(res))
    if res.get("sources"):
        assert set(res["sources"][0]) == {"nom", "statut", "classe", "millesime_servi", "veille_statut"}


# ════════════════════════════════ 4) GARDE-FOU (retire, ne refuse pas) ════════════════════════════════
def test_expurger_retire_le_non_source_et_garde_le_reste():
    outils_vus = [{"n": 3, "ouverts": [1, 2, 3]}]
    texte, retires = chat.expurger_non_source(
        "Il y a 3 incidents ouverts et 987654 alertes fantômes.", outils_vus)
    assert retires == ["987654"]
    assert "987654" not in texte
    assert "« non sourcé »" in texte
    assert "3 incidents ouverts" in texte          # le fait sourcé demeure
    assert "alertes fantômes" in texte             # le reste de la phrase demeure


def test_expurger_laisse_les_decimales_francaises_sourcees():
    # 18,7 est sourcé (présent tel quel) → gardé ; 42,9 ne l'est pas → retiré.
    texte, retires = chat.expurger_non_source(
        "La sauvegarde a 18,7 h d'âge, pas 42,9 h.", [{"age_h": 18.7}])
    assert "18,7" in texte and "42,9" not in texte
    assert retires == ["42,9"]


def test_expurger_ne_touche_pas_une_reponse_sans_chiffre_ni_les_chiffres_sources():
    t1, r1 = chat.expurger_non_source("Rien d'anormal ne ressort.", [{"n": 0}])
    assert t1 == "Rien d'anormal ne ressort." and r1 == []
    t2, r2 = chat.expurger_non_source("Il y a 0 job en échec.", [{"jobs": []}])
    assert r2 == [] and "0 job" in t2


# ════════════════════════════════ 5) REGISTRE / SURFACES ════════════════════════════════
def test_surface_john_lecture_sur_sonnet():
    from labuse.ai_models import (MODEL_SONNET, MODEL_SONNET_REPLI, model_for, SURFACES, INTERNE_KINDS,
                                  repli_pour, ACTIVE_MODELS)
    assert MODEL_SONNET == "claude-sonnet-5-5"
    assert model_for("john-lecture") == MODEL_SONNET
    assert "john-lecture" in SURFACES and "john-lecture" in INTERNE_KINDS
    assert repli_pour(MODEL_SONNET) == MODEL_SONNET_REPLI == "claude-sonnet-4-6"
    assert MODEL_SONNET in ACTIVE_MODELS


def test_sonnet_au_pricing_et_sans_temperature():
    from labuse.ai.core import PRICE, NO_TEMPERATURE_MODELS
    from labuse.ai_models import MODEL_SONNET
    assert MODEL_SONNET in PRICE and PRICE[MODEL_SONNET] == (3.0, 15.0)
    assert MODEL_SONNET in NO_TEMPERATURE_MODELS
