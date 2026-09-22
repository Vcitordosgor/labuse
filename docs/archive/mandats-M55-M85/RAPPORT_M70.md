# RAPPORT M70 — Fiche parcelle : diagnostics + inventaires (STOP arbitrage)

Branche `feat/m70-tiroirs` depuis `main` (`aafe059f`, M71/M74/M75 mergés). Parcelles mesurées :
**97415000AC0253** (canari, Saint-Paul, PM avec procédure BODACC + gérant 75 ans),
97407000AD0086 (Le Port, PPR rouge), 97413000BE0048 (Saint-Denis, ENS réel), + variées.
Run servi `q_v8_calibre` (gelé le **2026-07-29**).

**Les points visuels 2, 4, 6a, 7a sont DÉJÀ LIVRÉS** (commit avant ce STOP). Tout le reste
ci-dessous attend l'arbitrage de Vic. **Insight architectural clé** : les `lines` de la fiche
(Risques/Marché/Propriétaire) sont lues VERBATIM depuis `dryrun_cascade_results` du run gelé, PAS
recalculées. Donc beaucoup de faux négatifs « retirés du code » (M71) **survivent en production
dans le run figé** — les corriger exige de rejouer la cascade OU de filtrer/reformuler à la lecture.

---

## PÉCHÉS PRIORITAIRES (doctrine) — le cœur du mandat

| # | Péché | Tiroir | Cause | Statut |
|---|-------|--------|-------|--------|
| 1 | **ENS « Hors ENS. » (PASS)** sur 5 communes SANS donnée ENS | Risques | `kind_present` global (ENS existe → jamais UNKNOWN) alors qu'ENS couvre 19/24 communes | **FAUX NÉGATIF actif** |
| 2 | **« Pas de passoire thermique F/G recensée »** | Propriétaire/Règles | ligne survit dans le run gelé 29/07 malgré retrait code M71 | **FAUX NÉGATIF actif** |
| 3 | **« Aucune procédure collective recensée »** | Propriétaire | `BodaccLayer` ne consulte pas `bodacc_sondages` (M71-D) ; pas de garde source-vide | **FAUX NÉGATIF structurel** |
| 4 | **« Capacité d'accueil PV NULLE sur les 24 postes (S3REnR) »** | Réseaux | `grid_capacity` = 24 lignes mais `capa_dispo_mw=0` FABRIQUÉ (stub, geom NULL) | **FAUX POSITIF** |
| 5 | **OCS GE « Sol déjà artificialisé. »** verdict définitif | Marché | proxy BDCARTO servi sans réserve (contrairement à SarLayer) | **FAUX POSITIF de formulation** |
| 6 | **Pastilles « vérifiée »** | Données | `reliability_level` = colonne catalogue déclarative ; `source_checks` VIDE | **FAUX POSITIF de méthode** |
| 7 | **`parcel_amenites#12059`** (clé technique) | Marché + tous | `source_table#source_id` rendu tel quel | violation libellés_client |

Les corrections 1-3-4-5 sont dans la CASCADE (backend) → nécessitent code + **rejeu du run** (ou
filtrage à la lecture). 2 se règle aussi par le rejeu. 6-7 sont front/API (lecture).

---

## POINT 1 — Scores bruts à l'écran (inventaire)

