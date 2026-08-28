"""RADAR — schéma ISOLÉ `pige_*` (P0). DDL idempotente (FIX-GB-011), zéro écriture hors `pige_*`.

Domaine transactionnel HORS runs (comme le CRM) : les tables vivent en continu, pas de bascule.
Rien n'arrose le reste de l'app en V0 — l'isolement rend l'arrosage réversible (décidé plus tard).
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# ── Événements du domaine, journalisés dans l'event_log UNIFIÉ (kind varchar(24) — tous ≤ 24) ──
EV_NOUVELLE = "pige.nouvelle"
EV_BAISSE_PRIX = "pige.baisse_prix"
EV_STATUT_CHANGE = "pige.statut_change"
EV_VENDUE_DVF = "pige.vendue_dvf"
EV_SIGNALEMENT = "pige.signalement_client"
EV_DIGEST = "pige.digest_envoye"
EV_INTAKE_VIDE_48H = "pige.intake_vide_48h"
EVENEMENTS = (EV_NOUVELLE, EV_BAISSE_PRIX, EV_STATUT_CHANGE, EV_VENDUE_DVF,
              EV_SIGNALEMENT, EV_DIGEST, EV_INTAKE_VIDE_48H)

# ── Vocabulaire fermé (jamais deviné) ──
STATUTS = ("active", "en_vente_longue", "a_reverifier", "retiree", "vendue", "retiree_sans_vente")
NIVEAUX_RATTACHEMENT = ("source", "estime", "absent")   # Sourcé / Estimé / Absent
TYPES_BIEN = ("maison", "terrain", "immeuble", "appartement")


def captures_dir() -> Path:
    """Répertoire PRIVÉ des captures — hors racine publique, JAMAIS servi par le web (doctrine §2).
    Défaut prod `/srv/labuse/pige/captures` ; surchargé par LABUSE_PIGE_CAPTURES_DIR (dev/tests)."""
    from ..config import get_settings
    d = os.environ.get("LABUSE_PIGE_CAPTURES_DIR") or get_settings().pige_captures_dir
    return Path(d)


DDL = """
-- pige_biens : le BIEN physique (dédoublonné inter-portails), son rattachement, son cycle de vie.
CREATE TABLE IF NOT EXISTS pige_biens (
  bien_id serial PRIMARY KEY,
  commune varchar(60) NOT NULL,                 -- ∈ 24 communes (contrôlé à l'intake, sinon rejet)
  type_bien varchar(16),                        -- maison | terrain | immeuble | appartement
  est_copro boolean NOT NULL DEFAULT false,     -- appartement → parcelle de la copropriété, étiqueté « copro »
  idu varchar(14),                              -- parcelle rattachée (NULL = non rattachée)
  rattachement_niveau varchar(8) NOT NULL DEFAULT 'absent',  -- source | estime | absent
  rattachement_confiance numeric,               -- 0..1 (NULL si absent) — jamais un pin faussement sûr
  statut varchar(20) NOT NULL DEFAULT 'active', -- active|en_vente_longue|a_reverifier|retiree|vendue|retiree_sans_vente
  date_publication date,                        -- date PORTAIL si visible sur la vignette, sinon NULL
  date_premiere_saisie timestamptz NOT NULL DEFAULT now(),
  date_derniere_confirmation timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pige_biens_commune ON pige_biens (commune);
CREATE INDEX IF NOT EXISTS ix_pige_biens_idu ON pige_biens (idu);
CREATE INDEX IF NOT EXISTS ix_pige_biens_statut ON pige_biens (statut);

-- pige_annonces : une OCCURRENCE portail d'un bien (deux portails → 2 annonces, même bien_id).
CREATE TABLE IF NOT EXISTS pige_annonces (
  annonce_id serial PRIMARY KEY,
  bien_id integer NOT NULL REFERENCES pige_biens(bien_id) ON DELETE CASCADE,
  portail varchar(20) NOT NULL,                 -- slug ∈ pige.portails.PORTAILS
  url_sortante text NOT NULL,                   -- lien EXACT vers la source (le bouton le réutilise)
  date_saisie timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pige_annonces_url ON pige_annonces (url_sortante);
CREATE INDEX IF NOT EXISTS ix_pige_annonces_bien ON pige_annonces (bien_id);

-- pige_faits : les FAITS extraits + VALIDÉS. Chaque champ porte son étiquette Sourcé/Estimé/Absent
-- (jsonb `etiquettes` {champ: 'source'|'estime'|'absent'}). Rien de publiable avant `valide_at`.
CREATE TABLE IF NOT EXISTS pige_faits (
  bien_id integer PRIMARY KEY REFERENCES pige_biens(bien_id) ON DELETE CASCADE,
  prix integer,                                 -- € (NULL = Absent, jamais 0 muet)
  type_bien varchar(16),
  pieces integer,
  surface_hab numeric,
  surface_terrain numeric,
  dpe_classe varchar(2),                        -- A..G
  dpe_conso integer,                            -- kWh/m²/an
  dpe_ges integer,
  particulier_pro varchar(12),                  -- particulier | pro | NULL
  fraicheur_source varchar(12),                 -- 'publication' | 'saisie' (celle affichée)
  etiquettes jsonb NOT NULL DEFAULT '{}'::jsonb,
  valide_at timestamptz,                        -- NULL = non validé (rien de publiable)
  valide_par integer,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- pige_prix_historique : une ligne par CHANGEMENT de prix constaté → drapeau baisse + sparkline.
CREATE TABLE IF NOT EXISTS pige_prix_historique (
  id serial PRIMARY KEY,
  bien_id integer NOT NULL REFERENCES pige_biens(bien_id) ON DELETE CASCADE,
  date_constat date NOT NULL DEFAULT current_date,
  ancien_prix integer,
  nouveau_prix integer,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pige_prix_hist_bien ON pige_prix_historique (bien_id);

-- pige_captures : MÉTADONNÉES des captures (chemin privé, hash). JAMAIS servi par le web.
CREATE TABLE IF NOT EXISTS pige_captures (
  id serial PRIMARY KEY,
  bien_id integer REFERENCES pige_biens(bien_id) ON DELETE SET NULL,
  annonce_id integer REFERENCES pige_annonces(annonce_id) ON DELETE SET NULL,
  chemin_prive text NOT NULL,                   -- /srv/labuse/pige/captures/... hors racine publique
  hash varchar(64),                             -- sha256 (dédoublonnage + intégrité)
  date_capture timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pige_captures_bien ON pige_captures (bien_id);

-- pige_clics : chaque CLIC sortant (client, bien, date) → « usage par outil » du dashboard Produit.
CREATE TABLE IF NOT EXISTS pige_clics (
  id serial PRIMARY KEY,
  compte_id integer,
  bien_id integer REFERENCES pige_biens(bien_id) ON DELETE CASCADE,
  annonce_id integer REFERENCES pige_annonces(annonce_id) ON DELETE SET NULL,
  portail varchar(20),
  date_clic timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pige_clics_bien ON pige_clics (bien_id);
-- RADAR P1 (V3) : champs extraits sous le seuil de confiance → surlignés « à vérifier » à la
-- validation (mauve, réservé IA). Idempotent (ADD COLUMN IF NOT EXISTS), heal-safe.
ALTER TABLE pige_faits ADD COLUMN IF NOT EXISTS a_verifier jsonb DEFAULT '[]'::jsonb;
-- RADAR P5 (D2) : cycle de vie automatisé. `retiree_le` = quand le bien a été marqué retiré (base de
-- la qualification retiree_sans_vente, JAMAIS déduite d'un lien mort). Rapprochement DVF (vendue) :
-- date/valeur/délai/écart de prix — l'écart n'est SERVI que sur un rattachement Sourcé.
ALTER TABLE pige_biens ADD COLUMN IF NOT EXISTS retiree_le timestamptz;
ALTER TABLE pige_biens ADD COLUMN IF NOT EXISTS vendue_le date;
ALTER TABLE pige_biens ADD COLUMN IF NOT EXISTS vendue_valeur integer;
ALTER TABLE pige_biens ADD COLUMN IF NOT EXISTS vendue_delai_j integer;
ALTER TABLE pige_biens ADD COLUMN IF NOT EXISTS vendue_ecart_prix integer;
"""


def ensure_tables(engine: Engine) -> None:
    """Crée le schéma `pige_*` (idempotent). Split FIX-GB-011 (jamais de `split(';')` naïf)."""
    from ..db import sql_statements
    with engine.begin() as c:
        for stmt in sql_statements(DDL):
            if stmt.strip():
                c.execute(text(stmt))


def journaliser(db: Session, kind: str, titre: str, *, detail: str | None = None,
                idu: str | None = None, lien: str | None = None,
                compte_id: int | None = None, dedup: str | None = None) -> int:
    """Écrit un ÉVÉNEMENT de domaine Radar dans l'event_log unifié (insert direct — ce sont des faits
    de domaine, pas des notifications client ; la livraison cloche/mail au client passe par la veille,
    lot P4). `compte_id` NULL = flux pilote/admin (le rituel de Vic). `kind` ∈ EVENEMENTS."""
    assert kind in EVENEMENTS, f"événement Radar non déclaré : {kind!r}"
    return db.execute(text(
        "INSERT INTO event_log (kind, titre, detail, idu, lien, compte_id, source, dedup) "
        "VALUES (:k, :t, :d, :i, :l, :c, 'Radar', :dd) RETURNING id"),
        {"k": kind, "t": titre, "d": detail, "i": idu, "l": lien, "c": compte_id, "dd": dedup}
    ).scalar() or 0


def enregistrer_fraicheur(db: Session) -> str | None:
    """RADAR D4 — pose la fraîcheur du Radar au registre des sources = date de DERNIÈRE COLLECTE
    (`max(date_saisie)` de pige_annonces), JAMAIS une date de run. No-op si la source n'est pas au
    catalogue. Retourne la date posée (ISO) ou None si aucune collecte."""
    d = db.execute(text("SELECT max(date_saisie) FROM pige_annonces")).scalar()
    if d is not None:
        db.execute(text("UPDATE data_sources SET last_sync_at = :d "
                        "WHERE name = 'Radar (pige d''annonces)'"), {"d": d})
    return d.isoformat() if d is not None else None
