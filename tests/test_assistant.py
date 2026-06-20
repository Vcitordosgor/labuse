"""3.A — Assistant IA : garde-fou anti-hallucination, synthèse règles (sans clé), prompt strict.

Sans clé API on ne peut pas tester la réponse LIVE du modèle, mais on verrouille l'essentiel :
  - le prompt ne transmet QUE des faits réels (liste blanche) + une carte de provenance ;
  - le prompt système impose la structure 5 blocs, la provenance et le refus de conclure ;
  - l'absence de clé donne une SYNTHÈSE RÈGLES déterministe (jamais « cassé », jamais d'invention) ;
  - la synthèse règles reste prudente et cohérente sur 7 cas types Saint-Paul.
La recette « explication fidèle » par le modèle s'exécute dès la clé posée.
"""
from __future__ import annotations

import pytest

from labuse.api.assistant import (
    ENV_KEY,
    SYSTEM,
    assistant_facts,
    explain_parcel,
    is_configured,
    rules_summary,
)

FICHE = {
    "parcel": {"idu": "97415000AB0001", "commune": "Saint-Paul", "section": "AB", "numero": "1",
               "surface_m2": 1234.5, "centroid": {"lon": 55.27, "lat": -21.0}},
    "verdict": {"status": "opportunite", "opportunity_score": 78, "completeness_score": 64,
                "downgrade_reason": None},
    "faisabilite": {"zone": "U1c", "constructible": True, "verdict": "R+3 · ~12-18 logts",
                    "fourchette": {"niveaux": "R+3", "surface_plancher_m2": 900,
                                   "logements_au_sol": [12, 18], "hauteur_m": 12.0},
                    "volume3d": {"volume_m3": 7200},
                    "bilan": {"verdict": "charge foncière ~250 k€",
                              "charge_fonciere": {"central": 250000}, "fiable": True}},
    "bati": {"disponible": True, "label": "Aucun bâti significatif", "code": "vacant", "ratio_pct": 0},
    "cascade": [
        {"layer_name": "zonage_plu_gpu", "result": "POSITIVE", "detail": "Zone U constructible", "source": "GPU"},
        {"layer_name": "pente", "result": "SOFT_FLAG", "detail": "Pente forte 32 %", "source": "RGE ALTI"},
        {"layer_name": "ravine", "result": "UNKNOWN", "detail": "non ingéré", "source": "BD TOPO"},
    ],
    "sources_responded": ["GPU", "RGE ALTI"],
    "sources_silent": ["BD TOPO"],
    "resume": {"titre": "Belle opportunité", "prochaine_action": "Vérifier le PLU/CU"},
}


# ── Liste blanche des faits ───────────────────────────────────────────────────
def test_facts_liste_blanche_seulement_les_vrais_champs():
    f = assistant_facts(FICHE)
    assert set(f) == {"parcelle", "verdict", "faisabilite", "bilan_promoteur", "occupation_bati",
                      "contraintes_et_signaux", "completude", "niveaux_fiabilite", "resume_metier"}
    assert f["parcelle"]["surface_m2"] == 1234.5
    assert f["verdict"]["statut"] == "opportunite" and f["verdict"]["score_opportunite"] == 78
    assert f["faisabilite"]["hauteur_m"] == 12.0 and f["faisabilite"]["volume_enveloppe_m3"] == 7200
    assert f["occupation_bati"]["code"] == "vacant"
    # Provenance dérivée : zonage + occupation = sourcés ; bilan = estimé ; BD TOPO = absent.
    nf = f["niveaux_fiabilite"]
    assert "zonage PLU" in nf["sourcé"] and "coûts & charge foncière (bilan)" in nf["estimé"]
    assert "BD TOPO" in nf["absent_ou_a_verifier"] and nf["completude_niveau"] == "moyenne"
    # Le centroïde (donnée parasite) n'est PAS transmis au modèle.
    assert "centroid" not in str(f["parcelle"])


def test_facts_ne_garde_que_contraintes_et_signaux_pas_unknown():
    f = assistant_facts(FICHE)
    types = {c["type"] for c in f["contraintes_et_signaux"]}
    assert types == {"POSITIVE", "SOFT_FLAG"}            # UNKNOWN/PASS exclus
    assert all(c["motif"] for c in f["contraintes_et_signaux"])


def test_facts_donnee_absente_reste_nulle_jamais_inventee():
    f = assistant_facts({"parcel": {"idu": "X"}, "verdict": {}, "cascade": []})
    assert f["parcelle"]["surface_m2"] is None
    assert f["faisabilite"] is None and f["bilan_promoteur"] is None
    assert f["occupation_bati"] is None
    assert f["verdict"]["statut"] is None
    assert f["contraintes_et_signaux"] == []
    assert f["niveaux_fiabilite"]["completude_niveau"] == "inconnue"


# ── Prompt système : structure + sécurité imposées ────────────────────────────
def test_prompt_systeme_impose_structure_et_securite():
    s = SYSTEM.lower()
    for bloc in ("potentiel", "contraintes", "bâti", "économie indicative", "recommandation"):
        assert bloc in s
    assert "n'inventes aucun" in s or "n'inventes" in s
    assert "sourcé" in s and "estimé" in s and ("absent" in s or "à vérifier" in s)
    assert "fiabilité" in s and "données manquantes" in s
    assert "constructible" in s            # consigne explicite « jamais constructible certain »
    assert "refuses de conclure" in s


