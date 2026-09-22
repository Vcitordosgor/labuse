# RAPPORT M55-J — Bug carte d'analyse + 6 finitions (12/08/2026)

**Branche** : `feat/m55-j` (base : main `945660fa` = M55-I mergé). **8 commits** (un par point,
J5a = audit sans code) + ce rapport. **FRONT uniquement** — aucun changement moteur/endpoint.
CC ne merge jamais. Captures : `reports/m55-j/captures/`, harnais `frontend/qa/m55j_captures.mjs`.

---

## Point 1 (BUG) — la carte d'analyse ne mélange plus deux runs
**Constat reproduit** : filtres posés → analyse lancée → un filtre ajouté pendant la
révélation → « LABUSE a analysé les **33 622** parcelles… **77 308** retenues » →
retenues > analysées (faux positif). Cause : `fresh` (retenues+ventilation) figé au lancement,
mais `analyseTotal` (trameQ), `recap` et `perimetre` suivaient les filtres LIVE → divergence.

**Correctifs** (`FiltreLabuse.tsx`, `strings.ts`) :
1. **Snapshot du lancement** : à `lancer()`, on fige `snapFilters` et on tire LES DEUX effectifs
   du run (`fresh` = retenues/ventilation, `freshTrame` = effectif analysé). La carte dérive
   ENTIÈREMENT du snapshot (analysées, retenues, ventilation, récap, périmètre) — un seul run.
   L'intro n'affiche l'effectif analysé que depuis `freshTrame` (jamais le live).
2. **Filtres figés** pendant l'analyse (voir arbitrage ci-dessous).
3. **Filet d'invalidation** : si un chemin EXTERNE (sélecteur commune du header, URL, retour
   arrière) déplace les filtres pendant la révélation, `stale = !filtersEqual(filters, snapFilters)`
   → la carte affiche un état neutre « Vos critères ont changé — Relancer » plutôt qu'un chiffre
   périmé.

**Contrôle retenues ≤ analysées** : garanti par construction (les deux nombres viennent du même
run ; analysées = retenues + écartées).

**Preuve — les 4 chemins testés (harnais), aucun `retenues > analysées`** :
| chemin | résultat |
|---|---|
| (a) séquence du bug (ajout filtre pendant révélation) | filtres masqués (impossible) · ret 4 801 ≤ analysées 38 138 ✓ |
| (b) chemin externe (commune du header pendant révélation) | carte invalidée, phrase périmée masquée ✓ |
| (c) rechargement page fraîche avec `al=1` | aucune carte-phrase orpheline (phase idle) ✓ |
| (d) retour arrière navigateur | aucune phrase divergente ✓ |

**Arbitrage « disparaître » vs « désactiver » — choix : DISPARAÎTRE (+ récap)**, justifié :
- J'ai d'abord livré « désactiver » (`<fieldset disabled>`, filtres grisés visibles) en J1.
- Le point 6 (accordéon) a révélé l'interaction : garder les filtres VISIBLES rend la section
  Filtres HAUTE (~510 px) → ouvrir Filtres pendant l'analyse ne laisse PAS le listing récupérer
  la hauteur (contradiction avec J6). Le point 6 anticipe d'ailleurs le cas « si les filtres sont
  masqués ».
- J'ai donc **basculé (dans le commit J6) sur « disparaître »** : pendant l'analyse, les
  contrôles de filtres sont retirés et remplacés par un **récap compact des critères du run**
  (« ANALYSE EN COURS · Saint-Denis · Filtres figés — Relancer/Désactiver pour les changer »).
  J1 l'autorise explicitement (« la liste des critères doit rester lisible dans la carte »).
  Bénéfices : gel par NON-RENDU (encore plus robuste que disabled) + section Filtres compacte →
  le listing récupère la hauteur (J6). La liste des critères reste lisible.

**Fichiers** : `FiltreLabuse.tsx`, `strings.ts`. **Commits** : `3d12459c` (J1), `56a6cbe8` (bascule vers récap, avec J6).

## Point 2 — bloc Relancer/Désactiver : deux boutons hiérarchisés
Le lien souligné gris « désactiver » devient un vrai bouton. Composant `ActionBtn` factorisé
(un seul endroit pour la famille), variantes `primary` (Relancer, mint) / `secondary`
(Désactiver, contour). Majuscules initiales. **Fichier** : `FiltreLabuse.tsx`. **Commit** : `8edf2fe6`.

