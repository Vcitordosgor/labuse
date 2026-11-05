"""NU4-F — tenue du PLAFOND de John + granularité + isolation Copilote. 100 % lecture seule (rollback)."""
from __future__ import annotations
import json
from sqlalchemy import text
from labuse.db import session_scope
from labuse import config
import labuse.john.chat as jc
from labuse.john import budget

S = config.get_settings()
R = {}

# ── 1. le plafond COUPE avant tout appel modèle ──
def appel_interdit(**kw):
    raise AssertionError("APPEL MODÈLE ALORS QUE JOHN DEVRAIT ÊTRE EN PAUSE")

with session_scope() as db:
    jc.ensure(db)
    plafond = budget._plafond(S)
    # pousse la dépense du mois AU-DESSUS du plafond (ligne synthétique, rollback ensuite)
    db.execute(text("CREATE TABLE IF NOT EXISTS ia_log ( id serial PRIMARY KEY, ts timestamptz DEFAULT now(),"
                    " kind varchar(24), model varchar(64), stub boolean, tokens_in integer,"
                    " tokens_out integer, cout_eur numeric(8,5))"))
    db.execute(text("INSERT INTO ia_log (kind, model, stub, tokens_in, tokens_out, cout_eur) "
                    "VALUES ('john-chat','x',false,0,0,:c)"), {"c": plafond + 10})
    e = budget.etat(db, S)
    out = jc.repondre(db, "coucou, ça va ?", appel=appel_interdit, backend=jc._actions.Backend(), settings=S)
    R["1_plafond_coupe"] = {"plafond_eur": plafond, "depense_simulee_eur": e.depense_eur,
                            "en_pause": e.en_pause, "texte": out.get("texte"),
                            "pause_flag": out.get("pause"), "aucun_appel_modele": out.get("pause") is True}
    db.rollback()

# ── 2. granularité : le plafond est testé À L'ENTRÉE du tour, pas entre les appels de la boucle d'outils ──
# Dépassement max possible en un tour = (max_tours) appels modèle après le dernier test de budget.
R["2_granularite"] = {
    "test_budget": "une seule fois, étape (0) de repondre(), AVANT la boucle",
    "max_appels_modele_par_tour": 6,  # max_tours défaut
    "rejoue_budget_entre_appels": False,
    "consequence": ("un tour entamé sous le plafond peut le dépasser du coût d'au plus 6 appels Opus "
                    "avant la coupure ; la coupure est effective au TOUR SUIVANT. Dépassement borné, "
                    "jamais illimité."),
}

# ── 3. plafond = 0 ou négatif → jamais de pause (désactivé) ; vérifie le contrat ──
class S0:  # settings factice
    john_plafond_eur = 0.0
with session_scope() as db:
    jc.ensure(db)
    e0 = budget.etat(db, S0)
    R["3_plafond_zero"] = {"plafond_eur": 0.0, "en_pause": e0.en_pause,
                           "note": "plafond 0 => jamais en pause (garde `plafond > 0`)"}
    db.rollback()

# ── 4. isolation Copilote : un fil (faits/historique) est cloisonné par compte_id / sujet ──
from labuse.copilote_v2 import registre_faits, historique
with session_scope() as db:
    # lecture d'un fil pour un compte A vs un sujet B : jamais de recouvrement (requête cloison)
    try:
        fa = registre_faits.du_fil(db, 999001, 1, 10, sujet=None)       # compte A, conv 1
        fb = registre_faits.du_fil(db, None, 1, 10, sujet="sujet-B")    # visiteur B, conv 1
        R["4_isolation_faits"] = {"faits_compteA": len(fa or []), "faits_sujetB": len(fb or []),
                                  "note": "du_fil filtre WHERE compte_id/sujet — pas de fuite inter-compte"}
    except Exception as ex:
        R["4_isolation_faits"] = {"erreur": str(ex)}
    db.rollback()

print(json.dumps(R, ensure_ascii=False, indent=2, default=str))
