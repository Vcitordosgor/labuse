# ETUDE-ZONE-1 — l'Étude n'implante qu'en zone constructible

Branche `fix/etude-zone-1` (worktree `labuse-etude-zone`, ports 8832/6032). Pas de merge. DA existante.

## Le défaut

L'Étude de faisabilité (moteur `labuse.implantation`) construisait son **assiette** à partir de
l'**union cadastrale pleine** des parcelles (`ST_Union(geom_2975)`), puis n'en retranchait que les
reculs et le PPR rouge. La **portion non constructible** (zones A/N) restait dans l'assiette : sur
une parcelle à cheval U/N, le moteur pouvait poser bâtiments, places et allées **dans la partie N**.

C'est exactement la divergence que ZONE-1 avait fermée ailleurs (Dossier, Gabarit, résiduel) mais
qui subsistait dans l'Étude : `97416000DY0106` ressortait « 27-31 logements » calculés sur toute la
parcelle alors que sa zone dominante est N.

## Le correctif

`src/labuse/implantation/terrain.py` — `charger()` restreint l'assiette à sa **portion
constructible AVANT** d'appliquer reculs et PPR :

```
assiette = (union cadastrale) ∩ (zones PLU de famille U/AU)   →   reculs   →   − PPR rouge
```

- **Source unique de zonage** : les zones `plu_gpu_zone` et la famille via
  `labuse_zone_famille(subtype)` — EXACTEMENT la source de `faisabilite.zone_servie.zone_dominante`,
  donc du **Dossier** et du **Gabarit** (`FAMILLES_CONSTRUCTIBLES = ("U","AU")` importé de
  `zone_servie`). Constructible = U/AU ; A/N exclus.
- **Limites inchangées** : la classification voie/séparative reste faite sur le **contour cadastral
  réel** (`aw`). La coupure interne U↔A/N ne porte **aucun recul** — ce n'est pas une limite de
  propriété, juste une bascule de zone (la partie N est au même propriétaire).
