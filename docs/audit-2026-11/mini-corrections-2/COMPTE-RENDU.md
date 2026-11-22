# MINI-CORRECTIONS-2 — compte-rendu

**Branche** `fix/mini-corrections-2` (depuis `origin/main`) · worktree `~/Desktop/labuse-stationnement`
**Ports de recette** : API 7460 · front 10260 (séparés des sessions 8000/5173, base locale partagée, lecture seule).
**PDF source** : `~/Desktop/COCOCORRECTIONS.pdf` (les captures de Vic font foi).
**Captures avant/après** : `~/Desktop/mini-corrections-2/`, nommées par numéro de point.

Portée respectée : écrans seulement (aucun PDF/Excel modifié), DA existante, pas d'élargissement, pas de merge dans `main`, aucune prod touchée.

Qualité : `tsc -b` **vert**, `vitest run` **345/345 vert** (dont un test ajouté au point 24), `vite build` **exit 0**. Le hook de pre-commit/push passe sans `--no-verify`.

Légende d'état : **✅ fait** · **ℹ️ vérifié/expliqué (sans correctif nécessaire)**.

---

## FICHE PARCELLE

### 1. Rangées de la fiche — puce illisible au survol ✅
`frontend/src/styles/index.css` (règle de survol des `.tiroir`).
**Cause** : au survol, la carte de rangée passe en vert (`--fill-mint`) et la règle `RETOURS-18` force **tout** le texte descendant en encre sombre (`color:var(--ink)!important`). Or la puce de droite (Badge) garde son fond sombre (`bg-amber-bg`, `bg-mint-bg`…) → encre sombre sur fond sombre = illisible.
**Correctif** : au survol, la puce (`.t-right > span[class*="rounded-full"]`) reçoit un fond clair (`rgba(7,16,9,.08)`) + un liseré : l'encre sombre déjà imposée y redevient lisible, pour **toutes** les variantes de puce, sur **toutes** les rangées.
Captures : `01-before.png` / `01-after.png` (puce « 5 vigilances »).

### 2. Bouton « Copilote » — retirer l'icône ✅
`frontend/src/components/fiche/Fiche.tsx`. Le `<svg>` (bulle) a été retiré ; seul le texte « Copilote » reste. Captures : `02-before.png` / `02-after.png`.

