"""RETOURS-16 (point 9) — « → CRM » depuis un projet pousse EXPLICITEMENT les retenues dans le CRM.

Garde-fou de la cause corrigée : le bouton ne faisait que naviguer ; la synchro auto (geste Tinder)
ratait les retenues créées autrement OU dont la carte CRM avait été archivée. L'endpoint
`POST /projets/{pid}/vers-crm` réconcilie : insère les absentes, RESTAURE les archivées, ne touche pas
les actives — idempotent, SANS doublon (clé unique compte_id+parcel_id).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import projets

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _parcelle(s, idu):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()


@pytest.mark.db
def test_vers_crm_reconcilie_idempotent_sans_doublon(db_session, monkeypatch):
    s = db_session
    pc1 = _parcelle(s, "97160000AA0001")
    pc2 = _parcelle(s, "97160000AA0002")
    monkeypatch.setattr(projets, "_search_items",
                        lambda db, cadrage, limit, overrides=None: [{"idu": "97160000AA0001"}, {"idu": "97160000AA0002"}])
    pid = projets.projet_create(projets.ProjetIn(cadrage={"communes": ["X"]}, nom="VC"), None, s)["projet"]["id"]

    # deux retenues (la synchro auto crée déjà leurs cartes CRM)
    projets.projet_parcelle_statut(pid, "97160000AA0001", projets.StatutIn(statut="retenue"), None, s)
    projets.projet_parcelle_statut(pid, "97160000AA0002", projets.StatutIn(statut="retenue"), None, s)

    # on ARCHIVE la carte de la 1re retenue → elle est « sortie » du CRM (cas du bug : désynchro).
    s.execute(text("UPDATE pipeline_entries SET archived_at = now() WHERE parcel_id = :pc"), {"pc": pc1})
    s.flush()
    actives_avant = s.execute(text("SELECT count(*) FROM pipeline_entries WHERE archived_at IS NULL")).scalar()

    # « → CRM » : réconcilie — la 1re (archivée) REVIENT, la 2e est déjà là.
    out = projets.projet_vers_crm(pid, None, s)
    assert out["total"] == 2
    assert out["ajoutees"] == 1 and out["deja"] == 1

    # les deux retenues sont ACTIVES, et chacune n'a QU'UNE carte (aucun doublon).
    par_parcel = dict(s.execute(text(
        "SELECT parcel_id, count(*) FROM pipeline_entries WHERE parcel_id = ANY(:ids) "
        "AND archived_at IS NULL GROUP BY parcel_id"), {"ids": [pc1, pc2]}).all())
    assert par_parcel == {pc1: 1, pc2: 1}
    assert s.execute(text("SELECT count(*) FROM pipeline_entries WHERE archived_at IS NULL")).scalar() == actives_avant + 1

    # 2e appel : rien n'est ajouté, toujours aucun doublon (idempotent).
    out2 = projets.projet_vers_crm(pid, None, s)
    assert out2 == {"ok": True, "total": 2, "ajoutees": 0, "deja": 2}
    assert s.execute(text("SELECT count(*) FROM pipeline_entries WHERE archived_at IS NULL")).scalar() == actives_avant + 1


@pytest.mark.db
def test_vers_crm_projet_sans_retenue(db_session, monkeypatch):
    s = db_session
    _parcelle(s, "97160000BB0001")
    monkeypatch.setattr(projets, "_search_items",
                        lambda db, cadrage, limit, overrides=None: [{"idu": "97160000BB0001"}])
    pid = projets.projet_create(projets.ProjetIn(cadrage={"communes": ["X"]}, nom="VIDE"), None, s)["projet"]["id"]
    # aucune retenue (la parcelle reste « proposee ») → réponse vide, pas d'erreur.
    assert projets.projet_vers_crm(pid, None, s) == {"ok": True, "total": 0, "ajoutees": 0, "deja": 0}


@pytest.mark.db
@pytest.mark.parametrize("parcours", ["vers_crm", "retenue", "reactiver_projet"])
def test_restaure_carte_ancienne_sans_colonne(db_session, monkeypatch, parcours):
    s = db_session
    idu = "97160000CC0001"
    parcel_id = _parcelle(s, idu)
    monkeypatch.setattr(projets, "_search_items", lambda *args, **kwargs: [{"idu": idu}])
    pid = projets.projet_create(
        projets.ProjetIn(cadrage={"communes": ["X"]}, nom="Restauration"), None, s)["projet"]["id"]
    retenue = projets.StatutIn(statut="retenue")
    projets.projet_parcelle_statut(pid, idu, retenue, None, s)
    if parcours == "reactiver_projet":
        projets.projet_patch(pid, projets.ProjetPatchIn(statut="archive"), None, s)
    elif parcours == "retenue":
        projets.projet_parcelle_statut(pid, idu, projets.StatutIn(statut="ecartee"), None, s)

    # Simule une archive créée avant la correction, dont personne ne peut plus afficher l'étape.
    eid = s.execute(text(
        "UPDATE pipeline_entries SET status = 'ancienne_etape', archived_at = COALESCE(archived_at, now()), notes = 'rappel' "
        "WHERE parcel_id = :pc RETURNING id"), {"pc": parcel_id}).scalar_one()
    if parcours == "vers_crm":
        projets.projet_vers_crm(pid, None, s)
    elif parcours == "retenue":
        projets.projet_parcelle_statut(pid, idu, retenue, None, s)
    else:
        projets.projet_patch(pid, projets.ProjetPatchIn(statut="actif"), None, s)

    row = s.execute(text(
        "SELECT e.id, e.notes, e.archived_at, c.id AS colonne FROM pipeline_entries e "
        "LEFT JOIN crm_columns c ON c.key = e.status AND c.compte_id IS NOT DISTINCT FROM e.compte_id "
        "WHERE e.parcel_id = :pc"), {"pc": parcel_id}).mappings().one()
    assert row["id"] == eid and row["notes"] == "rappel"
    assert row["archived_at"] is None and row["colonne"] is not None
