# RETOURS-26 — recette de RETOURS-25 (suite)

Branche `fix/retours-23` (même branche), worktree `~/Desktop/labuse-outils`, ports 10010/7210.
**Pas de merge, aucun accès prod.** Vérifié dans **WebKit** (playwright 1.49.1, webkit-2104, reducedMotion) —
une capture par point dans `captures/` (gitignorées ; seul ce compte-rendu est suivi).

Hook complet **VERT** : `tsc -b` 0 · vitest **310/310** · `vite build` OK · scan secrets « rien trouvé » ·
pytest unitaires **3211 passed** (49 skipped = famille base, hors unitaires).

---

## 1. Boîte parcelle unique — option A, dans TOUS les outils

Maquette `docs/design/maquettes/nov-2026/10-boite-parcelle.png`, **option A**. Une fois la parcelle choisie
(saisie OU clic carte), le champ **reste rempli** : **adresse entière en gras** (passe à deux lignes si
besoin, jamais coupée), puis **« IDU · zone · surface »** en dessous, avec une **croix ✕** à droite qui vide
le champ et réaffiche la recherche. **Plus aucun bouton ni lien « Changer de parcelle » nulle part.**

- `EntreeParcelle.tsx` (le composant partagé) : bloc « parcelle choisie » réécrit en boîte option A. Épingle
  mint `◎`, adresse `font-semibold` `break-words`, méta `IDU · zone · surface` en mono discret, bouton ✕
  (`data-entree-vider`, `onChanger`), phrase d'aide dessous. Capture : **`p01-boite-parcelle.png`**
  (« 3 Chemin de la Citerne, 97417 Saint-Denis » · « BZ 1065 · Uh · 1 567 m² » · ✕).
- La **zone PLU** manquait à la source : ajoutée à `/parcels/search` côté back (`app.py`, `COALESCE(zone_lib,
  zone_fam)`, `LEFT JOIN parcel_zone_plu` **après le LIMIT** — ≤ 10 lignes, jamais un scan par parcelle ;
  gardée par `_zone_plu_ready`) et au type `searchParcels` (`lib/api.ts`). Vérifié live : `zone_plu` = « Uh »,
  « UAm », « UA » selon la parcelle.
- Comme tous les outils partagent `EntreeParcelle`, la boîte s'applique d'un coup à **Pièges, Gabarit, Taxe,
  Solaire, Calculette, Blocs/Successions, Comparer** et à **Remonter le temps** (son picker vit dans le
  panneau gauche `ModulePanel`, déjà `EntreeParcelle` → la boîte option A y apparaît automatiquement).
- **Estimer** (`AnalyserAnnonce.tsx`) n'utilisait pas `EntreeParcelle` (deux écrans + en-tête « · Changer de
  parcelle ») : refondu sur `EntreeParcelle` (un seul écran, champ → boîte remplie → rapport dessous ; la
  croix revient à la recherche). Le lien « Changer de parcelle » est **supprimé**.
- Les tests `EntreeParcelle.test.tsx` / `ClicCarte.test.tsx` sont mis à jour (plus de « Changer de parcelle » ;
  la croix `data-entree-vider` appelle `onChanger`).

## 2. Assemblage — espace, 4 lignes, libellés

Capture : **`p02-assemblage-bilan.png`** (BZ1065 + BZ0389 + BZ0798 + BZ0799, contiguës).

- **Espace tuiles ↔ « Bilan »** : la carte de résultat passe en `flex flex-col gap-2` → un espace **normal et
  constant** sépare les tuiles de « Bilan » (avant elles étaient collées, et « Bilan » ouvert empiétait).
- **Les 4 lignes du Bilan tiennent chacune sur une ligne** : libellé à gauche, valeur à droite ; la **précision**
  (€/m² de terrain, source DVF · fiabilité) passe **en dessous**, petite et alignée à droite, au lieu
  d'allonger la valeur et de la faire passer à la ligne. (Charge foncière estimée · Prix de sortie · Marché de
  la zone · la 4ᵉ ci-dessous.)
- **« Parcelles chiffrables 1/3 » → « Prix connu pour 1 parcelle sur 3 »** : libellé « Prix connu pour », valeur
  « N parcelle(s) sur M ». Vérifié WebKit : « Prix connu pour **1 parcelle sur 4** ».
- **« (approche plus lourde) » retiré** (ligne propriétaires). Vérifié WebKit : absent.
- **Phrase « Indivision : non détectable en open data… » retirée.** Vérifié WebKit : absente.
- **Titre « Étape 1 — » retiré** (une seule étape) → « Choisir les parcelles (N maximum) ». Vérifié WebKit :
  « Étape 1 » absent de la page.

## 3. Scan patrimoine — espace entre les deux chemins

Capture : **`p03-scan-chemins.png`**. Cause trouvée : la classe `.door` porte `margin-bottom:8px` ; les deux
chemins étaient dans `flex flex-col gap-2` **sans** `mb-0`, d'où 8 px (gap) + 8 px (marge) = **16 px**, le
double des autres outils (Communes, Solaire, qui mettent `mb-0`). Correctif : `mb-0` sur chaque `.door` → seul
le `gap-2` (8 px) compte, **même espace que partout ailleurs**.

## 4. Estimer — champ « surface habitable » saisissable, sans flèches

