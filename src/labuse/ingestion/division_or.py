"""O12 — DIVISION EN OR : parcelles où le bâti occupe un coin et laisse un résiduel DÉTACHABLE constructible.

FAUX POSITIF = PÉCHÉ MORTEL. Cet outil est livré **MASQUÉ** ; le livrable qui autorise l'exposition est un
**dossier de revue 20 cartes** validé VISUELLEMENT par Vic (pattern J3). Ici : le détecteur géométrique
conservateur + la table masquée `division_or_candidates`.

Géométrie (EPSG:2975, mètres) — seuils CONSERVATEURS :
  · parcelle ≥ 1000 m² (place pour DEUX lots viables) ;
  · bâti entre 8 % et 45 % de la parcelle (il y a un bâti, mais il ne remplit pas) ;
  · résiduel = plus grand polygone de (parcelle − bâti bufferisé 3 m) ;
  · résiduel entre 500 m² et (surface − 400) m² → le lot BÂTI conserve ≥ 400 m² (les deux lots restent viables) ;
  · **cercle inscrit du résiduel ≥ 9 m de rayon** (largeur ~18 m constructible, pas une lanière) ;
  · **façade voirie du résiduel ≥ 12 m** (accès INDÉPENDANT — le vrai discriminant) ;
  · **lot ≤ 50 % de la parcelle** (revue O12-ÎLE : un « lot » qui emporte presque toute la parcelle
    est un démembrement, pas une division — ex. 4 748 m² détachés de 5 433 m²) ;
  · **zonage du lot : U ou AU exigé** (revue O12-ÎLE : une division urbaine n'a pas de sens en zone
    A ou N). Zone dominante (plus grande intersection) du LOT dans `plu_gpu_zone` ; commune sans
    document (RNU) → lot gardé seulement si la parcelle est dans la PAU estimée (`parcel_pau`).
Revue O12-ÎLE, correctifs 2-3-4 :
  · **bâti d'activité exclu** — critère `ensemble_bati` de la cascade (bati.py) : ≥ 3 bâtiments
    (intersection ≥ 10 m², comme stats_batch) OU un bâtiment ≥ 400 m² → hangars, ensembles
    commerciaux, équipements ; le signal vise la division RÉSIDENTIELLE ;
  · **compacité du lot** ≥ COMPACITE_MIN (Polsby-Popper) — le cercle inscrit mesure le point le
    plus large, pas la forme d'ensemble : les lanières passaient ;
  · **littoral / domaine public** — lot exclu s'il touche : bande des 50 pas géométriques,
    forêt domaniale, cœur du Parc national, ou le TRAIT DE CÔTE (contact ≤ 1 m — le corridor
    50 pas a des trous de couverture, constaté au Barachois ; couches de la cascade).
  · **viabilité du LOT RESTANT** — l'emprise bâtie résultante côté propriétaire (bâti conservé /
    surface restante) est plafonnée : emprise max CALIBRÉE de la zone (PLU yaml) si elle existe,
    sinon EMPRISE_RESTANTE_MAX (plancher prudent) — la division ne doit pas rendre la parcelle
    du propriétaire non conforme (revue : 80-81 % d'emprise résultante sur 2 cartes).
Deux TYPES de division (O12-ÎLE D — le bâti dans le lot est CLASSÉ, pas exclu) :
  · **libre** : lot nu (tout le bâti retiré du calcul du résiduel) — prioritaire au tri ;
  · **demolition** : seul le bâtiment PRINCIPAL (plus grande emprise au sol) est retiré — le lot
    peut contenir du bâti SECONDAIRE, chiffré (« dont N m² à démolir »). Garde anti-découpage
    inversé : le principal n'est JAMAIS dans le lot (par construction) ET le bâti à démolir pèse
    au plus la moitié du bâti conservé (`bati_lot × 3 ≤ bati_total`) — sinon rejet.
    Une parcelle qui passe en libre reste libre (la variante démolition ne la remplace pas).
L'accès restant du lot BÂTI est jugé VISUELLEMENT en revue : la métrique automatique tentée
(façade_parcelle − façade_lot) s'est révélée invalide (valeurs négatives, artefact de la frontière
découpée) — on ne filtre pas sur un chiffre faux (finding O12).
Score de clarté : la façade voirie y est PLAFONNÉE à 30 m (revue O12-ÎLE : une façade de 465 m
est une bande linéaire le long d'une route, pas un candidat plus clair).

Rien n'est affirmé sur la constructibilité réglementaire (recul, prospect, servitudes) : le détecteur repère un
POTENTIEL géométrique, la revue humaine tranche. Gain estimé branché sur le Score É V2 (Estimé). Zéro donnée nouvelle.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..bati import ENSEMBLE_MIN_BATIMENTS, GRAND_BATIMENT_M2

def _seuils_cfg() -> dict:
    """M129-C — les ~20 seuils SORTENT DU DUR (config/seuils_geometrie.yaml section
    `division_or`, valeurs héritées ; repli historique si config absente). Les seuils issus
    des REVUES de Vic sont marqués dans le yaml — ajustables par commune plus tard."""
    try:
        from .. import config as _cfg
        return _cfg.seuils_geometrie().get("division_or", {})
    except Exception:  # noqa: BLE001
        return {}


_S = _seuils_cfg()

def _cosia_guard_sql(session) -> str:
    """M129-C P1.1 — garde CoSIA conditionnelle : table absente (base de test) → 'false'."""
    if not session.execute(text("SELECT to_regclass('parcel_bati_revele') IS NOT NULL")).scalar():
        return "false"
    return ("EXISTS (SELECT 1 FROM parcel_bati_revele rbz WHERE rbz.idu = zon.idu "
            f"AND rbz.emprise_cosia_m2 >= {int(_S.get('cosia_min_m2', 50))})")


def _pente_guard_sql(session) -> str:
    """M129-C P1.2 — garde PENTE conditionnelle (seuil config, degrés)."""
    if not session.execute(text("SELECT to_regclass('parcel_terrain') IS NOT NULL")).scalar():
        return "false"
    return ("EXISTS (SELECT 1 FROM parcel_terrain ptz WHERE ptz.idu = zon.idu "
            f"AND ptz.pente_moy_deg > {float(_S.get('pente_max_deg', 20))})")


EXPOSE = True    # VALIDÉ par Vic (28/07/2026) après 2 revues visuelles exhaustives + verdict
                 # de calibrage PLU (pool 35, 0 faux positif connu). Le câblage client (encadré →
                 # chiffres) est fait par M22-D (section divisibilité du Rapport de potentiel).
                 # DÉPENDANCE RÉCURRENTE : relancer scripts/o12_emprise_recheck.py après chaque
                 # évolution des PLU (le vrai plafond d'emprise peut faire tomber un candidat) —
                 # même principe que le garde-fou de fraîcheur bâti (PC Sitadel).

# Compacité minimale du lot (Polsby-Popper, 4π·aire/périmètre² — cercle=1, carré≈0.79,
# rectangle 1:10 ≈ 0.25). Revue O12-ÎLE (cartes 6/16/18 : lanières — le cercle inscrit mesure
# le point le plus LARGE, pas la forme d'ensemble). Seuil fixé sur la distribution île entière
# (P25=0.11, médiane=0.21 avant correctif) : 0.25 écarte les lots plus étirés qu'un 1:10.
COMPACITE_MIN = float(_S.get('compacite_min', 0.25))

# Emprise bâtie maximale du LOT RESTANT après division (revue O12-ÎLE, 4e itération : la
# division ne doit pas rendre la parcelle du PROPRIÉTAIRE non conforme — cartes 1 et 11 :
# 80-81 % d'emprise résultante, au-delà de toute règle de zone U, sans pleine terre).
# L'emprise max CALIBRÉE de la zone (config/plu_<commune>.yaml, emprise_sol_pct) prime
# quand elle existe ; sinon ce plancher prudent s'applique.
EMPRISE_RESTANTE_MAX = float(_S.get('emprise_restante_max', 0.60))

# ── O12-PARTIEL : le LOT DÉCOUPÉ (méthode « bande de façade ») ─────────────────────────────
# Sur les parcelles écartées par le ratio > 50 % (résiduel entier = démembrement), on cherche
# un SOUS-POLYGONE : bande ancrée sur le plus long segment CONTIGU de façade voirie du
# résiduel (ancre ≤ 25 m, 3 positions), poussée en profondeur (20-40 m, buffer à bouts
# droits) jusqu'à 600-900 m². Le lot ⊂ résiduel ⇒ AUCUN bâti dedans et recul 3 m du bâti
# conservé, par construction. Aucun critère validé n'est assoupli : compacité ≥ 0.28 (le
# plancher OBSERVÉ du pool validé, plus dur que COMPACITE_MIN), cercle inscrit ≥ 9 m, façade
# contiguë du lot ≥ 12 m, zone U/AU (PAU si RNU), gardes littoral, emprise restante plafonnée.
# ANTI-ENCLAVEMENT (GO Vic) : le lot RESTANT garde lui aussi ≥ 12 m de façade voirie contiguë,
# mesurée directement sur sa géométrie (parcelle − découpe) contre TOUTES les voiries — une
# parcelle traversante dont le reste donne sur la deuxième rue passe ; sinon rejet.
LOT_DECOUPE_MIN_M2 = int(_S.get('lot_decoupe_min_m2', 600))
LOT_DECOUPE_MAX_M2 = int(_S.get('lot_decoupe_max_m2', 900))
COMPACITE_MIN_DECOUPE = float(_S.get('compacite_min_decoupe', 0.55))   # revue 2, branche 2 (0.28 d'origine ne filtrait pas les lots en U)
ANCRE_LARGEUR_M = int(_S.get('ancre_largeur_m', 25))           # largeur de la bande côté rue (≥ 12 m de façade garantis)

# O12-PARTIEL-2 (arbitrages Vic 27/07/2026) :
# · ÉROSION du reste : un reste relié par un COULOIR est un reste en deux morceaux dans la
#   vraie vie. Le reste rétréci de EROSION_RESTE_M doit rester d'un seul tenant — 2 m d'érosion
#   ⇔ un couloir < 4 m (largeur minimale d'un accès utilisable) ne « connecte » plus.
#   Composantes comptées au-dessus de 25 m² (anti-bruit d'érosion).
# · Distance lot ↔ bâti ≥ 1 m contre TOUS les bâtiments (voisins compris) : garde-fou de
#   COHÉRENCE GÉOMÉTRIQUE (un lot à 0,4 m d'un mur signale une erreur de donnée), PAS une
#   règle d'urbanisme — le seuil 3 m est refusé : le dossier ne prononce AUCUNE
#   constructibilité réglementaire (recul, prospect, servitudes), on ne la simule pas.
# · Façade sur voirie QUALIFIÉE partout (plus seulement RNU) : une façade sur sentier, chemin
#   ou route empierrée n'est pas un accès (BD TOPO, cf. VOIRIE_QUALIFIEE).
EROSION_RESTE_M = int(_S.get('erosion_reste_m', 2))
DIST_BATI_MIN_M = int(_S.get('dist_bati_min_m', 1))
VOIRIE_QUALIFIEE = ("Route à 1 chaussée", "Route à 2 chaussées", "Rond-point")

# Revue 2 (arbitrage « règle de décision », branche 2 déclenchée — cf. O12_PARTIEL_RAPPORT.md) :
# · SOLIDITÉ du lot = aire / aire de l'enveloppe convexe (une bande franche ≈ 1, un lot en U
#   autour d'un bâtiment chute). Seuil 0.85 = le plus haut des seuils proposés qui préserve
#   TOUTES les cartes validées en revue (la plus basse : 0.898). Constat honnête : les U
#   « modérés » (0.86-0.91) ne sont séparables par AUCUN seuil sans perdre une validée —
#   classe résiduelle consignée comme limite ; les cas VUS en revue passent par la liste
#   d'exclusions de revue (config/o12_exclusions_revue.yaml).
# · COMPACITE_MIN_DECOUPE relevé 0.28 → 0.55 (branche 2 : « plancher 0.55 pour les extrêmes
#   indéfendables ») — redondant avec la solidité sur le pool mesuré, gardé en ceinture.
# · RESTE ≥ 400 m² : aligné sur la famille résiduelle (« le lot bâti garde ≥ 400 m² ») —
#   laisser 378 m² sous la maison du vendeur est un rognage, pas une division.
# · FRAÎCHEUR BÂTI : parcelle porteuse d'un PC Sitadel trop récent pour que BD TOPO (ingérée
#   28-29/06/2026) ait pu capter le chantier → exclue. Fenêtre : PC ≥ 2023-01-01 — la mise à
#   jour photogrammétrique IGN repose sur une ortho millésimée (cycle DOM ~3 ans, dernier
#   millésime exploitable ~2023) + 12-18 mois de chantier après PC : tout PC depuis début
#   2023 peut être bâti mais invisible de la couche. « Lot nu » = nu au vu de BD TOPO
#   (millésime), recoupé Sitadel — rien de plus n'est affirmé.
SOLIDITE_MIN_DECOUPE = float(_S.get('solidite_min_decoupe', 0.85))
PC_FRAIS_DEPUIS = str(_S.get("pc_frais_depuis", "2023-01-01"))

# Filtre par LIBELLÉ DESCRIPTIF de zone (finding BP0363 : « Ua — zone d'activités du
# Chaudron » passait le filtre par code). Mots-clés d'activité dans l'intitulé GPU, avec
# PROTECTION des descriptions mixtes habitat/centre-ville (« commerces … de proximité »,
# « l'habitat mais également les commerces ») — regex PostgreSQL, appliqué aux DEUX familles.
ACTIVITE_DESCR_RE = (r"zone d.activit|activit[ée]s? [ée]conomiq|activit[ée]s? commercial"
                     r"|vocation [ée]conomique|industriel|artisanal|logistiq|technopole"
                     r"|\mZAC\M|zone d.am[ée]nagement")
ACTIVITE_DESCR_PROTEGE_RE = r"habitat|r[ée]sidentiel|proximit[ée]"

DDL = """
CREATE TABLE IF NOT EXISTS division_or_candidates (
  idu           varchar(14) PRIMARY KEY,
  commune       varchar(64),
  surface_m2    int,
  bati_m2       int,
  bati_ratio    numeric(4,3),
  residuel_m2   int,
  residuel_rayon_m numeric(5,1),
  residuel_facade_m numeric(5,1),
  bati_facade_m numeric(5,1),
  zone          varchar(8),      -- zone dominante du lot (U/AU/AUc/AUs) ; NULL = commune RNU (PAU estimée)
  zone_lib      varchar(16),     -- libellé de la (sous-)zone (ex. Ud3) — clé du PLU calibré
  type_division varchar(12),     -- 'libre' (lot nu) | 'demolition' (bâti secondaire dans le lot)
  bati_lot_m2   int,             -- bâti contenu dans le lot (« dont N m² à démolir » ; 0 si libre)
  compacite     numeric(4,3),    -- Polsby-Popper du lot (4π·aire/périmètre² — 1=cercle)
  solidite      numeric(4,3),    -- aire / enveloppe convexe (bande franche ≈ 1, lot en U chute)
  emprise_restante numeric(4,3), -- emprise bâtie du lot RESTANT après division (viabilité côté propriétaire)
  gain_estime_eur int,           -- via Score É V2 si dispo (Estimé), sinon NULL
  clarte        numeric(5,1),    -- score de clarté géométrique (tri du dossier de revue)
  computed_at   timestamptz DEFAULT now()
);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS zone varchar(8);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS type_division varchar(12);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS bati_lot_m2 int;
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS compacite numeric(4,3);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS zone_lib varchar(16);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS emprise_restante numeric(4,3);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS lot_geom geometry(Polygon, 2975);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS aire_bati_dans_lot_m2 numeric(6,1);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS solidite numeric(4,3);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS note_revue varchar(120);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS run_label text;  -- M50 : run servi (étage 0 lu)

