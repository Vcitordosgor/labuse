"""Stabilisation de l'ÉTAT DÉMO (reproductibilité après recyclage du conteneur).

Ni nouvelle fonctionnalité métier, ni changement de scoring/seuils : seulement un
healthcheck, un seed de pipeline (sans aucun nom réel) et la liste des parcelles de démo.
La reconstruction elle-même réutilise les briques DURABLES existantes (init-db → ingestion
→ ensure_geom_2975 → evaluate), orchestrées par la commande CLI `rebuild-demo`.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Parcelles utiles en démo (IDU stables Saint-Paul) — rôle + ce qu'elles montrent + vigilance.
DEMO_PARCELS = [
    {"idu": "97415000BN1351", "role": "Opportunité vérifiée + bilan + PPR",
     "montre": "verdict, prix DVF fiable, charge foncière, périmètre PPR i_mvt",
     "vigilance": "PPR = prescriptions à vérifier, pas une exclusion"},
    {"idu": "97415000BO0057", "role": "Opportunité avec bilan promoteur lisible",
     "montre": "grande surface vendable, CA et charge foncière chiffrés (prix de marché fiable)",
     "vigilance": "hors îlot SAR (couverture partielle) ; bilan = simulation indicative"},
    {"idu": "97415000BH0283", "role": "SAR compatible (espace urbanisé à densifier)",
     "montre": "vocation SAR compatible — à croiser avec PLU/PPR", "vigilance": "compatibilité ≠ constructibilité"},
    {"idu": "97415000BO0845", "role": "Faux positif PARKING déclassé",
     "montre": "score brut élevé mais statut « faux positif probable » + motif parking OSM",
     "vigilance": "le score brut reste affiché (transparence)"},
    {"idu": "97415000BV1431", "role": "Faux positif PENTE déclassé",
     "montre": "déclassement pente 94 % + SAR vocation naturelle (à vérifier)", "vigilance": "—"},
    {"idu": "97415000BO0619", "role": "Micro-parcelle déclassée",
     "montre": "surface ~28 m² → faux positif (aucun programme possible)", "vigilance": "—"},
    {"idu": "97415000BN1086", "role": "Micro-parcelle déclassée (variante)",
     "montre": "surface ~29 m² → faux positif", "vigilance": "—"},
    {"idu": "97415000BK0023", "role": "Bord d'équipement CONSERVÉ (anti-sur-déclassement)",
     "montre": "effleure un parking (<30 %) → reste opportunité", "vigilance": "honnêteté : on ne sur-déclasse pas"},
]

# Seed pipeline : statut colonne + prospection MANUELLE réaliste, AUCUN nom de propriétaire réel.
_SEED_PIPELINE = [
    {"role": "proprietaire_a_identifier", "prospection": {
        "statut_proprietaire": "a_identifier", "source_statut": "non_renseignee",
        "prochaine_action": "Demander le relevé de propriété au SPF", "responsable_interne": "A. Promoteur",
        "notes_contact": "Repérée en réunion sourcing ; relevé à demander."}},
    {"role": "contact_a_preparer", "prospection": {
        "statut_proprietaire": "public_probable", "source_statut": "deduit_manuellement", "niveau_confiance": "faible",
        "contact_organisation": "Commune de Saint-Paul (à confirmer)", "prochaine_action": "Préparer courrier au service foncier",
        "responsable_interne": "B. Développement"}},
    {"role": "relance_prevue", "prospection": {
        "statut_proprietaire": "indivision_probable", "source_statut": "saisi_utilisateur", "niveau_confiance": "moyen",
        "prochaine_action": "Relancer le contact (1er échange sans réponse)", "responsable_interne": "A. Promoteur",
        "notes_contact": "Indivision probable (plusieurs droits) — bloqueur fréquent."}},
    {"role": "en_discussion", "prospection": {
        "statut_proprietaire": "identifie_manuellement", "source_statut": "document_externe_utilisateur",
        "niveau_confiance": "eleve", "contact_organisation": "EPF Réunion (interlocuteur)",
        "prochaine_action": "Caler un RDV de cadrage", "responsable_interne": "C. Direction"}},
]


def seed_demo_pipeline(session: Session, commune: str = "Saint-Paul") -> int:
    """Crée quelques entrées pipeline (idempotent) pour que le Kanban ne soit pas vide en démo.
    AUCUN nom de personne physique. Réutilise des parcelles réelles de la commune."""
    from . import models, prospection
    pids = session.execute(
        text("SELECT id FROM parcels WHERE commune = :c ORDER BY idu LIMIT :n"),
        {"c": commune, "n": len(_SEED_PIPELINE)}).scalars().all()
    n = 0
    for pid, spec in zip(pids, _SEED_PIPELINE):
        session.execute(text("DELETE FROM pipeline_entries WHERE parcel_id = :p"), {"p": pid})  # idempotent
        session.add(models.PipelineEntry(
            parcel_id=pid, status=spec["role"], priority="moyenne",
            notes=spec["prospection"].get("notes_contact", ""),
            prospection=prospection.merge_prospection(prospection.default_prospection(), spec["prospection"])))
        n += 1
    session.flush()
    return n


def healthcheck(session: Session, commune: str = "Saint-Paul") -> dict:
    """Contrôle l'état de la base pour une démo. Renvoie {ok, checks:[{name, ok, detail, critical}]}."""
    checks: list[dict] = []

    def chk(name, ok, detail, critical=True):
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "critical": critical})

    def scal(sql, **kw):
        return session.execute(text(sql), {"c": commune, **kw}).scalar()

    n_parcels = scal("SELECT count(*) FROM parcels WHERE commune = :c") or 0
    chk("Parcelles", n_parcels > 0, f"{n_parcels} parcelles {commune}")

    has_col = scal("SELECT 1 FROM information_schema.columns WHERE table_name='parcels' AND column_name='geom_2975'")
    n_invalid = scal("SELECT count(*) FROM parcels WHERE commune=:c AND geom_2975 IS NOT NULL AND NOT ST_IsValid(geom_2975)") if has_col else None
    n_null = scal("SELECT count(*) FROM parcels WHERE commune=:c AND geom_2975 IS NULL") if has_col else None
    chk("geom_2975 valide", bool(has_col) and not n_invalid and not n_null,
        f"colonne={'oui' if has_col else 'NON'} · invalides={n_invalid} · nuls={n_null}")

    n_idx = scal("SELECT count(*) FROM pg_indexes WHERE indexname IN "
                 "('idx_parcels_geom_2975','idx_spatial_layers_geom_2975')")
    chk("Index géométriques GIST", (n_idx or 0) >= 2, f"{n_idx}/2 index")

    dvf = session.execute(text(
        "SELECT count(*), min(extract(year FROM date_mutation))::int, max(extract(year FROM date_mutation))::int "
        "FROM dvf_mutations WHERE commune=:c"), {"c": commune}).one()
    chk("DVF geo-dvf", (dvf[0] or 0) > 0 and (dvf[2] or 0) >= 2024, f"{dvf[0]} mutations, période {dvf[1]}-{dvf[2]}")

    for kind, lbl in [("ppr", "PPR"), ("sar", "SAR"), ("osm_faux_positif", "OSM faux positifs")]:
        n = scal("SELECT count(*) FROM spatial_layers WHERE commune=:c AND kind=:k", k=kind) or 0
        chk(lbl, n > 0, f"{n} entités")

    n_fp = scal("SELECT count(*) FROM parcels p JOIN LATERAL (SELECT status FROM parcel_evaluations e "
                "WHERE e.parcel_id=p.id ORDER BY evaluated_at DESC LIMIT 1) e ON true "
                "WHERE p.commune=:c AND e.status='faux_positif_probable'") or 0
    n_decl = scal("SELECT count(*) FROM cascade_results WHERE layer_name='declassement'") or 0
    chk("Déclassement appliqué", n_fp > 0 or n_decl > 0, f"{n_fp} faux positifs · {n_decl} motifs cascade")

    # top 20 opportunités sans faux positif évident (surface ≥ 100, pas dominé par un équipement OSM)
    bad = scal("""
        WITH opp AS (SELECT p.id, p.geom_2975, ST_Area(p.geom_2975) a FROM parcels p
          JOIN LATERAL (SELECT status, opportunity_score, evaluated_at FROM parcel_evaluations e
            WHERE e.parcel_id=p.id ORDER BY evaluated_at DESC LIMIT 1) e ON true
          WHERE p.commune=:c AND e.status='opportunite'
          ORDER BY e.opportunity_score DESC, ST_Area(p.geom_2975) DESC LIMIT 20)
        SELECT count(*) FROM opp o WHERE o.a < 100
           OR EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind='osm_faux_positif' AND s.commune=:c
                      AND ST_Area(ST_Intersection(s.geom_2975,o.geom_2975))/NULLIF(o.a,0) >= 0.5)""") if has_col else None
    chk("Top 20 sans faux positif évident", bad == 0, f"{bad} faux positif(s) dans le top 20")

    crit_present = {k for (k,) in session.execute(text("SELECT DISTINCT kind FROM spatial_layers")).all()}
    reliable = all(k in crit_present for k in ("sar", "foret_publique", "trait_de_cote")) and \
        ("ppr" in crit_present or "georisque_alea" in crit_present)
    chk("Badge « Opportunité vérifiée » actif", reliable, "couches critiques présentes (reliable_ready)")

    has_prosp = scal("SELECT 1 FROM information_schema.columns WHERE table_name='pipeline_entries' AND column_name='prospection'")
    chk("Module prospection", bool(has_prosp), f"colonne prospection={'oui' if has_prosp else 'NON'}")
    n_pipe = scal("SELECT count(*) FROM pipeline_entries") or 0
    chk("Pipeline", True, f"{n_pipe} entrée(s) suivie(s)", critical=False)

    try:
        from .api.export import fiche_html, fiche_markdown
        f = {"parcel": {"idu": "TEST", "commune": commune, "surface_m2": 1000, "section": "X", "numero": "1"},
             "verdict": {"status": "opportunite", "opportunity_score": 70, "completeness_score": 60, "reasons": []},
             "cascade": [], "sources_responded": [], "sources_silent": [], "disclaimer": "x", "ai": None,
             "prospection": {"statut_label": "Propriétaire inconnu", "data": {}}}
        ok_exp = "Prospection propriétaire" in fiche_markdown(f) and "Prospection propriétaire" in fiche_html(f)
    except Exception as exc:  # noqa: BLE001
        ok_exp = False
    chk("Exports HTML/Markdown", ok_exp, "section prospection rendue")

    ok = all(c["ok"] for c in checks if c["critical"])
    return {"ok": ok, "commune": commune, "checks": checks}
