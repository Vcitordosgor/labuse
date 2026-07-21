"""PHASE A-1 étape 2, volet 2 — BADGE « fenêtre de sortie de défiscalisation ».

Table ADDITIVE `defisc_fenetres`, dérivée en LECTURE des sources DVF/permis/copro. Ne touche JAMAIS
les tables servies (`parcel_p_score_v2`, `dryrun_parcel_evaluations`, run `q_v6_m8`). Purement un signal
de classement horodaté et tracé, exposé sur la fiche et en filtre — **jamais une date de vente promise**,
**jamais une personne physique** (le badge dit « cette parcelle entre dans une fenêtre », pas « M. X vendra »).

Doctrine (validée volet 1, `scripts/a1_walkforward.py`) : une maison/monopropriété achetée neuve mute
≈ 2,4× plus dans la fenêtre de sortie d'engagement (+6 à +11 ans) qu'hors fenêtre (walk-forward as-of, OR
2,43 IC95 [1,49 ; 4,34], seed 974). Le signal est donc VALIDÉ ; ce module le matérialise.

Périmètre : **maisons individuelles / monopropriété uniquement** (`copro_rnic = copro_dvf = false`) — en
copropriété, revendre un lot ne rend pas la parcelle acquérable (cf. `A1_CADRAGE_DEFISC.md` §5).

Proxy « achat neuf » (cf. étape 1) : VEFA (label direct DVF), ou Vente de logement ≤ 3 ans après achèvement
d'un PC. On retient la DERNIÈRE acquisition neuf de la parcelle. Fenêtre = bande [Y+6, Y+11] (les deux
longueurs d'engagement — 6 ans Girardin/Pinel-6, 9 ans Scellier/Duflot/Pinel-9 — le dispositif exact est
inconnu, d'où « Estimé »). Acquisition = Sourcée (DVF) ; fenêtre = Estimée.

Ancrage temporel : `ref_year` explicite (JAMAIS `now()`, doctrine `anc.py`). `fenetre_active` = la bande
recouvre [ref_year, ref_year+2]. Rebuild complet idempotent.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

VEFA = "Vente en l'état futur d'achèvement"
DEFAULT_REF_YEAR = 2026        # année de prospection de référence (fenêtres actives 2026-2028)

DDL = """
CREATE TABLE IF NOT EXISTS defisc_fenetres (
  idu              varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  proxy            text    NOT NULL,       -- 'vefa' | 'permis_achevement'
  achat_neuf_annee int     NOT NULL,       -- Y : année d'acquisition neuf (Sourcé DVF)
  fenetre_debut    int     NOT NULL,       -- Y+6
  fenetre_fin      int     NOT NULL,       -- Y+11
  fenetre_active   boolean NOT NULL,       -- bande [Y+6,Y+11] ∩ [ref_year, ref_year+2] (Estimé, as-of build)
  statut           text    NOT NULL DEFAULT 'Estimé',
  source_libelle   text    NOT NULL,       -- trace : 'DVF VEFA 2016' | 'DVF vente 2017 + achèvement PC 2015'
  libelle_badge    text    NOT NULL,       -- phrase descriptive (CSV/trace, sans date-promesse)
  libelle_court    text    NOT NULL,       -- CHIP servi : « Sortie de défisc. probable · AAAA-AAAA · Estimé »
  detail           text    NOT NULL,       -- SURVOL : mécanisme + ×2,4 sourcé + « pas une prédiction »
  decote_pct       int,                    -- N2 : médiane revente/achat neuf (%) — recalculée DVF, NULL si N/A
  decote_n         int,                    -- N2 : nb de couples achat→revente ayant servi à la médiane
  decote_libelle   text,                   -- N2 : phrase « décote » servie (argument de négociation)
  updated_at       timestamptz DEFAULT now()
);
"""

# N2 — décote de revente défisc, RECALCULÉE depuis DVF (jamais codée en dur). Pour les parcelles MONO
# acquises en VEFA (neuf) puis revendues > 2 ans après (hors acte de livraison) : médiane du ratio
# prix_revente / prix_achat_neuf, bornée [0,2 ; 3] (anti-artefact DVF), avec le n.
_DECOTE_SQL = """
WITH m AS (
  SELECT id_parcelle AS idu, date_mutation::date AS dt, nature_mutation AS nat,
         valeur_fonciere AS val, type_local AS tl
  FROM dvf_mutations_histo WHERE nature_mutation IN ('Vente', :vefa) AND valeur_fonciere > 0
  UNION ALL
  SELECT id_parcelle, date_mutation::date, nature_mutation, valeur_fonciere, type_local
  FROM dvf_mutations_parcelle WHERE nature_mutation IN ('Vente', :vefa) AND valeur_fonciere > 0),