-- SNAPSHOT des tracés REVUS (revue 2) : photographie des lots découpés AVANT un re-run, pour
-- que le re-run distingue « tracé inchangé » (déjà revu / exclusion liée-géométrie tenue) de
-- « tracé modifié » (à re-revoir). Repeuplée par snapshot_review_lots() avant chaque re-run.
CREATE TABLE IF NOT EXISTS division_or_revue_snapshot (
  idu         varchar(14) PRIMARY KEY,
  lot_geom    geometry(Polygon, 2975),
  snapshot_at timestamptz DEFAULT now()
);
"""

# Détection pour UNE commune (batch raisonnable). Buffers/seuils = constantes ci-dessus.
_DETECT = """
WITH cand AS (
  SELECT p.id, p.idu, p.commune, p.geom_2975, p.surface_m2 FROM parcels p
  -- M50-SUITE : accepte le NOM (parcels.commune) OU le code INSEE (préfixe idu) — la CLI passait
  -- « 97415 » là où parcels.commune = « Saint-Paul » → 0 candidat (bug rebuild-à-0).
  WHERE p.commune = :commune AND p.surface_m2 BETWEEN {surface_min} AND {surface_max}
    AND EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975))),
bldg AS (
  SELECT c.id, b.geom_2975 AS g, ST_Area(ST_Intersection(b.geom_2975, c.geom_2975)) AS a
  FROM cand c JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975, c.geom_2975)),
-- nb_bat compte comme la cascade (bati.stats_batch) : intersection ≥ 10 m² (les voisins en
-- limite et les abris minuscules ne comptent pas) ; max_bat_m2 = plus grande emprise intersectée
bat AS (SELECT id, ST_Union(g) AS bgeom, sum(a) AS bat_m2,
               count(*) FILTER (WHERE a >= 10) AS nb_bat, max(a) AS max_bat_m2 FROM bldg GROUP BY id),
