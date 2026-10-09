"""CORRECTIFS-1 D3 (RGPD) — purge des données personnelles des dirigeants déjà stockées.

Deux gestes IDEMPOTENTS (rejouables sans effet de bord) :
  1. `owner_enrichment.payload` — retire la NATIONALITÉ des dirigeants (recherche-entreprises) :
     clé `nationalite` au niveau racine ET dans chaque élément de `payload->'dirigeants'`.
  2. `pm_dirigeants.raw` — VIDE (NULL) le payload brut RNE pour toute entreprise NON diffusible
     (`diffusible` faux ou inconnu) : il porte nom/prénoms/naissance/nationalité, à ne pas conserver.

Le chemin VIVANT (ingestion) applique déjà ces règles (`score_v_fetch._sans_nationalite`,
`inpi_rne._parse_pouvoir` : `raw` None si non diffusible) ; ceci nettoie l'EXISTANT.
"""
from __future__ import annotations

from sqlalchemy import text

# Strip nationalité : au niveau racine + dans chaque dirigeant du tableau `dirigeants`.
_PURGE_PAYLOAD = text("""
    UPDATE owner_enrichment
    SET payload = (
        CASE WHEN jsonb_typeof(payload->'dirigeants') = 'array'
             THEN jsonb_set(payload, '{dirigeants}',
                    (SELECT coalesce(jsonb_agg(d - 'nationalite'), '[]'::jsonb)
                     FROM jsonb_array_elements(payload->'dirigeants') d))
             ELSE payload END) - 'nationalite'
    WHERE payload ? 'nationalite'
       OR (jsonb_typeof(payload->'dirigeants') = 'array'
           AND EXISTS (SELECT 1 FROM jsonb_array_elements(payload->'dirigeants') d
                       WHERE d ? 'nationalite'))
""")

_PURGE_RAW = text("""
    UPDATE pm_dirigeants SET raw = NULL
    WHERE diffusible IS DISTINCT FROM TRUE AND raw IS NOT NULL
""")


def purger_nationalite_et_raw(engine) -> dict:
    """Joue les deux purges. Rend le nombre de lignes touchées par geste."""
    with engine.begin() as c:
        n_payload = c.execute(_PURGE_PAYLOAD).rowcount
        n_raw = c.execute(_PURGE_RAW).rowcount
    return {"payloads_nettoyes": int(n_payload or 0), "raw_vides": int(n_raw or 0)}