mono AS (SELECT idu FROM p_model_ext_copro WHERE NOT (COALESCE(copro_rnic,false) OR COALESCE(copro_dvf,false))),
vefa AS (SELECT m.idu, m.dt, m.val FROM m JOIN mono ON mono.idu = m.idu WHERE m.nat = :vefa),
couple AS (   -- revente EN FENÊTRE DE SORTIE [+5,+11] ans (contexte défisc), pas un flip rapide
  SELECT v.val AS acq, r.val AS res
  FROM vefa v
  JOIN LATERAL (
    SELECT r.val FROM m r
    WHERE r.idu = v.idu AND r.nat = 'Vente'
      AND r.dt BETWEEN v.dt + interval '5 years' AND v.dt + interval '11 years'
      AND r.tl IN ('Maison','Appartement') AND r.val > 0
    ORDER BY r.dt LIMIT 1) r ON true)
SELECT round(100 * percentile_cont(0.5) WITHIN GROUP (ORDER BY res/acq))::int AS pct, count(*) AS n
FROM couple WHERE res/acq BETWEEN 0.2 AND 3.0;
"""

# Dernière acquisition NEUF par parcelle MONO, avec l'année Y, le proxy et l'année d'achèvement (si permis).
_SELECT_RAW = """
WITH ach AS (
  SELECT pmp.idu, min(md.date_achevement) AS ach FROM p_model_permits pmp
  JOIN m10_permit_delais md ON md.permit_id = pmp.permit_id
  WHERE pmp.type = 'PC' AND md.date_achevement IS NOT NULL GROUP BY pmp.idu
),
muts AS (
  SELECT id_parcelle AS idu, date_mutation::date AS dt, nature_mutation AS nat, type_local AS tl
  FROM dvf_mutations_histo WHERE nature_mutation IN ('Vente', :vefa)
  UNION ALL
  SELECT id_parcelle, date_mutation::date, nature_mutation, type_local
  FROM dvf_mutations_parcelle WHERE nature_mutation IN ('Vente', :vefa)
),
neuf AS (
  SELECT m.idu, m.dt,
         EXTRACT(YEAR FROM m.dt)::int AS y,
         CASE WHEN m.nat = :vefa THEN 'vefa' ELSE 'permis_achevement' END AS proxy,
         EXTRACT(YEAR FROM a.ach)::int AS ach_year
  FROM muts m
  LEFT JOIN ach a ON a.idu = m.idu
  WHERE m.nat = :vefa
     OR (a.ach IS NOT NULL AND m.dt >= a.ach AND m.dt < a.ach + INTERVAL '3 years'
         AND m.tl IN ('Maison', 'Appartement'))
)
SELECT DISTINCT ON (n.idu) n.idu, n.y, n.proxy, n.ach_year
FROM neuf n
JOIN p_model_ext_copro c ON c.idu = n.idu
WHERE NOT (COALESCE(c.copro_rnic, false) OR COALESCE(c.copro_dvf, false))   -- MONO uniquement
ORDER BY n.idu, n.dt DESC;
"""

_INSERT = """
INSERT INTO defisc_fenetres
  (idu, proxy, achat_neuf_annee, fenetre_debut, fenetre_fin, fenetre_active, statut,
   source_libelle, libelle_badge, libelle_court, detail, decote_pct, decote_n, decote_libelle, updated_at)
VALUES
  (:idu, :proxy, :y, :deb, :fin, :active, 'Estimé', :src, :badge, :court, :detail,
   :decote_pct, :decote_n, :decote_libelle, now())
