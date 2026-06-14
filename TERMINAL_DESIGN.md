# LE TERMINAL FONCIER — système de design (v3)

> Source unique de vérité : **`src/labuse/api/web/terminal.css`**. `:root` = la variante SOMBRE
> (conservée pour réversibilité) ; `.sheet` = le **thème CLAIR « dossier »** validé pour la fiche.
> Toute valeur dérive des tokens — **aucune valeur magique** ailleurs.

## v3 — La fiche passe en CLAIR + jauge circulaire (le reste de l'app reste sombre)
- **Effet** : l'app de prospection est sombre (salle de marché) ; la fiche s'ouvre comme un
  **dossier clair** (rapport d'expertise) — fiche **élargie de 30 %** (728 px), ombre portée qui
  la détache du radar sombre.
- **Signature = jauge circulaire** (`renderGauge`) : anneau SVG dont la **couleur = le verdict**
  (vert / ambre / rouge / gris) et le **remplissage = le score réel** (`stroke-dashoffset`). Lisible
  d'un coup d'œil sur les 4 verdicts. La complétude devient une **métadonnée** discrète à côté.
- **Palette claire** : fond papier `#F7F5F0`, cartes `#FFFFFF`/`#FCFBF8`, encre `#2C2C2A`, hairline
  `#E2DDD2`. **Accent actions = bleu encre `#234E78`** (registre cadastre/tampon administratif —
  remplace l'ambre ; les verdicts gardent vert/ambre/rouge). Données en **mono** = relevé imprimé.
- **Verdicts** : version TEXTE assombrie (AA sur papier) + version VIVE (anneau de jauge, pastilles).
- **3D** : gabarit en **terre chaude** sur le papier (ressort, évoque le volume bâti).
- **Contrastes ≥ AA** vérifiés (min 4.70). **Réversibilité** : réécrire le bloc `.sheet` vers les
  tokens `:root` rebascule la fiche en sombre, zéro casse.
- Périmètre : **fiche uniquement** — carte, radar, sidebar, pipeline restent **sombres**.

## Fondations (inchangées depuis v2)

## Couleur — sémantique stricte (§2.A)
| Token | Hex | Usage EXCLUSIF |
|---|---|---|
| `--tf-bg` / `--tf-surface` / `--tf-surface-2` | `#0F1620` / `#18212E` / `#202C3C` | 3 profondeurs de surface, pas plus |
| `--tf-text` / `--tf-text-2` / `--tf-text-3` | `#E8ECF2` / `#AEB9C7` / `#8693A4` | 3 niveaux de texte (tous ≥ AA) |
| `--tf-border` | `#2A3645` | **hairline unique** |
| **`--tf-accent`** | **`#E89A4E`** | **RÉSERVÉ** : score d'opportunité + actions primaires. Rien d'autre. |
| `--tf-positive` / `--tf-flag` / `--tf-exclude` / `--tf-unknown` | `#5CC08C` / `#E0BC5A` / `#DD6A66` / `#7D8A9B` | **verdicts uniquement** (POSITIVE / SOFT_FLAG / HARD_EXCLUDE / inconnu) |

- **Badges méta** (« indicatif », « EPSG:2975 », « non calibré ») → **gris discret** (`--tf-surface-2` + `--tf-text-3`), jamais d'ambre.
- **Contraste** : toutes les combinaisons texte/fond vérifiées **≥ AA** (min mesuré 4.52:1).

## Typographie — 1 police par usage (§2.B), zéro serif
- **Titres & prose → Inter** (`--font-ui`). Fraunces banni de l'interface-outil.
- **Données chiffrées → IBM Plex Mono** (`--font-mono`) : scores, €, m², coordonnées, réf. cadastrale.
- Échelle nommée : `--fs-display 54` · `h1 22` · `h2 18` · `body 13` · `small 11.5` · `micro 10.5`.

## Espacement (§2.C) & Radius (§2.D)
- **Espacement** multiples de 4 : `--sp-1..8` (4/8/12/16/24/32). Rythme vertical homogène entre sections (`--sp-6`).
- **Radius** = 3 valeurs : `--radius-card 12` (panneaux) · `--radius-control 8` (cartes/boutons/champs) · `--radius-pill` (pastilles).

## Signature — le score d'opportunité (§2.E)
Grand chiffre **mono ambre** (`--fs-display`), **isolé** sur `--tf-surface`, **sans cadre ambre** (le
chiffre porte l'accent, pas le contour) et **sans barre verte** (le vert = verdict). La **complétude**
est secondaire : plus petite, en texte neutre, avec une fine jauge neutre — elle *qualifie* le score,
elle ne rivalise pas.

## Étape 2 — livré
- `terminal.css` réécrit autour du système (`:root` = référence ; `.sheet` mappe ses tokens locaux
  ET les tokens globaux qui fuyaient vers la référence).
- **Fiche** : en-tête, signature, lectures (verdicts à la couleur), capacité (cartes alignées), 3D
  (données neutres), promoteur, badges méta gris.
- **Bilan** (correction n°1) : **entièrement migré en sombre** — titre lisible, 3 stat-cards
  identiques à la capacité, tableaux sombres, bandeaux « non fiable / prix fragile » en
  avertissement sombre, panneau de calibration cohérent.
- **288→290 tests verts**, ruff clean, isolation stricte (reste de l'app inchangé).

## ⛔ Étape 3 (après validation) — propagation
Mêmes tokens sur : carte/radar (bandeau « verdicts partiels », stat-cards, légende), veille,
comparateur, **pipeline** (supprimer le serif du titre), modale démo (serif → Inter), sidebar.
Responsive, focus visible, `prefers-reduced-motion`, démo 8/8.
