# RELIQUATS FRONT (PJ2 · PJ4 · PJ5 · PJ6 + UI O2/O3) — rapport

Branche `fenetre/reliquats-front` (issue de main APRÈS merge de `fenetre/outils-suite` — prérequis tenu).
Un PJ = un lot = un commit. DA existante partout (dark, mint, violet premium). Zéro touche scoring/servi/golden.
**Validation finale = les yeux de Vic en local** (UI) ; les tests d'affichage (pattern `test_front_m2` :
marqueurs dans le source) sont le garde-fou de régression.

---

## R1 · PJ6 — le panneau IA ne cache plus la fiche ✅

**Constat honnête** : le lien « Voir l'entièreté de la fiche » (`data-askbar-voir-fiche`), le repli par
défaut et la réponse gardée existaient déjà (fix post-validation E, mergé). **Ce qui manquait — et ce que
Vic voyait** : le panneau déplié n'était PAS borné ; une réponse longue le gonflait et poussait l'en-tête
+ la nav des onglets hors du panneau (le panneau est au-dessus de la nav dans le flux).

**Règle dure appliquée** (`AskBar.tsx`) : zone de réponse **bornée à 36vh avec scroll interne**
(`data-askbar-reponse`) → le panneau IA ne peut plus chasser la nav, quelle que soit la longueur.
- Avant : réponse non bornée → nav hors écran sur réponse longue. Après : réponse scrolle en interne,
  en-tête + nav toujours visibles et cliquables.
- Repli mémorisé pendant la consultation (état React) ; reset volontaire au changement de parcelle
  (« l'IA ne s'impose jamais ») ; redéploiement 1 clic, cache inchangé (« aucun nouvel appel »).
- Tests : replié par défaut ; lien présent avec réponse ; réponse bornée ; redéploiement sans perte ;
  nav hors du panneau. **5/5.**

## R2 · PJ2 — boutons du parcours de tri ✅

**Constat** : Retenir (mint plein) / Écarter (corail) existaient, la sortie (✕ Quitter, barre haute, sobre,
`text-txt-mut`) était déjà distincte — mais **« À analyser » manquait sur la carte de décision** (la
mutation + `moveItem` + compteurs le géraient déjà : bouton jamais branché).

- Bouton **« ? À analyser »** ajouté entre Écarter et Retenir (`data-decision-analyser`), à la couleur de
  sa colonne d'arrivée Kanban **#E8B44C** — règle « une décision = la couleur de sa colonne » vraie pour
  les trois (écartée #E8695A · à analyser #E8B44C · retenue mint). Retenir reste le seul bouton plein.
- Titles explicites (réversibilité, destination). **Raccourcis clavier : il n'en existe pas → on n'en
  invente pas** (règle du lot, commentée dans le code).
- Tests : trois décisions présentes ; couleurs = colonnes Kanban ; sortie distincte ; pas de raccourcis
  inventés. **4/4.**

## R3 · PJ5 — tooltips + wording « deux brûlantes » ✅

- **Tooltip ×N** (panneau de résultats, `data-mult-tip`) : « Multiplicateur de rang — cette parcelle est
  classée N fois au-dessus de la moyenne de l'univers analysé. » Factuel ; **jamais de RR** en surface
  client (testé).
- **Tooltip jauge** : « Complétude des données : N/100 — part des sources disponibles pour cette
  parcelle. N'est PAS une note de qualité du terrain. »
- **Règle de wording appliquée — le mot exact : « Priorité dossier »** (cohérent avec l'existant matrice :
  À surveiller / À creuser / Écartée). L'échelle thermique (brûlante/chaude) est **réservée au tier P
  servi** ; la matrice Q×A ne parle plus thermique. Clé interne `chaude` **inchangée** (zéro régression
  API). Appliqué partout où la matrice s'affiche :
  | Surface | Avant | Après |
  |---|---|---|
  | `status.ts` (source du label) | Chaude | **Priorité dossier** |
  | Légende carte (mode legacy) | VERDICT | **VERDICT · MATRICE Q×A** + tooltip |
  | Fiche — bandeau événement | force « chaude » | force « priorité dossier » |
  | Fiche — section synthèse événement | Chaude par ÉVÉNEMENT | Priorité dossier par ÉVÉNEMENT |
  | Marqueurs communes (compteur = `matrice_statut`) | N chaudes | N en priorité dossier (matrice Q×A) |
  | Chip liste tier v2 | Chaudes | Chaudes **v2** (harmonisé avec Brûlantes v2) |
- **Désambiguïsation côte à côte** : `TierBadge` (tier v2 + « (matrice : …) ») porte le tooltip « Deux
  classements distincts… ce n'est pas le même calcul ».
- Résiduels vérifiés légitimes : IAStub/SegmentsPage/compteurs = tier P v2 ou clés internes.
- Tests : 5/5 (+ `test_front_m2` 6/6 inchangés).

## R4 · PJ4 — nettoyage visuel : **sans objet** (vérifié) ✅

**La surface d'origine n'existe plus** : l'ancienne restitution carte a été remplacée par M2 (kanban
`ProjetKanban` + parcours `ParcoursTinder` ; la « restitution » actuelle est le panneau copilote, pas une
carte). **Vérification d'héritage « brouillon » sur la carte du nouveau contexte** (`MapView`) : couches
thématiques opt-in (`visibility:'none'` par défaut), opacités faibles (0,10-0,22), labels communes à
source unique (Markers DOM) avec **anti-chevauchement déjà consigné** (OFFSETS côte Nord dense),
pastilles `#rang` conditionnées au zoom, liseré promues sans doublon v2/legacy (filtres exclusifs).
**Aucun brouillon hérité, rien de trivial à corriger.**