## Point 3 — accueil : retrait des trois « i »
**Garde-fou — contenu de chaque infobulle et son sort** :
| « i » | contenu | réserve d'honnêteté ? | sort |
|---|---|---|---|
| parcelles | « Compte exact du classement servi, recalculé à chaque mise à jour majeure. » | non (paraphrase + fraîcheur, déjà dite par le paragraphe « chaque donnée porte sa date ») | supprimé |
| communes | « Cadastre DGFiP — toutes les communes de La Réunion, sans exception. » | non (couverture POSITIVE + source DGFiP, présente sur la page Sources) | supprimé |
| sources | « Catalogue Sources : connecteurs publics actifs (DEAL, DGFiP, INSEE, BODACC, Sitadel…) — voir l'onglet Sources. » | non (pointeur vers la page Sources, accessible au Rail) | supprimé |

Aucune ne portait de réserve (millésime, « partiel », estimation) → **suppression franche**.
Le sourcing détaillé vit sur la page Sources (inchangée). `CLIENT.accueil.src` = 0-caller,
supprimé. **Fichiers** : `LeftPanel.tsx`, `strings.ts`. **Commit** : `fe39d6d9`.

## Point 4 — accueil : paragraphe élargi (largeur partagée), tenir sans scroll
Titre et paragraphe tirent leur largeur maximale d'**une seule valeur partagée** `--accueil-w`
(240 px, CSS var) — plus deux largeurs en dur. Le paragraphe (jadis `max-w-[32ch]`, plus étroit)
s'aligne sur le titre. Padding externe allégé (pt-6/pb-8 → pt-5/pb-5). Acquis M55-I préservé
(`justify-start` + `my-auto`, **logo entier aux 6 tailles**, revérifié).

**Hauteurs mesurées (contenu / disponible / écart, scroll)** :
| taille | avant | après |
|---|---|---|
| 1440×900 | 306 / 333 · scroll | 290 / 333 · **tient sans scroll** ✓ |
| 1200×800 | 306 / 271 · scroll | 290 / 271 · écart ~19 px |
| 1024×700 | 348 / 209 · scroll | 348 / 209 · écart **139 px** |
| 900×700 | 348 / 209 · scroll | 348 / 209 · écart **139 px** |
| 768×800 | 348 / 271 · scroll | 348 / 271 · écart 77 px |

**Écart résiduel — pour arbitrage Vic** : le levier « paragraphe » agit aux panneaux LARGES
(1440/1200, contenu 306→290). Aux panneaux ≤ 1024 px de large, le titre est déjà sur 3 lignes
(conteneur ~189 px) et le paragraphe remplit déjà la largeur → le levier n'a plus de prise. La
contrainte résiduelle est que **Couches ouverte** ne laisse que 209-271 px à l'accueil alors que
le contenu fait 290-348 px. Résorber cet écart demanderait de collapser Couches pendant l'accueil,
réduire la police du titre ou couper du contenu — hors du levier de ce point. **Commit** : `b0434a9a`.

## Point 5a — audit de caducité des paliers (source de vérité : la BASE)
Paliers **réellement produits par le moteur** (`SELECT tier … FROM parcel_p_score_v2 WHERE
run_id='q_v8_calibre'`, 11 valeurs distinctes) confrontés aux libellés affichés et à la modale :

| palier moteur (base) | n | libellé affiché (status.ts / ventilation) | décrit dans la modale ? |
|---|---|---|---|
| brulante | 118 | Brûlante | non (la modale décrit la MÉTHODE, pas les paliers) |
| chaude | 1 038 | Chaude | non |
| reserve_fonciere | 2 964 | Potentiel long terme | non |
| a_creuser | 29 978 | À creuser | non |
| declasse_bati_sature | 29 907 | Potentiel épuisé · bâti saturé | non |
| declasse_non_constructible | 6 168 | Potentiel épuisé · inconstructible (géométrie) | non |
| declasse_bati_revele | 4 051 | Potentiel épuisé · bâti révélé | non |
| declasse_zone_fermee | 2 804 | Potentiel épuisé · fermée à l'urbanisation | non |
| declasse_au_statut_inconnu | 210 | Potentiel épuisé · AU à statut inconnu | non |
| declasse_au_fermee | 70 | Potentiel épuisé · AU fermée | non |
| ecartee | 354 355 (= étage 0) | Écartée | non |

