# LE TERMINAL FONCIER — système de design (proposition · Temps 1)

> Refonte visuelle de LA BUSE en **terminal de décision foncière** (registre Linear / Bloomberg),
> ancré Réunion. **Temps 1 = ce système + la FICHE PARCELLE seule**, livré **isolé** (tout scopé sous
> `.sheet`, le reste de l'app inchangé). ⛔ **STOP & VALIDATE** avant déploiement global (Temps 2).

## Anti-cliché (garde-fou du brief)
Le réflexe « outil sombre » = near-black `#0a0a0a` + acid-green `#00ff88`. **Évité.** On s'en distingue
par un fond **océan profond bleuté** et un accent **ambre basalte** (terre volcanique réunionnaise).

## Tokens couleur
| Token | Hex | Rôle |
|---|---|---|
| `--paper` | `#0F1620` | fond fiche — océan profond bleuté (léger dégradé radial en haut-droite) |
| `--paper-2` | `#0B111A` | recess / panneaux enfoncés |
| `--card` | `#18212E` | élévation : cartes, panneaux |
| `--card-2` | `#1F2A39` | sur-élévation : champs, lignes actives |
| `--ink` / `--ink-soft` / `--ink-faint` | `#E6EAF0` / `#AEB9C7` / `#7E8B9C` | texte / secondaire / labels-sources |
| `--rule` / `--rule-2` | `#243042` / `#2E3C50` | hairlines (séparation par filets, pas par boîtes) |
| **`--accent`** | **`#E08A3C`** | **ambre basalte — RÉSERVÉ** : score d'opportunité, actions primaires, eyebrows clés |

### Sémantique des verdicts (donnée, pas déco — lisible à la couleur seule)
| Verdict | Hex | |
|---|---|---|
| POSITIVE / PASS / opportunité | `#4CAF7D` | vert sobre |
| SOFT_FLAG / à creuser | `#D9B04A` | jaune d'avertissement (distinct de l'accent orange) |
| HARD_EXCLUDE / faux positif | `#D9534F` | rouge sobre |
| UNKNOWN / exclue | `#6B7787` | gris neutre |

## Typographie (3 rôles, polices **vendorisées / offline-safe**)
- **Données & chiffres-clés → IBM Plex Mono** (nouvellement vendorisé, 400/500/600). **Toutes** les
  valeurs numériques en chasse fixe (`tnum`/`zero`) → alignement au pixel = confiance. Eyebrows et
  libellés de verdict en mono capitales tracées (registre « readout »).
- **Prose → Inter** (déjà vendorisé) : gloses, synthèse métier, explication de l'assistant.
- Fraunces (serif) est **retiré de la fiche** (trop éditorial pour un terminal).
- Échelle intentionnelle : score 58px · verdict 27px caps · titres data 20-30px · corps 13px · labels 10-11px.

## Élément signature
**Le score d'opportunité** : chiffre-roi en **grande chasse mono ambre** (58px), dans un panneau à
filet ambre, avec le **score de complétude** plus discret qui le qualifie. C'est ce qu'on retient de
la fiche — l'ambre marque toujours « le score d'opportunité ».

## Principes appliqués
Donnée = héros · densité maîtrisée (rythme 4/8px) · **hairlines** plutôt que boîtes lourdes ·
hiérarchie par typo+espace avant couleur · mouvement sobre (`prefers-reduced-motion` respecté) ·
focus clavier visible (liseré ambre) · copy côté promoteur (« Propriétaire », pas `owner_type`).

## Périmètre & garanties (Temps 1)
- **Refonte visuelle uniquement** : `terminal.css` (nouveau) + 3 woff2 + `@font-face`. **Aucune** ligne
  de logique, d'endpoint, ni de HTML de rendu touchée. **288 tests verts**, ruff clean.
- **Isolation stricte** : tous les sélecteurs sont scopés `.sheet…` → sidebar, carte, pipeline,
  comparateur **inchangés**. Rollback = retirer le `<link>` de `terminal.css`.
- Contraintes conservées : **offline-safe** (polices auto-hébergées, zéro CDN à l'exécution), Leaflet
  vendorisé, aucune dépendance lourde. Saint-Paul inchangé.

## ⛔ STOP — décision attendue
Valider la **direction** (palette, mono, score-signature, sémantique verdicts) sur la fiche avant le
**Temps 2** = application aux autres vues (carte/radar, veille, comparateur, pipeline, accueil) avec
les **mêmes tokens**, responsive, focus visible, tests verts, démo 8/8.
