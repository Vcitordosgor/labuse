# LA BUSE — Design System (référence)

> Source unique de vérité pour l'UI. Deux mondes assumés : **app sombre** (radar/carte, sidebar,
> pipeline, démo) et **fiche claire** (dossier d'expertise qui s'ouvre sur le sombre). Tout dérive
> des tokens ci-dessous — aucune valeur magique en dur.
>
> Fichiers : `styles.css` (`:root` = monde sombre), `terminal.css` (`:root` tokens `--tf-*` +
> bloc `.sheet` = fiche claire). Polices vendorisées (offline-safe) : `fonts.css`.

## 1. Couleur

### Monde sombre — `:root` (styles.css)
| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#0B1118` | fond app |
| `--panel` / `--panel-2` | `#111A24` / `#151F2B` | sidebar / cartes |
| `--line` | `#263241` | bordures |
| `--txt` / `--muted` | `#F4EFE4` / `#9BA6B3` | texte / secondaire |
| `--gold` / `--gold-soft` | `#D6B36A` / `#e8d2a3` | or LA BUSE (accent, actions) |

### Fiche claire — `.sheet` (terminal.css)
| Token | Hex | Usage |
|---|---|---|
| `--tf-bg` / `--tf-surface` / `--tf-surface-2` | `#F7F5F0` / `#FFFFFF` / `#FCFBF8` | 3 profondeurs |
| `--tf-text` / `--tf-text-2` / `--tf-text-3` | `#2C2C2A` / `#5F5E5A` / `#6F6E67` | 3 niveaux de texte (≥ AA) |
| `--tf-border` | `#E2DDD2` | hairline |
| `--tf-accent` / `--tf-gold` | `#846A22` / `#D6B36A` | or (texte AA / fond bouton) — **jamais de bleu** |

### Verdicts — sémantique stricte (les MÊMES partout : légende, carte, KPI, pastilles, fiche)
| Verdict | Sombre base (`--opp`…) | Sombre texte (`--*-soft`) | Clair (`--tf-positive`…) |
|---|---|---|---|
| Opportunité | `#2DBE87` | `#6BCF9C` | texte `#0F6E56` · vif `#1D9E75` |
| À creuser | `#C88422` | `#E0B65E` | texte `#854F0B` · vif `#C8841A` |
| Écartée / risque | `#D76055` | `#E78D7F` | texte `#A32D2D` · vif `#E24B4A` |
| Exclue / non évaluée | `#7C8694` / `#9BA3AF` | `#AAB2BD` | `#6E6D67` (gris) |

> **base** = remplissage carte / filet de pastille ; **soft** = le MÊME verdict en *texte* lisible
> (≥ AA) sur surface sombre. Une seule source : chips, légende, tooltips et Kanban tirent tous des
> tokens — aucune valeur de couleur en dur. Hors verdict : `--warn #E0B65E` = rappels / urgence
> temporelle (jamais une couleur de verdict).

**Règle** : l'accent (or) = score + actions primaires ; les couleurs verdict = **données uniquement** ;
badges méta = **gris discret**. Contrastes texte ≥ **AA** (4.5:1) vérifiés.

## 2. Typographie (vendorisée, zéro serif d'interface)
- **Inter** — titres + corps + prose (`--font-ui`).
- **IBM Plex Mono** — **toutes les valeurs chiffrées** (scores, €, m², coordonnées) → alignement = confiance.
- Fraunces : réservé au wordmark de marque, jamais aux titres d'interface.
- Échelle fiche : `--fs-h1 20` · `h2 16` · `body 12` · `small 11` · `micro 10` (densité −10 %).

## 3. Espacement · Radius
- Espacement multiples de 4 : `--sp-1..8` (4/8/10/14/20/28, densifié).
- **3 radius** : `--radius-card 12` (panneaux) · `--radius-control 8` (boutons/champs) · `--radius-pill` (pastilles).

## 4. Composants (CSS/JS)
| Composant | Sélecteur · fonction |
|---|---|
| **AppLoader** | `.app-loader` — couvre la carte au boot |
| **EmptyState** | `updateEmptyState()` — filtré vs « radar en préparation » + actions |
| **QuickFilters** | `.quick-filters .qf` — statut, sélection unique, actif or |
| **PremiumAlert** | `.banner` — « transparence méthodologique » |
| **PromoterNote** | `renderNotePromoteur()` · `.note-pro` / `.mc` — décision + 8 cartes métriques |
| **VerdictBadge** | `.chip.<status>` · jauge `.g-arc` (anneau = verdict, rempli = score) |
| **MetricCard / StatCard** | `.mc` · `.fc` |
| **AuditAccordion** | `.audit-head` + `<details>` (`.faisa-calc`, `.pm-detail`, `.cascade`) |
| **ActionPanel** | `.fiche-actions` — CTA vert « Ajouter au pipeline » + `.fa-more` (exports) |
| **PropertyStatus** | `.pm-status` — statuts courts + « Voir détails » |
| **SourceBadge** | `.src-summary` + `.src-chip` — « N analysées · X répondu · Y à vérifier » |
| **PipelineColumn** | `.kb-col` — accent d'entonnoir piloté par `tone` (config `pipeline.yaml`) : cold→warm→hot→reject, cap + pastille (`--col-accent`, gold = progression) |
| **PipelineCard** | `kbCard()` · `.kb-card` — réf · verdict · score · proprio · action |
| **DemoGuideModal** | `renderDemoStatus/Panel()` · `.dp-*` / `.ds-*` (commandes en détail développeur) |

## 5. Micro-copy (langage promoteur)
« Écartée » (≠ faux positif) · « Bilan à calibrer » (≠ non fiable) · « Traçabilité des sources »
(≠ cascade) · « Sources non disponibles · à vérifier » (≠ silencieuses) · « Signal positif, mais
potentiel limité seul » (≠ déclassée). Ton : foncier, sérieux, premium ; jamais « log technique ».

## 6. Garde-fous qualité
Responsive desktop/tablette ; focus clavier visible (`:focus-visible` or/ambre) ;
`prefers-reduced-motion` respecté ; offline-safe (polices + Leaflet vendorisés) ; AA partout.
