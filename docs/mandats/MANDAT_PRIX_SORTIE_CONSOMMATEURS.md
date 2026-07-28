# MANDAT — Prix de sortie neuf dans les 4 consommateurs hors fiche (Copilote, Banquier, Argumentaire, modules)

**SPEC — à exécuter (rédigé le 28/07/2026, arbitré par Vic). Suite directe et PRIORITAIRE de
l'application « instrument prix appartement de marché » (`CALIBRATION_PHASE_A_BACKTEST.md`,
§ APPLICATION). Ordre gravé : CONSOMMATEURS (ce mandat) → COÛT PAR TAILLE (mandat d'après). Un
correctif à la fois.**

---

## ⚠ CONSIGNE EN TÊTE — à ne pas adoucir (Vic, même consigne qu'au M26-B)

> **Tant que ce mandat n'est pas passé, la charge foncière servie par le Copilote, le Banquier,
> l'Argumentaire et les modules repose sur le prix de l'EXISTANT (~2 265 €/m²) et non du NEUF.
> Ces sorties ne se montrent à personne** — ni client, ni comité, ni démo. Seule la **fiche**
> sert une charge juste (instrument appartement de marché, mandat précédent). Le Copilote, le
> Banquier, l'Argumentaire et les modules sont **gelés à l'usage externe** jusqu'à la clôture de
> ce mandat et sa revue visuelle.

## 0 · Le problème, en une phrase

Quatre consommateurs de `compute_bilan` calculent une charge d'**opération neuve** à partir du
**prix de sortie de l'EXISTANT** (`sector_price`, ~2 265 €/m²). On ne vend pas du neuf au prix de
l'ancien : c'est une **erreur d'instrument**, pas un défaut de branchement. L'écart au vrai prix
de sortie (appartement de marché, 4 275 à 4 953 €/m² sur les 5 communes couvertes) est **du simple
au double**. La fiche a été corrigée (`resolve_prix_neuf_marche`, préséance, « non calculable » hors
5 communes) ; ces quatre-là non.

## 1 · Pourquoi c'est plus grave que « un branchement oublié »

1. **L'Argumentaire de négociation est touché.** C'est l'un des trois exports uniques du produit,
   et il fonde une **contre-offre** sur une charge bâtie avec le mauvais prix de sortie. Un client
   s'en sert pour négocier un prix d'achat : une charge sous-évaluée d'un facteur ~2 lui fait rater
   ou casser une affaire. C'est un faux chiffre servi dans un document de décision.
2. **L'incohérence entre écrans revient.** La fiche dira « non calculable » ; le Copilote affichera
   un chiffre pour la même parcelle. C'est le **×2,07 d'hier sous une autre forme** — et c'est ce
   qui se voit le plus vite devant un comité (« pourquoi deux nombres ? »). Un produit qui dit « je
   ne sais pas » sur un écran et sert un chiffre sur l'autre ne dit rien du tout.

## 2 · Les 4 consommateurs (sites d'appel repérés à l'audit de l'application)

| Consommateur | Site | Prix utilisé aujourd'hui | Passe bilan_params ? | Filtrant ? |
|---|---|---|---|---|
| **Copilote** (note marché par retenue) | `src/labuse/copilote/moteurs.py:385` | `sector_price` (existant) | non | **Non** (« PAS un filtre » — vérifié) |
| **Rapport de potentiel** (SENS 1) | `src/labuse/api/modules.py:815` | `sector_price` | non | Non (`bilan=None` non bloquant) |
| **Explication IA** (facts bilan) | `src/labuse/api/modules.py:943` | `sector_price` + défauts calculette | oui (cout/marge, PAS prix) | Non |
| **Banquier + Argumentaire** (PDF) | `src/labuse/api/briques_pdf.py:244` (→ `banquier.py:70`) | `sector_price` + `bilan_params_defaut()` | oui (cout/marge, PAS prix) | Non (`if bilan.charge_fonciere` → sinon fait omis) |

Référence à répliquer : **la fiche** (`faisabilite/db.py`, `resolve_prix_neuf_marche` + branche
« non calculable » servie). La **calculette** (`compute_calculette`) est HORS périmètre a priori
(le prix y est SAISI par l'utilisateur, pas `sector_price`) — à confirmer en phase A, pas à router.

## 3 · Méthode (phases, points d'arrêt)

### A — MESURE D'ABORD (bloquante, lecture seule)

Pour **chacun des 4 consommateurs**, sur les **5 communes couvertes** (Saint-Denis, Saint-Pierre,
Saint-Paul, Saint-Leu, Le Tampon) :
- l'**écart de charge** entre `sector_price` (actuel) et `resolve_prix_neuf_marche` (cible), à
  méthode et hypothèses identiques par ailleurs (mêmes échantillons seedés `m26-hyp` que le
  back-test, reproductibles) ;
- le **nombre de verdicts de viabilité qui s'inversent, et dans quel sens** (attendu : le prix neuf
  étant supérieur, la charge MONTE → des « non viables » repassent viables ; l'inverse doit être
  rare et s'expliquer). Distribution des écarts, pas une moyenne.

### B — LA QUESTION DE FOND, à trancher SUR PIÈCES (avant de router quoi que ce soit)

**`sector_price` est-il utilisé ailleurs à bon escient ?** Le prix de l'existant est le **bon**
instrument pour estimer la **valeur d'un bien existant** (comparables DVF, « prix probable du
foncier », affichage marché) ; il n'est **faux que pour le prix de sortie d'un bilan d'opération
NEUVE**. La MÊME fonction sert donc deux usages ; il faut les **distinguer** :
- **Usage LÉGITIME (garder `sector_price`)** : blocs « comparables / marché » (`out["prix_dvf"]`,
  `out["marche"]`, la bande de points, la volatilité/tendance), le « prix probable du foncier ».
- **Usage FAUX (router vers `resolve_prix_neuf_marche`)** : le **prix de sortie** injecté dans le
  bilan à rebours (`compute_bilan`).

Livrable B : la **cartographie de tous les appels `sector_price`** (`grep` exhaustif, méthode
`constructible_neuf`), chacun étiqueté « valeur de l'existant » vs « prix de sortie neuf ». On ne
route QUE les seconds. Point d'arrêt Vic sur cette cartographie avant toute écriture.

### C — ROUTAGE + « non calculable » sur les 19 communes

- Router les 4 consommateurs sur `resolve_prix_neuf_marche` (préséance override bassin sourcé >
  dvf secteur > dvf commune > non calculable) — idéalement via UN point de résolution partagé, pour
  qu'aucun futur consommateur ne retombe sur l'ancien piège.
- **Sur les 19 communes non couvertes, adopter le MÊME « non calculable » que la fiche**, avec les
  **formulations par cas déjà gravées** (`dvf_prix_neuf.motif_non_calculable` : social dominant /
  marché non observable ; patrimonial build-to-hold = motif d'opération). Non-filtrant partout : la
  parcelle est servie AVEC la mention, jamais écartée (M26-A). Une charge n'est JAMAIS affichée là
  où la fiche dit « je ne sais pas ».

### D — VÉRIFICATION VISUELLE des deux PDF (avant merge, exigence Vic)

**Banquier et Argumentaire exigent une revue visuelle** avant merge — même discipline que les
revues O12 et M26-B (PDF joints à la revue). Vérifier : (1) une parcelle des 5 communes → charge au
prix neuf, cohérente avec la fiche à l'euro ; (2) une parcelle des 19 communes → mention « non
calculable » (bonne formulation), aucun chiffre de charge, dossier toujours généré (non écarté).

## 4 · Question bloquante — les tiers bougent-ils ? score_e est-il affecté ?

Preuve par les maillons, pas par supposition (comme aux tours précédents) :
- **Tiers** : ces consommateurs écrivent-ils dans `parcel_p_score_v2` ? (attendu : non ; l'écrivain
  unique est `scoring/p_v2/pipeline.py`, run épinglé `q_v7_defisc`). À reprouver.
- **score_e** : est-il touché par ce mandat ? (attendu : NON — `score_e` a DÉJÀ été recomposé sur le
  nouvel instrument à l'application précédente ; ce mandat ne touche que les 4 consommateurs de
  `compute_bilan`, pas la table `score_e`). À confirmer.
- **Golden 116/116 + tiers au bit près** (120 / 1031 / 3587 / 72980 / 353945) avant ET après.
  Rappel de la clause d'honnêteté : le golden ne couvre AUCUN champ charge/marge — son PASS garantit
  le périmètre « ne doit pas bouger » (cascade, tiers, zonages, ancres), pas les charges. **Un tier
  bouge d'un bit → arrêt.**

## 5 · Interdits

Router un appel `sector_price` « valeur de l'existant » vers le prix neuf (usage légitime : ne pas
toucher) · afficher une charge de marché sur une commune non couverte · écarter (filtrer) une
parcelle sur une charge non calculable · merger un PDF sans revue visuelle · toucher au coût de
construction (mandat d'après) · recalculer score_e ou un run de scoring.

## 6 · Livrables

`RAPPORT_PRIX_SORTIE_CONSOMMATEURS.md` (mesure A + cartographie B étiquetée + preuve tiers/score_e
+ avant/après golden + PDF de revue Banquier & Argumentaire). Mesures seedées `m26-hyp`,
reproductibles. **Vic merge en `--no-ff`.**
