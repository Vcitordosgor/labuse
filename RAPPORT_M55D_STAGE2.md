# RAPPORT M55-D — PHASE 2 stage 2 (fusion des filtres) : LIVRÉ

Branche `feat/m55-d-filtres-ui` (base `main` = M55-D phase 1 + stage 1 mergés). Ajustement Vic :
**pas de contrôle « Mode d'analyse » au header** — le mode (interrupteur Analyse LABUSE + curseur
Mode B) reste dans le panneau, sobrement. Front seul, `filters` unique, moteur non touché.

## Livré
- **Header** : `AddFilter` (la 2ᵉ banque complète) → **« Filtres (N) »** : badge **N =
  `countActiveFilters`** (tous les filtres actifs, mode exclu) + **3 rapides** validés
  (Verdict / Surface / SDP) + **« Tous les filtres → »** qui révèle le panneau (`setVerdict`).
  Les critères experts (Déclassées, Potentiel, événement, veille, hors-copro, flags) **retirés du
  header**. `CheckRow` supprimé.
- **Panneau unique** (`FiltreLabuse`) : rapatriement des critères qui n'existaient QUE dans le
  header — section **« Verdict, potentiel & signaux »** (Verdict·tiers + Déclassées·motif +
  Potentiel ≥ + Avec événement + Masquer copro). **Aucun critère ne disparaît.**
- **Pré-réglages MARQUÉS** : libellé « cochent des filtres visibles, à défaire un par un » +
  puces à bordure tiretée ; au clic ils posent des critères visibles dans le panneau (le
  `ProfilSelecteur` « Vous cherchez ? » reste, idem).
- **Reset séparé** : « Réinitialiser les filtres — le mode d'analyse reste » (ne touche plus
  `analyseLabuse` ni le curseur Mode B). Tri ≠ mode.
- **`vite.config`** : `/filtre` ajouté au proxy dev — **manquait** (seul `/filters` y était), le
  compteur était 404 en `npm run dev` (pré-existant, même classe que `/adresses` en M55-B).

## Validation (non-régression)
- **Compte /filtre IDENTIQUE avant/après sur 5 combinaisons** (Saint-Paul, q_v8_calibre), piloté
  par URL → app → /filtre : C1 surface≥2000 = **9822** · C2 tiers=chaude = **188** · C3 sdp≥500 +
  constructible = **1710** · C4 flags=pente + zonage=U = **3770** · C5 analyse coupée = **51129**.
  Tous **OK**.
- **URL ancienne compatible** : `#f=1&tv=chaude&smin=2000` applique bien les DEUX clés historiques
  → 17 (chaude ∧ surface≥2000), identique à l'API.
- **Badge N** : `#f=1&smin=2000&fl=pente&tv=chaude` → bouton « Filtres **3** ».
- tsc 0, **vitest 29/29**, build vert. Captures `header_filtres_popover` · `panneau_unique` ·
  `preset_applique` · `mobile` (panneau utilisable en 390 px).

## Un critère = un seul endroit
La 2ᵉ banque (header) n'existe plus : le header ne porte que 3 raccourcis (Verdict/Surface/SDP,
mêmes champs du store) + le bouton vers LE panneau unique. Tous les autres critères vivent une
seule fois, dans le panneau. Le mode d'analyse est distinct (dans le panneau), reset séparé.

## Reste (mineur, hors périmètre strict de la fusion)
- « Mes vues » : la persistance complète (stage 1) fait qu'une vue capture désormais tri + mode ;
  un libellé explicite « capture aussi le mode » pourrait être ajouté (cosmétique).
CC ne merge jamais.