| fichier:ligne | ce qui s'affiche | tiroir/export | verdict |
|---|---|---|---|
| `Fiche.tsx` `Weight` (201) via `<Line>` Risques(2037)/Marché(2053)/Propriétaire(2167)/recherche(1771) | `+{w}`/`-{w}` en préfixe (ex. `-5`, `+12`) | Risques/Marché/Propriétaire/recherche | **Risques/Marché/Propriétaire CORRIGÉS pré-STOP** (hideWeight). Recherche (1771) reste — à trancher |
| `ViabilisationBlock.tsx:32-39` | `{via.score} / 100` + barre | Réseaux (**jauge**) | **À RETIRER** (cas particulier : 2ᵉ jauge interdite, doctrine ICD unique) |
| `Fiche.tsx` `IcdBlockView` (297) | `{icd.score}` chiffré + barre « Confiance données » | Données (**jauge**) | **À RETIRER** le nombre+jauge (cas particulier point 8) — verdict qualitatif « Confiance : haute » |
| `Fiche.tsx:1314/1570` `ecarteeMotif` | `qualité insuffisante (Q {q_score})` | carte verdict (écartées) | **À RETIRER** — expose Q brut |
| `pdf_premium.py:379` | `… · somme +{poids}` | PDF Premium | **À RETIRER** |
| `pdf_premium.py:402-407` | `+{w0}` préfixe par ligne | PDF Premium | **À RETIRER** |
| `pdf_premium.py:236` | `QUALITÉ / 100`, `ACCESSIBILITÉ / 100` | PDF Premium | à harmoniser (Q/A retirés de la fiche) |
| `ViabilisationBlock.tsx:47` (Pourquoi), `Fiche.tsx:1670` (Renouvellement), ScoreV2Block (Pourquoi) | `+{points}` sous « Pourquoi » | bloc Analyse | ✅ LÉGITIME (« Pourquoi ce score ») |

Synthèse : le composant `Weight` fuit le poids signé en préfixe ; 3 des 4 tiroirs concernés sont
corrigés pré-STOP ; restent à arbitrer les **deux jauges** (Réseaux `/100`, Confiance ICD chiffré)
— toutes deux violent « une seule jauge (ICD) » — le `(Q {q_score})` des écartées, la recherche
in-fiche, et les fuites du **PDF Premium**.

---

## POINT 5a — Clés techniques à l'écran (inventaire)

| fichier:ligne | clé exposée | où | correctif |
|---|---|---|---|
| `Fiche.tsx` `SourceRef` (212, rendu 221) | `{source_table}#{source_id}` (ex. `parcel_amenites#12059`, `spatial_layers#1397547`) | **toutes** les lignes de tiroir | retirer le `<span trace>` du rendu client (ou `data-*` non affiché) |
| `SourceDrawer.tsx:23/44` | même `source_table#source_id` | drawer Source | idem |
| `SourceDrawer.tsx:41` | `EXTRAIT — {layer}` (clé brute, ex. `bruit_route`) | drawer Source | passer par `layerLabel()` |
| `pdf_premium.py:410` | `ln["layer"][:26]` clé brute | PDF Premium | dictionnaire de libellés |
| `pdf_premium.py:422/426` | `source_table#source_id` | PDF Premium | retirer/aliaser |
| `Fiche.tsx:238` (Tip `couche {layer}`) | clé au **survol seulement** | — | ✅ LÉGITIME (choix audit S03-S05) |

Synthèse : source unique du « parcel_amenites#56909 » = le motif `${source_table}#${source_id}`
dans `SourceRef` (+ dupliqué SourceDrawer + pdf_premium). Correctif = retrait du rendu client.

---

## POINT 3 — Véracité tiroir RISQUES (10 couches)

**Fidélité base↔fiche parfaite** : les lignes servies = `dryrun_cascade_results` verbatim (18/18
identiques sur le canari). Toute la véracité repose sur le `detail` produit par la cascade.

- **ENS « Hors ENS. » (PASS) = FAUX NÉGATIF (péché mortel), actif.** ENS couvre 19/24 communes ;
  les 5 vides (**Les Avirons, Le Port, Saint-André, Sainte-Marie, Sainte-Suzanne**) reçoivent
  « Hors ENS. » alors qu'aucune donnée n'existe. Ex. servi : 97407000AD0086 (Le Port). Cause :
  `EnsLayer.evaluate` (phase1.py:707-713) teste `kind_present` GLOBAL puis `passed("Hors ENS.")`.
  **Correctif de référence déjà dans le repo** : `SarLayer` (phase1.py:162-183) gère la couverture
  partielle (« hors îlot ≠ absence » + réserve proxy). Porter la même garde à ENS (per-commune → UNKNOWN).