-- bâtiment PRINCIPAL = plus grande emprise au sol sur la parcelle — JAMAIS dans le lot proposé
princ AS (SELECT DISTINCT ON (id) id, g AS pgeom FROM bldg ORDER BY id, a DESC),
-- deux variantes de lot : LIBRE (tout le bâti retiré — le lot est nu) ; DÉMOLITION (seul le
-- principal est retiré — le lot peut contenir du bâti SECONDAIRE, chiffré « à démolir »).
-- Parcelle mono-bâtiment : les variantes coïncident, la variante démolition est sautée.
freed AS (
  SELECT c.id, c.idu, c.commune, c.surface_m2, c.geom_2975, bat.bat_m2, v.variante,
         lg.geom AS free_geom, ST_Area(lg.geom) AS free_m2,
         (ST_MaximumInscribedCircle(lg.geom)).radius AS rad
  FROM cand c JOIN bat ON bat.id = c.id JOIN princ ON princ.id = c.id
  CROSS JOIN LATERAL (VALUES ('libre', bat.bgeom), ('demolition', princ.pgeom)) AS v(variante, sub)
  CROSS JOIN LATERAL (SELECT g.geom FROM ST_Dump(ST_Difference(c.geom_2975, ST_Buffer(v.sub, {buffer_bati}))) g
                      ORDER BY ST_Area(g.geom) DESC LIMIT 1) lg
  WHERE bat.bat_m2 / c.surface_m2 BETWEEN {ratio_min} AND {ratio_max}
    AND NOT (v.variante = 'demolition' AND bat.nb_bat = 1)
    -- revue O12-ÎLE (2) : bâti d'ACTIVITÉ exclu — critère ensemble_bati de la cascade (bati.py)
    AND bat.nb_bat < {ens_min_bat} AND bat.max_bat_m2 < {grand_bat_m2}),
-- façade voirie du LOT détaché — le filtre d'accès (indépendant ≥ 12 m)
-- + borne lot/parcelle ≤ 50 % (au-delà c'est un démembrement, pas une division — revue O12-ÎLE)
acces AS (
  SELECT *,
    round((4 * pi() * free_m2 / power(ST_Perimeter(free_geom), 2))::numeric, 3) AS compacite,
    (SELECT coalesce(sum(ST_Length(ST_Intersection(ST_Buffer(v.geom_2975,1.5), ST_Boundary(free_geom)))),0)
       FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, free_geom, 2)) AS facade_free
  FROM freed
  WHERE free_m2 >= {lot_min} AND free_m2 <= surface_m2 - {reste_min} AND free_m2 <= surface_m2 * {lot_part_max} AND rad >= {rayon_min}
    -- revue O12-ÎLE (3) : COMPACITÉ du lot — le cercle inscrit mesure le point le plus large,
    -- pas la forme d'ensemble (lanières) ; Polsby-Popper 4π·aire/périmètre² ≥ seuil
    AND 4 * pi() * free_m2 / power(ST_Perimeter(free_geom), 2) >= {compacite_min}),
-- bâti contenu dans le lot proposé (0 par construction en variante libre) → « dont N m² à démolir »
demol AS (
  SELECT a.*, CASE WHEN a.variante = 'libre' THEN 0 ELSE coalesce(
      (SELECT round(sum(ST_Area(ST_Intersection(b.g, a.free_geom))))::int
       FROM bldg b WHERE b.id = a.id), 0) END AS bati_lot_m2
  FROM acces a),
-- zone dominante du LOT (plus grande intersection avec plu_gpu_zone) — U/AU gardés, A/N exclus ;
-- NULL (commune RNU sans document) → gardé seulement si la parcelle est dans la PAU estimée
zon AS (
  SELECT d.*, z.subtype AS zone, z.zone_lib, z.zone_descr
  FROM demol d
  LEFT JOIN LATERAL (
    -- libellé via attrs->>'libelle' (code seul, ex. Ud3) — z2.name mélange parfois
    -- « code : description » selon la commune d'ingestion ; name gardé comme DESCRIPTIF
    -- (filtre par mots-clés d'activité — finding BP0363, un code générique peut cacher une ZA)
    SELECT z2.subtype, z2.attrs->>'libelle' AS zone_lib, z2.name AS zone_descr FROM spatial_layers z2
    WHERE z2.kind='plu_gpu_zone' AND ST_Intersects(z2.geom_2975, d.free_geom)
    ORDER BY ST_Area(ST_Intersection(z2.geom_2975, d.free_geom)) DESC LIMIT 1) z ON true)
SELECT DISTINCT ON (idu)
       idu, commune, round(surface_m2)::int surface_m2, round(bat_m2)::int bati_m2,
       round((bat_m2/surface_m2)::numeric,3) bati_ratio, round(free_m2)::int residuel_m2,
       round(rad::numeric,1) residuel_rayon_m, round(facade_free::numeric,1) residuel_facade_m,
       NULL::numeric AS bati_facade_m,  -- accès du lot BÂTI : jugé VISUELLEMENT en revue (métrique
                                        -- façade_parcelle − façade_lot invalidée : négative, artefact
                                        -- de la frontière découpée — finding O12, pas de chiffre faux)
       zone, zone_lib,
       CASE WHEN bati_lot_m2 < 1 THEN 'libre' ELSE 'demolition' END AS type_division,
       bati_lot_m2, compacite,
       round(((bat_m2 - bati_lot_m2) / NULLIF(surface_m2 - free_m2, 0))::numeric, 3) AS emprise_restante
FROM zon
WHERE facade_free >= {facade_min}
  -- M129-C P1.1 — CoSIA branché : un bâti RÉVÉLÉ (que BD TOPO ne voit pas) invalide le lot
  -- calculé sur la couche aveugle. Le filet PC Sitadel reste (bâti récent AVEC permis).
  AND NOT ({cosia_guard})
  -- M129-C P1.2 — PENTE branchée (MNT jamais lu avant, audit) : seuil config (degrés)
  -- (P95 du gabarit 1000-6000 m² = 19,4° ; max des 7 validées = 17,9° — non calibré par revue).
  AND NOT ({pente_guard})
  AND (zone = 'U' OR zone LIKE 'AU%' OR (zone IS NULL AND ({pau_pred})))
  -- O12-GARDE (Vic 30/07) : garde de CONSTRUCTIBILITÉ EN AMONT. Un candidat dont la parcelle
  -- SUPPORT est écartée DÉFINITIVEMENT à l'étage 0 du RUN SERVI (`:served` = Q_A_RUN_LABEL → la
  -- garde SUIT automatiquement toute bascule future), OU marquée non constructible
  -- (`parcel_constructibilite` declasse_*), n'est PAS candidat.
  -- Restreint à `status = 'exclue'` (fait DÉFINITIF : PPR rouge, foncier public…), PAS
  -- `faux_positif_probable` (arbitrage Vic 30/07 : c'est une probabilité, pas un fait — écarter
  -- dessus serait écarter au soupçon ; et le bâti-avec-résiduel-détachable EST la prémisse d'O12,
  -- cohérent avec l'arbitrage produit du 29/07 : le bâti n'est pas disqualifiant par principe).
  AND NOT EXISTS (SELECT 1 FROM dryrun_parcel_evaluations de
                  WHERE de.parcel_id = zon.id AND de.run_label = :served
                    AND de.status = 'exclue')
  AND ({constr_guard})
  AND (variante = 'libre' OR bati_lot_m2 * 3 <= bat_m2)
  -- O12-PARTIEL-2 §4 : zonages d'activité exclus AUSSI du pool résiduel — par CODE (config)
  -- et par LIBELLÉ descriptif (un code générique peut cacher une zone d'activités : BP0363)
  AND ({activite_pred})
  AND (zone_descr IS NULL OR NOT (zone_descr ~* '{descr_re}') OR zone_descr ~* '{descr_protege}')
  -- EXCLUSIONS DE REVUE (traçables — config/o12_exclusions_revue.yaml) : la revue tranche
  AND ({revue_pred})
  -- revue O12-ÎLE (5) : VIABILITÉ DU LOT RESTANT — l'emprise bâtie résultante côté propriétaire
  -- (bâti conservé / surface restante) ne doit pas dépasser l'emprise max de la zone (PLU
  -- calibré s'il existe, sinon plancher prudent) : la division ne rend pas la parcelle non conforme
  AND (bat_m2 - bati_lot_m2) / NULLIF(surface_m2 - free_m2, 0) <= ({emprise_max})
  -- revue O12-ÎLE (4) : LITTORAL et domaine public non acquérable (couches de la cascade).
  -- Le corridor 50 pas ne couvre pas tout le front de mer (trou constaté au Barachois,
  -- Saint-Denis) → le CONTACT du trait de côte complète la maille.
  AND NOT EXISTS (SELECT 1 FROM spatial_layers l5 WHERE l5.kind='cinquante_pas'
                    AND ST_Intersects(l5.geom_2975, zon.free_geom))
  AND NOT EXISTS (SELECT 1 FROM spatial_layers lf WHERE lf.kind='foret_publique'
                    AND lf.subtype='domaniale' AND ST_Intersects(lf.geom_2975, zon.free_geom))
  AND NOT EXISTS (SELECT 1 FROM spatial_layers lp WHERE lp.kind='parc_national'
                    AND lp.subtype='coeur' AND ST_Intersects(lp.geom_2975, zon.free_geom))
  AND NOT EXISTS (SELECT 1 FROM spatial_layers lt WHERE lt.kind='trait_de_cote'
                    AND ST_DWithin(lt.geom_2975, zon.free_geom, 1))
ORDER BY idu, (variante = 'demolition'), free_m2 DESC;
"""


# INSERT ... SELECT : détection + gain (Score É) + clarté en UNE passe SQL (pas de boucle Python par ligne).
_INSERT = """
INSERT INTO division_or_candidates (idu, commune, surface_m2, bati_m2, bati_ratio,
    residuel_m2, residuel_rayon_m, residuel_facade_m, bati_facade_m, zone, zone_lib,
    type_division, bati_lot_m2, compacite, emprise_restante, gain_estime_eur, clarte, run_label)
SELECT d.idu, d.commune, d.surface_m2, d.bati_m2, d.bati_ratio, d.residuel_m2,
       d.residuel_rayon_m, d.residuel_facade_m, d.bati_facade_m, d.zone, d.zone_lib,
       d.type_division, d.bati_lot_m2, d.compacite, d.emprise_restante,
       se.marge_estimee,
       round((d.residuel_rayon_m * 2 + LEAST(d.residuel_facade_m, 30))::numeric, 1) AS clarte,
       :served AS run_label   -- M50 : stamp du run servi (étage 0 lu)
FROM ({detect}) d
LEFT JOIN score_e se ON se.idu = d.idu AND se.estimable
ON CONFLICT (idu) DO UPDATE SET commune=EXCLUDED.commune, surface_m2=EXCLUDED.surface_m2,
    run_label=EXCLUDED.run_label,
    bati_m2=EXCLUDED.bati_m2, bati_ratio=EXCLUDED.bati_ratio, residuel_m2=EXCLUDED.residuel_m2,
    residuel_rayon_m=EXCLUDED.residuel_rayon_m, residuel_facade_m=EXCLUDED.residuel_facade_m,
    bati_facade_m=EXCLUDED.bati_facade_m, zone=EXCLUDED.zone,
    type_division=EXCLUDED.type_division, bati_lot_m2=EXCLUDED.bati_lot_m2,
    compacite=EXCLUDED.compacite, zone_lib=EXCLUDED.zone_lib,
    emprise_restante=EXCLUDED.emprise_restante,
    gain_estime_eur=EXCLUDED.gain_estime_eur, clarte=EXCLUDED.clarte, computed_at=now()
"""


# O12-PARTIEL — détection du LOT DÉCOUPÉ pour UNE commune (méthode « bande de façade »).
# Univers : parcelles du périmètre actuel écartées par le SEUL ratio > 50 % (résiduel entier
# = démembrement) — filtres parcelle (surface, bâti 8-45 %, activité) inchangés. Le lot est
# découpé DANS le résiduel : aucun bâti dedans ni à moins de 3 m, par construction.
_DETECT_PARTIEL = """
WITH cand AS (
  SELECT p.id, p.idu, p.commune, p.geom_2975, p.surface_m2 FROM parcels p
  -- M50-SUITE : NOM (parcels.commune) OU code INSEE (préfixe idu) — cf. _DETECT.
  WHERE p.commune = :commune AND p.surface_m2 BETWEEN {surface_min} AND {surface_max}
    AND EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975))),