# ── Dégradation sans clé : synthèse règles, jamais « cassé » ───────────────────
def test_sans_cle_degrade_proprement(monkeypatch):
    monkeypatch.delenv(ENV_KEY, raising=False)
    out = explain_parcel(FICHE)
    assert out["available"] is False and out["reason"] == "no_key"
    assert "facts" in out                               # les faits restent dispo (preview/debug)
    assert "explanation" not in out                     # rien d'inventé sans le modèle
    assert "rules_summary" in out and out["rules_summary"]   # synthèse règles toujours fournie
    assert "**Recommandation**" in out["rules_summary"]


def test_is_configured_reflet_de_lenv(monkeypatch):
    """1.B — l'UI sait si l'assistant LLM est activable (bouton désactivé sinon)."""
    monkeypatch.delenv(ENV_KEY, raising=False)
    assert is_configured() is False
    monkeypatch.setenv(ENV_KEY, "sk-ant-test")
    assert is_configured() is True


# ── Synthèse règles : 5 blocs, prudente, cohérente sur 7 cas Saint-Paul ────────
def _facts(status, *, surface=1000.0, zone="U2c", constructible=True, sdp=300, logts=(4, 6),
           cf=120000, fiable=True, bati=("vacant", "Aucun bâti significatif", 2), micro=False,
           downgrade=None, contraintes=None, completude=85, silent=None):
    fiche = {
        "parcel": {"idu": "97415000ZZ0001", "commune": "Saint-Paul", "surface_m2": surface},
        "verdict": {"status": status, "opportunity_score": 67, "completeness_score": completude,
                    "micro_opportunite": micro, "downgrade_reason": downgrade},
        "faisabilite": ({"zone": zone, "constructible": constructible, "verdict": "synthèse",
                         "fourchette": {"surface_plancher_m2": sdp, "logements_au_sol": list(logts)},
                         "bilan": ({"verdict": "v", "charge_fonciere": {"central": cf},
                                    "fiable": fiable} if cf is not None else None)} if zone else None),
        "bati": ({"disponible": True, "code": bati[0], "label": bati[1], "ratio_pct": bati[2]}
                 if bati else {"disponible": False, "label": "non vérifiée", "code": "inconnu"}),
        "cascade": contraintes or [],
        "sources_responded": ["GPU", "DVF"], "sources_silent": silent or [],
        "resume": {},
    }
    return assistant_facts(fiche)


def test_rules_summary_cinq_blocs_obligatoires():
    md = rules_summary(_facts("opportunite"))
    for titre in ("**Potentiel**", "**Contraintes**", "**Bâti / libre**",
                  "**Économie indicative**", "**Recommandation**", "**Fiabilité**", "**Données manquantes**"):
        assert titre in md


def test_rules_summary_vraie_opportunite():
    md = rules_summary(_facts("opportunite", cf=250000, fiable=True))
    assert "Opportunité" in md and "INDICATIVE" in md          # économie toujours indicative
    assert "capacité ESTIMÉE" in md                            # jamais « constructible » certain


def test_rules_summary_micro_opportunite_pousse_assemblage():
    md = rules_summary(_facts("opportunite", surface=320, micro=True))
    assert "micro-opportunité" in md and "assemblage" in md.lower()


def test_rules_summary_a_creuser_reste_prudent():
    md = rules_summary(_facts("a_creuser", completude=35, silent=["PPR", "pente"]))
    assert "À creuser" in md
    assert "PPR" in md and "pente" in md                       # données manquantes citées
    assert "faible" in md.lower()                              # fiabilité faible signalée


def test_rules_summary_ecartee():
    md = rules_summary(_facts("exclue", contraintes=[
        {"layer_name": "risques", "result": "HARD_EXCLUDE", "detail": "PPR zone rouge"}]))
    assert "Écartée" in md and "PPR zone rouge" in md
    assert "Ne pas prospecter" in md


def test_rules_summary_faux_positif_bati():
    md = rules_summary(_facts("faux_positif_probable", downgrade="parcelle déjà bâtie 72 %",
                              bati=("deja_bati", "Parcelle déjà bâtie", 72)))
    assert "Faux positif probable" in md
    assert "déjà bâtie" in md                                  # occupation réelle citée
    assert "72 %" in md


def test_rules_summary_contrainte_forte():
    md = rules_summary(_facts("a_creuser", contraintes=[
        {"layer_name": "pente", "result": "SOFT_FLAG", "detail": "Pente forte 45 %"}]))
    assert "Pente forte 45 %" in md


def test_rules_summary_economie_estimee_ou_absente():
    # bilan non fiable → « fragile / ordre de grandeur », jamais un chiffre ferme
    md_frag = rules_summary(_facts("a_creuser", cf=80000, fiable=False))
    assert "fragile" in md_frag.lower() and "INDICATIVE" in md_frag
    # pas de bilan du tout → non chiffrée, aucune invention
    md_none = rules_summary(_facts("a_creuser", cf=None))
    assert "Non chiffrée" in md_none and "inventé" in md_none.lower()


def test_rules_summary_occupation_non_verifiee_si_absente():
    md = rules_summary(_facts("opportunite", bati=None))
    assert "Occupation non vérifiée" in md


@pytest.mark.db
def test_assistant_status_endpoint(engine, monkeypatch):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    monkeypatch.delenv(ENV_KEY, raising=False)
    with TestClient(app) as c:
        assert c.get("/assistant/status").json() == {"configured": False}