### 3. Bandeau RNU (Saint-Philippe) — version compacte ✅
`frontend/src/components/fiche/Fiche.tsx` (`data-rnu-banner`). Le bandeau tenait sur ~6 lignes. Version compacte : **une ligne de titre** (⚠ Commune au règlement national d'urbanisme — pas de PLU local) + **une ligne** « Parcelle DANS/HORS l'enveloppe urbanisée estimée », et **tout le reste** (régime national + avertissement sur l'estimation de l'enveloppe) dans un « i » au survol. **Aucune information supprimée.** Parcelle de test : `97417000AC0003` (Saint-Philippe est INSEE **97417**). Captures : `03-before.png` / `03-after.png`.

### 4. Bouton « Courrier SPF » — flèche invisible au survol ✅
`frontend/src/components/fiche/formes.tsx` (`OutilsSection`).
**Cause** : la flèche `→` avait une couleur figée `var(--mint)`. Au survol le bouton vert passe le texte en encre sombre (`mint-on`) mais la flèche restait verte sur fond vert → invisible.
**Correctif** : la flèche suit `currentColor` → elle passe en encre sombre avec le texte, toujours lisible. Captures : `04-before.png` / `04-after.png`.

### 5. « Signal de marché » — libellé cassé lettre par lettre ✅
`frontend/src/styles/index.css` (`.f-row`).
**Cause** : l'ancien `grid-template-columns:minmax(0,1fr) auto` laissait la valeur `auto` (ex. « 77 ventes au dernier trimestre (-43 % vs an-1) ») happer la largeur et écraser la colonne libellé à ~0 px → « Liquidité (DVF) » tombait en colonne, une lettre par ligne.
**Correctif** : passage en `flex-wrap` (+ retrait de `overflow-wrap:anywhere` sur le libellé). Le libellé reste entier ; quand la largeur manque, la **valeur retombe à la ligne sous le libellé**. Vaut pour **toutes** les lignes du bloc. Captures : `05-before.png` / `05-after.png`.

### 6. Parcelle 97415000CT1596 « Non identifié » — enquête + correctif ✅
**Enquête (preuves)** — parcelle id 37141 (80 route de l'Éperon, 97435 Saint-Paul, 7 875 m²) :
- **Absente du fichier des personnes morales** (cause directe) : `parcelle_personne_morale` = 0 ligne, `pm_proprietaires_millesimes` = 0 ligne. Le header Identité ne lit QUE cette source → repli codé « Non identifié ».
- **Mais la base SAIT déjà ce que c'est : une COPROPRIÉTÉ (prouvé)** : `p_model_ext_copro.copro_rnic = true` ; `rnic_coproprietes` (rattachement `cadastre`) → immatriculation **AD2103778**, nom d'usage **« LES JARDINS DE L'ÉPERON »**, 54 lots (30 hab.), syndic professionnel. Cette copro est **déjà servie** à la fiche (`f.coproprietes`) et affichée dans le corps du tiroir Identité (« COPROPRIÉTÉ RATTACHÉE »). Seul le header « Non identifié » contredisait son propre corps.
- Catégories écartées : bailleur (vide), propriétaire public (vide), pseudo-SIREN/indivision (aucune PM).
**Correctif** (front, `Fiche.tsx`) : quand il n'y a pas de personne morale DGFiP **mais** `f.coproprietes` existe, le header affiche **« Copropriété »** au lieu de « Non identifié » (le terrain d'une copro appartient au syndicat des copropriétaires, absent du fichier PM — ce n'est pas un propriétaire « non identifié »). Repli « Non identifié » conservé si ni PM ni copro. Libellé cohérent avec `OWNER_TYPES["copropriete"] = "Copropriété"`.
Captures : `06-before.png` (header « Non identifié » + corps copro contradictoire) / `06-after.png` (header « Copropriété »).

---

## CARTE

### 7. Étiquettes de communes qui se chevauchent ✅
`frontend/src/components/map/MapView.tsx` (marqueurs DOM par commune).
**Cause** : des décalages pixels **manuels** (`OFFSETS`) figés, alors que l'espacement des pastilles change avec la largeur du conteneur (`fitBounds`) → à 1280 px la côte était serrée (Saint-Leu/Les Avirons/Saint-Louis/L'Étang-Salé/Entre-Deux, Sainte-Marie/Saint-André…).
**Correctif** : anti-chevauchement **automatique en espace écran**. On part des `OFFSETS` comme nudge de base puis on **pousse verticalement** toute pastille qui recouvre une déjà placée, jusqu'à zéro chevauchement, recalculé sur les rectangles réellement rendus — à chaque `zoom`/`move`/`resize`. Robuste aux largeurs.
Vérifié **1280 / 1440 / 1920** : 24 noms visibles, aucun chevauchement. Captures : `07-before-{1280,1440,1920}.png` / `07-after-{1280,1440,1920}-map.png`.

### 8. Retirer « Zoomez ou cliquez une commune pour voir ses parcelles » ✅
`frontend/src/components/map/MapView.tsx`. L'indication (et sa variante zonageFill) est retirée entièrement : à l'échelle île plus aucun bandeau. On conserve seulement, une fois zoomé, « Cliquez une parcelle pour ouvrir sa fiche ». Captures : `08-before.png` / `08-after.png`.

### 9. Bouton « Vue de l'île » + navigation souris/clavier ✅
`frontend/src/components/map/MapView.tsx` (`MapToolbar` rend les +/−, bouton ajouté dans la même colonne sous les +/−).
Le bouton « Vue de l'île » efface commune/fiche commune/fiche parcelle et **force le recadrage** sur l'emprise de l'île (`refitCommune` bump un nonce même si on est déjà en mode île mais zoomé à la main).
**Navigation (vérifiée en code + runtime)** : `dragPan` (classe `maplibregl-touch-drag-pan` présente), molette (`scrollZoom` défaut maplibre, non désactivé), double-clic (`doubleClickZoom` activé hors outil de mesure), flèches clavier (`keyboard` défaut maplibre). **Curseur = main** (`cursor: grab`, vérifié en runtime). **Pas de joystick** — navigation maplibre native. Capture : `09-after-toolbar.png` (bouton ajouté sous +/−).

---

## MENU OUTILS

### 10. 16 phrases d'une ligne sous chaque outil ✅
`frontend/src/components/outils/registry.ts`. Chaque sous-titre réécrit en une ligne, sans « … », sans la police réduite `descSmall` (retirée des 5 outils concernés). **Les 16 phrases finales** :

1. **PLU** — « Le règlement d'urbanisme de chaque commune. »
2. **Permis** — « Qui construit quoi, et où, permis par permis. »
3. **Communes** — « Les 24 communes : marché, rythme, rareté. »
4. **Scan patrimoine** — « Ce qu'un propriétaire possède et construit. »
5. **Assemblage** — « Le potentiel de parcelles voisines réunies. »
6. **Comparer des parcelles** — « Des parcelles côte à côte, critère par critère. »
7. **Pièges et risques** — « Ce qui peut bloquer le projet, avant d'acheter. »
8. **Étude de zone** — « Habitants, emplois, marché autour d'une adresse. »
9. **Estimer un bien** — « Le prix d'un bien, par adresse ou annonce. »
10. **Remonter le temps** — « La parcelle vue du ciel, année après année. »
11. **Gabarit réglementaire** — « Où et jusqu'où implanter, selon les règles. »
12. **Taxe d'aménagement** — « La taxe du projet, calculée d'avance. »
13. **Prospection solaire** — « Les toits bien exposés, les piscines à équiper. »
14. **Blocs fonciers** — « Toutes les assiettes d'un même propriétaire. »
15. **Successions à venir** — « Le foncier à l'approche d'une succession. »
16. **Courrier propriétaire** — « Écrivez au propriétaire, LABUSE envoie. »

Captures : `10-before.png` (coupures « … » sur Permis, Étude de zone, Estimer, Gabarit) / `10-after.png`.

---

## TOUS LES OUTILS

### 11. Croix unifiée — plus de « changer » ni « Réinitialiser » nulle part ✅
Composant de référence : `EntreeParcelle.tsx` (carte à croix + phrase « La croix vide le champ… »).
- **Scan patrimoine (SCI MAHE / société)** : la carte société (`ScanPatrimoine.tsx`) adopte la grammaire de la croix — nom + SIREN + **✕** qui remet l'outil à zéro + phrase « La croix vide le champ : tapez un autre propriétaire ou SIREN. ». Le lien **« changer » est retiré**. Captures : `11-before.png` / `11-after.png` (exemple CBO TERRITORIA, le SIREN SCI MAHE n'étant pas résolu dans la base locale).
- **OwnerParcelles** (sous-panneau partagé Scan/Veille) : lien **« changer » retiré** (on recommence par la croix de la carte de sélection, ou la barre de recherche toujours visible en Veille).
- **Permis** : lien **« Réinitialiser les filtres » retiré** (`ModulePanel.tsx`, bloc proximité) — la parcelle de référence se vide par la croix, l'état revient au défaut via « Filtrer par état ».
- **Blocs fonciers** et **Successions à venir** (décision Vic, 2ᵉ passe) : le lien « Réinitialiser les filtres » est remplacé par **LA MÊME CROIX que partout ailleurs**, placée **en haut à droite du bloc de filtres**, qui **remet tous les filtres à leur valeur de départ**. Elle n'apparaît **que si un filtre a été modifié**. Captures : `11bis-blocs-before.png` / `11bis-blocs-after.png` · `11bis-successions-before.png` / `11bis-successions-after.png`.

