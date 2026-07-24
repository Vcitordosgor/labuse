# M15 — LOT A3 : refonte de l'outil « Matching promoteurs » (M19)

**Branche** : `fix/m15-a3-matching` · Build 0 erreur · Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuves `qa/m15/A3/`.

## Diagnostic (déjà posé en LOT A)
UI confuse : 3-4 sections empilées sans hiérarchie, **cartes profil/promoteur non cliquables**, et surtout **mélange DÉMO (illustratif) / RÉEL (SITADEL)** — le client pouvait douter de ce qui est réel.

## Refonte (spec Vic)
1. **DÉMO / RÉEL nettement séparés** — deux blocs, chacun avec son badge : « Profils de recherche · **DÉMO · EXEMPLES** » (violet) et « Promoteurs actifs du secteur · **RÉEL · SITADEL** » (menthe) + bannière qui l'annonce. Le client ne peut plus confondre.
2. **Cartes profil CLIQUABLES, un seul actif à la fois** : cliquer un profil le met en avant (bord violet, « ● … actif »).
3. **Les parcelles matchées s'allument sur la carte** : le profil est un jeu de critères (surface/SDP/commune) ; on les applique comme **filtre** via `/parcels` (aucun nouveau back) et on surligne les résultats (`setModuleMap`). Le compteur « N parcelle(s) allumée(s) » s'affiche sur la carte active.
4. **Cliquer une parcelle allumée → sa fiche avec la RAISON du match en tête** : chaque parcelle matchée reçoit un `moduleFiche` (« Correspond au profil … · Surface ✓ · SDP ✓ · Commune ✓ ») rendu en tête de fiche (`Fiche.tsx:1001`, `Module · matching`). Même mécanisme éprouvé que les autres outils (M01, M10).
5. **RG1** : l'outil démarre **vierge** — il ne lit plus `commune` du store (l'ancienne version héritait du filtre carte). Les promoteurs RÉELS suivent la commune du **profil actif**, pas la carte.
6. Compat-par-IDU (flux inverse, DÉMO, source de confusion) **retirée** ; « Tester le matching » (alertes cloche) retiré du flux visuel.

## Preuves
- `a3_profil_actif.png` : deux blocs badgés DÉMO/RÉEL, 2 profils cliquables, 1er profil **actif** (violet) + compteur de parcelles allumées.
- Vérifié : badge DÉMO + badge RÉEL présents ; clic profil → « actif — voir la carte » ; parcelles matchées poussées sur `moduleMap`.
- Raison du match : `Fiche.tsx` rend `modBlock` (moduleFiche[idu]) — wiring confirmé par code (le click-through headless n'est pas scriptable, le store n'étant pas exposé sur window ; le mécanisme est celui, déjà visible, des autres outils).

## Reste
- Le rendu « parcelles allumées » à l'échelle de l'île reste discret (surlignage `module-hl`) — comme l'Assemblage (A1), une couche de picking plus visible pourrait aider ; hors périmètre de cette refonte.
