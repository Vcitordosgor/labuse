# MANDAT RECETTE-4 — les restes, et deux sources qui dorment

**Branche** : `feat/recette-4` depuis `feat/recette-3`. **Worktree** : `~/Desktop/labuse-recette4`.
**Modèle CC** : Fable. **Rapport** : `docs/audit-2026-09/RECETTE-4.md`.

**Garde-fous** : étape 0 (pwd, branche, arbre propre, `.env`) · aucun merge · aucune bascule · aucun rescoring · aucun rebuild de cascade · DA existante · périmètre fermé aux points U1–U9.
**Règle de preuve** : rien n'est déclaré fait sans avoir été **constaté dans un vrai navigateur** (Playwright), contre le backend réel.
**Un commit par lot.**

---

## LOT 1 — Les deux branchements décidés

- **U1** — **Taxe foncière (TFPB, fichier REI).** Ingérée pour 24 communes sur 24, consommée nulle part. La brancher là où elle change une décision :
  - **fiche commune** : le taux communal en vigueur, avec son millésime et sa date d'effet, comme la taxe d'aménagement ;
  - **bilan Financier** : la taxe foncière due pendant la durée de portage entre dans les charges. Si le calcul demande une hypothèse (valeur locative estimée), elle est **dite** et sourcée, jamais devinée en silence.
  - Fiche au registre CIRCUIT, millésime affiché, alerte de fraîcheur comme pour la TA.
- **U2** — **Zonage A/B/C (DHUP).** Aujourd'hui en fiche commune seulement. Le faire descendre :
  - **fiche parcelle** : la zone de tension conditionne les dispositifs (Pinel outre-mer, PTZ, taux de TVA en accession sociale) — c'est une information de parcelle, pas de commune ;
  - **Financier** : là où elle change le régime applicable.
- **U3** — Ces deux sources n'entrent **pas** dans le scoring. Ce sont des informations servies, pas des variables du modèle.

## LOT 2 — Ce que RECETTE-3 a laissé (l'ancien lot 3)

- **U4** — **Financier** : vérifier que le document sort de bout en bout après les correctifs, et que **les 20 questions restantes apparaissent toutes dans le bilan**. Toute question dont la réponse n'apparaît nulle part sort du questionnaire, et le rapport dit lesquelles.
- **U5** — **Courrier propriétaire** : vérifier qu'aucun champ vide ne s'imprime, sur **trois parcelles différentes** dont une sans adresse connue et une détenue par une personne morale.
- **U6** — Reprendre tous les points de RECETTE-2 et RECETTE-3 marqués « à recetter à l'œil » et les **constater au navigateur**. En dresser la liste avec leur état réel.
- **U7** — Archiver la maquette apporteur validée à côté du rapport, comme référence des prochains tours.

## LOT 3 — Préparer le rebuild, sans le faire

- **U8** — DPU, PEB, ravines (DPF) et zones humides sont **affichés** sur la fiche et dans Pièges et risques, mais ne portent **aucun verdict dans la cascade servie** : un client lit « zone humide » sans que le classement en tienne compte. Écrire ce qu'il faut pour que ces quatre motifs entrent au prochain run : les règles de cascade à écrire ou à activer, le seuil de chaque motif (écartement dur ou simple vigilance), et ce que ça changerait en nombre de parcelles écartées.
- **U9** — **Ne rien exécuter** : ni rebuild, ni cascade, ni run. Livrer la note, Vic décide quand la jouer.

---

## Rapport
Un tableau des 9 points : numéro · état · ce qui a été constaté au navigateur · preuve `fichier:ligne` ou capture. U8 est une note écrite en français. Rien n'est mergé : Vic relit, recette, merge.