- **Le CHIFFRE affiché ≠ le clip géométrique.** La surface constructible servie au client
  (`contenance_totale_m2`) est **LUE de la source de zonage unique** —
  `Σ parcelles (contenance × zone_dominante.pct_constructible / 100)` — soit EXACTEMENT ce
  qu'affichent le Dossier (fiche §PLU) et le Gabarit (`api/gabarit.py` : `contenance × pct`).
  **Jamais** un recalcul géométrique sur le dessin (qui divergeait de 1 à 3 points, cf. l'ancien
  « Dossier Ud 45,6 % vs Gabarit 43 % »). Le clip géométrique (`∩ U/AU`) ne sert qu'au **dessin**
  (assiette tracée, zone d'implantation) et à garantir qu'aucun objet n'est posé en A/N.
- **No-op prouvé hors à-cheval** : si la portion constructible couvre ≥ 99,5 % de l'assiette
  (parcelle ~100 % U/AU), l'assiette ORIGINALE est conservée telle quelle — l'intersection PostGIS,
  même pleine, perturberait les sommets au flottant et ferait dériver les témoins `reel`.
- **Commune non zonée (RNU)** : aucune zone `plu_gpu_zone` ne touche l'assiette → on ne peut pas
  statuer → assiette pleine (on ne retire rien). Zone PLU connue mais 100 % A/N → assiette vide
  (rien de constructible), l'Étude rend « simulation impossible ».

Champs ajoutés au payload (`terrain`) : `aire_hors_zone_m2`, `pct_constructible`,
`note_constructibilite` (additifs, le front les ignore sans casser).

## Avant / après — témoin `97405000AL0751` (Petite-Île, UC 70 % / N 30 %, SANS PPR)

Preuves : `avant/etude.{json,pdf}` (API ancien code) et `apres/etude.{json,pdf}` (API corrigé).

| Grandeur (scénario A) | AVANT | APRÈS |
|---|---|---|
| Contenance servie | **1 023 m²** (parcelle entière) | **714 m²** (portion UC) |
| Assiette (dessin) | 971 m² | 677,7 m² |
| Zone d'implantation | 594,4 m² | 436,2 m² |
| Part non constructible retirée | — | **293 m² (N)** |
| Logements | **8** | **4** |
| SDP | 530 m² | 270 m² |

L'export PDF passe de « Assiette fusionnée 1 023 m² » à « Assiette fusionnée 714 m² » +
« Plafond d'emprise ≤ 357 m² (50 % de la contenance) », et la note
« Implantation limitée à la portion constructible (~69,8 %) ; 309 m² en zone non constructible (A/N)
exclus » est servie. Les 4 logements et tout le plan masse tiennent désormais dans la seule UC
(vérifié géométriquement : 0 objet hors assiette constructible — garde E-20).

**Même valeur partout (source unique).** La surface constructible servie par l'Étude
(`contenance_totale_m2` = **714,1 m²**) recoupe celle du Dossier (part 69,79 % × 1 023 = **714 m²**)
et du Gabarit (`surfaceNote` « dont ~714 m² en zone UC ») ; l'écart de 0,1 m² est le seul arrondi
d'affichage (le Gabarit arrondit à l'entier, l'Étude au dixième). E-20 le vérifie désormais
explicitement.

## `97411000AV0110` — « implantation 0 m² » : LÉGITIME

Parcelle Saint-Denis à cheval **Uh 57 % (382 m²) / N 43 % (283 m²)**, contenance 690 m² /
dessin 665 m². Après clip, la portion Uh = 396 m² en contenance (= 382 × 690/665), ce qui recoupe la
part servie par le Dossier et le Gabarit (garde E-18 : « part 57,5 % · gabarit 57 % · 396 m² »).

Décomposition de la zone d'implantation sur la portion Uh (382 m²) :

| Étape | Aire restante |
|---|---|
| Portion Uh | 382 m² |
| − reculs (voie 4 m + séparative 3 m) | **0 m²** |
| − PPR rouge (ne touche que 2,6 m² de l'Uh) | 0 m² |

**Les reculs à eux seuls consomment toute la portion Uh** : la bande Uh est trop étroite (le PPR
n'y est pour rien). Le « 0 m² » est donc **légitime**, pas un défaut — et il valait déjà 0 avant le
correctif (la parcelle pleine après reculs donnait aussi 0). Le correctif ne régresse rien ; il
rattache seulement honnêtement le terrain à ses 396 m² Uh au lieu des 690 m² pleins.

## Garde anti-régression

`scripts/coherence/chasse_docs.py` — **E-20** (« Étude : implantation confinée à la zone
constructible ») sur `97405000AL0751` :
1. l'assiette est restreinte (`pct_constructible` < 100, `aire_hors_zone_m2` > 0, note servie) ;
2. la surface constructible AFFICHÉE (`contenance_totale_m2`) **égale** celle du Dossier
   (Σ parts U/AU × contenance) ET du Gabarit (`surfaceNote`), à la tolérance de E-18
   (`max(2 m², 1 %)`) — preuve que l'Étude lit la source de zonage, pas le clip géométrique ;
3. **aucun** objet du plan masse (bâtiment, module, noyau, coursive, places, allées, accès, espace
   libre, zone) ne déborde de l'assiette constructible (test géométrique shapely ; SKIP si absent).

Un retour en arrière (clip retiré) fait tomber E-20 en ECART (plus de `pct_constructible` servi) ;
un recalcul géométrique du chiffre affiché (divergence du zonage) fait tomber le point 2.

## Vérifications

- Banc `chasse_docs.py` : **20 OK · 0 ECART · 0 SKIP** (19 existantes + E-20).
- pytest unitaire (sélection EXACTE du hook pre-push,
  `-m "not db and not local and not reel and not network"`) : **2600 passed, 48 skipped**.
- Front : `tsc -b` 0, `vitest` **277 passed (60 fichiers)**, scan secrets propre.
- pytest `reel` implantation sur base servie (`LABUSE_APP_DATABASE_URL` = base locale) :
  **112 passed** (tous les témoins L'Étang-Salé / Saint-André / Saint-Denis = 100 % U/AU →
  clip NO-OP, géométrie byte-identique). 2 échecs **`test_route_*`** (= appel HTTP qui passe par
  `session_scope`, que conftest redirige vers `labuse_test` VIDE → `parcelles introuvables` levé
  AVANT mon code) : **échec pré-existant d'environnement, prouvé identique sur l'arbre propre
  (`git stash`), indépendant de ce correctif**. Le hook pre-push n'exécute PAS les `reel`.
</content>
</invoke>