bldg AS (
  SELECT c.id, b.geom_2975 AS g, ST_Area(ST_Intersection(b.geom_2975, c.geom_2975)) AS a
  FROM cand c JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975, c.geom_2975)),
bat AS (SELECT id, ST_Union(g) AS bgeom, sum(a) AS bat_m2,
               count(*) FILTER (WHERE a >= 10) AS nb_bat, max(a) AS max_bat_m2 FROM bldg GROUP BY id),
freed AS (
  SELECT c.id, c.idu, c.commune, c.geom_2975, c.surface_m2, bat.bat_m2,
         lg.geom AS free_geom, ST_Area(lg.geom) AS free_m2
  FROM cand c JOIN bat ON bat.id = c.id
  CROSS JOIN LATERAL (SELECT g.geom FROM ST_Dump(ST_Difference(c.geom_2975, ST_Buffer(bat.bgeom, 3))) g
                      ORDER BY ST_Area(g.geom) DESC LIMIT 1) lg
  WHERE bat.bat_m2 / c.surface_m2 BETWEEN {ratio_min} AND {ratio_max}
    AND bat.nb_bat < {ens_min_bat} AND bat.max_bat_m2 < {grand_bat_m2}
    AND ST_Area(lg.geom) > c.surface_m2 * 0.5),
-- plus long segment CONTIGU de façade voirie du résiduel (ST_LineMerge) — l'ancre de la bande
fac AS (
  SELECT f.*, seg.geom AS fseg, ST_Length(seg.geom) AS flen
  FROM freed f
  CROSS JOIN LATERAL (
    SELECT g.geom FROM ST_Dump((
      SELECT ST_LineMerge(ST_Union(ST_Intersection(ST_Buffer(v.geom_2975, 1.5), ST_Boundary(f.free_geom))))
      FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, f.free_geom, 2))) g
    ORDER BY ST_Length(g.geom) DESC LIMIT 1) seg
  WHERE ST_Length(seg.geom) >= 12),
-- bande : ancre ≤ {ancre_w} m (3 positions) × profondeur 20-40 m (buffer à bouts droits),
-- clippée au résiduel — on retient la découpe de MEILLEURE compacité satisfaisant les seuils
carve AS (
  SELECT f.id, f.idu, f.commune, f.geom_2975, f.surface_m2, f.bat_m2, f.free_m2,
         best.lot_geom, best.lot_m2, best.compacite_lot, best.solidite_lot, best.rad
  FROM fac f
  CROSS JOIN LATERAL (
    SELECT lot.geom AS lot_geom, ST_Area(lot.geom) AS lot_m2,
           4*pi()*ST_Area(lot.geom)/power(ST_Perimeter(lot.geom),2) AS compacite_lot,
           ST_Area(lot.geom) / ST_Area(ST_ConvexHull(lot.geom)) AS solidite_lot,
           (ST_MaximumInscribedCircle(lot.geom)).radius AS rad
    FROM (VALUES (0.0),(0.5),(1.0)) pos(frac)
    CROSS JOIN generate_series(20, 40, 5) prof(d)
    CROSS JOIN LATERAL (
      SELECT CASE WHEN f.flen <= {ancre_w} THEN f.fseg
             ELSE ST_LineSubstring(f.fseg, pos.frac * (1 - {ancre_w} / f.flen),
                                   pos.frac * (1 - {ancre_w} / f.flen) + {ancre_w} / f.flen) END AS geom) an
    CROSS JOIN LATERAL (
      SELECT g.geom FROM ST_Dump(ST_Intersection(f.free_geom, ST_Buffer(an.geom, prof.d, 'endcap=flat'))) g
      ORDER BY ST_Area(g.geom) DESC LIMIT 1) lot
    WHERE ST_Area(lot.geom) BETWEEN {lot_min} AND {lot_max}
      -- reste ≥ 400 m² : aligné sur la famille résiduelle (le lot bâti garde ≥ 400 m²)
      AND ST_Area(lot.geom) <= f.surface_m2 - 400
      AND 4*pi()*ST_Area(lot.geom)/power(ST_Perimeter(lot.geom),2) >= {compacite_min_dec}
      -- SOLIDITÉ (revue 2) : bande franche exigée, pas de lot en U autour d'un bâtiment
      AND ST_Area(lot.geom) / ST_Area(ST_ConvexHull(lot.geom)) >= {solidite_min}
      AND (ST_MaximumInscribedCircle(lot.geom)).radius >= 9
    ORDER BY compacite_lot DESC LIMIT 1) best),