Capture : **`p04-estimer-surface.png`**. Le champ passe de `type="number"` (flèches haut/bas) à
`type="text" inputMode="numeric"` : **aucune flèche**, **clavier numérique** sur mobile, les non-chiffres sont
filtrés à la frappe. La valeur est **validée à la sortie du champ (blur) ou sur Entrée** — un brouillon local
(`surfaceDraft`) n'est reporté dans la valeur qui pilote l'estimation (`surfaceHab`) qu'à ce moment. Vérifié
WebKit : `type=text`, `inputmode=numeric`.

## 5. Gabarit 3D — les deux hauteurs écrites SUR la vue

Captures : **`p05-gabarit-3d-bz1065.png`** et **`p05b-gabarit-3d-ap1319.png`**.

Deux pastilles sont posées **sur la vue 3D** : **« Règle : X m »** (vert) et **« Bâti : N m »** (gris). Ce sont
des **Marker maplibre** (overlay HTML) : alignés sur l'écran (billboard), donc **droits et lisibles sous tous
les angles** (pitch/rotation). Détails techniques qui ont demandé deux corrections :
- le décalage écran passe par l'option **`offset`** du Marker, **pas** par un `transform` CSS sur l'élément
  (maplibre écrase le `transform` de l'élément par son propre transform de positionnement — sans quoi les
  pastilles se superposaient) ;
- les deux pastilles sont ancrées au **même point** (centre de la parcelle), séparées horizontalement (Règle à
  gauche, Bâti à droite) et verticalement **au prorata de la hauteur** → la pastille physiquement la plus haute
  s'affiche la plus haute, qu'il s'agisse de la règle ou du bâti.

**Le bâti est-il réellement à la hauteur de l'enveloppe ? NON — mesuré, il la DÉPASSE sur les deux parcelles.**
- **BZ1065** (demandée) : règle **7 m**, bâti existant **10 m** → le bâti dépasse la limite réglementaire
  actuelle.
- **AP1319 Saint-André** (2ᵉ témoin) : règle **17 m**, bâti **19 m** → même constat.

C'est cohérent et honnête : l'enveloppe verte est extrudée à la **hauteur MAXIMALE que la règle autorise
aujourd'hui** ; le bâti gris est extrudé à sa **hauteur RÉELLE mesurée** (LiDAR HD / BD TOPO). Quand une
construction est **antérieure à un abaissement du PLU**, elle peut donc **dépasser** l'enveloppe — ce n'est pas
un défaut de calcul, c'est « ce qui est là » vs « ce que la règle permet désormais ». Le texte d'explication du
panneau, qui affirmait à tort « le bâti est plus bas », est **réécrit en conditionnel** (sous / au-dessus / à la
hauteur) à partir des deux valeurs réelles.

> **Parcelle de la capture de Vic** : son IDU exact n'était pas fourni ; la vérification porte sur **BZ1065**
> (explicitement demandée) et un second témoin **AP1319 (Saint-André)**. Sur les deux, le bâti dépasse
> l'enveloppe — à confirmer sur l'IDU précis de Vic s'il nous le transmet (le mécanisme est générique).

## 6. Gabarit — règles non intégrées en UN SEUL bloc

Capture : **`p06-gabarit-regles-un-bloc.png`**. L'accordéon séparé « Le détail des N règles non intégrées »
(qui vivait dans la carte Couverture) **disparaît**. La **boîte jaune « ⚠ N règles applicables non intégrées »**
(sous « Voir les règles appliquées ») **DEVIENT l'accordéon** : son en-tête déplie **en dedans** le détail
complet (nom · pourquoi · source), exactement ce que renvoie le moteur (`nonIntegratedRules`), rien d'inventé.
Vérifié WebKit : **un seul** `[data-gabarit-non-integrees]`, situé dans « Voir les règles appliquées ».

## 7. Fiche parcelle — espaces noirs réduits autour des 6 tuiles

Capture : **`p07-fiche-tuiles.png`**. Les tuiles cumulaient un `marginTop:6` (inline) **et** un `padding:12px 0`
sur `.stats`, qui s'ajoutaient au `gap-3` (12 px) du conteneur défilant → ~30 px de vide noir au-dessus et
24 px au-dessous. Correctifs : `marginTop` retiré et `.stats` `padding:12px 0 → 0`. L'écart haut/bas des tuiles
vaut désormais **exactement le `gap-3` de la fiche** — le même rythme que le reste (entre sections).

---

## Fichiers touchés
**Front** : `outils/EntreeParcelle.tsx` (boîte option A) · `outils/AnalyserAnnonce.tsx` (Estimer : EntreeParcelle
+ champ surface) · `outils/moteurs.tsx` (Assemblage) · `outils/ScanPatrimoine.tsx` (chemins) ·
`outils/Gabarit.tsx` (hauteurs sur la vue + règles un bloc) · `outils/ModulePanel.tsx` (commentaire temps) ·
`components/fiche/Fiche.tsx` + `styles/index.css` (tuiles) · `lib/api.ts` (zone_plu) ·
`outils/EntreeParcelle.test.tsx` · `outils/ClicCarte.test.tsx`.
**Back** : `api/app.py` (`/parcels/search` → `zone_plu` dominante, joint après le LIMIT, gardé par
`_zone_plu_ready`).

## Reproduire les captures
Backend `PYTHONPATH=src …/.venv/bin/python -m uvicorn labuse.api.app:app --port 7210` · Vite
`LABUSE_API_DEV=http://127.0.0.1:7210 npx vite --port 10010` · `node /tmp/retours26-captures.mjs`
(+ `/tmp/retours26-fix.mjs` pour les vues 3D cadrées). Pilotage via `window.__labuse` (setModule/select/setMsel).
