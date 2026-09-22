# RAPPORT M65 — Passe visuelle : accueil, rail, couches, chrome, mode Clair

Branche `feat/m65-passe-visuelle` (depuis `main` = `07873273`, qui contient M64 mergé par Vic).
**NON mergé** (doctrine : CC ne merge jamais). tsc 0 · vitest inchangé · build vert.

## Précondition — note
Au démarrage du mandat, M64 n'était pas encore dans `main` (M64 = `99460eec` sur `feat/m64-carte`).
Pendant la clarification, **Vic a mergé `feat/m64-carte` dans `main`** (`07873273` « Merge branch 'feat/m64-carte' »).
La branche M65 est donc bien issue de `main` **avec** M64 — le point 8 a pu redéfinir le mode Clair M64. Choix confirmé par Vic : « Depuis main ».

## Décisions Vic prises en cours de mandat
- **3ᵉ case « sources » = 52** (sources branchées, `data_sources status='connecte'`), servie dynamiquement par `/accueil/chiffres`. Le « 62 » du mandat = **total catalogue** (connecte 52 + partiel 4 + a_faire 4 + manuel 2). Divergence mesurée et remontée ; rien codé en dur.
- **Base = `main`** (et non STOP/attente).
- **Contour d'île** validé après nettoyage (voir P8).
- **Précision** : Sombre = défaut au boot ET au reload ; Clair = bascule manuelle, jamais persistée → implémenté (`readBasemap` retourne toujours `'dark'`, `setBasemap` non persistée).

## Points livrés

**P1 — Bandeaux d'attention supprimés.** Bandeau ambre `.band` « Marché peu actif à … » (`Fiche.tsx`, monté 1×, `qualite_commune.degradee`) retiré : JSX + règles CSS `.band` + tokens `--f-amberband/txt/ico` (plus aucun usage). **Donnée non orpheline** : le tiroir « Qualité de la mesure · <commune> » (`data-qualite-commune`) porte le détail complet, indépendamment.

**P2 — Accueil refondu** (`LeftPanel.AccueilPreuves`, texte titre+paragraphe **inchangé mot pour mot**).
- (a) Bandeau 3 cases restylé (déjà 3 cases depuis M56-C) : grille 3 col gap 1px `#1E2622`, cases `#121815` rayon 10px ; chiffre 19px/500 `#F4F6F5` **au-dessus**, libellé 11px `#7C8A83` 4px dessous. Libellés : parcelles / communes / sources. Valeurs servies (431 663 / 24 / 52).
- (b) Halo respirant (`.accueil-halo` : cercle 520×520 `#4ADE80`, opacité 0,023↔0,067, échelle 0,945↔1,055, ~8s ; `prefers-reduced-motion` → fixe 0,045, sans animation). Conteneur `overflow-hidden`, halo z sous le contenu.
- (c) 2 boutons sur une ligne, largeurs égales, gap 9px : vert « Commencer → » (`#4ADE80`/`#06180E`, rayon 9px, padding 13px → ouvre Filtres) ; mauve « Découvrir LABUSE IA » (`#1A1430`/`#B9AEF2`/bord `#2E2552`, étincelles → **onglet Copilote**). Compteur `431 663` anime 0→valeur en 1,2s (sortie cubique), séparateur espace fine, **1×/session** (`sessionStorage`), reduced-motion → direct.

**P3 — Titres de catégories de couches → étiquettes.** `LE FOND / LES ZONAGES / RISQUES ET PROTECTIONS` : nouvelle classe `.layer-cat` (10px, ls 0,08em, `#7C8A83`, poids 400). « COUCHES » reste en `.label-caps`.

**P4 — Entrée « Recherche » retirée du rail (8→7).** Suppression : entrée rail + icône loupe, route `view==='ia'`, composant `IAStub.tsx` (`git rm`), import App, membre `'ia'` du type `View`. **Condition bloquante honorée** : `entretienDirect` câblé dans `CopiloteView` (préremplit le brief au montage, sans écraser une saisie), `ouvrirEntretien` bascule sur `'copilote'`. La recherche NL reste accessible via **l'omnibox du header** (`useApplySearch`, raccourci `/`). Câblage propre → suppression effectuée (pas de STOP).

**P5 — Boutons de carte à 70 %.** `BoutonCarte` (composant partagé, seule instance = zoom +/−) : 60→42px, glyphe 24→17px, rayon 12→8px ; gap conteneur 8→6px.

**P6 — Liseré vert de sélection au pointeur.** Ajout `:focus:not(:focus-visible){outline:none}` — aucun contour au clic ; `:focus-visible` (clavier, a11y) **conservé**. En-tête COUCHES / sections / cases sont de vrais `<button>` ; les pastilles « i » gardent leur `tabIndex` (exigence a11y, protégée par le mandat).

