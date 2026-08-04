# SPEC — Millésime amont des couches servies (chantier transverse, validé sur le principe)

> **RÉDACTION SEULE — rien d'implémenté** (consigne Vic 04/08 : « Ne pas implémenter avant
> que je la lise »). Règle de conception à outiller : « la fraîcheur d'une donnée est celle
> de sa source amont, jamais celle de son ingestion ni celle du moment où on la regarde. »

## 1 · Les trois dates (vocabulaire de la spec)
| date | définition | exemple DVF | exemple bâti |
|---|---|---|---|
| **millésime amont** | version/édition publiée par le fournisseur | « géo-DVF avril 2026 (années 2021-2025) » | « BD TOPO éd. 2026-06-15 » |
| **horizon de donnée** | date du fait le plus récent DANS la donnée | max(date_mutation) = 31/12/2025 | max(date_d_apparition) |
| date d'ingestion | quand NOUS l'avons chargée | 07/2026 | 28-29/06/2026 |

La confusion des trois est le piège rencontré 3 fois. Le client doit voir **l'horizon** ;
l'exploitant doit voir les trois.

## 2 · Colonnes à ajouter — `data_sources`
```sql
ALTER TABLE data_sources
  ADD COLUMN source_millesime      varchar(64),   -- édition fournisseur, texte libre normé
  ADD COLUMN source_horizon_at     date,          -- horizon de donnée (calculé à l'ingestion)
  ADD COLUMN source_cadence        varchar(32),   -- 'trimestriel', 'semestriel', 'hebdo', 'continu'
  ADD COLUMN prochain_millesime_at date;          -- prochaine publication attendue (si connue)
```
Renseignées PAR L'INGESTION (chaque ingester met à jour sa ligne), jamais à la main.
`last_sync_at` existant = date d'ingestion, inchangé.

## 3 · Couches concernées (1ʳᵉ vague) et valeurs attendues
| couche | source_millesime | horizon (requête) | cadence | prochain |
|---|---|---|---|---|
| DVF | « géo-DVF avril 2026 » | max(date_mutation) | semestriel | oct. 2026 (+S1-2026) |
| BD TOPO bâti | « éd. 2026-06-15 (WFS) » | max(date_d_apparition)* | trimestriel | sept. 2026 |
| CoSIA (si branchée) | « CoSIA 2025 (PVA 07-08/2025) » | date des vols | par PVA (≈3 ans) | PVA suivante |
| Sitadel | millésime Dido | max(date) valide | mensuel (delta) | — |
| BODACC | flux | max(date_annonce) | continu | — |
| DPE | flux ADEME | max(date_etablissement) | continu | — |
| GPU (PLU) | déjà traité par le garde-fou fraîcheur GPU-vs-mairie (train 6) — s'aligne sur ce vocabulaire | | | |

\* nécessite le prochain chargement BD TOPO (les dates sont conservées depuis le correctif du 04/08).

## 4 · Affichage fiche (client)
- **Règle : tout CHIFFRE servi issu d'une couche datée porte son horizon, à côté du chiffre,**
  pas dans un tiroir. Libellé court : « (ventes jusqu'à déc. 2025) », « (bâti IGN juin 2026) »,
  « (ortho juil. 2025) ».
- Existant à généraliser : le bandeau P14 `dvf_couverture` (« ventes jusqu'à … ») existe mais
  n'apparaît QUE dans le tiroir Faisabilité/Bilan — la tuile Marché d'en-tête (médiane €/m²,
  n ventes) est SANS étiquette → la doter du même libellé.
- Cartes de revue : date de prise de vue déjà affichée (fait, 04/08).
- Payload : un objet `fraicheur` par module (`{horizon, millesime, cadence}`) plutôt que des
  strings ad hoc — le front formate, l'API ne fabrique pas de phrases.

## 5 · Garde d'exploitation (2ᵉ vague, optionnelle)
`check_fraicheur()` dans `bascule_gardes` : à toute bascule, si `now() − source_horizon_at`
dépasse la cadence attendue ×2 → avertissement bruyant (pas bloquant : le retard de la source
n'est pas une faute de la bascule, mais il doit se VOIR).

## 6 · Ce que la spec ne fait PAS
- Pas de correction rétroactive des données ; pas de recalcul de scores.
- Pas d'affichage de la date d'ingestion au client (c'est une méta d'exploitation).
- Pas d'invention d'horizon quand la donnée n'en porte pas (afficher « horizon inconnu »).

## Estimation
Colonnes + renseignement par les 6 ingesters : ~1 j. Affichage fiche (tuile Marché + libellés
modules) : ~½ j. Garde : ~¼ j. Total ~2 j, découpable par couche (DVF d'abord — priorité Vic).
