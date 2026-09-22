# VEILLE-2 — Page Veille : avant / après (deux blocs)

La page Veille (`frontend/src/components/surveillance/SurveillancePanel.tsx`) a deux portes,
qui SONT les deux chemins du modèle. Le volet « Critères » (recherche sauvegardée) est retiré.

## AVANT (base c83c14a3)

    VEILLE
    ┌─ Le foncier ───────────────┐   ┌─ Les annonces ─────────────┐
    │  onglets : Parcelles │ Critères│  Radar (créer/gérer veilles)│
    │  · Parcelles suivies        │   │  commune (unique)           │
    │  · CRITÈRES : « Créer une   │   │  type · prix min/max        │
    │    veille » (recherche      │   │  surface terrain min        │
    │    sauvegardée, filtres     │   └─────────────────────────────┘
    │    carte, hash)             │
    └─────────────────────────────┘
    + bouton « 🔔 Créer une veille sur cette recherche » DANS les filtres carte (FiltreLabuse)

## APRÈS (feat/veille-2)

    VEILLE
    ┌─ Le foncier (PARCELLE) ────┐   ┌─ Les annonces (RADAR) ─────┐
    │  Parcelles suivies SEULES  │   │  Radar (créer/gérer veilles)│
    │  · barre IDU/adresse       │   │  commune(S) (multi-select)  │
    │    (refus motivé : invalide│   │  type · prix min/max        │
    │     / hors des 24)         │   │  surface MIN / MAX          │
    │  · liste : IDU · commune · │   │  particulier                │
    │    dernier événement ·     │   └─────────────────────────────┘
    │    retirer                 │
    └─────────────────────────────┘
    · plus AUCUN onglet « Critères »
    · plus AUCUN bouton « Créer une veille » dans les filtres carte ni les projets
    · deux chemins, rien d'autre : PARCELLE et RADAR

Diff : volet VoletCriteres supprimé (SurveillancePanel.tsx), bouton data-creer-veille +
mutation saveSearch supprimés (FiltreLabuse.tsx), commune→communes + surface min/max ajoutés
au formulaire Radar. tsc -b vert.
