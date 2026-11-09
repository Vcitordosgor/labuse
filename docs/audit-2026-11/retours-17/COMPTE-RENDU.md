# RETOURS-17 — corrections fines d'écran

Branche `fix/retours-17` · worktree `~/Desktop/labuse-retours17` · front dev 7120 / API 9920 (base
locale `labuse`, run servi `q_v20`). **Aucun accès prod. Aucun merge.** DA existante respectée
(`components/ui/`, tokens `styles/index.css`). Captures avant/après : `docs/audit-2026-11/retours-17/captures/{avant,apres}/`.

**Portes vertes** : `tsc -b` 0 · `vitest` 308/308 · `vite build` OK · scan secrets OK ·
`pytest` unitaires 3193 passed. (Cohérence/Python base : non impactés — changements 100 % front,
présentationnels, aucun chiffre/donnée modifié.)

---

## Les points, un par un

### 1. Outils — le champ d'adresse se vide pour la suivante
Nouveau comportement **opt-in** `viderApresPick` qui traverse `ParcelInput` → `AddressAutocomplete`
(signal de reset `resetSignal` incrémenté à chaque parcelle désignée → le champ se vide, sans passer
en état « résolu »). Posé sur les outils **multi-parcelles** qui réutilisent le même champ :
**Comparer** (`ComparePanel`) et **Assemblage** (`moteurs.tsx`). Les autres outils à parcelle passent
déjà par `EntreeParcelle`, qui REMPLACE le champ par la ligne « adresse · Changer de parcelle » dès
qu'une parcelle est choisie (donc le champ disparaît aussi). Fichiers : `AddressAutocomplete.tsx`,
`ParcelInput.tsx`, `EntreeParcelle.tsx`, `ComparePanel.tsx`, `outils/moteurs.tsx`.

### 2. Notifications — « préférences » et « tout lire » retirés ; pastille « 99+ » verte
`Header.tsx` : les deux actions d'en-tête du volet Notifications sont retirées (le volet Préférences
reste atteignable par l'événement `labuse:open-notif-prefs` ; le ✓ par ligne reste). La pastille du
compte non-lu passe de **ambre** à **vert** (`bg-mint text-mint-ink`).
Avant/après : `avant|apres/40-notifications.png`, `avant|apres/41-bell-99plus-*.png`.

### 3. Fiche — trait vertical à côté de la cloche retiré
`Fiche.tsx` : suppression du `<span className="hsep">` (séparateur) dans la barre d'actions de la fiche.
Avant/après : `avant/11-fiche-panel.png` vs `apres/11-fiche-panel.png`.

### 4. Fiche — chevron de survol des cartes : noir, pas gris
La règle historique ciblait `.chev`, que le composant `Chevron` ne porte pas → le chevron restait gris
au survol. Ajout d'une classe dédiée `t-chev` sur le chevron des tiroirs (`primitives.tsx`) + extension
de la règle `.tiroir.is-lien:hover` (`index.css`) → chevron en **noir (--ink)** au survol.
Après : `apres/17-fiche-chevron-noir-hover.png`.