**P7 — Codes postaux retirés.** Sélecteur de communes du header (`Header.tsx`, « Toute l'île » + liste) : `<span>` du CP supprimé après le nom. **Identité intacte** (clé `c.insee`, sélection `c.commune`) ; lookup `CP_PAR_COMMUNE` + import `CP_COMMUNES` retirés (0-caller). Voir « À signaler ».

**P8 — Mode Clair : inversion figure/fond.** La **mer** (`bg`) reste **noire** (`#060A08`) dans les deux modes (revert du `bg` blanc M64). La **terre** s'éclaire :
- Nouvelle couche `ile-mass` (fill `#C9C4B8`) = masse terrestre → la terre sans parcelle (cirques/forêt/volcan) est grise ; posée tout en bas de la pile vectorielle (sous overlays + parcelles), masquée en Sombre.
- Parcelles (trame neutre) → `#F4F2EC` blanc cassé opaque en Clair (branche neutre de l'effet palette, `basemap` en deps).
- Nouvelle couche `ile-cote` (line `#4ADE80` 2,2px) = trait de côte, **sur le contour dissous uniquement**, au-dessus des remplissages.
- Limites parcelles `#B9B3A6`/0,5px · limites communes `#2E7D52`/1,6px (≈3×) en Clair.
- Traits achromatiques (sélection/pulse/étiquette de zone) : bascule sombre M64 **conservée**.
- Pastilles de commune : **inchangées** (revert de l'adaptation « pastille claire » M64) — valeurs Sombre dans les deux modes.

*Artefact données* : `public/ile974.geojson` = **dissolution hors-ligne** des 24 communes (`shapely.unary_union`). La dissolution brute laissait **109 slivers** internes (gaps de simplification) → **nettoyés** (anneaux internes retirés, aire +0,06 %) ; contour validé par Vic sur aperçu. Le trait de côte se pose sur ce contour extérieur seul, jamais sur les limites internes.

## Report DA
`docs/DA-LABUSE.html` : tableau « CARTE — SOMBRE / CLAIR » (couche par couche, 2 colonnes) + specs accueil/chrome (3 cases, halo, boutons, layer-cat, boutons carte, focus). Tokens `--map-bg`/`--map-ile-clair`/`--map-parcelle-clair`/`--map-cote-clair` (remplacent `--map-bg-clair` M64). Spec « bandeau d'attention » marquée retirée.

## À signaler (décisions Vic, hors périmètre strict)
1. **62 vs 52** : la 3ᵉ case affiche 52 (branchées). Si Vic veut 62, changer le filtre de `/accueil/chiffres` (`count(*)` sans `status='connecte'`).
2. **QA `.mjs` périmés** : `m11_b1_captures`, `m11_b2_captures`, `projet_unifie`, `fix_pv` contiennent `setView('ia')` désormais mort (`inspect_clic_tout` clique `title="IA"` = Copilote, OK). Captures historiques hors CI ; à repointer sur l'omnibox si rejouées. Non supprimées (doctrine : pas de suppression sans preuve).
3. **`ProjetEntretien.tsx`** : désormais 0-caller (seul IAStub l'importait). Laissé en place (réversible) ; le montage de projet passe par le brief Copilote.
4. **FiltreLabuse — chips CP** : la grille de filtre « 1 · Communes » affiche le CP *comme libellé* (sans nom) — hors cible « code postal après le nom ». Laissée telle quelle ; à confirmer si Vic la veut aussi épurée.
5. **Pastilles #0F1512/#F4F6F5** : le mandat cite ces valeurs ; j'ai conservé les valeurs Sombre existantes (hot/cold, menthe pour commune à chaudes) pour ne pas aplatir la sémantique. À trancher si Vic veut le token plat.
6. **Halo accueil vs « ni halo ni lueur »** : exception explicitement mandatée ; notée dans la DA.

## Captures
`reports/m65/captures/` : `accueil-apres.png`, `rail-apres.png`, `couches-apres.png`, `communes-apres.png`, `carte-sombre-apres.png`, `carte-clair-apres.png`, `carte-clair-zoom-apres.png`, `carte-clair-interieur-apres.png`, `zoom-boutons-apres.png`, **`carte-sombre-vs-clair.png`** (côte-à-côte). `ile_compare.png` (contour brut/nettoyé).
*Note* : captures « avant » pixel non produites — la reconstruction du baseline M64 en place (via stash) est risquée avec le `git rm` (nécessiterait un worktree séparé) ; le avant→après est documenté par les valeurs (diff + tableau DA). La comparaison « deux modes de carte » (Sombre|Clair) est livrée.