-- façade voirie CONTIGUË du LOT découpé (revérifiée sur le lot, pas héritée de l'ancre)
-- + façade RESTANTE du lot conservé : la bande ne doit pas ENCLAVER la maison — le lot
-- restant garde ≥ 12 m de façade contiguë, MESURÉE DIRECTEMENT sur sa géométrie (parcelle −
-- découpe ; jamais par soustraction de longueurs, l'artefact du finding O12). Une parcelle
-- traversante dont le reste donne sur la DEUXIÈME rue passe naturellement (toutes voiries).
-- O12-PARTIEL-2 : + CONNEXITÉ du reste (C2 — composantes > 1 m², tolérance anti-slivers
-- cadastraux), + bâti ∩ lot mesuré contre TOUS les bâtiments, voisins compris (C3),
-- + façade sur voirie QUALIFIÉE — ouverte à la circulation publique : Route à 1/2 chaussées,
-- rond-point BD TOPO ; chemins, sentiers, routes empierrées, escaliers exclus (C5, RNU).
mesure AS (
  SELECT c.*,
    (SELECT coalesce(max(ST_Length(g.geom)), 0) FROM ST_Dump((
       SELECT ST_LineMerge(ST_Union(ST_Intersection(ST_Buffer(v.geom_2975, 1.5), ST_Boundary(c.lot_geom))))
       FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, c.lot_geom, 2))) g) AS facade_lot,
    (SELECT coalesce(max(ST_Length(g.geom)), 0) FROM ST_Dump((
       SELECT ST_LineMerge(ST_Union(ST_Intersection(ST_Buffer(v.geom_2975, 1.5), ST_Boundary(rg.geom))))
       FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, rg.geom, 2))) g) AS facade_reste,
    (SELECT count(*) FROM ST_Dump(ST_Difference(c.geom_2975, c.lot_geom)) g
       WHERE ST_Area(g.geom) > 1) AS nb_reste,
    (SELECT count(*) FROM ST_Dump(ST_Buffer(ST_Difference(c.geom_2975, c.lot_geom), -{erosion_m})) g
       WHERE ST_Area(g.geom) > 25) AS nb_reste_erode,
    round(coalesce((SELECT sum(ST_Area(ST_Intersection(b.geom_2975, c.lot_geom)))
       FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, c.lot_geom)),
       0)::numeric, 1) AS aire_bati_dans_lot_m2,
    (SELECT coalesce(max(ST_Length(g.geom)), 0) FROM ST_Dump((
       SELECT ST_LineMerge(ST_Union(ST_Intersection(ST_Buffer(v.geom_2975, 1.5), ST_Boundary(c.lot_geom))))
       FROM spatial_layers v WHERE v.kind='voirie'
         AND v.subtype IN ('Route à 1 chaussée', 'Route à 2 chaussées', 'Rond-point')
         AND ST_DWithin(v.geom_2975, c.lot_geom, 2))) g) AS facade_lot_route
  FROM carve c
  CROSS JOIN LATERAL (SELECT g.geom FROM ST_Dump(ST_Difference(c.geom_2975, c.lot_geom)) g
                      ORDER BY ST_Area(g.geom) DESC LIMIT 1) rg),
zon AS (
  SELECT m.*, z.subtype AS zone, z.zone_lib, z.zone_descr
  FROM mesure m
  LEFT JOIN LATERAL (
    SELECT z2.subtype, z2.attrs->>'libelle' AS zone_lib, z2.name AS zone_descr FROM spatial_layers z2
    WHERE z2.kind='plu_gpu_zone' AND ST_Intersects(z2.geom_2975, m.lot_geom)
    ORDER BY ST_Area(ST_Intersection(z2.geom_2975, m.lot_geom)) DESC LIMIT 1) z ON true)
SELECT idu, commune, round(surface_m2)::int surface_m2, round(bat_m2)::int bati_m2,
       round((bat_m2/surface_m2)::numeric,3) bati_ratio, round(lot_m2)::int residuel_m2,
       round(rad::numeric,1) residuel_rayon_m, round(facade_lot::numeric,1) residuel_facade_m,
       NULL::numeric AS bati_facade_m, zone, zone_lib,
       'decoupe' AS type_division, 0 AS bati_lot_m2,
       round(compacite_lot::numeric,3) AS compacite,
       round(solidite_lot::numeric,3) AS solidite,
       round((bat_m2 / NULLIF(surface_m2 - lot_m2, 0))::numeric,3) AS emprise_restante,
       lot_geom, aire_bati_dans_lot_m2
