# RAPPORT M58 — Tiroir Constructibilité — PHASE 0 (diagnostic)

Branche `feat/m58-constructibilite` (de `main`, qui contient b6 + m57). **Diagnostic
seul, aucun correctif.** Mesures : API `/modules/faisabilite/{idu}` (+ `/explain`),
`/parcels/{idu}`, code back, navigateur. Témoins : **97410000BM0950** (Saint-Benoît,
non constructible) et **97407000AI1821** (Le Port, constructible, zone Ud).

---

## Q1 — Contradiction logements (8-10 / 12-14 / 8-10)

**Origine mesurée (AI1821)** — 3 chiffres, UN seul calcul :
- **Tête / verdict** `capacite.verdict` = « R+6 · au sol ~10-11 logts » = la fourchette
  FINALE (`fourchette.logements_au_sol = [10,11]`), APRÈS plafonds.
- **Étape intermédiaire** `steps` : « Logements (avant plafonds) » = **~13 à 16**, puis
  « Plafond de densité (filet de sécurité) » = **≤ 11 logts** → le cap ramène 13-16 à 11.
- **Récit final** (`/explain`) : « …R+6… **10 à 11** logts » = de nouveau la valeur capée.

Ce n'est **PAS une contradiction** : c'est le **plafond de densité** appliqué ENTRE
l'étape « avant plafonds » (haute) et le total (bas). **Un seul rendement** (SHAB/SDP,
step « Surface habitable »), pas deux. La **valeur servie partout** (fiche
Constructibilité, PDF, scoring) = `fourchette.logements_au_sol` (capée). Le « 12-14 »
n'est qu'un chiffre d'étape intermédiaire, affiché tel quel dans la liste des steps →
il lit comme une incohérence. → Phase 1a : ne servir/affirmer qu'une valeur (la capée),
l'intermédiaire doit être clairement « avant plafonds ».

## Q2 — Contradiction zone (bandeau « A » vs capacité « AU*st »)

- Fiche `reglement_plu.zones` = **[A, Ub]** → bandeau « zone A ».
- Faisabilité `capacite.zone` = **'A'** (COHÉRENT avec le bandeau — même zone).
- MAIS `capacite.verdict` (`engine.py:183`) = chaîne **HARDCODÉE** : « Construction
  neuve non autorisée — secteur de transition **(AU\*st)** : travaux mineurs…, H max 4 m. »
  émise pour TOUT cas `not rules.constructible_neuf`, quelle que soit la zone réelle.

**Verdict** : les deux affichages lisent la MÊME zone (A) ; la contradiction vient du
**libellé de verdict générique** qui hardcode « AU*st » (+ « H max 4 m ») pour un cas
zone A. **Pas une régression M56-B4** (celle-ci = regex front ; ici = chaîne back de
longue date, `engine.py`). → Phase 1a : le verdict doit décrire la zone réelle (A =
agricole), pas un « AU*st » copié-collé.

## Q3 — « 0–0 logements », « Gabarit : ( m) », « SHAB vendable ~— »

Rendu par **FaisabiliteTab** (`Fiche.tsx:858-862`), bloc « Capacité constructible » :
```
Gabarit : {fo.niveaux} ({fo.hauteur_m} m)      → « ( m) » si absents
Logements : {logements_au_sol[0]}–{[1]}         → « 0–0 » (le ternaire teste isArray, PAS zéro)
SHAB vendable : ~{fmtM2(fo.shab_vendable_m2)}    → « ~— » si absent
```
Sur BM0950 (non constructible) `fourchette = {logements_au_sol:[0,0], logements_sous_sol:[0,0]}`,
pas de niveaux/hauteur/SHAB → « 0–0 », « ( m) », « ~— ». **La règle M56-B4 « un zéro
n'est pas une absence » n'a PAS été appliquée à CE bloc** : M56-B4 l'a posée sur la
VALEUR du tiroir (`logementsTxt`) et le bandeau 4 chiffres, jamais sur le rendu interne
de FaisabiliteTab. Le bloc s'affiche même quand `cap.verdict` dit « non autorisé ».
→ Phase 1c.

## Q4 — Doublon de capacité

Le tiroir Constructibilité rend TROIS composants (`Fiche.tsx:1852-1854`) :
`TransformationBlock` + **`FaisabiliteTab`** + **`BilanTab`** (si `!delaisse`).
- FaisabiliteTab : bloc **« Capacité constructible »** (verdict + gabarit/SDP/logements/SHAB
  + steps + IA + calculette).
- BilanTab : section **« Capacité (que peut accueillir ce terrain ?) »** (`{cap.verdict}`
  + SHAB vendable + stationnement) + Marché + Fiscal + RTAA.

