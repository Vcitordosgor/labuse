# RAPPORT M55-K — 5 finitions front (12/08/2026)

**Branche** : `feat/m55-k` (base : main `0999f925` = M55-J mergé). **6 commits** (un par point +
rapport). **FRONT uniquement** — aucun changement moteur/endpoint. CC ne merge jamais. Captures :
`reports/m55-k/captures/`, harnais `frontend/qa/m55k_captures.mjs`.

---

## Point 1 — ventilation : ligne de synthèse + « (filtres actifs) » retirées
**Constat** : sous la ventilation, une 2ᵉ ligne « N parcelles analysées → M opportunités détectées ·
filtres appliqués » entièrement dérivable de la ventilation, + double mention du filtrage
(« (filtres actifs) » puis « · filtres appliqués »).
**Modification** : suppression de la ligne de synthèse (composant `LigneClassement`) et de
« (filtres actifs) ». « (dans la zone) » CONSERVÉ (un polygone dessiné n'est pas visible autrement
— signal distinct, non redondant).

**Constat obligatoire — « opportunités détectées » : définition, appelants, sort** :
- **Définition** : `opportunites = uni.data?.opportunites ?? counts.brulante + counts.chaude`
  = **brûlantes + chaudes** (champ API `/filtre`, ou repli client).
- **Appelants** : (a) `LigneClassement` (var locale `opportunites`) = la ligne retirée ; (b) le
  **tooltip de la ventilation** (`title` ligne, `uni.data.opportunites` + `opportunites_evenement`)
  — VIVANT ; (c) l'outil `blocB.tsx` (son propre `opportunites`, endpoint différent) — VIVANT.
- **Sort** : retrait de l'affichage (LigneClassement) + des variables locales `opportunites` et
  `nFilters` (0-caller). **Le concept n'est PAS mort** : il reste servi par le tooltip de la
  ventilation et l'API/blocB. `total` conservé (pied de liste).
- **Vérifié** : jeu mixte (île) — ventilation = 118 + 1 038 + 2 964 + 29 978 + 43 210 + 354 355
  = **431 663** (somme boucle) ; synthèse et « filtres actifs » absents.

**Fichiers** : `ResultsSection.tsx`. **Commit** : `74326081`.

## Point 2 — deux entrées sur une seule ligne
**Constat** : « Comprendre le classement » / « Comprendre le scoring » débordaient sur deux lignes,
le premier coupé.
**Modification** : renommés « **Info classement** » / « **Info scoring** » (+ `text-[10px]`,
`px-1.5`, `whitespace-nowrap`). Destinations inchangées (deux modales distinctes, acquis M55-J).
**Vérifié à la largeur de panneau LA PLUS ÉTROITE** (240 px = clamp min, viewport ≤ 1000) : les
deux tiennent côte à côte sur une ligne (hauteur 21 px, même ligne) ; idem à 340 px.
**Fichiers** : `strings.ts`, `LeftPanel.tsx`. **Commit** : `c3846a35`.

## Point 3 — Relancer/Désactiver : cadre retiré, contour rouge sur Désactiver
**Constat** : cadre à liseré vert autour des deux boutons ; « désactiver » = lien souligné gris.
**Modification** : le cadre vert n'entoure plus QUE le rituel (décompte/révélation) ; à l'état
post-analyse les deux boutons vivent seuls. « Relancer » = variante DS `primary` (mint plein) ;
« Désactiver » = nouvelle variante DS `danger` (contour rouge `st-ecartee`, fond transparent).
Composant `ActionBtn` (un seul endroit pour la famille).

