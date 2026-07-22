"""AUDIT PAIEMENT · SEC-IDOR — la CLOISON MULTI-TENANT.

Sous le rideau pilote (mot de passe partagé) les données client (projets, CRM, veilles,
filtres, signalements) étaient GLOBALES : acceptable à un seul utilisateur. Dès qu'une
licence = un accès, un compte ne doit JAMAIS voir/toucher les données d'un autre — même
en devinant un id d'URL. Cette cloison existe donc dès la première licence.

Mécanique :
- chaque table à données client porte `compte_id` (NULL = bucket pilote/démo hérité) ;
- la garde d'auth résout le compte de la session et le pose sur `request.state.compte_id`
  (reliable : le scope Starlette est partagé middleware → endpoint) ;
- toute lecture filtre `compte_id IS NOT DISTINCT FROM :cid`, toute écriture pose `:cid` ;
- `IS NOT DISTINCT FROM` fait matcher NULL↔NULL : le pilote voit le bucket hérité, un
  compte ne voit que le sien.
Le filet de vérité = les tests d'isolation (compte A crée, compte B ne voit/touche rien) :
si un site d'accès est oublié, un test tombe.
"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

# tables à données PRIVÉES du client (les données publiques — parcelles, scoring, fiches —
# ne sont jamais scopées : c'est l'analyse partagée).
SCOPED_TABLES = ("projets", "pipeline_entries", "saved_searches", "saved_filters", "signalements")


def ensure_scoping(db: Session) -> None:
    """Ajoute `compte_id` (idempotent) aux tables à données client + index. Appelé au boot
    (`ensure_schema`) et par les tests. Les lignes existantes restent NULL (bucket hérité)."""
    for t in SCOPED_TABLES:
        if not db.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar():
            continue  # table pas encore créée par son module — elle naîtra scopée au besoin
        db.execute(text(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS compte_id integer"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{t}_compte ON {t}(compte_id)"))
        # FK + ON DELETE CASCADE (posée ici, pas dans l'ORM : create_all n'a pas la table
        # comptes en dépendance). Idempotent : on n'ajoute que si absente. Vitale RGPD :
        # supprimer un compte emporte SES projets/pipeline/veilles/filtres/signalements.
        fk = f"fk_{t}_compte"
        if not db.execute(text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": fk}).scalar():
            db.execute(text(f"ALTER TABLE {t} ADD CONSTRAINT {fk} FOREIGN KEY (compte_id)"
                            f" REFERENCES comptes(id) ON DELETE CASCADE"))

    # SEC-IDOR (le plus profond) : le CRM était UNIQUE(parcel_id) — une parcelle ne pouvait
    # vivre que dans UN pipeline de toute la base. Multi-tenant : la clé devient
    # (compte_id, parcel_id). NULLS NOT DISTINCT (PG 15+) garde le bucket pilote à une entrée
    # par parcelle ; repli sur la contrainte simple si le moteur est plus ancien.
    if db.execute(text("SELECT to_regclass('pipeline_entries')")).scalar():
        has_new = db.execute(text("SELECT 1 FROM pg_constraint WHERE conname = 'uq_pipeline_compte_parcel'")).scalar()
        if not has_new:
            db.execute(text("ALTER TABLE pipeline_entries DROP CONSTRAINT IF EXISTS uq_pipeline_parcel"))
            try:
                db.execute(text("ALTER TABLE pipeline_entries ADD CONSTRAINT uq_pipeline_compte_parcel"
                                " UNIQUE NULLS NOT DISTINCT (compte_id, parcel_id)"))
            except Exception:  # noqa: BLE001 — PG < 15 : NULLS NOT DISTINCT indisponible
                db.rollback()
                db.execute(text("ALTER TABLE pipeline_entries ADD CONSTRAINT uq_pipeline_compte_parcel"
                                " UNIQUE (compte_id, parcel_id)"))
    db.commit()


def current_compte(request: Request | None) -> int | None:
    """Le compte de la session courante (None = pilote/legacy). Posé par la garde d'auth
    sur request.state.compte_id ; None si absent (route publique, mode local sans auth, ou
    appel direct de la fonction en test — tolérant à request=None)."""
    return getattr(getattr(request, "state", None), "compte_id", None)


def scope_clause(alias: str = "") -> str:
    """Fragment WHERE de cloison — `<alias>compte_id IS NOT DISTINCT FROM :cid`. `alias`
    inclut le point (« p. »). Le paramètre `:cid` est à fournir par l'appelant."""
    return f"{alias}compte_id IS NOT DISTINCT FROM :cid"
