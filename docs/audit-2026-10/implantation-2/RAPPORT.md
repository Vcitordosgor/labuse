# IMPLANTATION-2 — Rapport

L'outil **Faisabilité devient l'étude de faisabilité EN LIGNE** : le moteur d'implantation collectif
d'[IMPLANTATION-1](../implantation-1/RAPPORT.md) est désormais **servi par l'API** et piloté par un
**écran** (configuration → scénarios), avec le **plan masse géoréférencé** sur la carte. La fiche
parcelle n'affiche plus de calcul : elle **ouvre l'outil** par un bouton.

> Nature du document : pré-faisabilité automatisée. Ni étude d'architecte, ni preuve de conformité,
> ni dossier de permis. Le mot « conforme » n'apparaît jamais. Toutes les hypothèses sont « Estimé ».

Branche `feat/implantation-2` (depuis `main` `1d0beea4`, **rebasée** sur `main` à jour — q_v19 servi).
Worktree `~/Desktop/labuse-implant2`, ports 8831 / 6031. **Pas de merge, pas de run, rien en prod.**

---

## LOT A — le moteur servi par l'API

### Un endpoint unique
`POST /modules/etude` (`src/labuse/api/modules.py`, modèle `EtudeIn`) :

- **Entrée** : `idus` (1 à 8 parcelles contiguës → assiette fusionnée `ST_Union`, comme l'Assemblage),
  `type_projet` (**collectif** seul actif), `objectif` (équilibre / plus de logements / plus de
  surface habitable / projet plus simple), `programme` (**LABUSE propose** ou **saisi** : nombre par
  type T2/T3/T4 + surface moyenne), `stationnement` (**aérien** seul actif), `terrain` (libéré),
  `hypotheses` (profondeur, surfaces par type, plancher→habitable — modifiables).
- **Sortie** (`src/labuse/implantation/service.py : etudier_payload`) : jusqu'à **3 scénarios**,
  chacun avec la **géométrie en GeoJSON WGS84** (plan masse pour la carte), la **capacité**, les
  **contrôles 4 états**, le **statut de l'étude**, les **hypothèses** effectives et les **versions**
  du moteur et des règles (citations incluses).

### Ce qui a été ajouté au moteur (sans toucher à `etudier()`)
`src/labuse/implantation/moteur.py` :

- `etudier_multi(...)` — jusqu'à 3 scénarios **faisables et géométriquement distincts** (signature
  forme + niveaux), **classés par l'objectif** (`_clef` : équilibre / plus_logements / plus_surface /
  plus_simple). Un seul trouvé → un seul affiché. Aucun → **« simulation impossible »** avec la raison.
- **Programme saisi** : `service._programme_vers_demande` (proportion réduite par le PGCD →
  répartition de pavage) + filtrage des candidats qui **contiennent** la demande ; si aucun ne la
  contient → **« ne tient pas »** en nommant ce qui plafonne (hauteur réglementaire ou largeur de la
  zone après reculs).
- **Hypothèses modifiables** : `conventions.avec_surcharges` (profondeur, plancher→habitable, surface
  par type ; bornées ; restent « Estimé » et **ne peuvent jamais** rendre un contrôle « Réussi »).
- `etudier()` (API historique) préservée **à l'identique** → les **99 tests `reel`**
  (`test_implantation1` + `test_implantation_distance`) passent inchangés sur la base q_v19.

La géométrie est dessinée en métrique (EPSG:2975) et **reprojetée en WGS84** (`geo.to_4326`) pour la
carte ; la reprojection est **revalidée** (une rotation/reprojection en flottant peut rendre
auto-sécant un polygone pourtant valide — corrigé côté monde *et* côté 4326 servi).

### Robustesse (banc, gate dur avant tout écran)
`docs/audit-2026-10/implantation-2/robustesse.py` → `robustesse.md`. **3 témoins + 20 parcelles U
tirées au hasard** (ordre déterministe par `md5(idu)`) dans **10 communes**. Tableau servies /
non servies (raison) / durée. **Invariants durs OK** :

- **0 géométrie invalide**, **0 chevauchement** (bâti · places · allées · accès · espaces libres),
- **0 contrôle « Réussi » sans règle citée**.

**14/23 assiettes servies** ; les 9 non servies le sont avec une **raison honnête** (pas de limite
voie, zone après reculs trop étroite, ou aucune implantation ne passe les contrôles durs). Le banc a
**trouvé et fait corriger deux bugs** avant l'écran : un `IndexError` (rectangle orienté minimal
dégénéré) et des polygones auto-sécants après rotation.

