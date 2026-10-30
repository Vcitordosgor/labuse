# RECETTE-4 — reprise de la recette Vic des 29 et 30/10

Branche `fix/recette-4` · worktree `~/Desktop/labuse-recette4` · API 9030 / front 6230 ·
base locale `labuse` (run servi `q_v20`). Pas de merge, aucun accès prod. Preuve = constat
navigateur (Playwright) ; captures sous `docs/audit-2026-10/recette-4/captures/` (hors git
par doctrine MENAGE-1 — livrées via l'app). Un commit par lot.

Légende : **AVANT** = constat Vic reproduit ici · **APRÈS** = après correctif, re-constaté.

---

## Lot 1 — T1 (état d'outil vidé au changement d'outil) + nettoyages Solaire / Assemblage

### T1 — « Changer d'outil vide tout l'état de l'outil quitté »

**Racine.** Le store vide bien l'état partagé (`setModule` remet `selectedIdu`,
`contexteCommune`, `moduleMap`… à null). Mais l'**état local React** des composants-outils
(sous-vue, commune choisie, onglet, champ saisi) ne tombe que si React **remonte** le
composant. Or `<Body />` dans `ModulePanel` n'était **pas keyé**. Quand deux clés d'outil
résolvent la **même fonction composant** — `communes`↔`barometre` → `Communes`,
`permis`↔`promesses` → `M03` — React **réutilise l'instance** à travers le changement
d'outil : la sous-vue (« Acquisitions récentes ») et sa commune survivaient.

**AVANT (reproduit).** Outil Communes → porte « Acquisitions récentes » → commune
Saint-Denis → bascule vers un autre outil → retour sur Communes : la sous-vue
« Acquisitions récentes » et « Saint-Denis » étaient **toujours là** (`select` encore monté).
→ `captures/t1-communes-AVANT.png`.

**Correctif (racine, mécanisme commun).** `frontend/src/components/outils/ModulePanel.tsx` :
`<Body key={def.key} />` aux deux points de rendu (branche normale + branche
`analyser-annonce`). React remonte **à neuf à chaque changement de clé d'outil** — garantie
uniforme pour TOUS les outils, pas seulement les paires aliasées.

**APRÈS (re-constaté).**
- Communes : `barometre` (acquisitions, Saint-Denis) → `communes` ⇒ retour à l'accueil
  (4 portes), plus de `select`. → `captures/t1-communes-APRES.png`.
- Scan patrimoine : porte « Un propriétaire » + saisie `TESTSTATE123` → PLU → retour
  `patrimoine` ⇒ accueil (2 portes), champ vidé.
- Les 5 outils cités (Communes, Scan patrimoine, Analyser une annonce, Prospection solaire,
  Successions) remontent désormais à neuf à tout changement d'outil.

### Prospection solaire — deux paragraphes retirés

**Mandat.** Supprimer les deux paragraphes sous le graphe mensuel (« Productible estimé… » et
« En clair… »).

**Correctif.** `ProspectionSolaire.tsx` — les deux `<p>` retirés ; le graphe mensuel et le
bloc annuel (qui porte déjà la maille) restent.

**APRÈS.** Parcelle `97410000AS1425` : graphe « Profil mensuel » présent, aucun des deux
paragraphes (`Productible estimé à la…` / `En clair : le potentiel…`). →
`captures/solaire-APRES.png`.

### Assemblage — encart d'en-tête retiré, noms de PM en entier

**Mandat.** Retirer l'encart d'explication en tête ; afficher les noms des personnes morales
en entier, sur plusieurs lignes si besoin.

**Correctif.** `moteurs.tsx` (M16) — `<Banner>` d'intro retiré ; `truncate` → `break-words`
sur la liste « PM : … » et sur la dénomination par parcelle.

