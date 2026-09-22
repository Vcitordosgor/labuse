# RAPPORT M61 — Bloc Analyse : repli, synthèse IA, doublons, en-tête, accueil

Branche `feat/m61-bloc-analyse` (depuis `main` = `c1155fa2`, qui contient M65 mergé par Vic).
Commit unique **NON mergé** (doctrine : CC ne merge jamais). Parcelle de référence 97410000AE0773 (Saint-Benoît).

## Précondition — note
Au démarrage, M65 n'était pas encore dans `main`. Pendant la clarification, **Vic a mergé M65 dans
`main`** (`c1155fa2` « Merge branch 'feat/m65-passe-visuelle' »). La branche M61 est donc bien issue
de `main` AVEC M65 — le point 6 (retrait du halo M65, bouton « Découvrir LABUSE IA ») est réalisable.
Choix Vic : « Depuis main ».

## Points livrés (présentation uniquement — aucun calcul, aucun score touché)

**P1 — Synthèse IA (priorité).** Le bug « à côté » venait de `.ia` (rangée flex) : `SyntheseIA`
rendait son résultat DANS la rangée, coinçant « Poser une question » en colonne. Refonte : un état
`iaOuvert` (`aucun` | `question` | `synthese`) au niveau de la fiche ; le panneau actif **REMPLACE**
la rangée des 2 boutons, pleine largeur, avec **« Replier »** qui ramène les boutons. Markdown rendu
par `renderRich` (même moteur que l'AskBar) → les gras s'affichent en gras, plus d'astérisques (vérifié :
« **Bâti / libre** », « **Économie indicative** » en gras). La mutation Synthèse (`syntheseM`) vit sur
la fiche → **replier puis rouvrir ne relance AUCUN appel** (mutate seulement si `!data && !isPending`).
« Poser une question » (AskBar) passe aussi pleine largeur (remplace la rangée, son « ✕ fermer » = Replier).

**P2 — Bloc Analyse repliable.** La carte verdict devient un TIROIR : en-tête cliquable
`data-analyse-toggle` (« Analyse LABUSE » + verdict au repli + chevron ⌃/›), corps repliable. État par
parcelle/session `store.analyseReplie[idu]` (jumeau de `verdictRevele`), **déplié par défaut**.
**INDÉPENDANT de l'accordéon exclusif** des 7 tiroirs (état propre, ≠ `ficheTiroir`/`FicheAccordionCtx`)
→ le replier/déplier ne ferme aucun autre tiroir. Le verdict n'apparaît dans l'en-tête qu'au repli
(évite de dupliquer le badge hero du corps).

**P3 — Doublon PLU.** Pastilles « constructible {zone} » et « N vigilance » RETIRÉES du bloc Analyse
(doublon au mot près des tiroirs Urbanisme/Risques). Le seul chip conservé = « signal proprio » (violet,
n'existe nulle part ailleurs à ce niveau). La faute « 3 vigilance » disparaît avec la pastille ; le tiroir
Risques pluralise déjà correctement (`vigilance{s}`).

**P4 — Renouvellement regroupé.** Le rang « Renouvellement — rang X/Y » porte désormais son
`▶ Pourquoi ce rang` dépliable JUSTE À CÔTÉ (`<details data-renouv-pourquoi>`, même mécanique que
« Pourquoi ce score »). L'ancienne section basse `data-analyse-renouv` est SUPPRIMÉE, son contenu
(explication + jauges de composantes + MicroTriple + source) absorbé dans le dépliant.

**P5 — En-tête de fiche.**
- Adresse COPIABLE : texte sélectionnable (`.addr` en flex, `user-select:text`, aucun `user-select:none`)
  + icône « copier » discrète (composant `CopyIdu` généralisé avec libellés paramétrables,
  `data-fiche-copy="adresse"`).
- « Voir sur Pages Jaunes ↗ » en JAUNE `--pj-jaune #F5C518` (nouveau token, seul jaune autorisé de
  l'app), `cursor:pointer` + soulignement au survol. Vérifié : `color = rgb(245,197,24)`.

**P6 — Accueil (hors fiche).**
- (a) Halo respirant M65 RETIRÉ : calque `.accueil-halo`, keyframes et règle `prefers-reduced-motion`
  supprimés ; le conteneur `data-accueil` repasse en fond plat #0A0C0B (plus de `relative`/`z-10`). Vérifié : `.accueil-halo` absent du DOM.
- (b) Bouton mauve « **LABUSE IA** » (verbe « Découvrir » retiré, étincelles conservées). Les 2 boutons
  tiennent sur UNE ligne, sans retour à la ligne (`whitespace-nowrap`), largeurs égales (flex-1), gap 9px.
  Vérifié : même hauteur (49px) et même Y pour les deux boutons.

## Report DA
- `docs/DA-FICHE-v6.html` : lien PJ jaune dans la maquette + 6 lignes VALEURS CLÉS (Pages Jaunes,
  adresse copiable, bloc Analyse tiroir, synthèse panneau, Renouvellement dépliant, doublon PLU retiré).
- `docs/DA-LABUSE.html` : token `--pj-jaune #F5C518` (SÉMANTIQUE) ; bloc accueil mis à jour (halo RETIRÉ,
  bouton « LABUSE IA », 2 boutons 1 ligne).

## Garde-fous (tous verts)
- `tsc` 0 · `vitest` 32/32 · `build` vert.
- **Console 0 erreur** sur les 4 parcelles M55-O (97408000AP1647, 97409000AR1260, 97411000HM0273,
  97407000AI1821) + AE0773 — analyse révélée + tiroir Analyse basculé + synthèse ouverte.
- **Exports PDF → 200** : `/parcels/{idu}/export.pdf?source=q_v8_calibre` (premium) et
  `/parcels/{idu}/export?format=onepager` = 200 (AE0773, AP1647).
- Accordéon exclusif des 7 tiroirs non régressé (le tiroir Analyse a un état séparé).
- Verdict à la demande non régressé (le CTA `data-demander-analyse` garde le geste ; rien calculé avant clic).

## À signaler
- **DA-FICHE-v6.html maquette** : la ligne `.band` « Marché peu actif à Sainte-Marie » (l.146) est un
  résidu du composant retiré en M65 P1 — divergence PRÉEXISTANTE (M65 n'avait mis à jour que DA-LABUSE).
  Laissée telle quelle (hors périmètre M61) ; à nettoyer dans une passe DA.
- `data-fiche-copy-idu` renommé `data-fiche-copy="idu"` (aucune référence externe trouvée en QA/tests).

## Captures
`reports/m61/captures/` : `accueil-apres.png` (halo retiré, 2 boutons 1 ligne « LABUSE IA »),
`entete-apres.png`, `analyse-deplie-apres.png` (tiroir + Renouvellement regroupé + pas de doublon),
`analyse-replie-apres.png` (verdict dans l'en-tête), `entete-analyse-contexte-apres.png` (Pages Jaunes
jaune + tiroir Analyse), `synthese-apres.png` (markdown gras rendu, pleine largeur, Replier).
