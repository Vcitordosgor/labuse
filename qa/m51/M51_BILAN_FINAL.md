# M51 — BILAN FINAL : annuaire PLU interrogeable + Saint-Benoît (CLOS)

Branche `m51-plu-annuaire` (base main post-M50-SUITE `b3ee2a17`). **Rien mergé — la main revient à Vic.**
Boussole tenue de bout en bout : **verbatim sourcé, jamais une synthèse** ; commune/document/article/
page PDF/millésime/lien sur chaque extrait ; le doute est DIT ; découverte hors cadre → STOP.

## P0 — Inventaire (arbitré → GO)
6/24 PDF exploitables en local, 21 YAML de citations, 15 re-fetchables GPU. Archi FTS+article+page PDF
validée (pas d'embeddings = hors boussole). Arbitrages Vic reçus.

## P1 — L'annuaire (livré)
- **Corpus** : **21 communes** — règlement écrit opposable **fetché du GPU par idurba**, **garde
  d'identité** (originalName GPU == idurba M40, sinon STOP), extraction **ZIP en HTTP Range** (~1 Mo
  vs 300 Mo), fidélité sha256 prouvée. **2 écarts idurba** (Saint-André 97409, Saint-Leu 97413 : GPU
  liste vide, révision) → **on attend l'approbation** (veille trimestrielle M41 les complètera). 1 RNU.
- **Ingestion** : `plu_reglement_extrait`, **3258 extraits article**, FTS french (GIN), citation **page
  PDF**, `doute` servi, `pagination_ambigue` détectée (Saint-Benoît = True).
- **Recherche + outil** : API `/modules/plu-annuaire/{search,communes}` (verbatim+réf+lien, RNU/révision
  honnêtes) ; **outil O13 « Annuaire PLU »** ; **bouton fiche → O13** (commune+zone pré-remplies).
- Provenance : `qa/m51/corpus_manifest.json`. Captures : `qa/m51/captures_p1.txt`.

## P2 — Saint-Benoît (lecture, mesures, rien appliqué)
18 fiches AU lues une à une (N°04 absente). Les 4 mesures (`M51_P2_SAINT_BENOIT.md §MESURES`) :
1. **Recul voirie** : déjà servi (5 m défaut) ; 17/18 fiches à 3 m = conservateur ; seul N°02 (AUb2)
   à 10 m sous-recul → **4 parcelles réserve**, marginal.
2. **Régime 1AU** : **pas d'écart** — Saint-Benoît raccordé (`parcel_au_statut` : 237
   `conditionnelle_operation` + 12 `declasse_au_fermee`).
3. **N°04 absente** → liste mairie (avec modifs n°2/n°3).
4. **PPR R1** : couche active, **pas de trou** — 0 parcelle AU servie en R1 (AUb14 déclasse 3 ;
   AUb7/AUb19 servies hors R1).

### Exception différée consignée (décision Vic)
**AUb2 Bourbier — recul voirie 10 m vs 5 m servi.** **AUCUNE entrée `zones:{AUb2}`** (effet de bord
au_statut disproportionné). Consignée au **registre des exceptions `config/exceptions_calibration.md`
(AK1442-01)** + pointeur dans l'en-tête `config/plu_saint_benoit.yaml`. Correction **différée** à la
prochaine calibration Saint-Benoît (rouverte par les modifs n°2/n°3). **4 IDU pour retrouvabilité** :
`97410000AE0025` · `97410000AE0027` · `97410000AE0250` · `97410000AE0251` (toutes `reserve_fonciere`).

## Vérification
- **0 tier / golden** : M51 ne touche aucun code de run/scoring ; brûlantes servies **118** (inchangé) ;
  `plu_reglement_extrait` isolée ; app importe (routes annuaire câblées). Front `tsc` 0 erreur.
- Captures verbatim+référence+lien, RNU honnête, révision honnête, Saint-Benoît pagination ambiguë,
  lien fiche→annuaire.

## Reste (post-merge, hors M51)
- Réconciliation 97409/97413 à l'approbation (auto, veille M41).
- Revoir `pagination_ambigue` possibles faux positifs (97406/97412/97418) — conservateur, non bloquant.
- Modifs n°2/n°3 Saint-Benoît + fiche N°04 : liste mairie (main Vic).

## Commits (branche `m51-plu-annuaire`)
`a3a0f15e` P0 · `67cb43a4` P1a/b · `826e388a`/`4fb7817f`/`bd613640` P1c · `5eb25c87` bilan P1 ·
`44764a0d` bouton fiche · `3706b1a1` P2 écarts · `2113f58a` P2 mesures · + registre exception (ce commit).

**M51 CLOS. Golden 117/117 · 0 tier · main à Vic pour le merge.**