**APRÈS.** Assiette contiguë `97422000BW1992 + BW2857 + BW2858` (bloc SA HLM) : en-tête =
directement « Étape 1 » (plus d'encart) ; « PM : SOCIETE ANONYME D'HABITATIONS A LOYER
MODERE DE LA REUNION » affiché **en entier sur 2 lignes**, non tronqué. →
`captures/assemblage-APRES.png`, `captures/assemblage-pm-nom-APRES.png`.

_tsc -b : 0 erreur._

---

## Lot 2 — Étude de zone (menu Activité) · Permis (« Tous ») · Courrier (référence)

### Étude de zone — menu « Activité (destination) » retiré (outil + Docs + PDF)

**Mandat.** Supprimer le menu « Activité (destination) » de l'outil, de Docs et du PDF.

**Correctif.**
- Outil `EtudeZone.tsx` : `DestinationSelect` retiré, `sous_destination` n'est plus envoyé, le
  bloc verdict `DestinationsBloc` et la condition `res.destinations` supprimés (+ imports morts).
- Docs `DocumentsView.tsx` : le `DestinationSelect` de la fenêtre Étude de zone retiré ; l'URL
  PDF n'emporte plus `sous_destination`.
- PDF `exports/blocs/etude_zone.py` : le bloc « Activité étudiée » (verdict par zone) supprimé.

**APRÈS.** Outil Étude de zone : plus de libellé « Activité (destination) », plus de
`[data-destination-select]`. PDF `/etude-zone.pdf?idu=97410000AS1425&rayon_km=1` (HTTP 200,
132 Ko) : `pdftotext` ⇒ 0 occurrence de « Activité étudiée » / « Destinations ». →
`captures/etudezone-APRES.png`.

### Permis — « Tous » réellement appliqué à l'arrivée

**AVANT (racine).** Le segment par défaut est « Tous » (`seg='tous'`), mais la fenêtre `months`
était initialisée à **24** (init state + effet de montage) — la fenêtre « Récent » — alors que
`choisirSeg` applique **240** pour « Tous ». D'où le constat Vic : chip « Tous » affiché actif,
données « Récent » appliquées.

**Correctif.** `ModulePanel.tsx` (M03) : `months` initial `240` (hors `promesses`) et l'effet de
montage aligné sur `choisirSeg` (`'tous' → 240`).

**APRÈS.** À l'arrivée : chip « Tous » actif (`aria-pressed`) ET « **50 808** dans la sélection »
(toute la base), plus 5 640 (Récent). Compteur et sélection cohérents. →
`captures/permis-tous-APRES.png`.

### Courrier — référence non séquentielle

**Mandat.** Plus de « Demande n° 2 ». Une référence lettres + date, non séquentielle (ex. C-2610-KD).

**Correctif.** `courrier.py` : `_reference(id, ts)` = `C-DDMM-XX` (DDMM = date de la demande ;
XX = 2 lettres dérivées de l'id par md5→base26, non devinables, sans révéler le volume ni le
rang). Champ `reference` ajouté à la réponse `creer_demande` (branche neuve + dédup). Front
(`api.ts`, `ModulePanel.tsx`) : la confirmation affiche `demande.reference` (repli rang/id).

**APRÈS.** `POST /courrier/demande` ⇒ `"reference":"C-3010-IW"` (id 51, rang 21 — jamais montrés).
Parcours complet navigateur ⇒ « ✓ Demande **C-3010-VB** transmise. » →
`captures/courrier-ref-APRES.png`.

_tsc -b : 0 erreur._

---

## Lot 3 — Copilote (cartes exemples) + Notifications (intro retirée)

### Copilote — grille d'exemples à 2 colonnes, cartes larges, rien de tronqué

**Mandat.** Grille à 2 colonnes de cartes larges, icône à gauche, texte 13 px sur 2–3 lignes,
rien de tronqué.

**Correctif.** `AccueilCopilote.tsx` : `grid-cols-5` → `grid-cols-2` ; texte `text-[12px]
leading-tight` → `text-[13px] leading-snug` ; padding/gap élargis ; pas de `line-clamp`.

**APRÈS.** Mesuré navigateur : `gridTemplateColumns` = **2 colonnes**, cartes **296 px** de
large, police **13 px**, `anyTruncated = false` sur les 10 cartes. →
`captures/copilote-cards-APRES.png`.

### Notifications — paragraphe d'intro retiré

**Mandat.** Supprimer « Ce qui bouge sur vos parcelles suivies … réellement détecter. ».

**Correctif.** `Header.tsx` : le `<p>` d'intro retiré (ternaire `prefsOpen ? … : <p>` → `prefsOpen
&& …`) ; la requête `entete-cloche` (qui l'alimentait) et son import retirés.

**APRÈS.** Panneau Notifications ouvert : en-tête « NOTIFICATIONS · 1045 », puis directement la
liste — plus aucune occurrence de « Ce qui bouge sur » / « réellement détecter ». →
`captures/notif-sans-blurb-APRES.png`.

_tsc -b : 0 erreur._
