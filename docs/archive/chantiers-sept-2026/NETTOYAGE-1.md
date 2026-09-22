# NETTOYAGE-1 — Légende morte + statut hypsométrie

**Branche** `feat/couches-tuyau` · **départ** `3b7b80f9`. Un commit, aucun merge.

## Lot 1 — la légende V1

**Correction d'abord (mon erreur dans COHERENCE-1).** J'avais écrit que `Legend.tsx` ne s'affiche jamais. **Faux** : la légende V1 rend bel et bien les légendes de **peinture** — **Verdict** (mode analyse), **Zonage PLU**, **Permis** (outil Permis) — pilotées par `mapPeint`/`module` (bien vivants). Ma vérification initiale n'avait testé que `verdict` sans `analyse` (donc `opinion = verdict && analyse = false`), d'où le faux « 0 nœud ». Vérifié cette fois : dès qu'on ouvre l'outil Permis ou le mode analyse, `[data-legend]` apparaît, avec un en-tête **« Légende · 0 couche »**.

**Ce qui était réellement mort** :
- le **compteur « · N couches »** : `nCouches = Object.entries(layers).filter(…!BASE_FOND).length` lisait le store `layers` V1 (retiré à COUCHES-RETRAIT-1, plus alimenté) → il affichait **toujours « · 0 couche »** sur une légende pourtant visible ;
- les **groupes `if (layers.X)`** des anciennes couches overlay (zonage-gpu, 50pas, znieff, ppr, parc, bpe, aléas, transport, axes, HT, tcsp, contraintes, nature, sols, dispositifs, vefa, renouv) — remplacés par le tuyau (`TuyauLegend`), ils ne rendaient plus (rien ne met `layers.X` à vrai).

**Fait** (`frontend/src/components/map/Legend.tsx`, 362 → 131 lignes) :
- retiré le compteur « · N couches » (en-tête = **« Légende »** seul), `BASE_FOND`, et tous les groupes `if (layers.X)` ;
- retiré ce qui n'était plus atteint : le read `layers`, `bpeDomains`/`toggleBpeDomain`, `dispoActif`/`contraintesActif`/`natureActif`/`solsActif`, `tTheme`/`MAP_THEME`, `TOKENS`, `critereDerive`, et les imports morts (`BPE_DOM`, `CINQUANTE_PAS_COLOR`, `EQUIP_META`) ; `opinion` simplifié en `verdict && analyse` (`layers.couleurs_verdict` était mort) ;
- **gardé** la légende vivante : groupes **Permis**, **Verdict**, **Zonage** (inchangés), le composant `Groupe`, `useV2Actif`, la persistance localStorage.

Le groupe **Équipements (OSM)** (`equipPeint = peint.equipements`) est aussi retiré : `peint.equipements` dérive de `layers.equipements`, jamais mis à vrai (idem couches V1).

**Preuve** : `captures/nettoyage1/{avant,apres}/legende_permis.png` — la légende (outil Permis) est **identique** ; seul l'en-tête change, prouvé par le `textContent` du DOM : **avant** « Légende · 0 couche » → **après** « Légende ». Le groupe Permis (« Achevé ou autre »…) est inchangé. `tsc -b` vert, vitest **205/205**.

## Lot 2 — statut de l'hypsométrie

« Carte hypsométrique du littoral (DEAL Lizmap) » : **`a_faire` → `partenariat_requis`** (reliability `sous_convention`).

**Pourquoi `partenariat_requis` et pas `retiree`** : le vecteur existe chez le producteur mais est **refusé en WFS** — il faut une **convention avec la DEAL** pour l'obtenir. Ce n'est pas un abandon (`retiree`) : la donnée est débloquable par partenariat, et un chantier est nommé (courrier lot 5). Meanwhile la submersion **réglementaire** est déjà couverte par les aléas PPRL vecteur — donc faible priorité, mais pas retirée.

**Raison inscrite** (seed `seed_sources.py` + ligne `data_sources` en base) : *« servie en WMS image seulement, couche `Courbes_de_niveau_hypsometrique__en_metres` refusée en WFS (ServiceException, vérifié 13/09/2026) — aucun vecteur sans convention DEAL ; submersion réglementaire déjà servie par les PPRL vecteur »*. **Ligne conservée** (trace de l'évaluation, comme les 5 `alias`), non supprimée.

**Preuve** : `status='a_faire'` en base → **0** ligne ; vitrine (`WHERE_AFFICHEES`) toujours **94** (le passage `a_faire`→`partenariat_requis` reste hors vitrine).

## Gates
`tsc -b` vert · vitest 205/205 · `labuse circuit verrous` COMPLET VERT 25/25.