FROM zon
WHERE facade_lot >= 12
  -- M129-C P1 — mêmes gardes que la famille résiduelle : bâti RÉVÉLÉ (CoSIA) + PENTE (MNT)
  AND NOT ({cosia_guard})
  AND NOT ({pente_guard})
  AND facade_reste >= 12
  -- C2 : le reste doit être D'UN SEUL TENANT (tolérance 1 m² pour les slivers cadastraux)
  AND nb_reste = 1
  -- C2-érosion (GO Vic) : rétréci de {erosion_m} m, le reste tient toujours d'un seul tenant
  -- (un couloir < {erosion_m}×2 m n'est pas un accès utilisable) — composantes > 25 m²
  AND nb_reste_erode <= 1
  -- C3 : lot NU strict — bâti ∩ lot ≤ 1 m² (bruit de numérisation), voisins compris
  AND aire_bati_dans_lot_m2 <= 1
  -- C3.3 (GO Vic, option b) : lot à ≥ 1 m de TOUT bâti — garde-fou de COHÉRENCE GÉOMÉTRIQUE
  -- (0,4 m d'un mur = erreur de donnée), PAS une règle d'urbanisme (le 3 m simulerait un
  -- prospect que le dossier refuse explicitement de prononcer)
  AND NOT EXISTS (SELECT 1 FROM spatial_layers bd WHERE bd.kind='batiment'
                    AND ST_DWithin(bd.geom_2975, zon.lot_geom, {dist_bati_min}))
  -- C5 ÉTENDU (GO Vic) : la façade repose sur une voirie QUALIFIÉE partout, plus seulement en
  -- RNU — sentier/chemin/empierrée ne sont pas un accès
  AND facade_lot_route >= 12
  -- C4 : zonages exclus par CODE (config : activité, touristique, équipements, AU fermées…)
  AND ({activite_pred})
  -- C4-libellé (finding BP0363) : mots-clés d'activité dans le DESCRIPTIF de zone,
  -- descriptions mixtes habitat/proximité protégées
  AND (zone_descr IS NULL OR NOT (zone_descr ~* '{descr_re}') OR zone_descr ~* '{descr_protege}')
  -- FRAÎCHEUR (revue 2) : PC Sitadel trop récent pour la couche BD TOPO → « lot nu » non garanti
  AND ({pc_pred})
  -- EXCLUSIONS DE REVUE (traçables — config/o12_exclusions_revue.yaml) : la revue tranche
  AND ({revue_pred})
  AND (zone = 'U' OR zone LIKE 'AU%' OR (zone IS NULL AND ({pau_pred})))
  AND bat_m2 / NULLIF(surface_m2 - lot_m2, 0) <= ({emprise_max})
  AND NOT EXISTS (SELECT 1 FROM spatial_layers l5 WHERE l5.kind='cinquante_pas'
                    AND ST_Intersects(l5.geom_2975, zon.lot_geom))
  AND NOT EXISTS (SELECT 1 FROM spatial_layers lf WHERE lf.kind='foret_publique'
                    AND lf.subtype='domaniale' AND ST_Intersects(lf.geom_2975, zon.lot_geom))
  AND NOT EXISTS (SELECT 1 FROM spatial_layers lp WHERE lp.kind='parc_national'
                    AND lp.subtype='coeur' AND ST_Intersects(lp.geom_2975, zon.lot_geom))
  AND NOT EXISTS (SELECT 1 FROM spatial_layers lt WHERE lt.kind='trait_de_cote'
                    AND ST_DWithin(lt.geom_2975, zon.lot_geom, 1));
"""


_INSERT_PARTIEL = """
INSERT INTO division_or_candidates (idu, commune, surface_m2, bati_m2, bati_ratio,
    residuel_m2, residuel_rayon_m, residuel_facade_m, bati_facade_m, zone, zone_lib,
    type_division, bati_lot_m2, compacite, solidite, emprise_restante, lot_geom,
    aire_bati_dans_lot_m2, gain_estime_eur, clarte, run_label)
SELECT d.idu, d.commune, d.surface_m2, d.bati_m2, d.bati_ratio, d.residuel_m2,
       d.residuel_rayon_m, d.residuel_facade_m, d.bati_facade_m, d.zone, d.zone_lib,
       d.type_division, d.bati_lot_m2, d.compacite, d.solidite, d.emprise_restante, d.lot_geom,
       d.aire_bati_dans_lot_m2,
       se.marge_estimee,
       round((d.residuel_rayon_m * 2 + LEAST(d.residuel_facade_m, 30))::numeric, 1) AS clarte,
       :served AS run_label   -- M50 : stamp du run servi (étage 0 lu)
FROM ({detect}) d
LEFT JOIN score_e se ON se.idu = d.idu AND se.estimable
ON CONFLICT (idu) DO UPDATE SET commune=EXCLUDED.commune, surface_m2=EXCLUDED.surface_m2,
    run_label=EXCLUDED.run_label,
    bati_m2=EXCLUDED.bati_m2, bati_ratio=EXCLUDED.bati_ratio, residuel_m2=EXCLUDED.residuel_m2,
    residuel_rayon_m=EXCLUDED.residuel_rayon_m, residuel_facade_m=EXCLUDED.residuel_facade_m,
    bati_facade_m=EXCLUDED.bati_facade_m, zone=EXCLUDED.zone, zone_lib=EXCLUDED.zone_lib,
    type_division=EXCLUDED.type_division, bati_lot_m2=EXCLUDED.bati_lot_m2,
    compacite=EXCLUDED.compacite, solidite=EXCLUDED.solidite,
    emprise_restante=EXCLUDED.emprise_restante,
    lot_geom=EXCLUDED.lot_geom, aire_bati_dans_lot_m2=EXCLUDED.aire_bati_dans_lot_m2,
    gain_estime_eur=EXCLUDED.gain_estime_eur,
    clarte=EXCLUDED.clarte, computed_at=now()
"""


def _ensure_ddl(session: Session) -> None:
    """DDL seulement si le schéma n'est pas déjà au dernier état (colonne la plus récente) :
    les ALTER ... IF NOT EXISTS prennent un verrou EXCLUSIF même à vide et, en parallèle par
    commune, se mettent en file derrière chaque INSERT long — constaté sur le run O12-PARTIEL
    (workers bloqués ~40 min sur un CREATE TABLE no-op)."""
    up_to_date = (
        session.execute(text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name='division_or_candidates' AND column_name='solidite'")).scalar()
        and session.execute(text("SELECT to_regclass('division_or_revue_snapshot')")).scalar() is not None)
    if not up_to_date:
        session.execute(text(DDL))


# tolérance de comparaison de tracés : deux lots dont la différence symétrique fait moins de
# 2 % de l'aire sont « le même tracé » (le détecteur est déterministe → un tracé inchangé est
# quasi identique ; une autre ancre donne un polygone franchement différent).
_TRACE_SYMDIFF_TOL = 0.02


def _insee_par_commune() -> dict[str, str]:
    """{nom de commune → INSEE} depuis le référentiel officiel (24 communes)."""
    from .run_all import REUNION_COMMUNES
    return {nom: insee for insee, nom in REUNION_COMMUNES}


def check_exclusions_revue() -> list[str]:
    """Vérifie la cohérence de config/o12_exclusions_revue.yaml et renvoie la liste des
    problèmes (vide = OK). Chaque entrée doit porter une `commune` connue dont l'INSEE ÉGALE
    les 5 premiers chiffres de l'idu (verrou anti-IDU-fantôme, revue 3), une `nature` valide,
    et un idu de 14 caractères sans apostrophe. Une entrée invalide est IGNORÉE au chargement
    (fail-safe : une config cassée n'exclut rien plutôt que d'exclure la mauvaise parcelle)."""
    import yaml

    from ..config import get_settings
    insee = _insee_par_commune()
    problems: list[str] = []
    try:
        cfg = get_settings().config_path / "o12_exclusions_revue.yaml"
        entries = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("exclusions") or []
    except Exception as exc:  # noqa: BLE001
        return [f"config illisible : {exc}"]
    for e in entries:
        idu, com, nat = str(e.get("idu", "")), e.get("commune"), e.get("nature")
        if len(idu) != 14 or "'" in idu:
            problems.append(f"{idu!r} : idu invalide")
        elif com not in insee:
            problems.append(f"{idu} : commune inconnue {com!r}")
        elif idu[:5] != insee[com]:
            problems.append(f"{idu} : préfixe {idu[:5]} ≠ INSEE {insee[com]} de {com}")
        if nat not in ("permanente", "liee_geometrie"):
            problems.append(f"{idu} : nature invalide {nat!r}")
    return problems


def _exclusions_revue() -> list[dict]:
    """Entrées d'exclusion de revue VALIDES (config/o12_exclusions_revue.yaml). Une entrée
    incohérente (préfixe INSEE ≠ commune, nature absente…) est ÉCARTÉE — jamais utilisée pour
    exclure la mauvaise parcelle. [] si le fichier est absent."""
    import yaml

    from ..config import get_settings
    insee = _insee_par_commune()
    try:
        cfg = get_settings().config_path / "o12_exclusions_revue.yaml"
        entries = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("exclusions") or []
    except Exception:  # noqa: BLE001 — config illisible → aucune exclusion
        return []
    ok = []
    for e in entries:
        idu, com = str(e.get("idu", "")), e.get("commune")
        if (len(idu) == 14 and "'" not in idu and com in insee and idu[:5] == insee[com]
                and e.get("nature") in ("permanente", "liee_geometrie")):
            ok.append(e)
    return ok


def _revue_idus(nature: str | None = None) -> list[str]:
    """IDU exclus par la revue, filtrés par nature ('permanente' | 'liee_geometrie' | None=tous)."""
    return [str(e["idu"]) for e in _exclusions_revue()
            if nature is None or e.get("nature") == nature]


def _revue_pred_sql(*, decoupe: bool) -> str:
    """Prédicat SQL des EXCLUSIONS DE REVUE — exclusion PERMANENTE par IDU (revue 3, 2e
    correctif : `liee_geometrie` abandonnée car elle s'auto-annulait, cf. yaml). `decoupe`
    est conservé pour la signature ; les deux familles excluent par IDU (une parcelle découpe
    ne matche pas un résiduel et vice-versa — l'union est inoffensive).

    M-C (F6) : VALEURS LIÉES — plus de concaténation de littéraux (ancienne garde « ' » not in x).
    La liste d'IDU passe en paramètre :revue_idus (rempli par les build). `<> ALL(ARRAY[])` = vrai
    pour tous → le cas « aucune exclusion » est géré sans branche « true » spéciale."""
    return "idu <> ALL(:revue_idus)"


def snapshot_review_lots(session: Session, *, commit: bool = True) -> int:
    """Photographie les tracés découpés COURANTS dans division_or_revue_snapshot — à appeler
    AVANT un re-run (qui remplace les lignes). Le re-run s'en sert pour distinguer un tracé
    inchangé (déjà revu / exclusion liée-géométrie tenue) d'un tracé modifié (à re-revoir).
    NON DESTRUCTIF s'il n'y a rien à photographier (0 découpe en base) : le snapshot existant
    est préservé — ainsi un run résiduel qui TRUNCATE la table avant le run découpe ne
    l'efface pas (l'orchestrateur prend le snapshot une seule fois, tout au début)."""
    _ensure_ddl(session)
    src = session.execute(text(
        "SELECT count(*) FROM division_or_candidates "
        "WHERE type_division = 'decoupe' AND lot_geom IS NOT NULL")).scalar()
    if not src:
        return session.execute(text("SELECT count(*) FROM division_or_revue_snapshot")).scalar()
    session.execute(text("TRUNCATE division_or_revue_snapshot"))
    n = session.execute(text(
        "INSERT INTO division_or_revue_snapshot (idu, lot_geom) "
        "SELECT idu, lot_geom FROM division_or_candidates "
        "WHERE type_division = 'decoupe' AND lot_geom IS NOT NULL")).rowcount
    if commit:
        session.commit()
    return n


def _zones_activite_doc() -> dict:
    """config/o12_zones_activite.yaml (mandat O12-PARTIEL-2 C4 + arbitrages) — {} si absent."""
    import yaml

    from ..config import get_settings
    try:
        cfg = get_settings().config_path / "o12_zones_activite.yaml"
        return yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — config illisible → aucune exclusion
        return {}


def _zones_activite(commune: str) -> list[str]:
    """Libellés de zones exclus du gisement pour la commune (activité, touristique,
    équipements, ZAC, AU strictes… — arbitrés, sourcés dans le yaml)."""
    return [str(x) for x in (_zones_activite_doc().get("exclusions") or {}).get(commune, [])]


def _activite_pats() -> list[str]:
    """Motifs regex toutes-communes (exclusions_pattern : familles AU fermées 2AU*/3AU*…),
    liés en paramètre :activite_pats."""
    return [str(p) for p in (_zones_activite_doc().get("exclusions_pattern") or [])]


def _activite_pred_sql(commune: str | None = None) -> str:
    """Prédicat SQL « la zone du lot n'est PAS un zonage exclu » : liste par commune +
    motifs toutes-communes (familles AU fermées 2AU*/3AU*).

    M-C (F6) : VALEURS LIÉES — plus de littéraux concaténés (ancienne garde « ' » not in x). Les
    libellés (par commune) passent en :activite_libs, les motifs regex en :activite_pats ; les
    build remplissent ces paramètres. `commune` n'influe plus sur le TEXTE (il détermine la VALEUR
    de :activite_libs, calculée côté appelant via _zones_activite). `<> ALL([])` / `~ ANY([])`
    gèrent le cas vide (vrai partout)."""
    return ("(zone_lib IS NULL OR (zone_lib <> ALL(:activite_libs) "
            "AND NOT (zone_lib ~ ANY(:activite_pats))))")


def _resolve_commune(session: Session, commune: str) -> str:
    """INSEE (5 chiffres) → NOM (parcels.commune), via la réf `commune_conso_enaf` (24 lignes, O(1)).
    Une entrée déjà-nom (ou un code introuvable) passe telle quelle.

    POURQUOI (M50-SUITE-2) : le détecteur filtre `parcels.commune` (= le NOM), indexé par
    `ix_parcels_commune`. Filtrer par le code INSEE demandait `left(idu,5) = :c` — expression NON
    indexable (le btree `ix_parcels_idu` est sous collation ≠ C, aucune borne d'octets ne s'y mappe)
    → **Parallel Seq Scan de 431 663 lignes** à CHAQUE commune (~3 min), et le `OR` avec le nom
    cassait AUSSI l'index pour l'entrée-nom. C'est ce qui rendait le rebuild île >1 h → interrompu →
    jamais commité (constaté). En amont, on résout une fois vers le NOM : détecteur indexé (~s),
    plafonds PLU (slug = nom) correctement chargés, et la colonne `commune` reste stockée en NOM."""
    if not (len(commune) == 5 and commune.isdigit()):
        return commune
    if session.execute(text("SELECT to_regclass('commune_conso_enaf')")).scalar() is None:
        return commune  # réf absente (base de test) → on laisse l'entrée telle quelle
    nom = session.execute(
        text("SELECT commune FROM commune_conso_enaf WHERE insee = :c"), {"c": commune}).scalar()
    return nom or commune


def all_communes(session: Session) -> list[str]:
    """Liste CANONIQUE des communes de l'île — la réf `commune_conso_enaf` (24 lignes), ordonnée par
    INSEE (stable/reproductible), renvoyée en NOMS (parcels.commune, chemin indexé). Pour un rebuild
    `--all` qui ne peut oublier aucune commune (M50-SUITE-2 : `--communes` seul = manque). Réf absente
    (base de test) → liste vide (l'appelant décide)."""
    if session.execute(text("SELECT to_regclass('commune_conso_enaf')")).scalar() is None:
        return []
    return [r[0] for r in session.execute(text(
        "SELECT commune FROM commune_conso_enaf ORDER BY insee"))]


def build_divisions_partiel(session: Session, communes: list[str], *, commit: bool = True,
                            log=lambda *_: None) -> dict:
    """O12-PARTIEL — détecte les LOTS DÉCOUPÉS (type 'decoupe', famille DISTINCTE des lots
    résiduels — jamais fusionnée). Univers disjoint du pool résiduel (ratio > 50 % vs ≤ 50 %) :
    aucun conflit de clé. Mêmes gardes que le pool validé, aucun critère assoupli."""
    _ensure_ddl(session)
    from ..scoring.score_v_constants import Q_A_RUN_LABEL   # M50 : stamp du run servi (:served)
    has_score_e = session.execute(text("SELECT to_regclass('score_e')")).scalar() is not None
    has_pau = session.execute(text("SELECT to_regclass('parcel_pau')")).scalar() is not None
    pau_pred = "EXISTS (SELECT 1 FROM parcel_pau pp WHERE pp.idu = zon.idu)" if has_pau else "false"
    # fraîcheur bâti : recoupement Sitadel si la table existe, sinon pas de garde (et on l'assume)
    has_sitadel = session.execute(text("SELECT to_regclass('sitadel_permits')")).scalar() is not None
    pc_pred = (f"NOT EXISTS (SELECT 1 FROM sitadel_permits sp WHERE sp.idu_codes ? zon.idu "
               f"AND sp.type = 'PC' AND sp.date >= '{PC_FRAIS_DEPUIS}')") if has_sitadel else "true"
    # M-C (F5) : total = somme des lots découpés des communes de CE RUN, accumulé dans la boucle
    # (avant : count(*) global 'decoupe' avant la boucle PUIS refait à chaque commune — mélange
    # « pré-run » et « toute la table », pas la mesure du run).
    total = 0
    revue_idus, activite_pats = _revue_idus(), _activite_pats()   # M-C (F6) : valeurs LIÉES (une fois)
    failures: list[str] = []
    for commune in communes:
        commune = _resolve_commune(session, commune)  # M50-SUITE-2 : INSEE → NOM (indexé) en amont
        try:
            # M50-SUITE : PURGE des découpes de la commune AVANT réécriture (mêmes règles : commune vide,
            # pas périmée ; tracés REVUS préservés ; le snapshot de revue conserve les géométries revues).
            session.execute(text(
                "DELETE FROM division_or_candidates WHERE commune = :c "
                "AND type_division = 'decoupe' AND coalesce(note_revue,'') = ''"),
                {"c": commune})
            detect = _DETECT_PARTIEL.format(
                cosia_guard=_cosia_guard_sql(session),
                pente_guard=_pente_guard_sql(session),
                surface_min=int(_S.get('surface_min_m2', 1000)),
                surface_max=int(_S.get('surface_max_m2', 6000)),
                ratio_min=float(_S.get('bati_ratio_min', 0.08)),
                ratio_max=float(_S.get('bati_ratio_max', 0.45)),
                pau_pred=pau_pred, ens_min_bat=ENSEMBLE_MIN_BATIMENTS,
                grand_bat_m2=int(GRAND_BATIMENT_M2), emprise_max=_emprise_max_sql(commune),
                lot_min=LOT_DECOUPE_MIN_M2, lot_max=LOT_DECOUPE_MAX_M2,
                compacite_min_dec=COMPACITE_MIN_DECOUPE, ancre_w=ANCRE_LARGEUR_M,
                solidite_min=SOLIDITE_MIN_DECOUPE,
                activite_pred=_activite_pred_sql(commune),
                erosion_m=EROSION_RESTE_M, dist_bati_min=DIST_BATI_MIN_M,
                descr_re=ACTIVITE_DESCR_RE, descr_protege=ACTIVITE_DESCR_PROTEGE_RE,
                pc_pred=pc_pred, revue_pred=_revue_pred_sql(decoupe=True)).strip().rstrip(";")
            if has_score_e:
                insert_sql = _INSERT_PARTIEL.format(detect=detect)
            else:
                insert_sql = _INSERT_PARTIEL.replace("se.marge_estimee,", "NULL::int,").replace(
                    "LEFT JOIN score_e se ON se.idu = d.idu AND se.estimable", "").format(detect=detect)
            session.execute(text(insert_sql), {"commune": commune, "served": Q_A_RUN_LABEL,
                                               "revue_idus": revue_idus, "activite_pats": activite_pats,
                                               "activite_libs": _zones_activite(commune)})
            # M50-SUITE-2 : commit ATOMIQUE PAR COMMUNE (cf. build_divisions) — durable + incrémental.
            if commit:
                session.commit()
        except Exception as e:   # noqa: BLE001 — commune ISOLÉE (rollback), l'île continue (cf. build_divisions)
            session.rollback()
            failures.append(commune)
            log(f"⚠ division-or-partiel {commune} ÉCHEC ({type(e).__name__}: {str(e)[:120]}) — ignorée, continue")
            continue
        n = session.execute(text(
            "SELECT count(*) FROM division_or_candidates WHERE commune = :c "
            "AND type_division = 'decoupe'"),
            {"c": commune}).scalar()
        total += n
        log(f"division-or-partiel {commune} : {n} lots à découper")
    if failures:
        log(f"⚠ {len(failures)} commune(s) EN ÉCHEC (non écrites, île poursuivie) : {failures}")
    log(f"division_or_candidates (decoupe) : {total} lots à découper (MASQUÉ)")
    return {"total": total, "expose": EXPOSE, "failures": failures}


def _emprise_max_sql(commune: str) -> str:
    """Plafond d'emprise bâtie du LOT RESTANT : les emprises max CALIBRÉES du PLU de la commune
    (config/plu_<slug>.yaml, `emprise_sol_pct` chiffré, clé = libellé de zone) priment via un
    CASE sur zone_lib ; toute zone non calibrée retombe sur le plancher EMPRISE_RESTANTE_MAX."""
    try:
        from ..faisabilite import plu_rules
        rules = plu_rules.load_rules(commune)
    except Exception:  # noqa: BLE001 — pas de PLU calibré lisible → plancher prudent partout
        rules = {}
    pairs = [(code, r.emprise_sol_pct) for code, r in sorted(rules.items())
             if isinstance(r.emprise_sol_pct, float) and "'" not in code]
    if not pairs:
        return str(EMPRISE_RESTANTE_MAX)
    whens = " ".join(f"WHEN '{code}' THEN {pct / 100:.2f}" for code, pct in pairs)
    return f"CASE zone_lib {whens} ELSE {EMPRISE_RESTANTE_MAX} END"


def build_divisions(session: Session, communes: list[str], *, commit: bool = True, log=lambda *_: None) -> dict:
    """Détecte les candidats division-en-or pour une liste de communes. Table MASQUÉE (flag EXPOSE=False).
    Une passe SQL par commune (détection + gain Score É + clarté), pas de boucle Python par ligne."""
    _ensure_ddl(session)
    has_score_e = session.execute(text("SELECT to_regclass('score_e')")).scalar() is not None
    # PAU estimée (mandat RNU) : si la table existe, une commune SANS zonage garde ses candidats
    # dans la PAU ; sinon (base sans branche RNU) un lot sans zone est simplement exclu.
    has_pau = session.execute(text("SELECT to_regclass('parcel_pau')")).scalar() is not None
    pau_pred = "EXISTS (SELECT 1 FROM parcel_pau pp WHERE pp.idu = zon.idu)" if has_pau else "false"
    # O12-GARDE : run servi (Q_A_RUN_LABEL, suit toute bascule) + garde non-constructibilité.
    from ..scoring.score_v_constants import Q_A_RUN_LABEL
    has_constr = session.execute(text("SELECT to_regclass('parcel_constructibilite')")).scalar() is not None
    constr_guard = ("NOT EXISTS (SELECT 1 FROM parcel_constructibilite pc WHERE pc.parcel_id = zon.id "
                    "AND pc.label IN ('declasse_zone_fermee','declasse_non_constructible'))"
                    if has_constr else "true")
    # M-C (F5) : total = somme des candidats des communes de CE RUN (accumulé dans la boucle), pas
    # un count(*) GLOBAL de toute la table refait à chaque commune (avant : 24 scans complets pour
    # un seul log, et un total incluant les communes hors de ce run).
    total = 0
    revue_idus, activite_pats = _revue_idus(), _activite_pats()   # M-C (F6) : valeurs LIÉES (une fois)
    failures: list[str] = []
    for commune in communes:
        commune = _resolve_commune(session, commune)  # M50-SUITE-2 : INSEE → NOM (indexé) en amont
        try:
            # M50-SUITE : PURGE de la commune AVANT réécriture (résiduel libre/demolition) — un rebuild
            # à 0/moins doit laisser la commune VIDE, pas périmée (avant : upsert seul → périmés survivants).
            # Tracés REVUS (note_revue = décision humaine) PRÉSERVÉS. Commune résolue en NOM (parcels.commune).
            session.execute(text(
                "DELETE FROM division_or_candidates WHERE commune = :c "
                "AND type_division IN ('libre','demolition') AND coalesce(note_revue,'') = ''"),
                {"c": commune})
            # plafond d'emprise (PLU calibré) et zonages exclus dépendent de la commune → SQL par commune
            detect = _DETECT.format(pau_pred=pau_pred, ens_min_bat=ENSEMBLE_MIN_BATIMENTS,
                                    grand_bat_m2=int(GRAND_BATIMENT_M2),
                                    compacite_min=COMPACITE_MIN,
                                    surface_min=int(_S.get('surface_min_m2', 1000)),
                                    surface_max=int(_S.get('surface_max_m2', 6000)),
                                    buffer_bati=int(_S.get('buffer_bati_m', 3)),
                                    ratio_min=float(_S.get('bati_ratio_min', 0.08)),
                                    ratio_max=float(_S.get('bati_ratio_max', 0.45)),
                                    lot_min=int(_S.get('lot_min_m2', 500)),
                                    reste_min=int(_S.get('reste_min_m2', 400)),
                                    lot_part_max=float(_S.get('lot_part_max', 0.5)),
                                    rayon_min=int(_S.get('rayon_inscrit_min_m', 9)),
                                    facade_min=int(_S.get('facade_min_m', 12)),
                                    cosia_guard=_cosia_guard_sql(session),
                                    pente_guard=_pente_guard_sql(session),
                                    emprise_max=_emprise_max_sql(commune),
                                    activite_pred=_activite_pred_sql(commune),
                                    descr_re=ACTIVITE_DESCR_RE,
                                    descr_protege=ACTIVITE_DESCR_PROTEGE_RE,
                                    constr_guard=constr_guard,
                                    revue_pred=_revue_pred_sql(decoupe=False)).strip().rstrip(";")
            if has_score_e:
                insert_sql = _INSERT.format(detect=detect)
            else:   # pas de Score É → gain NULL, sans jointure
                insert_sql = _INSERT.replace("se.marge_estimee,", "NULL::int,").replace(
                    "LEFT JOIN score_e se ON se.idu = d.idu AND se.estimable", "").format(detect=detect)
            session.execute(text(insert_sql), {"commune": commune, "served": Q_A_RUN_LABEL,
                                               "revue_idus": revue_idus, "activite_pats": activite_pats,
                                               "activite_libs": _zones_activite(commune)})
            # M50-SUITE-2 : commit ATOMIQUE PAR COMMUNE (purge+insert dans LA MÊME transaction, puis
            # commit). Durable + incrémental : un rebuild île lent/interrompu GARDE les communes finies.
            # Jamais de purge commitée sans son insert : DELETE et INSERT commitent ensemble, ici.
            if commit:
                session.commit()
        except Exception as e:   # noqa: BLE001
            # M50-SUITE-2 : une commune qui CASSE (ex. requête pathologique + timeout, géométrie
            # invalide) est ISOLÉE — rollback de SA SEULE transaction (les communes déjà commitées
            # restent, prouvé) — et l'île CONTINUE. Avant : l'exception remontait et avortait tout ;
            # comme Les Avirons est en tête d'ordre INSEE, l'île ne produisait alors RIEN.
            session.rollback()
            failures.append(commune)
            log(f"⚠ division-or {commune} ÉCHEC ({type(e).__name__}: {str(e)[:120]}) — ignorée, l'île continue")
            continue
        n = session.execute(text(
            "SELECT count(*) FROM division_or_candidates WHERE commune = :c"),
            {"c": commune}).scalar()
        total += n
        log(f"division-or {commune} : {n} candidats")
    if failures:
        log(f"⚠ {len(failures)} commune(s) EN ÉCHEC (non écrites, île poursuivie) : {failures}")
    log(f"division_or_candidates : {total} candidats (MASQUÉ — attend le dossier de revue Vic)")
    return {"total": total, "expose": EXPOSE, "failures": failures}


def top_candidates(session: Session, *, limit: int = 20, communes: list[str] | None = None,
                   type_division: str | None = None) -> list[dict]:
    """Les meilleurs candidats pour le dossier de revue 20 cartes — divisions LIBRES d'abord
    (le cas classique), puis clarté géométrique décroissante.
    `communes` : échantillonnage ÉQUILIBRÉ en tourniquet — le rang-1 de chaque commune, puis les
    rang-2, etc. ; une commune à court de candidats est compensée par les autres.
    `type_division` : restreint à 'libre' ou 'demolition' (dossier de revue dédié à un type)."""
    if session.execute(text("SELECT to_regclass('division_or_candidates')")).scalar() is None:
        return []
    where = "WHERE type_division = :type" if type_division else ""
    params: dict = {"lim": limit}
    if type_division:
        params["type"] = type_division
    tri = "(type_division = 'demolition'), clarte DESC, residuel_m2 DESC"
    if not communes:
        rows = session.execute(text(
            f"SELECT * FROM division_or_candidates {where} ORDER BY {tri} LIMIT :lim"),
            params).mappings().all()
        return [dict(r) for r in rows]
    where = (where + " AND" if where else "WHERE") + " commune = ANY(:communes)"
    params["communes"] = communes
    rows = session.execute(text(
        f"""
        SELECT * FROM (
          SELECT c.*, row_number() OVER (PARTITION BY commune ORDER BY {tri}) rn
          FROM division_or_candidates c {where}) t
        ORDER BY rn, {tri} LIMIT :lim
        """), params).mappings().all()
    return [{k: v for k, v in dict(r).items() if k != "rn"} for r in rows]


def all_candidates_for_review(session: Session) -> list[dict]:
    """TOUT le pool pour un dossier de revue EXHAUSTIF (revue 2 : un défaut attrapable seulement
    par l'œil ⇒ l'échantillon ne suffit plus). Ordre : découpes par commune, puis résiduels
    (libre avant démolition). Chaque candidat porte `revue_statut` (par rapport au snapshot des
    tracés revus) : 'nouveau' / 'inchange' / 'modifie' pour les découpes, 'residuel' sinon."""
    if session.execute(text("SELECT to_regclass('division_or_candidates')")).scalar() is None:
        return []
    has_snap = session.execute(text("SELECT to_regclass('division_or_revue_snapshot')")).scalar() is not None
    statut = (
        f"""CASE WHEN c.type_division <> 'decoupe' THEN 'residuel'
                 WHEN s.idu IS NULL OR s.lot_geom IS NULL THEN 'nouveau'
                 WHEN ST_Area(ST_SymDifference(c.lot_geom, s.lot_geom))
                      < {_TRACE_SYMDIFF_TOL} * ST_Area(s.lot_geom) THEN 'inchange'
                 ELSE 'modifie' END"""
        if has_snap else "CASE WHEN c.type_division <> 'decoupe' THEN 'residuel' ELSE 'nouveau' END")
    join = "LEFT JOIN division_or_revue_snapshot s ON s.idu = c.idu" if has_snap else ""
    rows = session.execute(text(
        f"""
        SELECT c.*, {statut} AS revue_statut
        FROM division_or_candidates c {join}
        ORDER BY (c.type_division = 'decoupe') DESC, c.commune,
                 (c.type_division = 'demolition'), c.clarte DESC, c.residuel_m2 DESC
        """)).mappings().all()
    return [dict(r) for r in rows]