---

## R5 · UI des outils O2 et O3 ✅ (décision mi-course honorée)

### O2 · Scoreur d'adresse inversé — trouvable en < 5 s
- **Bouton « ⌖ Scorer une adresse » dans le header, à côté de la recherche** (`data-scoreur-open`,
  `Header.tsx`) → panneau (`ScoreurAdresse.tsx`) : champ **« Collez une adresse »** (autofocus) + champ
  **prix demandé € optionnel** (« saisi à la main — jamais scrapé », title explicite) → `POST /scoreur-adresse`.
- **Fiche verdict** : adresse résolue, tier (via `TierBadge` — « hors run » honnête si non évaluée),
  commune/surface/IDU, **Score É** (libellé avec niveau), et si prix fourni la **confrontation** :
  chip Opportunité (mint) / Dans le marché (ambre) / Cher pour un opérateur (corail) / Non estimable,
  message + marge résiduelle + avertissement Estimé de l'API. **Hors base → message honnête** de l'API,
  jamais un verdict inventé. Lien « Ouvrir la fiche complète → » (`select(idu)`).
- C'est l'outil de démo « seconde opinion avant d'offrir » : un clic depuis n'importe quel écran.

### O3 · Anti-fiche « Pourquoi pas ? » — onglet de fiche conditionnel
- **Onglet « Pourquoi pas ? »** ajouté à la nav de la fiche **seulement pour les parcelles écartées ou
  flaggées** (`verdictEcartee || lines.some(SOFT_FLAG)`) — `GET /anti-fiche/{idu}` à l'ouverture de
  l'onglet (pas de fetch inutile).
- Rendu tel que servi : cadre + synthèse, motifs **RÉDHIBITOIRE** (✕ corail) puis **VIGILANCE** (⚠ ambre),
  **chaque motif avec sa source** ; « aucun motif » affiché tel quel (rien d'inventé) ; avertissement API.
- **Règle PJ6 respectée** : l'onglet vit dans la même barre de nav (toujours visible) ; le panneau du
  scoreur est un overlay du header qui ne recouvre pas la nav de la fiche.
- `api.ts` : `scoreurAdresse()` + `getAntiFiche()` typés (pattern `j<T>` existant).

---

# STOP FINAL

## Récapitulatif
5 lots, 5 commits, sur `fenetre/reliquats-front` (issue de main post-merge outils-suite — prérequis tenu).
**Tests front : 21/21 reliquats + 6/6 M2 (inchangés) = 27 verts ; `tsc --noEmit` propre ; `vite build` OK.**
Zéro touche scoring/servi/golden ; DA existante réutilisée partout (dark, mint, violet premium, tokens
couleur du Kanban M2).

## La règle de wording appliquée (et où)
**« L'échelle thermique est réservée au tier P servi »** — mot retenu pour la matrice Q×A :
**« Priorité dossier »** (clé interne `chaude` inchangée, zéro régression API). Surfaces modifiées :
`status.ts` (source), légende carte (« VERDICT · MATRICE Q×A »), fiche (bandeau + synthèse événement),
marqueurs communes (compteur backend = matrice), chip liste « Chaudes v2 » (harmonisation) ; tooltip de
désambiguïsation sur `TierBadge` (seul endroit où les deux classements coexistent côte à côte).

## Captures avant/après
Les tests d'affichage figent les marqueurs de chaque lot (avant/après décrits précisément par lot
ci-dessus). **Les captures d'écran sont remplacées par la validation visuelle de Vic en local** — c'est
la voie prévue par le mandat (« c'est de l'UI — ses yeux ») ; aucun harnais de capture navigateur n'est
branché sur cette branche (finding ci-dessous).

## Findings
1. **PJ6 était aux ⅔ fait** (fix post-validation E mergé) — le manque réel était l'absence de borne de
   hauteur du panneau (la nav sortait de l'écran sur réponse longue). Corrigé par la règle dure (36vh).
2. **« À analyser » existait partout sauf à l'écran** (mutation, compteurs, Kanban) — seul le bouton
   manquait dans la carte de décision. Symptomatique des livraisons « backend prêt, surface oubliée ».
3. Un **harnais de captures** (playwright + serveur seedé) rendrait les prochains mandats UI
   auto-documentants — à considérer post-M7.
4. `IAStub` (exemples NL « les chaudes… ») parle le langage de recherche du tier P v2 — conforme à la
   règle, non modifié.