- **ABF « Hors périmètre ABF » (PASS)** : la couche ne porte que 200 tampons MH (SPR/AVAP non
  ingérés). Le libellé négatif est plus large que la portée réelle → « hors abords MH » serait honnête.
- Toutes les autres couches (PPR/aléas repliés dans `risques`, ICPE, sols pollués, cavités, MVT,
  pente, ravines, trait de côte, eau) : **cohérentes** avec la base pour la parcelle, sources amont exactes.
- **Manquant** : `bruit_route` (1 004 emprises, nuisance sonore) existe en base mais n'est dans
  **aucun onglet** de la fiche. `cinquante_pas` (163) remonte via SUP/règlement, pas Risques (OK).

---

## POINT 5b — Véracité tiroir MARCHÉ

- **OCS GE « Sol déjà artificialisé. » / « Sol naturel (ZAN) » = verdict DÉFINITIF sur un PROXY
  BDCARTO** (phase1.py:717-731), servi **sans réserve de proxy** (contrairement à SAR). Faux positif
  de formulation. Atténuant : dégrade honnêtement hors intersection (« non couverte ici »). M74 a
  requalifié la SOURCE (catalogue) mais pas la LIGNE cascade.
- **Divergence des 3 comptes de ventes DVF** (le point de l'encart « Autour, à moins de 100 m ») :
  - Ligne « Marché DVF » (`marche_secteur`) : **1 mutation ≤ 250 m / 5 ans, médiane 379 €/m²**.
  - Encart « Autour < 100 m » (`voisinage_proche`, M42) : **1 vente / 1 permis** (100 m, 36 mois).
  - Bloc secteur (`dvf_parcelle.secteur`, MicroSpark) : **3 ventes terrain, médiane 173 €/m²** (secteur cadastral, 5 ans).
  Chaque chiffre est exact dans SA fenêtre, mais les trois cohabitent **sans clé de lecture** ; et
  **379 €/m² (ligne) vs 173 €/m² (secteur terrain)** côte à côte sans réconciliation = incohérence
  de PRÉSENTATION à harmoniser (rappeler le rayon, séparer terrain/bâti).
- **Potentiel foncier « Hors îlot » = HONNÊTE** (contrairement à ENS) : la couche intersecte 24/24
  communes, « pas dans un îlot désigné » ≠ donnée manquante. NE PAS traiter comme un faux négatif.
- **Friche « Aucune friche recensée »** : honnête (« recensée » borne l'affirmation à l'inventaire).
- Aménités, Accès voirie, SITADEL, Marché DVF : cohérents avec la base.

---

## POINT 6b — Véracité/utilité tiroir RÉSEAUX

- **« Capacité d'accueil PV NULLE sur les 24 postes (S3REnR) » = FAUX POSITIF.** `grid_capacity` a
  24 lignes (les 24 postes) MAIS `capa_dispo_mw = 0` **fabriqué en dur** (stub 2026-07-11, `geom`
  NULL). `ilot_s3renr_note` fait `count FILTER (capa_dispo_mw<=0)` → 24/24 → « NULLE » mécaniquement.
  On énonce une saturation totale de l'île comme un fait sourcé alors que rien n'est mesuré.
  → reformuler « donnée S3REnR non encore ingérée — à vérifier auprès d'EDF SEI » (le disclaimer
  existe déjà mais est noyé sous « NULLE »).
- **4 preuves de viabilisation** : cohérentes avec `parcel_viabilisation` (score 90, Permis 30 /
  Façade 25 / Zone U 20 / Adjacence 15). Non-faux-positif.
- **Gestionnaires (5)** : lus de `config/gestionnaires_via.yaml` (SAISIS À LA MAIN, `confidence:high`
  déclaratif, `a_jour_au` retiré pré-STOP). Honnête et utile (contact admin) mais le **pavé
  administratif** (« Ex-régie communale transférée au TCO… », double disclaimer DT-DICT) est long/répété → repliable.