**Réserve rapportée — nuance rouge Désactiver vs Réinitialiser** : les deux partagent le MÊME
token `st-ecartee` (rgb 232,105,90). Ils diffèrent DÉJÀ par la nuance : **Désactiver** = `border/60`
+ texte pleine opacité (plus marqué, c'est une action de la paire principale) ; **Réinitialiser**
= `border/40` + texte `/80` (plus estompé, danger discret). Vic peut décider de les distinguer
davantage (teinte) si la gravité différente (Désactiver réversible vs Réinitialiser destructif)
doit sauter aux yeux. **Fichiers** : `FiltreLabuse.tsx`. **Commit** : `fff371b0`.

## Point 4 — récap « ANALYSE EN COURS » retiré à la bonne étape
**Les deux étapes identifiées** (le récap `data-analyse-recap` s'affichait à toutes les étapes
`analyseActive`) :
- **COUNTING** (précédente — « au moment où les filtres viennent d'être figés ») : récap présent,
  **pas de phrase** (décompte). → récap CONSERVÉ.
- **REVEALED** (courante) : récap présent **ET** phrase « … Selon vos critères (…) : … » présente. →
  récap RETIRÉ.

**Constat obligatoire — critères lisibles à l'étape du retrait ?** OUI : à REVEALED, la phrase
« **Selon vos critères (Saint-Denis)** » de la carte de révélation porte les critères. Preuve
(sonde) : COUNTING = récap présent + décompte ; REVEALED = récap absent + « Selon vos critères »
présent. → **suppression franche, aucun angle mort**.

Nota : à l'état POST-ANALYSE (Relancer/Désactiver), il n'y a PAS de phrase — le récap y est la
SEULE source des critères, il y est donc CONSERVÉ (le retirer là créerait l'angle mort que le
constat obligatoire proscrit). **Fichiers** : `FiltreLabuse.tsx`. **Commit** : `e60d35fb`.

## Point 5 — panneau plein hauteur, fond continu
**CAUSE MESURÉE** (avant tout correctif) : l'`<aside>` (le panneau) occupe **DÉJÀ** toute la
hauteur — `h-full` résout (l'aside est un flex-child stretched), `aside.bottom == viewport` dans
**tous les états** (accueil / filtres / post-analyse) et **toutes les tailles** (700/900/1200/1400),
`scrollHeight == clientHeight`, et le pixel au bas du panneau est bien l'aside en `bg-surface-1`
(rgb 11,16,13) — fond continu jusqu'en bas. La « zone noire vide » = ce surface-1 sous le contenu,
qui EST la cible (« espace en bas à l'intérieur du panneau »).

**La vraie cause de l'impression « le panneau s'arrête »** : (1) les tiroirs Couches/Filtres sont
plafonnés à `max-h-[Xvh]` — ils ne remplissent pas la place quand il n'y a ni accueil ni résultats
sous eux (jusqu'à **396 px** de gap mesuré à 1400×) ; (2) un **séparateur ORPHELIN**
(`border-t`) est rendu après les filtres même quand rien ne suit (VerdictHero null, ResultsSection
null), matérialisant un faux « fin du panneau ».

**Fix** : `sectionFill = accueilVu && !verdict` — quand la section ouverte est le DERNIER contenu,
son conteneur et son tiroir passent en `flex-1 min-h-0` (remplissent, sans plafond) et le
séparateur orphelin n'est plus rendu → contenu + fond surface-1 continus jusqu'en bas. Sinon
(accueil ou résultats présents, eux `flex-1`) : comportement plafonné inchangé.

**Non-régressions vérifiées** : scroll interne sur contenu long (viewport 640 : scrollHeight 1002 >
clientHeight 440, scroll fonctionne) · accueil M55-I (logo intégralement visible) · post-analyse
(ResultsSection `flex-1` remplit, listing intact) · invariant accordéon (défaut A · après analyse B ·
page fraîche A · jamais 0 ni 2) · pas de débordement horizontal (`overflow-x-clip` conservé).
**Fichiers** : `LeftPanel.tsx`. **Commit** : `4ba7ee8d`.

---

## Validation (non-régression globale)
- **5 combinaisons /filtre** strictement identiques (front-only) : 431 663 · 38 138 · 1 156 ·
  2 458 · 948.
- **Ventilation** (K1) sur jeu mixte : somme des 6 paliers boucle sur 431 663.
- **K2** : deux boutons sur une ligne au panneau 240 px.
- **Accordéon** : défaut A · analyse → B · page fraîche → A · invariant tenu.
- **Persistance filtres** intacte après rechargement (URL porte `c=Saint-Denis`).
- **Console** : 0 erreur. **tsc 0 · vitest 32/32 · build vert**.

## Périmètre
Front + libellés (strings.ts). Aucun changement moteur, aucun endpoint. `feat/m55-k` en attente de
merge par Vic.