**Même source** : les deux appellent `getFaisabilite` → `['bilan', idu]` → `b.capacite`.
Ce sont **deux composants distincts** qui rendent le **même `cap.verdict` + fourchette**
→ la capacité est affichée **deux fois**. → Phase 1b : un seul bloc.

## Q5 — Calculette de charge foncière « reste en Chargement »

Route mesurée : `/bilan/calculette-defaults` = **200** ; POST `/modules/faisabilite/{idu}/charge`
= **200**. **Dans le navigateur** (BM0950 + AI1821) : les 2 requêtes passent (200) et la
calculette **RÉSOUT** — BM0950 « Capacité constructible non résolue pour cette parcelle » ;
AI1821 « Charge foncière de marché non atteignable sur cette commune ». **Pas reproduite
comme bloquée.**

- **Code mort ?** NON : `<Calculette>` est rendu dans FaisabiliteTab (`Fiche.tsx:928`),
  l'emplacement ACTUEL de la charge foncière (le « déplacement vers Faisabilité » a déjà
  eu lieu — c'est bien là qu'elle vit). Pas dépréciée.
- **Fragilité RÉELLE** : `Calculette` reste sur `<Loading « Chargement »/>` tant que
  `!defs.data`, avec `useQuery(..., staleTime: Infinity)` **sans `retry` ni état d'erreur**.
  Si `calculette-defaults` échoue UNE fois (blip réseau), la calculette reste « Chargement »
  DÉFINITIVEMENT (pas de retry, pas de message). C'est le mode d'échec probable observé
  par le mandant. → à traiter (état d'erreur + retry), pas à supprimer comme code mort.

## Q6 — Bouton IA sur parcelle non calculable

`FaisabiliteTab` (`Fiche.tsx:903`) : le bouton « Expliquer ce calcul en clair » est affiché
`{cap && ...}` — dès que `cap` existe, MÊME si `cap` est un cas « non autorisé »
(fourchette [0,0], 0 step). Sur BM0950, `cap` existe (verdict « non autorisé », `steps=[]`)
→ le bouton IA s'affiche alors qu'il n'y a **aucun calcul (0 step) à expliquer**.
→ Phase 1e : conditionner à `steps.length > 0` (ou `cap.constructible`).

## Q7 — Taxe d'aménagement, le « 5 % »

`fiscal.ta_note` (back) = « Taxe d'aménagement : taux communal à confirmer en mairie
(non ingéré) — **hypothèse indicative 5 %** + part départementale. » Le 5 % est une
chaîne **hardcodée, purement AFFICHÉE**. `fiscal` ne contient que `qpv`, `tva`, `ta_note`.
La charge foncière (`postChargeFonciere`) n'utilise que coût + marge + prix — **le 5 %
n'alimente AUCUN calcul servi** (ni bilan ni charge). → Phase 1f : ne pas afficher de
taux inventé ; dire « taux communal non ingéré — à confirmer en mairie ».

## Q8 — RTAA DOM : références citées

**Ce que la fiche SERT réellement** (`b.rtaa.exigences`, mesuré) :
- cadre : **CCH art. R.192-1** (décret n°2024-168 du 01/03/2024)
- ecs : **CCH art. R.192-2** (décret n°2024-168, en vigueur 01/01/2025)
- thermique / acoustique / aération : **arrêtés du 17/04/2009** (les trois volets)
  modifiés **11/01/2016** (art. cités : th. 5/6/9/10/13 ; ac. 3/4/7/8/11 ; aér. 3/4/5-7).

**Écart avec l'énoncé du mandat** : le mandat demande de vérifier « CCH **R.182-1** » et
« CCH **R.162-1 à R.162-4** » — or la fiche cite **R.192-1 / R.192-2** (pas R.182, pas
R.162). Soit l'énoncé a mémorisé d'autres numéros, soit une autre version. **Je NE peux
PAS vérifier ces articles contre Légifrance dans cet environnement** (pas d'accès web
confirmé). **Citations non vérifiées ici, à confirmer** : R.192-1 / R.192-2 (recodification
2024-168) et le millésime « modifié 11/01/2016 » des arrêtés du 17/04/2009.
**Aucune correction d'autorité** (consigne respectée) — je signale, je ne tranche pas.

## Q9 — Ratio de grounding

Mesuré sur AI1821 (`capacite.steps[].prov`, **11 steps** — pas 8 ; le nombre varie
par parcelle/scénario) :
- **6 sourcée** (steps 1-4 emprise/reculs/%/niveaux ; 10-11 stationnement),
- **4 estimée** (occupation gabarit, SHAB rendement, logements avant plafonds, plafond),
- **1 dérivé** (SDP brute).
→ ≈ 55 % sourcé / 36 % estimé / 9 % dérivé. Les 4 premières étapes (géométrie/PLU) sont
sourcées ; les coefficients (occupation 45 %, hé 3 m, rendement SHAB) sont estimés.
**Note** : l'endpoint `/explain` renvoie une provenance AGRÉGÉE légèrement différente
(etape 1-4 SOURCE, 5-9 ESTIME) — deux représentations du grounding qui ne s'alignent pas
parfaitement (à unifier si Phase 1). BM0950 (non constructible) : **0 step** → aucun
grounding (rien à sourcer).

---

## Synthèse

| Q | Constat mesuré |
|---|---|
| 1 | 3 chiffres = un calcul avec **plafond de densité** (avant/après cap), pas 2 rendements ; valeur servie = la capée. |
| 2 | Bandeau et capacité lisent la MÊME zone (A) ; le verdict hardcode « AU*st » (`engine.py:183`) — libellé faux, pas régression M56-B4. |
| 3 | Bloc « Capacité constructible » (FaisabiliteTab) n'applique PAS « un zéro n'est pas une absence » → « 0–0 », « ( m) », « ~— ». |
| 4 | **Doublon** : FaisabiliteTab et BilanTab rendent la capacité (même `b.capacite`) deux fois. |
| 5 | Calculette **fonctionne** (200, résout) ; PAS code mort (elle EST la charge foncière de Faisabilité). Fragilité : `staleTime:Infinity` sans retry → « Chargement » définitif si un échec. |
| 6 | Bouton IA affiché dès que `cap` existe, même sans step à expliquer (BM0950 : 0 step). |
| 7 | « 5 % » = chaîne hardcodée `ta_note`, **purement affichée**, hors de tout calcul servi. |
| 8 | Fiche cite **R.192-1 / R.192-2** (pas R.182/R.162 de l'énoncé) + arrêtés 17/04/2009 mod. 11/01/2016 ; **non vérifiables ici** contre Légifrance — signalé, non corrigé. |
| 9 | 11 steps : **6 sourcée / 4 estimée / 1 dérivé** ; grounding `steps.prov` ≠ grounding `/explain` (à unifier). |

**Point séparé (carte masquée par la fiche)** : non diagnostiqué en P0 (correctif UI
d'ordre visuel, Phase 1). Constaté : la fiche (`<aside>` à droite, 400px) recouvre la
`MapToolbar` (Sombre/3D/outils, `absolute right-4 top-4`). Décalage à prévoir en Phase 1.

## STOP — PHASE 0
Phase 0 terminée. **Aucun correctif.** En attente d'arbitrage sur la Phase 1 (a→h) +
le point carte. Points ouverts pour le mandant : Q8 (numéros d'articles à confirmer —
R.192 servi vs R.182/R.162 de l'énoncé) ; Q5 (la calculette n'est pas bloquée ici — si
le mandant la revoit bloquée, l'IDU + la console aideraient). NE PAS MERGER.

---

# PHASE 1 — correctifs (arbitrage mandant)

Présentation + libellés (Q1/Q2/f = back, aucun **calcul** ni **route** modifiés — seules
des **chaînes servies** et le **rendu**). Témoins : **AI1821** (constructible, Le Port),
**BM0950** (non constructible, zone A, Saint-Benoît).

## Q1 — trois chiffres = un calcul avec plafond (libellés, PAS le calcul)
`engine.py` — steps reformulés, arithmétique **inchangée** :
- « Logements — **avant plafond de densité** » = `~13 à 16` (surface/logt).
- « Logements — **après plafond (≤ N logts)** » = valeur capée (AI1821 : `~11 à 11`).
- Tête (`verdict`) et récit final (`/explain`) citent **la même** valeur capée (la seule
  servie). Phrase ajoutée côté fiche : « **La fourchette retenue est celle après plafond
  de densité.** » → l'intermédiaire ne lit plus comme une contradiction.

## Q2 — verdict non-constructible : zone RÉELLE, plus d'« AU*st » inventé
`engine.py:187` — le verdict `not constructible_neuf` ne hardcode plus « secteur de
transition (AU*st), H max 4 m ». Il cite la **zone réellement lue** :
`f"Construction neuve non autorisée en zone {rules.code}."` (BM0950 → « …zone **A**. »,
cohérent avec le bandeau). **Aucun code secteur affiché s'il n'est pas lu sur la parcelle.**

**Autres chaînes `fini(False, …)` de `engine.py` — revues (aucune n'invente de zonage)** :
- `:194` « Habitat interdit au règlement — zone à vocation économique/activités… » —
  émis sur `habitat == "interdit"` : décrit **la règle** (fait), pas un code secteur inventé. Conservé.
- `:219` « Terrain trop exigu compte tenu des reculs (**{recul_used} m**)… » — **dynamique** (valeur lue). OK.
- `:282` « Hauteur non disponible (à_vérifier) — capacité non calculable. » — repli **honnête**. OK.
- `:404` « Non constructible en l'état malgré le zonage (**{rp} théorique**)… » — **dynamique**. OK.
→ La seule chaîne fautive (AU*st générique) est corrigée ; les autres sont factuelles ou paramétrées.

## Q5 — calculette : fragile, PAS morte → retry + état d'erreur (jamais de zone muette)
`Fiche.tsx` (CalculetteBody) — `useQuery('calculette-defaults', retry: 2)` ; si `isError`,
plus de « Chargement » perpétuel mais un **état explicite** : « Chargement de la calculette
impossible. » + bouton « **Réessayer** » (`refetch`). DA règle 8 respectée. Calculette **conservée**.
**Bonus dev/prod** : `/bilan` MANQUAIT au proxy Vite (`vite.config.ts`) → `calculette-defaults`
tombait en **404 rouge en `npm run dev`** (200 en prod, même origine). Ajouté au proxy — le
404 rouge (et l'état d'erreur Q5 déclenché par cet artefact dev) disparaît en dev.

## Q8 — RTAA : **NE RIEN MODIFIER** (consigne). Les articles servis (R.192-1/R.192-2) restent.
## Q9 — provenance unifiée : `steps.prov` **et** `/explain` dérivent tous deux de
`_faisa_step_prov(s.source, s.prov)` (`modules.py`) — **une source, un endroit**. Déjà unifié
(vérifié en P0) ; aucun code à changer, consigné ici.

## b — doublon capacité supprimé (un seul rendu)
`BilanTab` ne rend plus la section « Capacité (…) » (verdict/SHAB/stationnement dupliqués) :
la capacité vit **uniquement** dans `FaisabiliteTab`. BilanTab garde Marché → Fiscal → RTAA.

## c — zéros / « ( m) » / « ~— » → « — » ou « non calculable »
`FaisabiliteTab` : garde `capaciteReelle = logMax > 0`. Si faux → « Capacité logements non
calculable pour cette parcelle. » ; sinon grille avec repli **par champ** « — » (fini « 0–0 »,
« ( m) », « ~— »). Vérifié sur BM0950.

## e — bouton IA seulement si `steps > 0`
`{cap && steps.length > 0 && …}` — plus de bouton « Expliquer ce calcul » quand il n'y a
**aucune** étape à expliquer (BM0950 : 0 step).

## f — taxe d'aménagement : plus de taux inventé
`modules.py` `ta_note` : « **taux communal non ingéré — à confirmer en mairie** (part
communale + part départementale). » Le « 5 % » hardcodé (hors calcul) est retiré.

## g — pas de fausse précision quand ≥4 hypothèses empilées
`CalculetteBody` : les écarts % (`ecart_pct`, `demande_moins_max_pct`) sont **arrondis au
point** (`Math.round`, plus de décimale). Note explicite : « le résultat empile **4
hypothèses** (coût, marge, prix de sortie DVF, prix demandé) — les écarts sont arrondis au
point de %. »

## h — ordre : capacité → calcul replié + IA → marché → fiscal → RTAA replié
`FaisabiliteTab` : « Le calcul, étape par étape » **replié par défaut** (`showSteps=false`).
RTAA déjà repliable (RtaaBlock). Ordre du tiroir : capacité (FaisabiliteTab) → BilanTab
(Marché → Fiscal → RTAA).

## Point carte — MapToolbar décalée à l'ouverture de la fiche
`MapToolbar.tsx` : conteneur `right` piloté par `ficheOuverte = selectedIdu != null && view
!== 'sources'` → **16px → 416px** (largeur fiche 400 + marge 16), `transition: right 180ms`,
retour à la fermeture. Vérifié (style calculé : `16px` fermé / `416px` ouvert). Aucun
contrôle inaccessible.

## Guard-rails (tous verts)
`tsc -b --force` = **0** · `vitest run` = **32/32** · `vite build` OK · **5 exports PDF →
200** (parcels/export, dossier, dossier-banquier, lettre-zonage, argumentaire) · **console
0 erreur** sur AI1821 + BM0950 (tiroir Constructibilité déplié, calculette, calcul). Valeurs
Q1/Q2/f servies identiques en API et à l'écran (revérifiées après redémarrage backend).

## STOP — PHASE 1
Correctifs a→h + Q1/Q2/Q5/f/g + point carte livrés. **Q8 intouché** (consigne). **Q9**
déjà unifié. Commit « M58-P1 constructibilité ». **NE PAS MERGER.**
