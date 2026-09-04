# AUDIT — INTÉGRATION DES 13 OUTILS (après refonte)

**Branche** : `audit/outils-integration` · **Date** : 2026-08-24 · **Type** : audit seul (aucun code modifié, un seul rapport)
**Méthode** : 3 inventaires parallèles (ponts / composants SOCLE / grandeurs croisées) + vérifications ciblées back+front (cascade, config servie, libellés réels). Postgres en lecture stricte, serveur intact.

**Périmètre** : ce qui se passe ENTRE les outils — PAS un ré-audit outil par outil (les 14 mandats de refonte sont mergés, rapports dans `docs/audit-2026-08/`). Cinq axes : ponts, composants partagés, grandeurs croisées, cycle de vie, régressions.

**Verdict global** : l'intégration est **saine**. Les ponts transmettent au bon format et se nettoient ; les grandeurs cœur (SHAB, résiduel, tier) ont une **source unique** sans recalcul front. Les écarts sont **mineurs à moyens** et surtout **pédagogiques** (mots réutilisés pour des grandeurs voisines) ou du **câblage mort**. Les deux décisions ouvertes de Vic ont un impact réel et sont documentées ci-dessous (I3, I4).

---

## 1. Ponts inter-outils (périmètre 1)

Convention du store (zustand, `useApp.ts`) : un émetteur pose un `*Prefill` ou appelle une action, le récepteur le **lit au montage puis le remet à `null`** (consommé-reset). Motif M-ENTREE.

| Pont | Émetteur | Canal | Récepteur | Format ⇄ | Nettoyage | Verdict |
|------|----------|-------|-----------|----------|-----------|---------|
| Assemblage → Courrier | moteurs.tsx:286 | `courrierPrefillIdus` | ModulePanel:773 | `string[]` ⇄ `string[]` | reset au montage | ✓ sain |
| Pièges → Courrier | ModulePanel:1083 | `courrierPrefillIdus` | ModulePanel:773 | `string[]` ⇄ `string[]` | reset au montage | ✓ (canal partagé, cf I6) |
| Fiche → Comparaison | Fiche.tsx:2300 | `openCompare`+`addToCompare` | ComparePanel:33 | `string` → `string[]` cumul. | TTL 15 min (intentionnel) | ✓ sain |
| Fiche → Remonter le temps | Fiche.tsx:2304 | `parcelPrefill`→`tempsPinIdu` | ModulePanel:649 / TimeMachine:60 | `string` → pin carte | reset au unmount | ✓ sain |
| Densifier → Fiche | Renouvellement.tsx:232 | `select(idu)` + `setOpen(false)` | Fiche.tsx:1335 | `string` | overlay fermé synchrone | ✓ sain |
| Copilote → Carte | ReponseInline.tsx:43 | `carte_filtre` → setFilters | (carte/listing) | `Record` → filtres | versé à l'arrivée | ✓ (depuis FIX-PONT-TIER) |
| Fiche → Faisabilité | Fiche.tsx:2143 | `parcelPrefill` | M22Programme:72 | `string` | reset au montage | ✓ sain |
| Fiche → Assemblage | Fiche.tsx:2153 | `parcelPrefill` | moteurs.tsx:136 | `string` | reset au montage | ✓ sain |
| Fiche → Étudier/Calculette | Fiche.tsx:2148 | `calcPrefill` | EtudierBien.tsx:70 | `string` | reset au montage | ✓ sain |
| Fiche → PLU | Fiche (porte PLU) | `pluPrefill {insee,zone}` | PluAnnuaire:31 | struct exacte | reset au montage | ✓ sain |
| Fiche → Communes | Fiche.tsx:2271 | `communePrefill` (+setCommune) | Communes.tsx:149 | `string` | reset au montage | ✓ sain |
| Fiche → Risques | Fiche.tsx:2188 | `setModule('risques')` (fiche reste) | ModulePanel:1103 lit `selectedIdu` | `string` | fiche non fermée | ✓ sain |
| Copilote → PLU/Calc/Parcelle | ReponseInline.tsx:38-40 | `prefill_plu`/`prefill='calcPrefill'`/`prefill_idu` | mêmes récepteurs | struct/`string` | posé à l'ouverture | ✓ sain |
| Carte (picking) → Comparaison | MapView.tsx:926 | `addToCompare` | ComparePanel | `string` cumul. | TTL 15 min | ✓ sain |
| Carte → Permis (drawer) | MapView (clic point) | `permitToOpen` | ModulePanel:314 | `string` | reset après ouverture | ✓ sain |

