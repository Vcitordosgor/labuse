# M22-FINITION — UNIFICATION DES 8 PDF · RAPPORT

Branche unique **`fix/m22-f-unification`**, basée sur `feat/m22-d-potentiel` **+ merge de
`feat/m22-b-lettre-zonage`** (la lettre est une branche sœur de la lignée 0→A→C→D : sans
elle, impossible d'unifier les 4 briques ni de faire C8 ; merge de branches de travail,
PAS un merge dans main — l'ordre Vic devient **0→A→B→C→D→F**, F arrivant sans conflit
puisqu'elle contient déjà B). Golden 116/116 (:8024, dev_mode). Suite 1144 verts, 10 échecs
= les mêmes préexistants que main. Preuves : `qa/revue_pdf_v2/` (8 documents, PNG 150 dpi
page à page + PDF sources) vs `qa/revue_pdf/` de la revue v1 (non versionnée, zip fourni).

## Correctifs livrés (ordre de priorité du mandat)

### C1 — COHÉRENCE DES CHIFFRES (boussole) ✅
- `bilan_params_defaut()` (bilan.py) = **LA source d'hypothèses unique** (2500 €/m² SDP,
  21 % marge & frais agrégés) ; le bilan du Banquier (`briques_pdf.collect`) et la
  calculette la consomment tous deux — la calculette n'y superpose que les saisies.
- Encadré « **Hypothèses de calcul** » IDENTIQUE en forme (`hypotheses_encadre`, brique),
  rendu dans le Banquier (section bilan) ET l'Argumentaire (partie 5).
- **Tests** : `test_c1_banquier_et_calculette_memes_totaux` (mêmes CA + charge foncière),
  `test_c1_encadre_hypotheses_identique_en_forme`.
- **Preuve sur pièce** : AC0197 → **160 k€** dans le Banquier (p.1, synthèse + héros) ET
  l'Argumentaire (p.1, héros + phrase). La v1 disait 103 k€ vs 160 k€.

### C2 — UNE SEULE IDENTITÉ VISUELLE ✅
- `briques_pdf.PAGE_CSS` porte désormais la **DA impression du Flash** : @font-face
  Inter / JetBrains Mono / Space Grotesk (OFL, api/fonts), palette menthe print, h1/h2
  Space Grotesk, cartouches `.cartouche` (styles du Flash), page de garde avec
  **wordmark + silhouette** (`wordmark_html`, path SVG source unique pdf_premium).
- **Une seule carte Situation** : le plan cadastral clair partout (`map_html(ign=False)`
  par défaut — l'ortho IGN reste disponible en option, plus jamais par défaut).
- Puces Sourcé/Estimé conservées ; pieds légaux conservés et présents sur les 8 documents.

### C7 — BANDEAU DE CONTEXTE PARTOUT ✅
- `render_pdf(..., produit=, idu=, commune=)` → bandeau running du Flash sur **chaque
  page** des 4 briques : « LABUSE — produit · IDU — commune » + date à droite, filet
  menthe. La page de garde porte le wordmark graphique à la place (même règle que le
  Flash). Aucune page orpheline : vérifiable sur toute page intérieure de
  `qa/revue_pdf_v2/{banquier,lettre_zonage,argumentaire,potentiel}/`.

### C6 — CHIFFRE-HÉROS ✅
- `.cartouche.hero .valeur` 27 pt menthe (style cartouche Flash, pas de nouvelle DA) :
  Argumentaire p.1 = **prix d'achat max** ; Potentiel p.1 = **SDP résiduelle** (toujours
  « Estimé » : dérivée de règles calibrées) ; Banquier p.1 = **charge foncière** — les
  trois à la même taille.

### C4 — LES DEUX PAGES FAIBLES ✅
- **Fiche parcelle p.1** : carte VERDICT LABUSE en tête (gros label coloré, méta à
  droite), sections cascade en **cartouches M19** (« Règles d'urbanisme », « Risques »,
  « Marché », « Propriétaire ») avec résumé (n signaux · somme des poids), **plafond
  2 pages** avec compteur honnête (« … N signaux non imprimés — la fiche écran porte la
  liste complète »). 2 pages conservées.
