# RAPPORT M55-D stage 9 — PHASE 2 : la page d'accueil qui prouve

Branche `feat/m55-d-stage9` (phase 1 `55d30c61` + phase 2 `006beae9`), non mergée. Validation Vic
phase 1 appliquée (opérations reconstituées = 2 501 ensembles fonciers · bascules = 573).
tsc 0, vitest 32/32, build vert.

## Backend — `/accueil/chiffres` (cache 1 h)
`src/labuse/api/accueil.py` (router inclus dans app). **Aucun chiffre en dur** : 12 valeurs
mesurées à la requête (cache serveur 1 h) — parcelles du run servi (`Q_A_RUN_LABEL`), communes,
sources connectées, mutations d'entraînement (L2-F 2017-2024), communes calibrées, défisc
actives, permis caducs, ensembles fonciers privés ≥ 3, bascules vers tiers hauts
(q_v7_defisc → run servi) — plus le golden lu du JSON **versionné** (118 parcelles / 777
vérifications). Un chiffre introuvable = `null` → le front le **masque**, il ne l'invente pas.
`RUN_PRECEDENT` documenté (à faire suivre à chaque bascule de run, comme `served_run.txt`).

## Front — trois blocs, trois messages
Titres à la première personne de Vic, conservés :
- **« Je couvre tout »** — 431 663 parcelles notées · 24 communes sur 24 · 52 sources publiques
  branchées. *Rien de l'île ne vous échappe.*
- **« Je ne devine pas »** — appris sur 65 326 mutations réelles (2017-2024) · 23 PLU calibrés
  article par article · 118 parcelles-témoins re-vérifiées avant chaque mise en ligne.
  *Chaque chiffre est traçable à sa source réglementaire.*
- **« Je vois ce que personne ne voit »** — 797 fenêtres de sortie de défiscalisation ouvertes ·
  2 161 permis estimés caducs · 2 501 ensembles fonciers reconstitués — même propriétaire,
  3 parcelles ou plus · 573 parcelles devenues brûlantes ou chaudes à la dernière mise à jour.
  *Des opportunités invisibles ailleurs.*

Chaque chiffre porte son **« i » sourcé** (Tip). L'intro que Vic aime reste en tête — son nombre
devient **dynamique**. Doctrine en pied. **Un seul lien « Commencer → »** (aucun CTA d'analyse,
acquis stage 8). Textes dans `strings.ts` (libellés = fonctions du nombre servi). Ton sobre —
les chiffres parlent.

## Validation
- **Les 10 chiffres affichés == la réponse `/accueil/chiffres`** (test d'égalité automatisé — tous ✓).
- **Grep « rien en dur »** : propre — les seuls nombres restants sont les coordonnées du SVG,
  les années 2017-2024, le seuil de définition « ≥ 3 » et le millésime MAJIC (des définitions,
  pas des counts).
- Titres 3/3 · l'accueil **disparaît après « Commencer »** (prouvé) · **mobile vérifié**.
- Captures `s9_accueil_preuves`, `s9_accueil_mobile`.

## Reste au déploiement
Rien de spécifique (l'endpoint lit la base + le golden versionné). Le responsive (phase 1) est
acté. CC ne merge jamais.