**Constat** : 18 canaux tracés, tous **format émetteur == format récepteur**, consommé-reset systématique. Aucune divergence de format, aucun IDU perdu.

### Canaux déclarés mais INERTES — cf I5
- **`m02Prefill`** : récepteur câblé (ModulePanel:121, Scan patrimoine) mais **aucun émetteur** dans les 13 outils.
- **`permitHover`** : déclaré au store (useApp:362) mais **jamais écrit** (aucun `setPermitHover(...)` émetteur trouvé).

---

## 2. Composants partagés du SOCLE (périmètre 2)

| Composant | État | Détail |
|-----------|------|--------|
| **ParcelInput** | ✓ cohérent | 100 % des outils qui saisissent une parcelle passent par le composant partagé (EtudierBien, ParcelPicker, ProspectionSolaire, blocB, Renouvellement) — **aucune réimplémentation** de barre. Validation IDU (`estIdu`/`iduComplet`), autocomplétion (`AddressAutocomplete`), placeholder uniformes. |
| **ListPagination / Footer** | ✓ cohérent | `PAGE_SIZE = 400` (ListPagination.tsx:16). Tous en **offset serveur** via `useInfiniteQuery` + `getNextPageParam` (Faisabilité, Densifier, PLU Lot A). Seul **M22 Programme = 200** (colonnes plus lourdes — divergence justifiée). Aucun outil ne pagine côté client sur ces listes. |
| **CLOSE_OVERLAYS** | ✓ + réserve I7 | Constante (useApp.ts:415) fermant les **4 overlays plein écran** : `compareOpen`, `comparePicking`, `communesTableOpen`, `densifierTableOpen`. Appelée par 14 sites (openFiltres, setView, setModule, openCompare, openDensifier, openSurveillance, toggleOutils[ouverture], …). Cycle **verrouillé par `overlays.test.ts`** (8 cas). |

**Résidus d'état** : `compareIdus`/`compareTouchedAt` **survivent** à la sortie (TTL 15 min — **intentionnel et documenté**, retour sans perte). `setView` remet à zéro explicitement `sourceLine`, `surveillanceOpen`, `module`, `selectedIdu`, `parcours`, `openProjet` (au-delà de CLOSE_OVERLAYS). **Réserve** : `sourceLine` (tiroir de source) n'est PAS dans CLOSE_OVERLAYS et n'est pas remis par `setModule` — il ne tombe qu'à `setView` (cf I7).

---

## 3. Grandeurs croisées (périmètre 3)

| Grandeur | Source | Recalcul front ? | Cohérence | Réf |
|----------|--------|------------------|-----------|-----|
| **SHAB vendable** | `engine.py:469` `shab_vendable_m2 = sol_central × logt_moyen`, servi via `fiche_payload` | ❌ non | ✓ **source unique** — Fiche, Étudier, Faisabilité lisent la même valeur servie, même libellé « SHAB vendable » | Fiche.tsx:764, EtudierBien:134 |
| **Résiduel (SDP)** | cache `parcel_residuel.sdp_residuelle_m2` | ❌ non | ✓ **source unique** — Fiche, Étudier, Densifier, ModulePanel lisent le même cache ; Étudier porte l'alerte `residuel < vendable` (pont vers Pièges) | EtudierBien:85, Fiche.tsx:348 |
| **Charge foncière** | `bilan.py compute_bilan_servi()` (une équation) | ❌ (POST réutilise la même) | ✓ — Assemblage (cumulée), Étudier, Calculette, Comparateur, Copilote lisent tous la même équation ; **jamais écrêtée** (négatif servi honnêtement, rouge) | moteurs.tsx:228, Fiche.tsx:712 |
| **Prix de marché** | 3 sources DISTINCTES : ancien commune (`sector_price`), neuf parcelle (`resolve_prix_neuf_marche`), terrain nu zone (`prix_terrain_nu_zone`) | ❌ non | ⚠ pas de divergence de calcul, mais **confusion possible** ancien/neuf/commune-vs-local (cf I2) | marche_commune.py:70/87 |
| **Tier v2 / classement** | `parcel_p_score_v2.tier_v2`, rendu via `effectiveTier()` (rendu seul) | ❌ non | ✓ **source unique** — `TierBadge` + `TIER_V2_META` (M135) partout ; libellé/couleur canoniques | status.ts:28, TierBadge.tsx |