- **Fiche projet** : un champ vide **ne s'imprime pas** (plus jamais de « — ») ; sous
  3 sections remplies → bandeau « Projet en cours de constitution » (preuve : Projet
  Beta #34, quasi vide → bandeau rendu).

### C8 — LA LETTRE DEVIENT UNE ATTESTATION ✅
- **Référence unique `LZ-AAAA-NNNN`** stockée en base (table additive
  `lettre_zonage_refs`, une référence par édition, retry sur collision, contrainte
  UNIQUE) ; **date d'édition en tête** (ligne de référence sous le titre) ; **bloc de
  clôture « Édité par LABUSE »** (n°, date, « permet de vérifier l'authenticité de
  l'édition » — le mot « opposable » reste banni pour la lettre).
- Preuve : `qa/revue_pdf_v2/lettre_zonage/` (réf LZ-2026-0001 en tête, clôture p.3).

### C3 — TITRES ET DIFFÉRENCIATION ✅
- Template Flash/Dossier : **h1 = le produit** (« Rapport Flash » / « Dossier
  parcelle ») + sous-titre descriptif « Étude de faisabilité indicative d'une parcelle » ;
  `TEMPLATE_VERSION 1.1 → 1.2` (cache invalidé proprement). La mention « Généré via
  LABUSE pour [raison sociale] » du Dossier s'imprime déjà sur chaque page (couverture
  incluse, position fixe — inchangé).
- Lettre §2 : « **PLU de Saint-Paul, approuvé le 27/09/2012** » en tableau ; le nom de
  fichier du règlement passe en note.
- Argumentaire : borne basse ≤ 0 **interdite dans la phrase de synthèse** → « dans le
  scénario bas, l'opération ne supporte aucune charge foncière » (rendu sur AC0197).

### C9 — DEUX DATAVIZ (optionnel : FAIT) ✅
- **Bande de points DVF** (Argumentaire, partie 2) : chaque vente retenue = un point
  (clé additive `prix_points` de `sector_price` — les prix RETENUS, aucune agrégation
  nouvelle), médiane marquée, bornes affichées, note « aucune vente n'est fabriquée ni
  lissée ».
- **Cascade du bilan à rebours** (Argumentaire, partie 5) : CA → − marge & frais →
  − construction (→ − VRD) → = terrain, **termes exacts du moteur** (clé additive `calc`
  de `compute_calculette`, aucun recalcul), scénario médian, valeurs sur les barres.
- Style : Inter, vert LABUSE, fonds clairs — DA existante, SVG inline WeasyPrint.

## C5 — LIGNE ÉDITORIALE BANQUIER vs ARGUMENTAIRE (rapport seul, décision Vic)

**Le problème** : 3 pages quasi identiques (comparables DVF, 11 steps de faisabilité,
bilan) — un client qui achète les deux paie deux fois le même cœur.

**La distinction proposée** (un document = un lecteur = une question) :
- **Dossier banquier** — *lecteur : le financeur du PORTEUR*. Question : « ce projet
  tient-il debout ? ». Il doit RASSURER : synthèse exécutive, sérieux du chiffrage,
  risques assumés, marge. Pages à SPÉCIALISER : garder la faisabilité 11 steps INTÉGRALE
  (le banquier veut la traçabilité), garder le Score É (marge), AJOUTER un plan de
  financement indicatif (apport/foncier/construction — données déjà présentes) et un
  échéancier type de l'opération. RETIRER : l'écart de négociation (hors sujet devant un
  banquier).
- **Argumentaire de négociation** — *lecteur : le VENDEUR (en face du promoteur)*.
  Question : « pourquoi ce prix ? ». Il doit DÉMONTRER : le marché point par point (C9),
  la cascade (C9), l'écart. Pages à SPÉCIALISER : remplacer la faisabilité 11 steps par
  un RÉSUMÉ 4 lignes (SDP, logements, hauteur, articles clés — le vendeur n'a pas besoin
  du moteur complet), garder réductions de capacité + vigilance. RETIRER : le Score É et
  les permis SITADEL détaillés (posture interne, pas de négociation).
- **Règle de gamme** : le Banquier = POUR CONVAINCRE UN TIERS DE FINANCER ; l'Argumentaire
  = POUR FONDER UN PRIX FACE AU VENDEUR. Le seul contenu commun légitime : identité de la
  parcelle + tableau des prix DVF (la donnée est la même, la lecture diffère).

**Décision Vic attendue** : valider cette spécialisation (mandat de mise en œuvre séparé),
ou assumer le recouvrement (deux portes d'entrée du même socle, prix distincts).

## Notes honnêtes
- **Paginations v2** : flash 7 · dossier 7 · banquier 7 (6 en v1 : la garde DA aère) ·
  fiche 2 · lettre 3 · argumentaire 8 (6 en v1 : + 2 dataviz) · potentiel 6 · projet 1.
- Le Banquier n'est PLUS pixel-identique à la v1 (c'était l'invariant du LOT 0) : M22-F
  **assume** de le refondre visuellement (C2/C6/C7) — les totaux, sections et doctrine
  sont inchangés, les chiffres changent UNIQUEMENT par C1 (hypothèses unifiées).
- `test_banquier.py::test_bilan_porte_score_e_et_estime` et consorts passent sans
  modification (les sections gardent leur structure interne).
- Générations de preuve : synthèse IA neutralisée (clé vidée) — repli déterministe.
- ⚠ Session M-RENOUV toujours active dans le clone principal : M22-F a été développé
  dans un **worktree isolé** (`labuse-m22f`) — zéro collision cette fois.
