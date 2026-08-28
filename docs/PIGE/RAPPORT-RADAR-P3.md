# RAPPORT DE RECETTE — RADAR P3 (l'écran client)

Branche `feat/radar-p3` (depuis main incluant P0+P2+P1). Commits par lot C1→C4. Ligne rouge tenue :
**des faits et un lien, jamais le titre/texte/photo de l'annonce, jamais les coordonnées de l'annonceur.**
Aucune capture servie par le web. Réutilise `pige/*` (portails, tables, rattachement, api) sans le réécrire.

---

## C1 — Les données côté client — **FAIT**

`pige/client.py` — lecture pour un compte CLIENT (jamais admin) :
- `lister()` : biens **VALIDÉS uniquement** (`valide_at IS NOT NULL`) ; statuts par défaut `active` +
  `en_vente_longue`, les autres accessibles en filtre. Filtres commune/type/prix/surface(hab+terrain)/
  particulier-pro/statut/période/**rattaché (oui/non/indifférent)**. Tri serveur (récentes, prix ↑/↓,
  ancienneté, baisses) + pagination. Renvoie `n_total` (compteur du filtre) et **`n_rattaches`** (les
  pins de la carte). Chaque bien : faits + **étiquettes Sourcé/Estimé/Absent**, rattachement (idu+niveau
  +confiance) ou absence, coords (rattachés seulement), portail + url_sortante, dates, drapeau baisse.
- `detail()` : + **historique de prix**.
- `enregistrer_clic()` → **`pige_clics`** (client, bien, date) : chaque clic SORTANT logué (usage Produit).
- `signaler()` → événement `pige.signalement_client` — **NE change JAMAIS le statut** (anti-abus), il
  alerte Vic (remontée en tête de file de re-vérif).
Endpoints `/radar/biens`, `/radar/biens/{id}`, `/radar/clic`, `/radar/signaler` (compte via
`current_compte`). Verrou `tests/test_pige_client.py` 7/7.

## C2 — L'écran : filtres + carte + listing — **FAIT**

Outil **`radar`** (registry, groupe *marché*, R1) — `RadarClient.tsx`, **patron des outils** (filtres à
gauche, carte à droite) + listing. **Branché sur la carte existante** (pas de carte parallèle) : les pins
sont poussés via `module-extra` (`kind='radar'`, **couleur par statut** — vert marque/ambre/bleu, **jamais
le mauve réservé IA**). **Carte = rattachés SEULEMENT** ; un bien non rattaché n'a **aucun** pin.
**Listing = TOUS** les biens avec une pastille — **choix de libellé rapporté : « sur la carte » /
« non localisé »** (court, honnête, dit au client s'il peut cliquer vers la parcelle ou seulement vers la
source). Triable. Chaque filtre affiche le compteur (`n_total` + `n_rattaches`).
**Clic dans le listing (décision Vic, à la lettre)** : bien **rattaché** → `flyTo` + `select(idu)` +
ouverture de la **fiche du bien** ; bien **non rattaché** → **directement le portail** (nouvel onglet,
`rel="noopener noreferrer"`) et **clic logué**.

## C3 — La fiche d'un bien — **FAIT**

`BienFiche` (dans `RadarClient.tsx`) : faits + étiquettes, **historique de prix** (liste datée),
statut, **parcelle rattachée + niveau de confiance** ; un **Estimé** dit ses candidates / « à confirmer,
jamais un point faussement sûr ». Le **gros bouton « Voir l'annonce sur [portail] »** est le SEUL chemin
vers la source (clic logué). Bouton **« Signaler : annonce retirée / erreur »** → `pige.signalement_client`,
sans changer le statut.
**Fiche parcelle existante** : si un bien Radar VALIDÉ est rattaché à la parcelle, un bloc DISCRET
(`_q_v2_fiche.radar_bien` → `Fiche.tsx`, dans le tiroir Propriétaire) montre le fait + le statut + le
lien. DA-cohérent, hors scoring.

## C4 — Intégration et recette — **FAIT**

Outil au menu Outils (aplati), DA LABUSE, **couleurs depuis la source unique** (`mint` de
`config/brand_colors.json`) ; **le mauve n'apparaît nulle part** dans l'écran client. Recette déroulée avec
un jeu **[RADAR-TEST]** représentatif (rattaché Sourcé + baisse, rattaché Estimé, 2 non rattachés,
plusieurs communes/statuts) — **purgé en fin, vérifié SQL** (`pige_biens`=0, `pige_clics`=0).

**Cas prouvés** (captures + tests) : filtre « non rattaché » qui **vide la carte mais garde le listing**
(compteur « N · 0 sur la carte ») · clic rattaché → **carte + fiche** · clic non rattaché → **portail**
(nouvel onglet, clic logué dans `pige_clics`) · fiche **Estimé** avec sa parcelle probable · **signalement**
sans changement de statut · bien affiché sur sa **fiche parcelle** · **liste vide** → message honnête
(« Aucun bien ne correspond… Élargissez la recherche », pas d'écran blanc).

**Mobile (390)** : l'outil vit dans le panneau gauche de l'app, qui devient un **tiroir plein écran** sur
téléphone — filtres + compteur + listing empilés et utilisables au pouce ; la carte est le fond plein
écran, atteinte en refermant le panneau (patron mobile existant de l'app). La fiche du bien **remplace** le
listing dans le même panneau (bouton « ← retour »). Vérifié sur la capture 390.

**Captures livrées : 6** (`docs/PIGE/captures/`) — écran (`radar-client-ecran-{d,m}.png`), fiche bien
(`radar-client-fiche-{d,m}.png`), fiche parcelle (`radar-fiche-parcelle-{d,m}.png`), en **1440 et 390**.

---

## RECETTE (FIN)
- **Aucun contenu d'annonce affiché** (faits + lien uniquement) ✓ · **carte = rattachés seulement,
  listing = tout avec pastille** ✓ · **clic conforme C2** (rattaché→carte / non rattaché→portail) ✓ ·
  **clics logués dans `pige_clics`** ✓ · **signalement sans changement de statut** ✓ · **Radar hors
  scoring** ✓.
- **Le test anti-requêtes-portails de P0 reste VERT** (`tests/test_pige_socle.py` 5/5 ; aucun nom de
  portail en dur dans l'écran client — le portail vient de la donnée) ✓.
- **Couleurs depuis la source unique** (`mint`), **zéro mauve** côté client ✓.
- **tsc 0 · build ✓** · **suite au niveau base (worktree `cb414f0c`)** : base 1895 / branche 1903,
  **0 fail** ✓ · **[RADAR-TEST] purgés (vérifié SQL)** ✓.

Findings : —