**Findings** : palier décrit-mais-absent-du-moteur = **AUCUN** ; libellé divergent = **AUCUN**
(les 11 paliers ont un libellé affiché cohérent partout — status.ts, ventilation, defTiers,
ScoringV2 ; les 6 `declasse_*` regroupés en « Potentiel épuisé »). La modale décrit la MÉTHODE
(mutabilité, ×N, entraînement), pas les paliers — c'est l'absence que 5b comble. Seule scorie :
un commentaire docstring stale « Réserve foncière » dans `ScoringV2.tsx` (NON affiché — le libellé
y est « Potentiel long terme »). **→ Pas d'écart de vocabulaire → 5b débloqué.**

## Point 5b — deux entrées Classement / Scoring côte à côte
Deux entrées JUMELLES dans le bandeau de l'analyse (même traitement) : « Comprendre le
classement » (méthode) et « Comprendre le scoring » (sens des paliers), chacune sa modale
(`store.algoModale`). Le lien isolé « comprendre le scoring → » du bas des résultats DISPARAÎT
(**constat** : il n'était pas en fin de listing long — juste sous la ventilation, en tête du
bloc — donc aucun service « visibilité de fin de liste » perdu). Contenu « scoring » : réutilise
`CLIENT.revelation.defTiers` (échelle verbale EXISTANTE, source unique aussi utilisée par les
tooltips de la carte d'analyse) + `defTiers.ecartee` ajouté comme source unique ; couleurs =
palette `status.ts`. Aucune définition dupliquée. **Fichiers** : `LeftPanel.tsx`, `ResultsSection.tsx`,
`useApp.ts`, `strings.ts`. **Commit** : `bcae381d`.

## Point 6 — accordéon : Couches se rétracte à l'ouverture de l'Analyse
Transition EXPLICITE (effet `verdict false→true` → `panneauSection='filtres'`, champ unique —
retirée des `onRetract` dispersés). Couches se rétracte, Filtres devient la section ouverte
(elle porte le récap compact + Relancer/Désactiver) → le listing récupère la hauteur.
**Articulation avec J1** : les filtres étant MASQUÉS (récap) pendant l'analyse, la section Filtres
est compacte — c'est ce qui permet au listing de gagner la hauteur. L'invariant « exactement une
section ouverte » tient (vérifié : défaut A, après analyse B, page fraîche A, jamais 0 ni 2).
**Fichiers** : `LeftPanel.tsx`, `FiltreLabuse.tsx`. **Commit** : `56a6cbe8`.

## Point 7 — « Masquer » → « Retour », destination unique
**Grep exhaustif de « Masquer »** (toutes formes, `frontend/src`) : **1 seule occurrence
affichée** — le bouton `data-verdict-off` du bandeau VerdictHero, qui sert LES DEUX bandeaux
(« Tri factuel — sans analyse » ET « ✓ Analyse LABUSE affichée »). Autres hits = commentaires
(App.tsx « masquer sous la fiche », ResultsSection « masquer les copropriétés » retiré). Renommé
« **Retour** ». **Destination définie à UN seul endroit** (`store.retourFiltres`) : sortir de la
vue verdict (analyse ou tri factuel) + `panneauSection='filtres'` + `analyseLabuse=false` →
atterrit sur **Filtres ouvert et éditable**, jamais Couches (cohérent avec J6). Vérifié sur les
deux bandeaux. **Fichiers** : `useApp.ts`, `LeftPanel.tsx`. **Commit** : `1856d431`.

---

## Validation (non-régression)
- **Point 1** : les 4 chemins → aucun `retenues > analysées` (tableau ci-dessus).
- **Accueil** : mesuré taille par taille (tableau P4) ; **logo M55-I toujours entier** aux 6 tailles.
- **Accordéon** : défaut A · après analyse B (J6) · page réellement fraîche → A · invariant tenu
  (jamais 0 ni 2 sections).
- **Console** : 0 erreur. **Persistance filtres** intacte après rechargement (URL porte `c=Saint-Denis`).
- **tsc 0 · vitest 32/32 · build vert**.
- **Ventilation bouclée** : 13 + 90 + 127 + 1 876 + 2 695 = 4 801 retenues + 33 337 écartées
  = **38 138** (total Saint-Denis) ✓.
- **5 combinaisons /filtre** strictement identiques (front-only, aucun endpoint touché).

## Périmètre
Front + libellés (strings.ts). Aucun changement moteur, aucun endpoint. `feat/m55-j` en attente
de merge par Vic.
