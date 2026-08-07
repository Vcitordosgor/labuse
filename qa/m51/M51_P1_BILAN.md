# M51-P1 — Bilan : annuaire PLU (verbatim sourcé) livré

Branche `m51-plu-annuaire` (base main post-M50-SUITE). Boussole tenue : **verbatim sourcé, jamais
une synthèse** ; chaque extrait porte commune/document/article/page PDF/millésime/lien ; le doute est DIT.

## Corpus (P1a) — fetch GPU par idurba, garde d'identité
- **21 communes servables** : règlement écrit opposable récupéré du **Géoportail de l'Urbanisme** par
  idurba, **garde d'identité** (originalName GPU == idurba M40 `plu_millesimes.yaml`, sinon STOP).
  Extraction **ZIP en HTTP Range** — on tire ~1 Mo (la pièce écrite), pas les ~300 Mo du pack
  graphique. **Fidélité prouvée** (sha256 archive == copie locale). Provenance consignée par document
  (url_api, url_archive, fetched_at, sha256) → `corpus_manifest.json`.
- **2 écarts idurba — NON servis (arbitrage Vic)** : **Saint-André (97409)** et **Saint-Leu (97413)** —
  le GPU renvoie une **liste vide** pour leur grid (révision en cours, l'opposable ancien 2019/2007
  n'est pas servi par le endpoint document). Garde respectée : on ne sert pas un règlement non
  réconcilié. → **à réconcilier avec toi** (autre voie que le grid, ou attendre l'approbation).
- **1 RNU** : Saint-Philippe (97417) — pas de règlement communal, dit dans l'outil.

## Ingestion (P1b) — extraits ARTICLE, FTS french
- Table `plu_reglement_extrait` (insee/commune/idurba/millésime/document/zone/article_ref/**page_pdf**/
  texte_verbatim/**doute**/doute_motif/**pagination_ambigue**/source_url/fetched_at/tsv GIN).
- **3 258 extraits, 21 communes**. Granularité **article** (regex multi-format : `Article U 4`,
  `Ua 1`, `1-`, `R111-2`, titres). Citation **page PDF** (fiable ; la page imprimée est ambiguë).
- **doute SERVI** (11 extraits quasi-vides flaggés « vérifier au PDF »). **pagination_ambigue**
  détectée et dite — **Saint-Benoît = True** (double numérotation, bloc annexes p.PDF 49-162).

## Recherche + outil (P1c)
- API `GET /modules/plu-annuaire/search?q=&insee=&zone=` — FTS french, **verbatim + référence
  complète + lien**, aucun résumé. `insee` absent = île entière. `zone` = famille (pour le lien fiche).
- API `GET /modules/plu-annuaire/communes` — état corpus (24) : servable / RNU / révision / non ingéré,
  **réponse honnête**.
- Outil **« Annuaire PLU » (O13)** dans Outils (modèle Vérif procédure) : sélecteur commune (RNU/révision
  désactivées + dites), recherche, résultats = verbatim + article/zone/page PDF/document/millésime/lien
  GPU, **badge doute**, **note pagination ambiguë**. `tsc --noEmit` : 0 erreur.
- **Lien contextuel fiche→annuaire** : `reglement_block` (bloc règlement de la fiche, M9) porte
  désormais `annuaire:{insee,zone}` — la donnée du deep-link vers O13 pour la zone servie.

## Vérification
- **0 tier / golden** : M51 ne touche AUCUN code de run/scoring ; brûlantes servies = **118**
  (compte post-M39 établi, inchangé) ; `plu_reglement_extrait` isolée. App importe (217 routes,
  2 annuaire câblées). Front `tsc` 0 erreur.
- **Captures** : `qa/m51/captures_p1.txt` — recherche verbatim+référence+lien, réponse RNU honnête,
  réponse révision honnête, Saint-Benoît pagination ambiguë servie, lien fiche→annuaire.

## Reste (à ton arbitrage / suites)
1. **Câblage du bouton front fiche→O13** (prefill insee+zone à l'ouverture de l'outil, modèle M22
   prefill) — la donnée est servie, le bouton reste à poser. Petit sliver front.
2. **P2 Saint-Benoît** : les 19 fiches AU (N°01-19, pages PDF 49-162 du `97410_reglement.pdf` ingéré)
   à passer une à une vs la calibration servie ; écarts → liste pour arbitrage (PAS de changement de
   calibration sans STOP). Incertitude modifs n°2/n°3 (M40) reste dite.
3. **Saint-André / Saint-Leu** : réconcilier l'opposable (hors grid GPU) ou attendre l'approbation.
4. **pagination_ambigue** : quelques communes (97406/97412/97418) flaggées par l'heuristique — à
   revoir (possibles faux positifs) ; conservateur (dire l'ambiguïté) plutôt que taire.
