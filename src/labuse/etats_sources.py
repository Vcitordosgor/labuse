"""RETOURS-8 (R1/R2) — UN SEUL VOCABULAIRE pour l'état d'une source.

Avant : quatre chiffres se contredisaient (bandeau « rien à injecter », chip « 1 à rafraîchir »,
Pilotage « 0 nouvelle version / 3 manuelles en retard », page Sources client « 2 en retard »).
Trois mécanismes distincts les nourrissaient — l'agent (sentinelle, version amont constatée), la
fraîcheur (heuristique « dernière publication + cadence »), les rappels manuels — sans arbitre.

Ici l'arbitre : `etat_source(row)` rend UN état parmi quatre, et `lister_etats(conn)` produit LA
liste unique dont TOUS les compteurs dérivent (Catalogue, bandeau, Pilotage, page Sources client,
notification). Un test verrouille l'égalité des compteurs (R1.3).

Règle de priorité (R1.2) : **quand l'agent surveille une source, son constat gagne**. L'heuristique
« publication ancienne » ne peut plus contredire un « amont identique » — DPE et DVF sont ce cas : le
producteur est en retard sur SA cadence, LABUSE ne l'est pas. La ligne dit « à jour ».

Projection client (R2) : le client ne voit que DEUX états. `nouvelle_version` → « pas à jour »
(mise à jour en cours) ; **tout le reste → « à jour »**. Le mot « retard » n'apparaît jamais côté client.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text

from . import sentinelle
from .sources_catalog import WHERE_AFFICHEES, masquees_param

#: les QUATRE états admin — le vocabulaire unique. Ordre = priorité d'affichage (geste attendu d'abord).
ETATS = ("nouvelle_version", "a_rafraichir", "a_jour", "non_surveillee")

#: méthodes de veille qui sont une VRAIE sonde amont (un rappel manuel n'en est pas une).
_SONDES = ("api", "page", "entete", "temoin")

#: cadence normée → tournure « le producteur publie … » (mention non-surveillée, jamais un jugement).
_CADENCE_HUMAIN = {
    "hebdomadaire": "chaque semaine", "hebdo": "chaque semaine", "mensuel": "chaque mois",
    "mensuelle": "chaque mois", "trimestriel": "chaque trimestre", "trimestrielle": "chaque trimestre",
    "semestriel": "chaque semestre", "semestrielle": "chaque semestre", "annuel": "chaque année",
    "annuelle": "chaque année", "continue": "en continu", "continu": "en continu",
}


def _jjmm(d) -> str | None:
    """Une date/datetime → « JJ/MM/AAAA » (ou None). Tolère str ISO déjà formée."""
    if d is None:
        return None
    if isinstance(d, str):
        return d[:10]
    try:
        return d.strftime("%d/%m/%Y")
    except Exception:  # noqa: BLE001 — jamais casser un affichage pour une date exotique
        return None


def etat_source(row, *, now: datetime | None = None) -> dict:
    """UN état de source parmi les quatre, + les libellés à afficher. Fonction PURE : `row` est un
    mapping portant `name`, `veille_methode`, `veille_statut`, `veille_actif`,
    `veille_cadence_attendue`, `last_sync_at`, `source_cadence`, `source_horizon_at`.

    Retour :
      · `etat`         — un de ETATS (vocabulaire admin unique) ;
      · `etat_client`  — projection deux états : 'a_jour' | 'pas_a_jour' (R2) ;
      · `publie_le`    — dernière publication producteur (JJ/MM/AAAA) si connue, sinon None ;
      · `cadence`      — mention « le producteur publie … » pour les non-surveillées (jamais rouge) ;
      · `phrase_admin` — la phrase honnête du dashboard ;
      · `phrase_client`— la phrase honnête de la page Sources client.
    """
    now = now or datetime.now(tz=timezone.utc)
    methode = row.get("veille_methode")
    statut = row.get("veille_statut")
    actif = row.get("veille_actif")
    surveillee = methode in _SONDES and actif is not False
    publie_le = _jjmm(row.get("source_horizon_at"))
    cad = (row.get("source_cadence") or "").strip().lower()
    cadence_h = _CADENCE_HUMAIN.get(cad)

    if surveillee:
        # L'AGENT GAGNE. L'heuristique de cadence est ignorée : un « amont identique » ne peut pas
        # devenir « en retard » parce que le producteur, lui, a du retard sur sa propre cadence.
        if statut == "nouvelle_version":
            etat = "nouvelle_version"
            phrase_admin = "Nouvelle version disponible chez le producteur — à injecter."
            phrase_client = "Mise à jour en cours."
        else:
            # 'ok', None (pas encore sondée), 'injoignable', 'illisible' → aucune version plus récente
            # CONNUE : la source est à jour. (Un échec de sonde est signalé À PART au dashboard.)
            etat = "a_jour"
            phrase_admin = ("À jour — le producteur n'a rien publié depuis le " + publie_le + "."
                            if publie_le else "À jour — l'agent a vérifié, l'amont est identique.")
            phrase_client = "À jour."
    elif methode == "rappel":
        # Source manuelle : à rafraîchir SI la cadence attendue est dépassée (geste de Vic).
        cadence_attendue = row.get("veille_cadence_attendue")
        lsa = row.get("last_sync_at")
        overdue = (cadence_attendue is not None and lsa is not None
                   and (now - (lsa if lsa.tzinfo else lsa.replace(tzinfo=timezone.utc))).days
                   > int(cadence_attendue))
        if overdue:
            etat = "a_rafraichir"
            phrase_admin = "À rafraîchir — source manuelle, cadence attendue dépassée."
            phrase_client = "À jour."   # côté client : jamais « en retard » (mandat R2)
        else:
            etat = "a_jour"
            phrase_admin = "À jour — source manuelle dans sa cadence."
            phrase_client = "À jour."
    else:
        # Aucune sonde : NON surveillée. L'heuristique de cadence devient une simple MENTION,
        # jamais un état rouge (R1.1). Côté client : à jour.
        etat = "non_surveillee"
        mention = (f"Le producteur publie habituellement {cadence_h}" if cadence_h else None)
        if mention and publie_le:
            mention += f" ; dernière publication le {publie_le}."
        elif mention:
            mention += "."
        phrase_admin = mention or "Non surveillée — pas d'URL amont à millésime stable."
        phrase_client = "À jour."

    return {
        "etat": etat,
        "etat_client": "pas_a_jour" if etat == "nouvelle_version" else "a_jour",
        "publie_le": publie_le,
        "cadence": cadence_h,
        "phrase_admin": phrase_admin,
        "phrase_client": phrase_client,
    }


_SQL_ETATS = (
    "SELECT d.id, d.name, d.last_sync_at, d.source_cadence, d.source_horizon_at,"
    "       v.methode AS veille_methode, v.dernier_statut AS veille_statut, v.actif AS veille_actif,"
    "       v.cadence_attendue_jours AS veille_cadence_attendue"
    "  FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id"
    f" WHERE {WHERE_AFFICHEES}"
)


def lister_etats(conn, *, now: datetime | None = None) -> list[dict]:
    """LA liste unique : une entrée par source AFFICHÉE, avec son `etat` (et les libellés). Toutes les
    surfaces (Catalogue, bandeau, Pilotage, Sources client) dérivent leurs compteurs d'ICI — c'est ce
    qui garantit qu'elles ne peuvent plus se contredire. `conn` = connexion SQLAlchemy (engine.begin()
    ou Session). Tolère l'absence de `source_veille` (base neuve) → tout « non surveillée »/« à jour »."""
    now = now or datetime.now(tz=timezone.utc)
    try:
        rows = conn.execute(text(_SQL_ETATS), {"masquees": masquees_param()}).mappings().all()
    except Exception:  # noqa: BLE001 — table absente (base de test partielle) : liste vide, jamais un 500
        return []
    out = []
    for r in rows:
        d = dict(r)
        d.update(etat_source(r, now=now))
        out.append(d)
    return out


def compteurs(etats: list[dict]) -> dict:
    """Les compteurs admin, dérivés de la liste unique. `nouvelle_version` et `a_rafraichir` sont les
    deux gestes attendus (Pilotage) ; `total`/`a_jour`/`non_surveillee` complètent le Catalogue."""
    c = {e: 0 for e in ETATS}
    for x in etats:
        c[x["etat"]] = c.get(x["etat"], 0) + 1
    c["total"] = len(etats)
    # projection client (R2) : « pas à jour » = les nouvelles versions ; tout le reste « à jour ».
    c["pas_a_jour"] = c["nouvelle_version"]
    c["client_a_jour"] = c["total"] - c["nouvelle_version"]
    return c


# rétro-lien vocabulaire : la nature Y5.4 (sentinelle) reste l'étiquette VISUELLE de la sonde ; l'état
# ci-dessus est le VERDICT. On garde `nature` accessible pour le panneau admin sans le dupliquer.
nature = sentinelle.nature
