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
# États VÉRIFIÉS après `rebuild-demo --commune 97415` (peuvent évoluer si les données changent).
# États VÉRIFIÉS après rebuild + correctif R1 « déjà bâti » (BD TOPO bâtiments).
# Mis à jour après l'IMPORT COMPLET (LOT 2, 51 129 parcelles) : BV0912 → « à creuser » (ER 81 +
# accès) — la donnée commune complète affine le verdict, on accepte le verdict plus conservateur.
DEMO_PARCELS = [
    {"idu": "97415000BK0023", "attendu": "opportunite",
     "role": "Parcelle VITRINE — opportunité VACANTE (0 % bâti, vérifiée à l'orthophoto)",
     "montre": "opp ~74, 9723 m² NUS avec accès voirie ; prix de marché FIABLE ~5310 €/m² (14 ventes) ; CA indicatif ~32-35 M€",
     "vigilance": "« vérifiée » = sur couches dispo ; bilan = simulation indicative"},
    {"idu": "97415000HP0390", "attendu": "a_creuser",
     "role": "À creuser — EMPLACEMENT RÉSERVÉ (ER 39) + accès à vérifier + surface limite",
     "montre": "score 63 en zone U (constructible) mais 3 SOFT_FLAG honnêtes : « ER 39 - Aménagement du chemin "
               "Bien-Aimé » (prescription PLU), « pas d'accès direct évident à la voirie » et « surface 397 m² "
               "sous le seuil de valorisation (400 m²) » → rétrogradée honnêtement en « à creuser », pas vendue "
               "comme opportunité",
     "vigilance": "ER réservé + accès à confirmer + surface limite ; LABUSE signale les contraintes, ne survend pas"},
    {"idu": "97415000BP0571", "attendu": "faux_positif_probable",
     "role": "RÉSIDENCE EXISTANTE détectée — correctif « déjà bâti » (ex-fausse vitrine)",
     "montre": "score brut 77 MAIS « ensemble bâti : 4 bâtiments couvrant 18 % (BD TOPO) » → faux positif. "
               "Avant le correctif, LABUSE la vendait comme opportunité à 23,5 M€ — plus maintenant.",
     "vigilance": "l'histoire à raconter : le produit se corrige et le montre"},
    {"idu": "97415000BN1351", "attendu": "a_creuser", "role": "À creuser — PÉRIMÈTRE PPR (inondation + mvt)",
     "montre": "le PPR rétrograde l'opportunité en « à creuser » + bilan affiché",
     "vigilance": "PPR = prescriptions à vérifier, PAS une exclusion"},
    {"idu": "97415000DH0145", "attendu": "a_creuser",
     "role": "À creuser — SAR compatible + zone AUc MAIS PPR fort (compatible ≠ constructible)",
     "montre": "tout dit « go » (SAR « vocation compatible — espace urbanisé à densifier », zone AUc "
               "constructible, surface utile 706 m², marché fort ~2 087 €/m²) SAUF le risque réel : « PPR fort "
               "inondation + mouvement de terrain (~33 %) » + accès non identifié (~18 m) → à creuser",
     "vigilance": "parcelle tentante mais risque fort réel ; compatibilité SAR/zonage ne vaut pas constructibilité automatique"},
    {"idu": "97415000BO0845", "attendu": "faux_positif_probable", "role": "Faux positif PARKING déclassé",
     "montre": "score brut ~82 mais « faux positif probable » + motif « parking sur 82 % (OSM) »",
     "vigilance": "le score brut reste affiché (transparence)"},
    {"idu": "97415000BV1431", "attendu": "faux_positif_probable", "role": "Faux positif PENTE déclassé",
     "montre": "« pente 103 % — terrain non aménageable » + ⚠ proxy SAR divergent du PLU (zone AU)", "vigilance": "—"},
    {"idu": "97415000BO0619", "attendu": "faux_positif_probable", "role": "Micro-parcelle déclassée",
     "montre": "« micro-parcelle 28 m² — aucun programme possible »", "vigilance": "—"},
]


def demo_overview(session: Session, commune: str = "Saint-Paul") -> list[dict]:
    """Parcelles de démo enrichies de leur verdict LIVE — pour le panneau « Démo guidée »,
    l'endpoint /demo et la QA (warm-demo). `conforme` = statut live == statut attendu."""
    out: list[dict] = []
    for i, spec in enumerate(DEMO_PARCELS, 1):
        row = session.execute(text(
            "SELECT p.id, e.status, e.opportunity_score FROM parcels p "
            "LEFT JOIN LATERAL (SELECT status, opportunity_score FROM parcel_evaluations e "
            "  WHERE e.parcel_id = p.id ORDER BY evaluated_at DESC LIMIT 1) e ON true "
            "WHERE p.idu = :idu"), {"idu": spec["idu"]}).mappings().first()
        status = row["status"] if row else None
        out.append({
            "ordre": i, "idu": spec["idu"], "role": spec["role"], "montre": spec["montre"],
            "vigilance": spec["vigilance"], "attendu": spec["attendu"],
            "present": bool(row), "status": status,
            "opportunity_score": row["opportunity_score"] if row else None,
            "conforme": bool(row) and status == spec["attendu"],
        })
    return out

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
    AUCUN nom de personne physique.

    Suit les parcelles de DÉMO crédibles (opportunités / à creuser de DEMO_PARCELS) — pas
    « les 4 premières par ordre d'IDU », qui faisaient suivre des faux positifs en démo
    (constat d'audit). Repli sur de vraies opportunités si les parcelles de démo manquent."""
    from . import models, prospection
    wanted = [p["idu"] for p in DEMO_PARCELS if p["attendu"] in ("opportunite", "a_creuser")]
    pids = session.execute(
        text("SELECT id FROM parcels WHERE commune = :c AND idu = ANY(:idus) ORDER BY array_position(:idus, idu) LIMIT :n"),
        {"c": commune, "idus": wanted, "n": len(_SEED_PIPELINE)}).scalars().all()
    if len(pids) < len(_SEED_PIPELINE):                       # base de test / parcelles absentes
        extra = session.execute(text(
            """SELECT p.id FROM parcels p
               LEFT JOIN LATERAL (SELECT status FROM parcel_evaluations e WHERE e.parcel_id=p.id
                 ORDER BY evaluated_at DESC LIMIT 1) e ON true
               WHERE p.commune = :c AND p.id <> ALL(:got)
               ORDER BY (e.status = 'opportunite') DESC NULLS LAST, p.idu LIMIT :n"""),
            {"c": commune, "got": list(pids) or [0], "n": len(_SEED_PIPELINE) - len(pids)}).scalars().all()
        pids = list(pids) + list(extra)
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

    for kind, lbl in [("ppr", "PPR"), ("sar", "SAR"), ("osm_faux_positif", "OSM faux positifs"),
                      ("batiment", "Bâtiments (BD TOPO)")]:
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
    except Exception:  # noqa: BLE001
        ok_exp = False
    chk("Exports HTML/Markdown", ok_exp, "section prospection rendue")

    ok = all(c["ok"] for c in checks if c["critical"])
    return {"ok": ok, "commune": commune, "checks": checks}