> ⚠ **Performance** : la recherche parcourt 225 candidats (3 formes × 5 niveaux × 15 longueurs), chacun
> dessiné intégralement. Durée typique **2–35 s**, une assiette à géométrie PPR complexe a atteint
> **~114 s**. Acceptable pour une étude à la demande (l'écran affiche « Génération… ») ; une recherche
> grossière-puis-fine serait le prochain gain, sans changer le comportement validé.

### Tests dédiés
`tests/test_implantation2.py` (**13 tests `reel`**, verts) : payload/entêtes, 3 chiffres clés,
scénarios distincts, contrôles 4 états (**verrou « Réussi ⇒ citation »**), versions moteur+règles,
**GeoJSON valide + 0 chevauchement re-mesuré sur le 4326 servi**, **programme saisi qui tient / qui
ne tient pas** (cause nommée), **hypothèses surchargées qui recalculent**, **objectif qui pilote le
rang**, et la route `POST /modules/etude` (sert les scénarios ; **400** sur entrée invalide).

---

## LOT B — l'écran (remplace l'outil Faisabilité sur place)

`frontend/src/components/outils/M22Programme.tsx`, réécrit. **Clé `programme` / num M22 inchangés → le
verrou « 17 outils » tient** (label « Étude de faisabilité »). **Aucun calcul dans le front** : l'écran
n'affiche que le payload de `POST /modules/etude` et filtre le GeoJSON par couche cochée (affichage,
pas calcul — prouvé par test).

- **État 1 — configuration** : assiette 1–8 parcelles (saisie **adresse OU clic carte**, un seul
  composant `EntreeParcelle` ; chips ✕ ; **8 max**), type (collectif ; **maisons groupées / lotissement
  grisés « bientôt »**), objectif (4), programme (LABUSE propose / je saisis T2·T3·T4 + surface),
  stationnement (aérien ; **en ouvrage « bientôt »**), terrain (libéré ; **en gardant le bâti
  « bientôt »**), bouton **« Générer les scénarios »**.
- **État 2 — scénarios** : jusqu'à **3 cartes** (les **deux statuts** + 3 chiffres + compte des
  contrôles), **onglets A / B / C**, **3 chiffres clés** (logements · places · SDP), **sections
  repliables** (programme, distribution par niveau, stationnement & accès, **contrôles 4 états** avec
  citation au survol, **hypothèses modifiables** → *Recalculer* / *Valeurs LABUSE*), bouton **« Voir en
  3D dans le gabarit → »**, **couches activables** du plan masse.
