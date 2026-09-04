# INVENTAIRE T5 — infobulles (+ notes T4 en-têtes, T6 survol) — RETOURS-12

## T5 — infobulles (redondante = à retirer)

| Fichier:Ligne | Contexte | Texte | Redondante ? |
|---|---|---|---|
| map/MapView.tsx:1576-1578 | Pastilles communes carte | `{commune} — {n} parcelles… · ouvrir la fiche commune` | **OUI** (à retirer / ne garder que le fait non affiché) |
| outils/VeillePromoteurs.tsx:223 | Bouton fiche parcelle | `Ouvrir la fiche parcelle` | **OUI** (à retirer) |
| outils/Communes.tsx:127 | Ligne acquisitions | `Ouvrir la parcelle {idu}` | **OUI** (répète le lien affiché sous la ligne — voir O11) |
| projets/ProjetKanban.tsx:97 | Ligne projet | `Ouvrir la fiche · glisser pour décider` | garder (2 affordances) |
| outils/Renouvellement.tsx:69,212 | icône i / titres colonnes | définitions techniques | garder |
| M22Programme.tsx:148, blocB.tsx:179 | formules/colonnes | définitions | garder |
| RadarView.tsx:98 | badge « Sous le marché » | référentiel €/m² | garder (fait non affiché) |

## T4 — en-têtes de tableau sticky

| Fichier:Ligne | Table | sticky ? | fond | z |
|---|---|---|---|---|
| outils/Renouvellement.tsx:206 | Densifier | oui | bg-bg-3 opaque | aucun z |
| outils/ProspectionSolaire.tsx:214 | Solaire | oui | bg-surface-2 opaque | aucun z |
| outils/ModulePanel.tsx:703 | comparatif | oui | bg-surface-1 | aucun z |
| outils/M22Programme.tsx:162 | programme récap | oui | bg-surface-1/95 | z-10 |
| outils/blocB.tsx:171 | Comparaison communes | oui | bg-bg-3 | z-10 |
| admin/Courrier.tsx, Produit.tsx, Destinations.tsx | admin | NON | — | — |

Problème : z-index hétérogène/absent (overlays parent z-40), certaines translucides. Décision : classe/utilitaire commun `sticky top-0 z-20 bg-*` opaque partout.

## T6 — survol/contraste

Racine : `.hover-fill:hover * { color:var(--ink) !important }` (index.css:145) force le
contenu en encre sombre sur vert plein → les chips `bg-mint-bg text-mint` deviennent
illisibles. Cas critique : **Communes.tsx:128** (badge millésime `2024→2025` sur ligne
acquisitions en hover-fill). Correctif au niveau CSS : sur `.hover-fill:hover`, les chips
(`.chip`) reçoivent un fond sombre plein + texte clair (contraste ≥ 4,5:1). Pas de
débordement -mx détecté (à vérifier en recette sur la ligne Saint-Joseph).