### 5. Fiche — espace au-dessus bouché en noir ; en-tête collé à top:0
**Vrai défaut** (précisé par Vic) : l'en-tête collant se collait à **top:8px**, laissant une bande
transparente de 8 px au-dessus de lui — au défilement, le contenu (boutons **Analyse LABUSE / Copilote**)
apparaissait DERRIÈRE, au-dessus de l'en-tête. Corrigé : `.tete-collee` se colle désormais à **top:0**
avec un **fond opaque `--bg-0`** couvrant toute la hauteur jusqu'au bord haut du panneau ; le petit
espace noir au-dessus de la carte grise vit À L'INTÉRIEUR du bloc collant (`padding-top`), donc il reste
collé lui aussi ; la **carte grise à bords arrondis** devient un enfant `.tete-carte` (inchangée). Le
`pt-2` du conteneur défilant est retiré. **Vérifié en défilant** (sonde DOM : au point haut, c'est
`.tete-collee` qui peint, plus un `.tiroir` défilant). Fichiers : `Fiche.tsx`, `index.css`. Avant/après
en défilement : `avant/19b-fiche-scroll-bleed.png` (boutons verts au-dessus de l'en-tête) vs
`apres/19-fiche-scroll-entete-net.png` (rien au-dessus).

### 6. « + CRM » / « + Projet » — tout en vert, survol blanc sur vert opaque
`Fiche.tsx` : **« + Projet »** passe de l'ambre au **vert** (mêmes classes que « + CRM » :
`act-mint hover-fill`, état rattaché/ouvert `act-cmp`). `index.css` : au survol, les boutons d'action
de la fiche (`.fiche-v6 .act.hover-fill:hover`) affichent un **texte blanc** sur le vert opaque (au
lieu de l'encre sombre générique). L'ambre n'est plus porté par aucun bouton — réservé aux pastilles
« projet ». Après : `apres/12-crm-projet-boutons.png`, `apres/13-projet-hover.png`.

### 7. Listing des projets — « Parcelle » jamais coupé, pas de défilement horizontal
`ProjetKanban.tsx` : les grilles de la liste « À trier » (en-tête + lignes) passent de colonnes FIXES
à colonnes **rétractables** — « Parcelle » garde `minmax(56px,1fr)` (jamais coupé) ; Signaux/Surface se
compriment (`minmax(0,…)`) avant tout débordement ; la colonne porte déjà `overflow-hidden` → aucun
défilement horizontal, même à largeur réduite (tiroir Filtrer ouvert). « Nouveau projet » existe déjà
(bouton vert) et le survol de ligne est déjà vert opaque (`[data-projet-row]:hover`).
Après : `apres/30-projets.png`, `apres/31-projet-kanban.png`.

### 8. CRM — « Déplacer », libellés non coupés, « Note » → fiche section note
- `DeplacerMenu.tsx` : « Déplacer vers… » → **« Déplacer »** (test `Kanban.test.tsx` mis à jour).
- `Kanban.tsx` : le **champ de note inline du kanban est retiré** ; la note s'affiche en lecture seule,
  et « Note »/« + Note » **ouvre le détail de la carte directement sur la section Notes** (focus +
  scroll sur le textarea). *(La fiche parcelle n'a pas de section note ; « la fiche » a été interprété
  comme le panneau de détail de la carte, qui porte la section Notes.)*
- Libellés coupés : revue — rien d'autre n'est tronqué (l'IDU et les étiquettes de colonne tiennent).

### 9. Panneau filtres fermé — le compteur « 1 » n'apparaît pas
`LeftPanel.tsx` : la pastille du nombre de filtres actifs sur la languette (panneau fermé) est retirée
(le compte reste visible dans l'en-tête de la section Filtres, panneau ouvert).

### 10. Badge « constructibilité très limitée » — sans le « i »
`Fiche.tsx` : l'infobulle « ⓘ » (exceptions A/N) est retirée du badge ; libellé seul.

### 11. Estimer — le symbole € remplace le $ ✅
Le « $ » était une **icône** (SVG lucide *DollarSign*), pas un texte — d'où l'introuvabilité par
recherche de chaîne. C'est l'icône de la tuile **« Estimer »** dans la grille d'outils de la fiche
parcelle (`Fiche.tsx`, `data-estimer-tile`, juste au-dessus de « Estimations indicatives issues de… »).
Remplacée par l'**icône € (lucide *Euro*)**. Après : `apres/80-estimer-tile-euro.png`.

### 12. Liens externes de la fiche
`liensExternes.ts` (+ test `liensExternes.test.ts`) :
- **Pages Jaunes réparé** : le `?ou=<adresse>` seul renvoyait **404** (« Aucun résultat — Commerces »).
  Ajout du paramètre `quoiqui=` (même vide) → **HTTP 200**, page de résultats valide sur l'adresse.
  Vérifié en navigateur réel (404 → 200).
- **Google Earth EN LIGNE** : fini le KMZ ; le lien ouvre `earth.google.com/web/@<lat>,<lon>,150a,…`
  centré sur la parcelle (vérifié : Earth charge et centre). Signature `googleEarthUrl(coords)`.
- **Cadastre** (redirige proprement vers `cartes.gouv.fr`, centré), **Google Maps** (`?api=1&query=lat,lon`),
  **Géorisques/Errial** : vérifiés en navigateur, OK (inchangés).

### 13. Fenêtres Docs — « Fiche → » et petites phrases retirées ; Comparatif
`catalogue.ts` : toutes les `explication` (« Une page depuis la fiche », « Se calcule sur les données
de la fiche et vos ratios », etc.) vidées. `DocumentsView.tsx` : lien **« Fiche → » retiré**
(`ParcelleResolue`), rendu conditionnel des `explication` (plus de `<p>` vide), **Comparatif** :
« Quelles parcelles ? (2 à 3) » → **« (jusqu'à 3) »**, et le **3ᵉ champ porte le même libellé** que les
deux autres. Avant/après : `avant|apres/51-docs-comparatif-porte.png`, `avant|apres/52-docs-dossier-resolue.png`.

### 14. Sources — phrase « 434 582 parcelles couvertes… micro-parcelles… » retirée
`SourcesPage.tsx` : le paragraphe de réconciliation est supprimé (la tuile « parcelles couvertes » du
bandeau reste). Avant/après : `avant/60-sources.png` (phrase présente) vs `apres/60-sources.png`.

### 15. Noms des fichiers exportés — `<IDU> — <Nom>.pdf` (PDF / Excel / ZIP)
`ouvrirDocument.ts` : nouvel argument `filename` → le document est **téléchargé sous ce nom exact** via
une ancre `download` (le nom d'un blob ouvert en onglet n'est pas maîtrisable). `DocumentsView.tsx` +
`catalogue.ts` : chaque génération et chaque « Ouvrir » de « Mes documents » nomment le fichier
`<IDU> — <Nom du document>.<ext>` (`.pdf`, `.zip` pour le pré-dossier, `.xlsx` pour l'Excel du Bilan).
Exemple : `97411000BZ1065 — Estimation.pdf` (champ `fichier: 'Estimation'` ajouté à la carte « Estimer
un bien » puisque son nom d'export diffère du libellé de carte).

### 16. Aucun identifiant de run (« Q_V20 ») visible côté client + test
`AnalyseLabuseCard.tsx` : la prop `version` (qui affichait « · q_v20 » dans l'en-tête de la carte) est
**retirée** (vue + appelant `Fiche.tsx`). Le run reste un détail serveur (`?source=`), jamais montré.
Test `AnalyseLabuseCard.test.tsx` réécrit : **garde que la carte ne contient aucun label `q_v…`**.
*(Les panneaux Admin internes gardent leurs labels de run — hors « côté client ».)*

### 17. « Demander à LABUSE » → « Analyse LABUSE » ; deux boutons côte à côte, même taille
`strings.ts` : `demanderAnalyse` → **« Analyse LABUSE »**. `Fiche.tsx` : le 2ᵉ bouton devient
**« Copilote »**. Les deux sont dans la même rangée flex (`.fiche-v6 .ia`), chacun `flex-1` → même
taille, côte à côte. Avant/après : `avant/11-fiche-panel.png` vs `apres/11-fiche-panel.png`.

### 18. 3D — « Relief » / « Relief + bâtiments » garde le zoom et le centre
`MapView.tsx` : le recentrage sur la parcelle à l'entrée en 3D (`easeTo center=centroïde`, offset −200)
est **retiré** ; seul le pitch s'incline (center/zoom inchangés). **Vérifié en direct** : avant
(center 55.4295,-20.8852 · zoom 16 · pitch 0) → après activation de « Relief + bâtiments » (center et
zoom **identiques** · pitch 55 · terrain actif). Après : `apres/70-3d-relief-centre-conserve.png`.

### 19. Puces « moyen » de la Situation → « impact moyen / faible / fort »
`primitives.tsx` : la puce de sévérité (composant `Line`, section « Situation ») affiche
`SEV_LABEL` → **« impact fort / impact moyen / impact faible »** au lieu du mot nu.

### 20. Fiche — adresse et IDU espacés comme « Secteur »
`index.css` : l'adresse ne colle plus à l'IDU (fin du `margin-top:-4px`) ; IDU, adresse et Secteur
portent un **écart régulier de 6 px**. Avant/après : `avant/11-fiche-panel.png` vs `apres/11-fiche-panel.png`.

---

## Récap statut

| # | Point | Statut |
|---|-------|--------|
| 1 | Champ adresse se vide (Comparer + outils) | ✅ |
| 2 | Notifications : préférences/tout lire retirés ; 99+ vert | ✅ |
| 3 | Fiche : trait vertical cloche retiré | ✅ |
| 4 | Fiche : chevron survol noir | ✅ |
| 5 | Espace au-dessus fiche noir ; en-tête collé top:0 (rien au-dessus au défilement) | ✅ (vérifié en défilant) |
| 6 | + CRM / + Projet verts ; survol blanc sur vert opaque | ✅ |
| 7 | Listing projets : Parcelle non coupé, pas de scroll H, Nouveau projet, survol vert | ✅ |
| 8 | CRM : « Déplacer », Note → détail/section note, champ kanban retiré | ✅ |
| 9 | Filtres fermés : compteur « 1 » n'apparaît pas | ✅ |
| 10 | Badge « constructibilité très limitée » sans le « i » | ✅ |
| 11 | Estimer : € remplace $ (icône de la tuile) | ✅ |
| 12 | Liens externes (PJ réparé, Earth en ligne, Cadastre/Maps/Géorisques) | ✅ |
| 13 | Docs : Fiche → et petites phrases retirées ; Comparatif | ✅ |
| 14 | Sources : phrase 434 582… retirée | ✅ |
| 15 | Noms fichiers exportés `<IDU> — <Nom>.pdf` (+ Excel/ZIP) | ✅ |
| 16 | Aucun run « Q_V20 » visible + test | ✅ |
| 17 | « Analyse LABUSE » + « Copilote » côte à côte même taille | ✅ |
| 18 | 3D : Relief garde zoom/centre | ✅ (vérifié live) |
| 19 | Puces « moyen » Situation → « impact moyen/faible/fort » | ✅ |
| 20 | Fiche : adresse et IDU espacés comme Secteur | ✅ |

**Les 20 points sont traités.**
