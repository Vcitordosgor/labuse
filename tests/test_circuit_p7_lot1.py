"""CIRCUIT-P7 (lot 1) — les deux cartes de l'onglet Sources (Sonde de nuit + Agents) et la portée
du menu « Envoyer les agents ». Les cartes lisent des réservoirs DÉJÀ assemblés (pas de recompte au
front) ; la portée choisit qui l'agent va voir. Fonctions pures, testables sans base."""
from labuse.api import dashboard as D


def _res(methode, passage, statut="ok", echecs=0, actif=True, etat=("mint", "à jour")):
    return {"veille": ({"methode": methode, "passage": passage, "statut": statut,
                        "echecs_consecutifs": echecs, "actif": actif} if methode else None),
            "etat": list(etat)}


def test_carte_sonde_ne_compte_que_les_amonts_sondables():
    reservoirs = [
        _res("api", "2026-09-24T03:48", statut="ok"),
        _res("api", "2026-09-23T03:48", statut="injoignable", echecs=3,
             etat=("rouge", "sonde en panne")),                       # en panne (>=3 échecs)
        _res("agent", "2026-09-22T22:17"),                            # pas une sonde → hors amont
        _res(None, None, etat=("gris", "jamais vérifiée")),           # aucune veille → hors amont
        _res("page", "2026-09-24T03:48", statut="nouvelle_version",
             etat=("ambre", "nouvelle version")),
    ]
    c = D.carte_sonde(reservoirs, nouvelles=1)
    assert c["interrogeables"] == 3          # les 2 api + la page ; ni l'agent ni le sans-veille
    assert c["interrogees"] == 3
    assert c["en_panne"] == 1                 # l'injoignable à 3 échecs
    assert c["nouvelles"] == 1                # vient de compter_etats, pas recompté ici
    assert c["dernier_passage"] == "2026-09-24T03:48"   # le max des passages
    assert c["cadence"]                        # une phrase de cadence, jamais vide


def test_carte_sonde_amont_desactive_exclu():
    # une sonde désactivée (actif=False) n'est pas « interrogeable » : le job la saute.
    reservoirs = [_res("api", "2026-09-24T03:48", actif=False)]
    assert D.carte_sonde(reservoirs, nouvelles=0)["interrogeables"] == 0


def test_portee_agents_tous():
    reservoirs = [
        {"nom": "A", "etat": ["mint", "à jour"], "mode": "api"},
        {"nom": "B", "etat": ["mint", "à jour"], "mode": "api"},
        {"nom": "OSM", "etat": ["mint", "à jour"], "mode": "en_direct"},        # flux → exclu de --tous
        {"nom": "INPI", "etat": ["mint", "à jour"], "mode": "sans_millesime"},  # sans millésime → exclu
    ]
    # « tous » = comme `--tous` : les réservoirs interrogeables, SANS flux en direct ni sans-millésime
    # (pas de DB nécessaire → c=None).
    assert sorted(r["nom"] for r in D._cibles_agents_portee(None, reservoirs, "tous")) == ["A", "B"]


def test_semaine_agents_une_sur_deux():
    from datetime import date
    from labuse.jobs import semaine_agents
    # semaine ISO paire = « on », impaire = « off » (cadence 15 jours).
    assert semaine_agents(date(2026, 1, 5)) != semaine_agents(date(2026, 1, 12))   # 2 semaines voisines
    assert semaine_agents(date(2026, 1, 5)) == semaine_agents(date(2026, 1, 19))   # 2 semaines de même parité