ON CONFLICT (idu) DO UPDATE SET
  proxy = EXCLUDED.proxy, achat_neuf_annee = EXCLUDED.achat_neuf_annee,
  fenetre_debut = EXCLUDED.fenetre_debut, fenetre_fin = EXCLUDED.fenetre_fin,
  fenetre_active = EXCLUDED.fenetre_active, source_libelle = EXCLUDED.source_libelle,
  libelle_badge = EXCLUDED.libelle_badge, libelle_court = EXCLUDED.libelle_court,
  detail = EXCLUDED.detail, decote_pct = EXCLUDED.decote_pct, decote_n = EXCLUDED.decote_n,
  decote_libelle = EXCLUDED.decote_libelle, updated_at = now();
"""


def _compute_decote(session) -> tuple[int | None, int | None]:
    """N2 — médiane RECALCULÉE du ratio revente/achat-neuf (%) + n, sur les VEFA mono revendues."""
    r = session.execute(text(_DECOTE_SQL), {"vefa": VEFA}).first()
    if not r or r[1] is None or r[1] < 10:      # n < 10 → pas d'affirmation (pas de chiffre fragile)
        return None, None
    return int(r[0]), int(r[1])


def _decote_libelle(pct: int | None, n: int | None) -> str | None:
    if pct is None:
        return None
    return (f"Les biens défiscalisés se revendent en médiane à ~{pct} % de leur prix d'achat neuf "
            f"(reventes DVF Réunion, n={n} · backtest A-1) · Estimé — argument de négociation, "
            f"pas une estimation du bien affiché.")


def _row(idu: str, y: int, proxy: str, ach_year: int | None, ref_year: int,
         decote_pct: int | None = None, decote_n: int | None = None) -> dict:
    deb, fin = y + 6, y + 11
    active = (deb <= ref_year + 2) and (fin >= ref_year)          # bande ∩ [ref_year, ref_year+2]
    if proxy == "vefa":
        src = f"DVF VEFA {y}"
    else:
        src = f"DVF vente {y}" + (f" + achèvement PC {ach_year}" if ach_year else " + achèvement PC")
    # wording factuel, sourcé, SANS date de vente promise (roadmap « Rejeté ») et SANS nommer le
    # dispositif (on ne l'affirme jamais — VEFA/permis ne disent pas Pinel vs Girardin).
    badge = f"achat neuf {y} — DVF · fenêtre de sortie d'engagement {deb}-{fin} · Estimé"
    court = f"Sortie de défisc. probable · {deb}-{fin} · Estimé"
    detail = (
        f"Bien acheté neuf en {y} (source DVF). À l'expiration de l'engagement d'un dispositif de "
        f"défiscalisation (6 à 9 ans), la propension de revente augmente — mesuré ×2,4 vs hors fenêtre "
        f"(walk-forward as-of 2021-2025, sourcé). Fenêtre estimée {deb}-{fin}. "
        f"Signal de timing, PAS une prédiction : ni une date de vente, ni une personne."
    )
    return {"idu": idu, "proxy": proxy, "y": y, "deb": deb, "fin": fin,
            "active": active, "src": src, "badge": badge, "court": court, "detail": detail,
            "decote_pct": decote_pct, "decote_n": decote_n,
            "decote_libelle": _decote_libelle(decote_pct, decote_n)}


def build_defisc_fenetres(session: Session, *, ref_year: int = DEFAULT_REF_YEAR,
                          commit: bool = True, log=lambda *_: None) -> dict:
    """Construit/rafraîchit `defisc_fenetres` (rebuild complet idempotent). Lecture seule des sources.
    `commit=False` pour les tests transactionnels (fixture rollback-ée). Renvoie {'total', 'active'}."""
    session.execute(text("DROP TABLE IF EXISTS defisc_fenetres"))  # rebuild complet (table dérivée : schéma évolutif)
    session.execute(text(DDL))
    decote_pct, decote_n = _compute_decote(session)              # N2 — recalculé une fois pour tout le run
    raw = session.execute(text(_SELECT_RAW), {"vefa": VEFA}).mappings().all()
    rows = [_row(r["idu"], int(r["y"]), r["proxy"], r["ach_year"], ref_year, decote_pct, decote_n) for r in raw]
    for r in rows:
        session.execute(text(_INSERT), r)
    if commit:
        session.commit()
    n_active = sum(1 for r in rows if r["active"])
    log(f"defisc_fenetres : {len(rows)} parcelles mono neuf, {n_active} fenêtre active (ref {ref_year}-{ref_year+2})")
    return {"total": len(rows), "active": n_active}