- **Bloc RACCORDEMENT (QUALITATIF)** : `niveau` (utile), `assainissement` (fait d'absence vrai),
  `disclaimer` **redondant** avec le disclaimer global de viabilisation → fusionner, rien d'opposable perdu.
- **Permis proximité** « 24 <100m / 47 <200m » (viabilisation, stock cumulatif tous millésimes) vs
  « 2 permis <100m 36 mois » (voisinage_proche, flux récent) : **cohérent** (deux fenêtres), mais
  mérite une note explicative (ordres de grandeur choquants côte à côte).
- Rien de significatif non affiché côté réseaux (aucune table de tracé, interdit).

---

## POINT 7b — Véracité tiroir PROPRIÉTAIRE (le plus important)

- **« Pas de passoire thermique F/G recensée » = FAUX NÉGATIF ACTIF.** M71 a bien supprimé la classe
  `DpePassoireLayer` du CODE (tombstone etage2.py:80-83, grep vide). **MAIS** la fiche live la sert
  encore : `{"layer":"dpe_passoire","detail":"Pas de passoire thermique F/G recensée.","date":"2026-07-29"}`
  — les `lines` viennent de `dryrun_cascade_results` (run gelé 29/07, antérieur au retrait). Adossée
  à 17 DPE en base. → rejouer le run, OU filtrer `dpe_passoire` à la lecture.
- **« Aucune procédure collective recensée » = FAUX NÉGATIF STRUCTUREL (non réglé par M71-D).**
  `bodacc_sondages` est peuplé (12 605/12 605, 177 procédures) MAIS **jamais consulté par la cascade** :
  `BodaccLayer` (etage2.py:64) lit seulement `v_foncier_sous_pression` et émet le PASS dès que
  `type_procedure` est None, **sans garde source-vide** → « sondé, rien » et « jamais sondé »
  (2 872 non_sondable) écrasés en un même PASS. Brancher `bodacc_sondages` au verdict.
- **« Propriétaire inconnu (Fichiers fonciers sous convention non branchés) »** : modèle HONNÊTE,
  nomme la cause — à CONSERVER (c'est le patron des deux corrections ci-dessus).
- **Âge dirigeant « Gérant âgé (75 ans) »** : expose l'âge EXACT d'un dirigeant de PM nommée →
  **réserve RGPD P2-34**. « proche de la retraite / horizon de transmission » sans le nombre suffirait.
  Ne rien changer au stockage ; arbitrer l'affichage.

---

## POINT 8b — Véracité tiroir DONNÉES ET MÉTHODE

- **En-tête « 28 sources · couverture 90 % »** : « 28 » = `data_sources.length` (sources dont une
  couche a tourné sur la parcelle) **inflaté** (Géorisques éclaté en 6 lignes — écho du « 62 gonflé »
  de M66 à échelle fiche). « couverture 90 % » = `icd.score` (85 sur le canari, pas 90 — le « 90 »
  du mandat vient d'une autre parcelle). C'est la complétude des couches, pas un taux de sources.
- **Pastilles « vérifiée » = FAUX POSITIF de méthode.** Viennent de `reliability_level` (colonne
  STATIQUE du catalogue), PAS de `source_checks` (VIDE, 0 ligne). « vérifiée » est une auto-déclaration,
  pas un contrôle. Cas grave : **DPE ADEME « vérifiée » sur 17 lignes** en base. SAFER/ENS/OCS GE/SAR/
  50 pas « à confirmer » (cohérent). ZNIEFF/EDF/ODRE absentes de la liste canari (pas de faux positif
  sur cette parcelle). → « vérifiée » doit refléter une vraie vérification (source_checks) ou changer de libellé.
- **Bloc « QUALITÉ DE LA MESURE · SAINT-PAUL »** (RR intra 4.6, île 6,7, 50 593 parcelles, base 1,74 %) :
  **jargon d'audit interne** (RR, pouvoir discriminant, out-of-sample, taux de base) devant client.
  Repli proposé : « Fiabilité du classement sur Saint-Paul : robuste (mesuré sur 50 593 parcelles) ».
- **Jauge « Confiance données » (ICD chiffré)** : 3ᵉ jauge + score exposé **DEUX FOIS** (en-tête
  « couverture 90 % » + IcdBlockView en gras). DA-FICHE-v6 proscrit les « % nus ». → « Confiance :
  haute » (déjà dans `icd.libelle`) sans le nombre ni la barre.
- `solar_grid` (15 680 lignes PVGIS) alimente le solaire mais n'apparaît pas en data_sources (omission mineure de traçabilité).

---

## POINT 8a — Bloc « DONNÉES ABSENTES » (arbitrage Vic)

C'est la matérialisation du 3ᵉ terme de la doctrine (Sourcé / Estimé / **Absent**). Le supprimer
laisserait croire la fiche complète. **Par défaut : le CONSERVER replié + reformulé « Ce que LABUSE
ne peut pas savoir sur cette parcelle ».** Rendu actuel : `Fiche.tsx:1330-1334` (donneesAbsentes) +
puce « ○ ». **Vic tranche : repli+reformulation, ou suppression sèche.** (Non touché sans arbitrage.)

---

## POINT 8c — « Signaler une erreur » : BRANCHÉ et fonctionnel

Le bouton **n'est PAS mort** et ne mène PAS au `/feedback` orphelin.
- Composant `SignalerErreur` (Fiche.tsx:399), bouton (414). Au clic → `postSignalement` (api.ts:449)
  → **`POST /signalements`** (app.py:3619, `@app.post("/signalements")`).
- Payload : `{ idu, type_erreur ∈ SIGNALEMENT_TYPES, champ?, commentaire? }` (pas de run/contexte scoring).
- Backend : `INSERT INTO signalements` (cloison `compte_id`), file QA humaine lisible via
  `GET /signalements` + export CSV. Test : `POST /signalements` corps vide → **422** (vivant).
- Après envoi : « ✓ Signalement enregistré (n°{id}) — merci. Il sera revu manuellement. »
- **Le `/feedback` orphelin est un AUTRE objet** : c'était le widget « Ce lead vous est-il utile ? »
  (FeedbackStrip), RETIRÉ de la fiche en M55-L pt 7 ; `POST /feedback` reste un backend sans UI
  (422 corps vide, vivant mais injoignable). Ce bouton-ci ne le concerne pas. **RAS sur 8c.**

---

## POINT 9 — Tableau outil → tiroir (arbitrage Vic — valide chaque rattachement)

Rappel : la grille « OUTILS SUR CETTE PARCELLE » en pied de fiche est SUPPRIMÉE (annule M60-d) ;
au plus UNE porte par outil ; un outil sans tiroir logique reste hors fiche. **Non implémenté** (attend validation).

| Outil | Tiroir proposé | Justification |
|---|---|---|
| Comparer des parcelles | Marché | compare surface/zonage/capacité/**marché**, ancré parcelle |
| Remonter le temps | Marché | évolution de la parcelle dans le temps (contexte marché) |
| Comparateur de communes | Marché | indicateurs marché par commune |
| Vérif procédure PLU | Urbanisme | IDU → commune en procédure PLU / sursis |
| Annuaire PLU | Urbanisme | règlement opposable de la commune |
| Changement PLU (simulplu) | Urbanisme | « et si cette zone passait constructible ? » |
| Courrier propriétaire (SPF) | Propriétaire | **déjà livré pré-STOP (7a)** |
| Scan patrimoine | Propriétaire | déjà porte (M60), SIREN du propriétaire |
| Calculette foncière | Constructibilité | déjà porte (M60) |
| Faisabilité (programme) | Constructibilité | capacité constructible |
| Division parcellaire | Constructibilité | détacher un lot |
| Assemblage | Constructibilité | fusion parcelles contiguës |
| Contrôle avant achat (due diligence) | Risques | passe la parcelle au crible avant achat |
| Servitudes invisibles | Risques | contraintes dormantes |
| Renouvellement, Foncier fantôme | Constructibilité | capacité résiduelle/verrouillée |
| Radar mutations, Mode bailleur, Rareté, Quoi de neuf, Matching, Scorer adresse, Baromètre, Radar permis, Promesses mortes, Vélocité, ZAN, Suivi secteur | **hors fiche** | échelle commune/île/portefeuille, pas une parcelle |

---

## POINT 10 — « Remonter le temps » montre toute la Réunion (bug)

Cause : **aucun `center` n'est passé au composant**. `TimeMachine` (TimeMachine.tsx:49) accepte
`center?` mais `App.tsx:314` rend `<TimeMachine />` **sans prop** → `center===undefined` → le
recadrage `if (center) past.jumpTo({center, zoom:17})` (ligne 88) ne s'exécute jamais → la vue reste
sur `SP_BOUNDS = [55.21,-21.14,55.35,-20.97]` (bbox large fixe, ligne 8). De plus la couche parcelles
affiche TOUTES les promues (statuts chaude/a_surveiller/a_creuser), jamais l'IDU isolé.
**Correctif** (non appliqué) : passer `center={centre parcelle}` depuis le store à App.tsx:314,
`fitBounds` sur la bbox de la parcelle, filtrer la couche sur l'IDU. Le slider avant/après existe déjà.

---

## POINT 11 — « Pré-dossier PC » cassé (bug DEV uniquement)

L'endpoint backend **fonctionne** : `GET /pre-dossier/{idu}.zip` (pre_dossier.py:29/209, monté
app.py:4193) → **200** (ZIP servi, testé sur 97410000BV0120). Le bug est **propre au serveur de dev
Vite** : `vite.config.ts:48` a `base:'/socle/'` ; le lien est construit en relatif
`/pre-dossier/${idu}.zip` (api.ts:365, `<a href>` Fiche.tsx:2458) → hors de la base `/socle/` → Vite
renvoie son message « did you mean /socle/pre-dossier/…zip ». `GET /socle/pre-dossier/…zip` → **404**
côté backend. En PROD (FastAPI sert `dist/` même origine) le lien 200. **Correctif** (non appliqué) :
ajouter `/pre-dossier` à `apiPaths` du proxy dev (`vite.config.ts:74`) — même famille que « /bilan
manquait au proxy » (M58). Option 2 : préfixer l'URL via `import.meta.env.BASE_URL` (moins propre).

---

## DÉCISIONS ATTENDUES DE VIC (avant correction de contenu)

1. **Faux négatifs cascade (ENS, passoire, BODACC)** : rejouer le run `q_v8_calibre` (corrige les 3
   d'un coup, mais régénère le golden) **OU** filtrer/reformuler à la lecture (plus léger, pas de rejeu) ?
2. **ENS** : garde per-commune → UNKNOWN « ENS non renseignés pour cette commune » (patron SarLayer). OK ?
3. **OCS GE** : ajouter la réserve proxy à la ligne (« proxy BDCARTO, indicatif »). OK ?
4. **S3REnR** : reformuler « capacité NULLE » → « donnée non ingérée, à vérifier EDF SEI ». OK ?
5. **Jauges** : retirer la jauge Réseaux `/100` et le nombre ICD (garder « Confiance : haute »). OK ?
6. **Pastilles « vérifiée »** : n'afficher « vérifiée » que si `source_checks` non vide, sinon
   « déclarée fiable » / « cadence producteur ». OK ?
7. **Clé technique `source_table#source_id`** : retrait du rendu client (fiche + drawer + PDF). OK ?
8. **Âge dirigeant** : masquer le nombre (« proche de la retraite »). OK ?
9. **DONNÉES ABSENTES (8a)** : repli+reformulation, ou suppression sèche ?
10. **Point 9** : valides-tu les rattachements outil→tiroir du tableau ? (grille terminale supprimée)
11. **Divergence DVF (5b)** : harmoniser les 3 comptes avec une clé de lecture (rayon/fenêtre) ?
12. **Bugs 10 (time machine) et 11 (pré-dossier dev)** : correctifs proposés — GO ?

**Garde-fous à ce STOP** : tsc 0 · vitest 37/37 · build vert · visuels 2/4/6a/7a livrés et vérifiés
(en-tête viabilisation 20px = 1 ligne, portes patrimoine/SPF OK) · défilement M68 non régressé.
**NE PAS MERGER.**

---

# PHASE 1 — corrections (arbitrages Vic appliqués)

## Ce qui est LIVRÉ (immédiat, effectif tout de suite)
- **Déc. 4** — pastilles « vérifiée » → **« suivie »** au point unique `_FIAB` (couvre DPE) ; couleurs
  honnêtes (suivie=mint, à confirmer=ambre, reste neutre) ; « N couches vérifiées » → « évaluées ».
  Vérifié live : **0 « vérifiée »** sur la fiche.
- **Déc. 5** — les **deux jauges retirées** : ViabilisationBlock `/100`+barre → phrase qualitative ;
  ICD score+barre → **verdict qualitatif** (`icd.libelle`). Une seule jauge dans la fiche.
- **Déc. 6** — clé technique `source_table#source_id` retirée de SourceRef, SourceDrawer (+ EXTRAIT
  via `layerLabel`) et **PDF Premium** (ref + préfixe poids + somme + layer brut → libellés FR).
- **Déc. 8** — bloc absences **conservé, replié** (`<details>`), reformulé « Ce que LABUSE ne peut
  pas savoir sur cette parcelle ».
- **Déc. 11** — bug 10 (TimeMachine `center={flyTo?.center}`) + bug 11 (`/pre-dossier` au proxy Vite).
- Points visuels **2/4/6a/7a** (commit précédent).

## Ce qui est POSÉ dans le code (effectif au REJEU, pas avant — déc. 1)
Les `lines` de la fiche viennent du run gelé ; ces correctifs prennent effet quand le run est rejoué.
- **Déc. 2** — ENS garde per-commune (`kind_present_commune`) → « Donnée ENS non disponible sur cette
  commune » (UNKNOWN, jamais « Hors ENS ») ; OCS GE réserve proxy visible ; S3REnR : plus de « capacité
  NULLE » sur le stub (déjà effectif live, `elec_pv=None`). + 3 tests ENS.
- **Déc. 3** — BODACC branché à `bodacc_sondages` : « sondé le [date] » / « non concluant » / « sans
  objet ». + 2 tests.
- **Déc. 7** — âge dirigeant sans nombre exact (label seul, score inchangé).

## Déc. 1 — CHIFFRAGE DU REJEU (pour ton séquencement)
**Ordre demandé** : rebaser le golden (mandat séparé) → rejouer → constater. Rien rejoué ici.
- **Ce que le rejeu régénère** : `dryrun_cascade_results` (les lignes de fiche) + `parcel_p_score_v2`
  (431 663 scores/tiers) + la **référence golden**.
- **Ce qui bascule** (mesuré) :
  - Les libellés des 5 couches (ENS/passoire/BODACC/OCS GE/âge) — la passoire **disparaît** (couche
    retirée M71, ne tourne plus).
  - **Tiers : quasi stables.** `bodacc` = INFO ×0 (0 impact) ; `age_dirigeant`/`ocs_ge` = label seul
    (poids/sévérité inchangés) ; **ENS** : « Hors ENS » PASS → UNKNOWN sur les **3 communes vides
    (Le Port, Saint-André, Sainte-Suzanne) = ~45 000 parcelles** → +1 UNKNOWN chacune ⇒ légère baisse
    de `a_completude` ; bascule de tier possible seulement pour les rares parcelles au ras du
    double-verrou `a_completude_min` (à mesurer au rejeu, attendu marginal).
  - **Golden** : à régénérer (il reflétera les nouveaux libellés ENS/BODACC — c'est le but).
- **Durée** : un run complet = cascade dry-run + score-v2 sur 431 663 parcelles ; ordre de grandeur
  **~15–45 min** (mesurable au lancement). La régénération golden est incluse dans le geste (garde #6).
- **Recommandation de séquencement** : (1) mandat golden-rebase (rebaser la référence sur le run
  servi actuel, éteindre les 33 FAIL préexistants) ; (2) rejouer q_v8_calibre avec les correctifs
  M70 posés ; (3) mesurer les bascules ENS-complétude + régénérer golden ; (4) constater la
  disparition des 3 faux négatifs. **Tant que (2) n'a pas eu lieu, la fiche montre encore les
  anciens libellés cascade — c'est attendu, décision 1.**

## Déc. 10 — DVF : analyse + ce qui est posé
- Le bloc **`market_signal` (M-U) est DÉJÀ single-calc** (`moteurs.py` : « calcul unique lu par
  l'outil, la fiche et market_signal ») → pas de divergence fiche/export sur ce bloc.
- Les deux autres chiffres DVF portent déjà leur clé de lecture : encart voisinage « (< 100 m,
  36 mois) », spark secteur « N ventes secteur · DVF — {millésime} ».
- **La divergence de MÉDIANE** (ligne cascade « Marché DVF » 379 €/m², rayon 250 m, tous biens ÷
  surface terrain — vs secteur 173 €/m², terrain seul) vient de **deux calculs différents DANS LA
  CASCADE GELÉE**. La réconcilier = aligner le calcul de médiane de la couche `dvf` sur la méthode
  secteur → **change cascade, effectif au rejeu** (même lot que déc. 2/3). Décision 1 interdit le
  filtre/relabel de lecture. **Posé pour le rejeu** ; je te propose au rejeu : la ligne cascade DVF
  adopte la médiane terrain du secteur (point de calcul unique), vérif programmatique fiche==export.
  Dis-moi si tu confirmes cette méthode avant que je l'écrive dans la couche.

## Déc. 9 — TABLEAU OUTIL → TIROIR (à valider rattachement par rattachement)
La grille « OUTILS SUR CETTE PARCELLE » (pied de fiche, M60-d) sera SUPPRIMÉE **après** ta validation
(déc. 12). Rien retiré/branché tant que tu n'as pas validé la table ci-dessous (déjà au corps du
rapport, §Point 9). Rappel des rattachements proposés :
- **Marché** : Comparer des parcelles · Remonter le temps · Comparateur de communes
- **Urbanisme** : Vérif procédure PLU · Annuaire PLU · Changement PLU (simulplu)
- **Propriétaire** : Courrier SPF *(déjà livré 7a)* · Scan patrimoine *(déjà porte M60)*
- **Constructibilité** : Calculette *(déjà porte M60)* · Faisabilité · Division · Assemblage
- **Risques** : Contrôle avant achat (due diligence) · Servitudes invisibles
- **hors fiche** : Radar mutations, Mode bailleur, Rareté, Quoi de neuf, Matching, Scorer adresse,
  Baromètre, Radar permis, Promesses mortes, Vélocité, ZAN, Suivi de secteur.
Valide (ou corrige) rattachement par rattachement → j'implémente les portes + supprime la grille (déc. 12).

## Garde-fous (état à ce point)
tsc 0 · vitest 37/37 · build vert · **golden 33 FAIL = baseline (0 régression)** · tests cascade
58+14 passed · console 0 erreur · **0 « vérifiée » / 0 clé technique / 0 jauge (sauf ICD déchiffré)
sur la fiche** · défilement M68 non régressé · S3REnR ne dit plus « capacité NULLE » (live).

## DÉCISIONS RESTANTES POUR TOI
1. **Séquencement du rejeu** (golden-rebase d'abord ?) — cf. chiffrage.
2. **Déc. 10** : confirmes-tu que la ligne cascade DVF adopte la médiane terrain du secteur (méthode) ?
3. **Déc. 9** : valides-tu les rattachements outil→tiroir (→ déc. 12 : suppression de la grille) ?

**NE PAS MERGER.**