**SDP — trois coefficients pour des grandeurs voisines** (cf I1) : `coef_rendement 0.80` (SDP→SHAB vendable, engine), `1 + circulations% = 1.20` (utile→SDP capacité, M22 Programme, éditable), `×1.03` (Assemblage, M16). Ce sont des grandeurs **différentes** et chaque écran nomme la sienne, mais le mot « SDP » est réutilisé — risque de comparaison abusive entre outils.

---

## 4. Cycle de vie croisé (périmètre 4)

Enchaînements testés par lecture de code (résidus, overlays fantômes, sélections perdues) :
- **setView** = navigation exclusive : purge `sourceLine`, `surveillanceOpen`, `module`, `selectedIdu`, `parcours`, `openProjet`, `entretienDirect`, `iaRestitution` + CLOSE_OVERLAYS. Propre.
- **setModule** (changement d'outil) : purge via CLOSE_OVERLAYS les 4 overlays plein écran, mais **PAS `sourceLine`** → un tiroir de source ouvert sur une fiche peut survivre à un changement d'outil (I7, faible).
- **Comparaison** : `compareIdus` survit 15 min (intentionnel) ; `clearCompare()` explicite disponible.
- **Temps** : `tempsPinIdu` remis à `null` au unmount du composant — pas de pin fantôme après sortie.
- **Courrier** : `courrierPrefillIdus` consommé-reset au montage — pas de re-pré-remplissage à la ré-ouverture.

Aucun overlay fantôme ni sélection perdue détecté au-delà de I7.

---

## 5. Régressions (périmètre 5)

Les outils alimentent aussi fiche / carte / veille / projets :
- **Carte** : `addToCompare` (picking), `tempsPinIdu`, `permitToOpen`, `carte_filtre` → tous sains ; le pont Copilote→carte est corrigé (FIX-PONT-TIER, tier reproduit).
- **Projets (Kanban)** : consomme `marche_eur_m2` (« marché commune ») — voir I2 (libellé non daté « ancien »).
- **Veille** : le tag `parcel_veille_succession` (dirigeant âgé / SCI dormante) est alimenté par Score V **hors tier** — cohérent avec sa nature de radar patrimonial ; MAIS la cascade, elle, **score** l'âge dirigeant (I4).
- **Fiche** : source unique pour SHAB/résiduel/tier (§3) ; porte tous les ponts sortants (§1). Pas de régression de grandeur.

Aucune régression fonctionnelle détectée. Les deux points de friction (I1 SDP, I2 prix) sont **pédagogiques**, pas des bugs de calcul.

---

## 6. Décisions ouvertes de Vic (à documenter, PAS à trancher)

### I4 — `age_dirigeant` : pèse-t-il dans le score ? · gravité : moyenne (à trancher Vic)
**Oui — mais dans UN des deux moteurs seulement, et les deux se contredisent.**
- **Score V (le TIER servi brulante/chaude/…)** : tous les signaux dirigeant sont à **0 point** (`score_v_constants.py:135`, v1.3 « correction des signes », backtest daté : dirigeant 70-75 ans vend « ~nul »). L'âge dirigeant + SCI dormante **sortent de V** vers le tag `parcel_veille_succession` (radar 3-7 ans, « jamais compté dans V »). → **ne lève pas le tier**.
- **Cascade (score d'opportunité de la FICHE, étage 2)** : la couche `age_dirigeant` **attribue un bonus POSITIF** « Gérant proche de la retraite — horizon de transmission », **live en config servie** : `opportunity_weights.yaml:42 age_dirigeant: 14` (courbe 55/65/75/85 → 4/8/12/14), `cascade_rules.yaml:443`. Commentaire du code (`etage2.py:41`) : « le score (pts, magnitude) reste calculé sur l'âge réel — seul le libellé change » (M70 décision 7, RGPD : l'âge exact est **masqué à l'écran**, le score l'utilise). Évalué **uniquement** sur PM à dirigeant physique daté ; propriétaire **particulier → `unknown`/sans objet** (aucun poids ; PiegesLot masque d'ailleurs le champ si ≠PM).
- **Tension à trancher** : le backtest a mis le signal à 0 dans V, la cascade lui donne jusqu'à 14 pts. Un bien PM à dirigeant âgé affiche une **ligne positive « transmission »** en fiche (cascade) alors que son **tier n'est pas relevé** (Score V). Décision Vic : réconcilier (aligner la cascade sur le verdict backtest de V) ou assumer deux lectures (tier = probabilité de vente datée ; cascade = signal patrimonial qualitatif).

### I3 — libellé du tier « Priorité » · gravité : faible (à trancher Vic)
Le libellé **canonique est « Priorité »** (`TIER_V2_META`, M135 : brulante → label « Priorité », long « À contacter en priorité ») et il est **cohérent partout** via `TierBadge` (Fiche, Carte, Étudier, M22, Copilote, Légende, LeftPanel). Le mot thermique brut « brûlante » ne subsiste comme **texte affiché qu'à UN endroit** : la vignette Stock foncier (`blocB.tsx:261` « {n} brûlantes »). Tant que Vic n'a pas tranché le libellé, ce mot legacy coexiste avec « Priorité » pour le même tier. Correctif candidat : aligner la vignette sur le label canonique (ou assumer « brûlantes » comme terme métier interne).

---

## 7. Gravités & correctifs candidats (sans les faire)

| Réf | Constat | Gravité | Correctif candidat |
|-----|---------|---------|--------------------|
| **I1** | « SDP » recouvre 3 coefficients (0.80 SHAB / 1.20 M22 / 1.03 Assemblage) pour des grandeurs voisines | moyenne | nommer distinctement à l'écran (SHAB vendable / SDP capacité gabarit / SDP assemblage) ou afficher le coef appliqué |
| **I2** | prix marché : Kanban « marché commune » non daté « ancien » ; fiche « prix de sortie » = neuf secteur | moyenne | préciser les libellés (ancien/neuf, échelle commune/secteur) — sources uniques, pas de recalcul, juste la pédagogie |
| **I3** | tier « Priorité » (M135) cohérent sauf 1 vignette « brûlantes » (blocB) | faible (Vic) | aligner la vignette Stock foncier — après décision libellé |
| **I4** | `age_dirigeant` pèse dans la cascade (14 pts, live) mais 0 dans Score V — moteurs contradictoires | moyenne (Vic) | réconcilier cascade↔V, ou documenter les deux lectures ; l'âge exact reste masqué (RGPD OK) |
| **I5** | canaux store inertes : `m02Prefill` (sans émetteur), `permitHover` (jamais écrit) | faible | retirer, ou brancher l'émetteur manquant |
| **I6** | `courrierPrefillIdus` partagé Assemblage+Pièges (dernier écrit gagne) | faible | sain en usage séquentiel (consommé-reset) ; garde inutile sauf double-set simultané |
| **I7** | `sourceLine` (tiroir source) survit à `setModule` (fermé seulement par `setView`) | faible | ajouter `sourceLine: null` à `setModule` ou à CLOSE_OVERLAYS |

**Points sains à conserver** (non exhaustif) : 18 ponts au format exact + consommé-reset ; ParcelInput/ListPagination sans réimplémentation ; CLOSE_OVERLAYS + `overlays.test.ts` verrouillent le cycle des overlays ; SHAB/résiduel/tier/charge = **source unique backend, zéro recalcul front** ; charge foncière jamais écrêtée (verdict honnête).

**Conclusion** : après refonte, les 13 outils s'assemblent proprement. Aucun bug de transmission ni divergence silencieuse de calcul. Les quatre points « moyens » sont soit pédagogiques (I1, I2), soit des arbitrages Vic (I3, I4) ; les trois « faibles » (I5-I7) sont du ménage. Rien ne bloque, tout est traçable.
