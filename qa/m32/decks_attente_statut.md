# M32 — Aparté : statut des decks de revue en attente (lecture seule)

Decks pré-M28 : `qa/dette4/revue_suspectes.pdf` (32) et `revue_90_cadastre.pdf` (90). Question :
combien méritent encore une revue visuelle, combien sont déjà traités par les règles M28 ?

## Méthode (et sa limite honnête)

Les générateurs (`gen_revue_suspectes.py`, `gen_revue_90_cadastre.py`) **interrogent la base en
direct** et n'écrivent qu'un HTML dans `/tmp` — **aucun manifeste d'IDU persisté**, et les PDF ne
sont pas extractibles au texte. Les IDU EXACTS des decks d'époque ne sont donc pas récupérables
depuis un fichier source. Mais les requêtes sont déterministes : les **re-jouer aujourd'hui** donne
la population COURANTE sous la même logique. Les comptes diffèrent des decks parce que **M28 a
re-mesuré l'emprise bâtie (CoSIA) et recalculé le run servi en place**. Référence « d'époque » =
`q_v8_calibre_pre_m28` (le run servi juste avant M28). Tableau complet : `qa/m32/decks_attente_idus.csv`.

## Deck « suspectes » (32 → **3** aujourd'hui)

Population = parcelles bien classées mais **vides < 20 m²** (couche BD TOPO) AVEC preuve indépendante
(piscine / PV / DVF-bâti). Re-jeu actuel : **3 parcelles** — 1 chaude (tête servie), 2 écartées.

**Pourquoi le passage de 32 à 3 = M28 les a traitées.** Sur les ~195 parcelles top-1000 (pré_pond)
qui portent une détection, le devenir actuel est :

| tier actuel | n |
|---|---|
| ecartee | 128 |
| **declasse_bati_revele** | **33** |
| **declasse_bati_sature** | **13** |
| chaude | 11 |
| declasse_zone_fermee / non_constructible / au_statut_inconnu | 5 / 3 / 2 |

→ **46 déclassées par les règles bâti M28** (revele + sature) : la re-mesure CoSIA a révélé le bâti
que la couche voyait absent, elles ont quitté l'ensemble « < 20 m² » et sont tombées en déclassement.
**Le deck suspectes est donc quasi entièrement SUPERSÉDÉ par M28.** Reste **1 parcelle en tête**
(chaude) qui justifie encore un œil ; les 2 autres sont écartées.

## Deck « 90 cadastre » (90 → **37** aujourd'hui)

Population = parcelles en **tête servie**, vides < 20 m² (couche), **sans aucun indice** piscine/PV/DVF,
MAIS dont le **bâtiment CADASTRE intersecte > 20 m²** (la couche a raté un bâti que le cadastre voit).
Re-jeu actuel : **37 parcelles** — **33 chaudes + 4 brûlantes**, toutes en tête servie.

**Pourquoi M28 ne les traite PAS.** `declasse_bati_revele` s'appuie sur **CoSIA**, qui voit ces
parcelles vides LUI AUSSI — seule la géométrie du cadastre révèle le bâtiment. C'est la dette
**« couche bâtiment lacunaire »** (indice #), distincte du bâti-révélé CoSIA. Ces 37 **méritent
encore la revue visuelle** : ce sont exactement les cas que les règles automatiques ne peuvent pas
trancher (aucune couche raster ne les voit).

## Conclusion

| Deck | D'époque | Aujourd'hui | En tête servie | Traité par M28 | Mérite encore revue |
|---|---|---|---|---|---|
| suspectes | 32 | **3** | 1 (chaude) | ✅ ~46 déclassées (bati_revele/sature) | **1** |
| 90 cadastre | 90 | **37** | 37 (4 brûl. + 33 chaudes) | ❌ (CoSIA aveugle, dette couche lacunaire) | **37** |

- **~38 parcelles** méritent encore une revue visuelle (down de ~122), **concentrées sur le cohorte
  cadastre-lacunaire** — pas sur les suspectes-avec-indice (celles-là, M28 les a tranchées).
- **Recommandation** : ne re-générer/revoir QUE le deck 90-cadastre (37 parcelles à jour), et
  classer le deck suspectes comme absorbé par M28 (1 résidu à vérifier au fil de l'eau). Le vrai
  gisement restant = **la couche bâtiment lacunaire** (le cadastre voit un bâti que ni BD TOPO ni
  CoSIA ne voient) — dette ouverte, indépendante de M28.

Aucune écriture hors ce rapport + le CSV. Les ré-extractions restent la priorité du tour.
