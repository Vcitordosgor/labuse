# FAISABILITE-POLISH-1 — lisibilité du panneau Faisabilité (320 px)

**Branche** `fix/faisabilite-polish-1` (base `main` `a40e1af7`, PAS mergée).
**Périmètre** : mise en page seule. Aucun calcul, aucun texte de fond changé — le panneau lit
toujours l'unique appel moteur (`POST /modules/faisabilite/{idu}/scenario`, FAISABILITE-3).
**DA** : `docs/audit-2026-09/DA-AUDIT-1/CHARTE-DA-1.md`.

Fichiers touchés :
- `frontend/src/components/fiche/constructibilite.tsx` — réécriture de la mise en page de `FaisabiliteTab` (le rendu, pas les données).
- `frontend/src/components/shared/GrilleOutils.tsx` — `GrilleOutils` accepte désormais `cols={2}` (2 × 2).

## Ce qui change

**Grille** — un seul rythme vertical : 24 px entre sections (`gap-6`), 12 px entre lignes d'une
section (`gap-3`), aucune section n'ajoute de padding horizontal (le gutter unique vient du
conteneur). Tous les titres de section passent par `GroupLabel` (capitales espacées, comme la fiche
parcelle). Plus aucun texte tronqué en « … » sauf la ligne de source (§ étapes).

**Verdict** — quatre lignes empilées, jamais mêlées : (1) la phrase seule, taille titre ; (2) une
rangée de chips (Ce qui limite · Règles sourcées · Plancher estimé) ; (3) une ligne de texte gris
(ce qui limite) ; (4) la source PLU en petit. Avant, la chip « Ce qui limite » et son texte
partageaient une ligne et la date PLU était collée aux badges.

**Ce que le PLU permet** — chaque règle = trois lignes empilées : libellé en petites capitales
grises · valeur en clair pleine largeur · ligne source (chip Sourcé/état + « Art. · p. »). Un filet
fin entre les règles. Plus aucune colonne libellé/valeur côte à côte (qui coupait la valeur en deux
à 320 px). Le nom du PLU vit dans l'info « i » du titre, pas dans la ligne.

**Tester un projet** — les deux champs empilés pleine largeur, unité dans le champ (« logements »,
« m² »), libellé au-dessus (avant : deux colonnes serrées).

**Nos hypothèses** — trois champs empilés pleine largeur, unité dans le champ ; « ↻ Revenir aux
valeurs LABUSE » en Bouton lien SOUS les champs (avant : dans le titre).

**Le calcul, étape par étape (8)** — accordéon Chevron de la charte (◀ fermé / ▼ ouvert, chevron
vert), replié par défaut. La valeur chiffrée de chaque étape est `white-space: nowrap` (jamais
coupée) ; seule la ligne de source peut se tronquer.

**Actions du bas** — les 4 boutons (Voir en 3D · Taxe d'aménagement · Comparer · Écrire au
propriétaire) sont des tuiles du composant partagé « Étudier ce bien » (`GrilleOutils`/`OutilCase`,
icône + titre), 2 × 2 à largeurs égales, sans « → ». Le texte « Pré-faisabilité indicative… » reste
en dernier, en petit.

## Captures avant/après (1440 px, panneau entier, 3 témoins)

Dossier `captures/`. Servies par le moteur en base dev (chiffres dev, pas prod) :

| # | témoin | commune / zone | cas | avant | après |
|---|--------|----------------|-----|-------|-------|
| 1 | `97422000BR0332` | Le Tampon · Uc | bâti présent → **2 scénarios** | `avant-1-bati.png` | `apres-1-bati.png` |
| 2 | `97415000BO0843` | Saint-Paul · U1pru | terrain nu, constructible, 8 étapes | `avant-2-nue.png` | `apres-2-nue.png` |
| 3 | `97411000BZ1065` | Saint-Denis · Uh | non constructible (terrain exigu), 7 règles PLU | `avant-3-nonconstr.png` | `apres-3-nonconstr.png` |

## Vérification

- `tsc --noEmit` : 0 erreur.
- `vitest run` : **201 passés** (dont `Faisabilite.test.tsx` 9/9).
- `vite build` : OK.