### 12. État de chargement du Bouton vert lisible ✅
`frontend/src/components/Loading.tsx` + `frontend/src/components/ui/Bouton.tsx`.
**Cause** : `Chargement variant="inline"` forçait **toujours** `text-txt-mut` (gris) sur le wrapper, donc même avec `accent="courant"` les points (`bg-current`) et le libellé étaient gris → gris sur vert = illisible.
**Correctif** (dans le composant, donc partout) : quand `accent="courant"` (chargement **dans** un bouton plein), points + libellé prennent la **couleur du texte du bouton** (encre sombre). Un **état `loading`** a été ajouté au composant `Bouton` (désactive + `aria-busy` + Chargement en `currentColor`). Capture after : `12-after.png` (« Calcul de la zone… » en sombre lisible sur le vert). *Before : capture Vic (PDF p.12, gris sur vert) — l'état est transitoire.*

### 13. Pas de défilement horizontal dans un panneau d'outil ✅
`frontend/src/styles/index.css` + `frontend/src/components/outils/ModulePanel.tsx` (`data-outil-panel` sur l'aside des outils).
**Cause** : les corps d'outils défilent en vertical (`overflow-y-auto`) ; la règle CSS « si un axe est auto et l'autre visible, le visible devient auto » faisait apparaître une barre horizontale dès qu'un contenu débordait d'1 px.
**Correctif** : `[data-outil-panel] [class*="overflow-y-"] { overflow-x:hidden }` — force l'axe X à `hidden` sur tout conteneur défilant du panneau outil (la table plein écran des Communes vit hors de ce panneau, non affectée). Illustré par la rangée de rayons de l'Étude de zone (point 28) qui ne déborde plus.

---

## PLU

### 14. Retirer l'encadré « 974xx_reglement_….pdf · édition … · Indexé… » ✅
`frontend/src/components/outils/PluAnnuaire.tsx` (`data-plu-doc-etat` supprimé). L'en-tête « PLU du … » reste ; la recherche porte toujours sur le verbatim indexé, dit juste en dessous. Captures : `14-before.png` / `14-after.png` (mode recherche, Saint-Paul).

---

## PERMIS

### 15. En-tête — une seule section ✅
`frontend/src/components/outils/ModulePanel.tsx`. Fusion du triplet répété en **une** section : le nombre + « permis autorisés · Sitadel au JJ/MM/AAAA » + la précision « autorisés ≠ instruction en cours » repliée dans un « i ». Capture after : `15-16-after.png`. *Before : PDF Vic p.6.*

### 16. « Filtrer par état » — explication en « i », couleurs des points ✅
`frontend/src/lib/permisEtats.ts` + `ModulePanel.tsx` + `MapView.tsx`.
- Explication de chaque état **repliée dans un « i »** (plus de 2ᵉ ligne).
- **Quatre couleurs distinctes** (Achevé et Autre ne sont plus fondus) : **Récents = bleu** · **Dormants = rouge** (corail) · **Achevés = gris** · **Autres = orange** — **même source** (`PERMIS_ETAT_COLOR`) pour les **points de la carte**, les **pastilles du panneau** et la **légende**.
- La pastille porte un **liseré neutre** pour rester **visible quand la ligne est survolée/sélectionnée** (fond menthe) : le point « récent » (désormais **bleu**) ne disparaît plus sur le survol vert.
Capture after : `15-16-after.png`. *Before : PDF Vic p.7.*

### 17. Fiches de permis ouvertes depuis la carte — coupées en haut ✅
`frontend/src/components/map/MapView.tsx` (`ouvrirBullePermis`).
**Cause** : la fiche permis **chargée** est plus haute que l'estimation `_POP_H` (360 px) utilisée pour choisir l'ancre ; ancrée au-dessus d'un point, elle passait **sous la barre du haut** (coupée). C'est pourquoi « seuls les points récents semblaient s'ouvrir bien » (leur fiche, plus courte, ne dépassait pas).
**Correctif** : la hauteur de la bulle est **bornée** à la zone visible de la carte (et à `_POP_H`) avec défilement interne → l'ancre redevient exacte, la bulle est **toujours entièrement visible**, pour tous les types de points. *Avant/après : état lié à un clic carte ciblé ; correctif vérifié en code (la hauteur ne peut plus excéder le conteneur). Before : PDF Vic p.14.*

### 18. Bloc « Veille promoteurs » — remise en ordre ✅
`frontend/src/components/outils/VeillePromoteurs.tsx`. Recherche pleine largeur (inchangée) ; **Commune + Catégorie sur une ligne, même largeur** (grille 2 colonnes) ; **champ date avec libellé** « Opérations déposées depuis » ; **compteur « N opérations · N logements » sur une ligne** + « i » portant la définition d'une opération ; « 200 affichées (plafond 200) » remplacé par **« Les 200 premières sont affichées : affinez la recherche »** uniquement quand le plafond est atteint. Capture after : `18-after.png`. *Before : PDF Vic p.11.*

---

## COMMUNES

### 19. Colonne « €/m² VEFA » souvent vide — vérification ℹ️ (normal, aucun correctif)
**Verdict : NORMAL.** La colonne est vide quand le nombre de ventes VEFA **à €/m² calculable** est **< 8** (seuil `config/dvf_profils.yaml:68`, lu par `neuf_vefa_seuil()` ; décision d'affichage `api/comparateur.py:60-63`). Fenêtre : 5 ans ancrés sur la dernière vente VEFA (pivot 2025-12-31). C'est l'état réel du marché réunionnais (la VEFA est rare hors grandes communes), pas un trou de données.

Table de preuve (24 communes, fenêtre 5 ans) :

| Commune | n VEFA calculable | médiane €/m² | affiché |
|---|---|---|---|
| Saint-Denis | 355 | 4878 | ✅ |
| Saint-Paul | 326 | 4745 | ✅ |
| Saint-Pierre | 158 | 4931 | ✅ |
| Saint-Leu | 155 | 4958 | ✅ |
| Le Tampon | 130 | 4785 | ✅ |
| La Possession | 88 | 4221 | ✅ |
| Sainte-Marie | 83 | 4190 | ✅ |
| L'Étang-Salé | 66 | 4796 | ✅ |
| Petite-Île | 25 | 5277 | ✅ |
| Les Trois-Bassins | 15 | 6370 | ✅ |
| Saint-Benoît | 6 | 1304 | — (n<8) |
| Saint-Louis | 5 | 2421 | — (n<8) |
| Le Port | 1 | 5406 | — (n<8) |
| Saint-André | 1 | 2933 | — (n<8) |
| Bras-Panon | 1 | 1837 | — (n<8) |
| Sainte-Suzanne | 1 | 238 | — (n<8) |
| Salazie | 1 | 1366 | — (n<8) |
| Les Avirons · Saint-Joseph · Cilaos · Entre-Deux · La Plaine-des-Palmistes · Saint-Philippe · Sainte-Rose | 0 | — | — (0 vente) |

**10/24 affichées, 14/24 sous le seuil** — conforme au constat documenté dans le code (`dvf_marche.py:185-186`). Le **« i » existe déjà** sur l'en-tête de colonne (`blocB.tsx`, `O6Comparateur`) : « — = moins de 8 ventes VEFA (médiane instable sous le seuil) ». **Aucun correctif requis.** Capture : `19-after.png` (table avec « — » et l'en-tête « €/m² VEFA (i) »).

---

## SCAN PATRIMOINE

### 20. Onglet Construction à zéro opération — n'afficher que « Aucune opération pour ce filtre. » ✅
`frontend/src/components/outils/VeillePromoteurs.tsx` (mode `strict`). Quand le propriétaire ciblé n'a rien construit (`strictVide`), on masque : le titre « Ce qu'ils construisent », le texte d'explication, le compteur « 0 opération · 0 logements… » et la note de bas. Restent uniquement **« Aucune opération pour ce filtre. »** et le **bouton réservé à l'admin** (pour l'admin). *Correctif vérifié en code ; capture d'un propriétaire à 0 opération non reproduite faute de société « sans construction » identifiée dans la base locale. Before : PDF Vic p.7-8.*

---

## ASSEMBLAGE

### 21. Couleurs hors charte + « estimé » en badge + écart en texte normal ✅
`frontend/src/components/outils/moteurs.tsx`.
**D'où viennent les couleurs** : « 159 m² estimés » était en **orange** (`text-amber`, ligne « Après démolition ») et « −263 m² par rapport à l'existant » en **rouge** (`text-st-ecartee` quand l'écart est négatif). Ces couleurs signalaient à tort une **opinion** sur un simple **chiffre estimé**.
**Correctif** : plus de texte coloré hors charte — le nombre est en texte normal, **« estimé » passe par le badge habituel** (neutre), et l'écart s'écrit en **texte normal avec son signe** (`+`/`−`). Captures : `21-22-before.png` / `21-22-after.png`.

### 22. « par rapport à l'existant » qui déborde ✅
Même carte : retrait du `whitespace-nowrap` sur l'écart (+ conteneur `flex-wrap`) → le texte **passe à la ligne** au lieu de déborder de la case. Captures : `21-22-before.png` (texte coupé à droite) / `21-22-after.png`.

### 23. Retirer le bouton « Étude de faisabilité de cet assemblage → » ✅
`frontend/src/components/outils/moteurs.tsx`. Le pont est retiré de l'Assemblage (l'Étude de faisabilité reste accessible par Docs). Before : `23-before.png` (bouton présent) ; after : bouton absent (cf. `21-22-after.png`, plus de bouton en pied).

---

## COMPARER DES PARCELLES

### 24. « Comparer (3/3) » n'affichait que la barre de titre — reproduit, corrigé, testé ✅
`frontend/src/components/compare/ComparePanel.tsx` (+ test `CompareTableau.test.tsx`).
**Reproduction / cause** : l'API `/compare` répond correctement (3 parcelles → 3 lignes, vérifié). Le bug est **front** : le rendu du tableau ne traitait **que trois cas** (0 parcelle · requête en cours · `parcels>0`). Si la requête **échoue** ou **répond sans parcelle exploitable** (parcelles ignorées / hors périmètre, cas possible en prod), **plus rien** ne s'affichait sous le titre → exactement le symptôme de Vic.
**Correctif** : ajout des deux états manquants — **erreur** (avec réessai, `data-compare-erreur`) et **« aucune donnée »** (`data-compare-aucune`). L'utilisateur a toujours un retour ; le cas nominal affiche bien le tableau.
**Test ajouté** (`CompareTableau.test.tsx`, 3 cas) : parcelles → tableau ; réponse vide → repli ; échec → état d'erreur. *Avec les parcelles de Vic (BZ0824/BZ0381/BZ1065), le tableau s'affiche désormais (3 colonnes, vérifié). Before : PDF Vic p.15.*

### 25. Sous-titre « Jusqu'à 3 parcelles — barre ou clic carte. » → retirer le suffixe ✅
`ComparePanel.tsx` → « Jusqu'à 3 parcelles. ». Capture after : `25-after.png`. *Before : PDF Vic p.15.*

---

## PIÈGES ET RISQUES

### 26. Retirer de l'écran « Non couvert : oléoducs… » — contenu dans le « i » ✅
`frontend/src/components/outils/blocB.tsx` (`O5Servitudes`). Le texte « Non couvert : oléoducs (Le Port, Sainte-Marie)… Le certificat d'urbanisme fait foi. » est retiré de l'écran et **déplacé dans un « i »**. À l'écran il ne reste qu'une mention discrète « Couverture des contrôles » + le « i ».

### 27. Retirer l'encart « Aucune intersection détectée » et ses puces — familles dans le même « i » ✅
Même composant. L'encart « AUCUNE INTERSECTION DÉTECTÉE » et ses puces (Sols pollués, Bruit, ICPE, Monuments et sites, ER/EBC, Eau et zones humides, Espaces naturels, Procédure PLU) sont retirés. La **liste des familles contrôlées sans résultat** va dans **le même « i »** que le point 26.
Test mis à jour (`blocB.O5.test.tsx`) : vérifie que l'encart visible a disparu et que les familles + « Non couvert » sont dans le « i ». Captures : `26-27-before.png` (les deux encarts) / `26-27-after.png` (ligne discrète + « i »).

---

## ÉTUDE DE ZONE

### 28. Sélecteur de rayon — retirer « 5 km », refaire les marges ✅
`frontend/src/components/outils/EtudeZone.tsx`. Les rayons servis sont filtrés `≤ 2` → **0,5 / 1 / 2 km** (le back sait toujours calculer 5 km, l'UI ne le propose plus). Marges refaites : les boutons se répartissent (`flex-1`, largeur égale) et peuvent passer à la ligne → **la rangée tient dans son cadre sans rien couper** (plus de défilement horizontal, cf. point 13). Captures : `28-before.png` (0,5/1/2/**5** serré) / `28-after.png` (0,5/1/2 réparti).

### 29. Les sept sections de l'accordéon fermées par défaut ✅
`EtudeZone.tsx` : `openSecs` initialisé à `new Set()` (plus d'ouverture d'office d'« Immobilier »). Les 7 sections (Population, Économie, Immobilier, Foncier, Contraintes, Équipements, Dynamique) sont **toutes fermées** au départ. Captures : `29-before.png` (Immobilier ouvert) / `29-after.png` (tout fermé).

---

## ESTIMER

### 30. Choisir une parcelle ouvre la fiche + retirer le lien « Ouvrir la fiche parcelle → » ✅
`frontend/src/components/outils/AnalyserAnnonce.tsx` (outil « Estimer un bien »). À la sélection d'une parcelle, l'appel passe de `focusParcelle(parcelle)` à `focusParcelle(parcelle, { fiche: true })` → **la fiche s'ouvre** en même temps, **l'outil reste ouvert** à gauche (même comportement que la Calculette foncière). Le lien **« Ouvrir la fiche parcelle → » n'existe plus** dans le code `main` (retiré lors d'un refactor antérieur ; la capture de Vic, p.2, vient du build prod plus ancien) — rien à retirer de plus.

---

## PROSPECTION SOLAIRE, DOCS, CRM

### 31. Tuiles « Piscines » et « Ensoleillement » — retirer les deux flèches ✅
`frontend/src/components/outils/ProspectionSolaire.tsx`. La flèche « → » est retirée des deux tuiles. Captures : `31-before.png` / `31-after.png`.

### 32. Page Docs — retirer la flèche de chaque tuile ✅
`frontend/src/components/documents/DocumentsView.tsx` (`DocCard`). La flèche « → » en tête de chaque tuile est retirée. Captures : `32-before.png` / `32-after.png`.

### 33. CRM — haut de la première carte coupé sous l'en-tête ✅
`frontend/src/components/crm/Kanban.tsx`. Le conteneur des cartes (`overflow-y-auto`, `px-2.5 pb-2.5`) n'avait **pas de padding haut** : la 1ʳᵉ carte était collée sous l'en-tête de colonne et son bord supérieur (ring/ombre/badge) était coupé. Ajout de **`pt-2.5`**. Captures : `33-before.png` / `33-after.png`.

---

## Récapitulatif

| # | Point | État | # | Point | État |
|---|---|---|---|---|---|
| 1 | Rangée survol | ✅ | 18 | Veille promoteurs | ✅ |
| 2 | Copilote icône | ✅ | 19 | €/m² VEFA | ℹ️ normal |
| 3 | Bandeau RNU | ✅ | 20 | Scan Construction 0 | ✅ |
| 4 | Courrier SPF flèche | ✅ | 21 | Assemblage couleurs | ✅ |
| 5 | Signal marché wrap | ✅ | 22 | Assemblage débord | ✅ |
| 6 | Non identifié → Copropriété | ✅ | 23 | Assemblage bouton Étude | ✅ |
| 7 | Étiquettes communes | ✅ | 24 | Comparer vide + test | ✅ |
| 8 | Hint zoom retiré | ✅ | 25 | Comparer sous-titre | ✅ |
| 9 | Vue de l'île + nav | ✅ | 26 | Pièges « Non couvert » → i | ✅ |
| 10 | 16 phrases | ✅ | 27 | Pièges « Aucune intersection » → i | ✅ |
| 11 | Croix unifiée (dont Blocs/Successions) | ✅ | 28 | Rayon sans 5 km | ✅ |
| 12 | Bouton loading lisible | ✅ | 29 | Accordéon fermé | ✅ |
| 13 | Pas de scroll horizontal | ✅ | 30 | Estimer ouvre fiche | ✅ |
| 14 | PLU encadré retiré | ✅ | 31 | Tuiles solaires flèches | ✅ |
| 15 | Permis en-tête fusionnée | ✅ | 32 | Docs tuiles flèches | ✅ |
| 16 | Permis états i + couleurs | ✅ | 33 | CRM carte coupée | ✅ |
| 17 | Permis fiche coupée | ✅ | | | |

Tous les points sont traités. L'arbitrage du point 11 est tranché : Blocs et Successions passent aussi à la croix (en haut à droite du bloc de filtres, visible seulement si un filtre a été modifié, remet tout au départ).