- **Plan masse sur la carte** depuis le GeoJSON de l'API : calques dédiés `etude-*`
  (`frontend/src/components/map/MapView.tsx`) stylés par `kind` (palette du rendu moteur), activés en
  n'injectant que les couches cochées. Le **clic-carte en module `programme` compose l'assiette**
  (comme l'Assemblage), couche de picking visible.
- **Règles UI gravées** : sélection adresse OU clic (un composant), multi-parcelles 8 max,
  **Réinitialiser** en haut à droite, **quitter l'outil vide son état** (assiette + plan masse), les
  **« i » au survol**, options grisées « bientôt ».

Tests : `Etude.test.tsx` (**7**, dont le **verrou « aucun calcul front »** : décocher une couche ne
change aucun chiffre ; bascule d'onglet sans recalcul ; « ne tient pas » servi ; Réinitialiser).
tsc **0**, vitest **12/12** (Etude + Faisabilite). 2 tests obsolètes de l'ancien M22 retirés.

---

## LOT C — la fiche parcelle

`frontend/src/components/fiche/Fiche.tsx` : **plus aucun calcul de faisabilité dans la fiche**. Le
panneau interactif `FaisabiliteTab` (sélecteur de scénario, hypothèses, « tester un projet », 8 étapes)
**n'est plus monté** ; à sa place, un bouton **« Étude de faisabilité → »** ouvre l'outil M22 sur la
parcelle (idiome `parcelPrefill`). Le bouton « Faisabilité » du tiroir outils est renommé de même. Le
composant reste **ré-exporté** (CalculetteFonciere + tests de non-régression), mais la fiche ne le rend
plus. tsc 0, vitest 112/112 (fiche + outils + map).

### ⚠ STOP documenté — l'export Dossier LIT l'ancien calcul (vérification demandée)
La vérification exigée par le mandat a trouvé que **l'export Dossier lit l'ancien moteur de
faisabilité** :

- `src/labuse/exports/robinet_fiche.py : _fourchette_logements` → `parcel_faisabilite` alimente la
  ligne **« Capacité (logements) »** du Dossier (`capacite_logements`) ;
- **Flash** (`src/labuse/flash/data.py`) et le **Scoreur** (`src/labuse/api/scoreur.py`) rejouent aussi
  `parcel_faisabilite`.

**Conséquence, et STOP sur ce point** : je **ne touche pas** au moteur de faisabilité backend
(`src/labuse/faisabilite/`) ni à ses lecteurs — les retirer casserait le Dossier, le Flash et le score.
L'étude en ligne (IMPLANTATION-2) est un **moteur distinct** (`src/labuse/implantation/`) qui coexiste.
La fiche cesse seulement d'**afficher** le calcul ; elle continue d'exposer les indicateurs **servis**
(SDP résiduelle, prix de sortie), qui proviennent de la même source que le Dossier — cohérence
préservée.

Le **Copilote**, lui, **ne lit PAS** le calcul de capacité : il n'utilise que `faisabilite.zonage`
(résolution de zone / règlement) et `faisabilite.marche_commune` — vérifié (aucun appel à
`parcel_faisabilite` ni `estimate_capacity`).

---

## Preuves

- **Tests** : 99 `reel` (moteur historique) + **13** `reel` (IMPLANTATION-2) + **12** vitest (écran) +
  **112** vitest (fiche/outils/carte). tsc 0.
- **Robustesse** : `robustesse.md` (banc 23 assiettes, invariants durs OK).
- **Captures avant / après** de l'outil et de la fiche sur **L'Étang-Salé**, **Saint-André**,
  **Saint-Denis** : dossier `captures/` (voir ci-dessous).

### Captures
_(dossier `docs/audit-2026-10/implantation-2/captures/`, prises dans l'app réelle — API 8831 +
front 6031, viewport 1440×900, run q_v19)_

**Avant** — l'ancien outil « Faisabilité » (une parcelle → panneau de calcul `FaisabiliteTab`) et la
fiche qui rendait ce même panneau. L'avant est **indépendant de la parcelle** (même panneau partout),
montré une fois sur L'Étang-Salé :

- `avant-outil-etang.png` — ancien outil (scénario Terrain libéré / bâti gardé, « tester un projet »,
  hypothèses) ; `data-faisa-panneau` présent.
- `avant-fiche-etang.png` — tiroir Potentiel de la fiche AVEC le panneau de calcul inline.

**Après** — le nouvel écran « Étude de faisabilité » (config → scénarios + plan masse) et la fiche qui
n'offre plus qu'un bouton :

| Terrain | Outil (après) | Fiche (après) |
|---|---|---|
| L'Étang-Salé (UA) | `apres-outil-etang-config.png` (config 4 parcelles) · `apres-outil-etang-scenarios.png` (3 scénarios exploitables R+3, plan masse) | `apres-fiche-etang.png` (bouton « Étude de faisabilité → », **plus de panneau de calcul** : `data-faisa-panneau` absent) |
| Saint-André (UC) | `apres-outil-standre-scenarios.png` (3 scénarios « à compléter », barre/L R+2) | bouton identique (panneau parcelle-agnostique) |
| Saint-Denis (Ui) | `apres-outil-stdenis-scenarios.png` (3 scénarios « à compléter », R+2/R+5/R+3, contexte PPR) | — |

Vérifié en direct dans le navigateur : les 3 chiffres affichés = ceux du payload (ex. L'Étang-Salé
28 logts · 34 places · **1 800 m² SDP**) ; dans la fiche, `data-faisa-panneau` est **absent** (le
calcul n'est plus rendu), seul le bouton « Étude de faisabilité → » subsiste.

---

## Reproduire

```
# base réelle (lecture seule), venv du dépôt principal, repère /src du worktree
PGHOST=/tmp PYTHONPATH=src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
<python> docs/audit-2026-10/implantation-2/robustesse.py        # banc de robustesse

# tests dédiés (marqués reel)
LABUSE_APP_DATABASE_URL=…@/labuse PYTHONPATH=src <python> -m pytest tests/test_implantation2.py -q
```

API en dev : `uvicorn labuse.api.app:app --port 8831` ; front : `LABUSE_API_DEV=http://127.0.0.1:8831
npm run dev -- --port 6031` ; l'outil est « Étude de faisabilité » (groupe Instruire).
