# CHASSE-DONNEES-FIX-1 — RAPPORT (verdict)

Branche `fix/chasse-donnees-1`, worktree `~/Desktop/labuse-chasse-fix`, local q_v18, ports 8750/5950.
Exécution du `MANDAT-FIX.md` sur les 83 écarts de `ECARTS.md`. **On a corrigé les CAUSES, pas les
lignes** : chaque lot supprime une cause (un seul chemin de code par notion) et la verrouille par
une garde du banc `scripts.coherence.chasse_donnees`.

## Verdict en 5 lignes

1. **Banc `scripts.coherence.chasse_donnees` : 24 OK · 0 ECART · 0 SKIP (24 gardes)** — exit 0.
2. **55/83 écarts FERMÉS** par correctif de cause (7 commits, un par lot), chacun vérifié sur son témoin + garde.
3. **28/83 LAISSÉS avec motif** : latents (corrects aujourd'hui, le front se protège), limites WeasyPrint, caches/jobs opérationnels, millésimes-en-dur front (tsc non vérifiable dans le worktree), ou hors liste explicite du mandat.
4. **AUCUN correctif livré ne change le résiduel ni le score** — tout est lecture/affichage/fenêtre/étiquette. **Pas de q_v19 requis** pour déployer cette chasse.
5. Seule l'APPLICATION MOTEUR des règles PLU du Lot 6 (gradation hauteur / recul H/2, `modifie_calcul:false` donc NON faite) demanderait un q_v19 — ~1 545 parcelles — décision séparée.

## Sortie du banc (finale)

```
[OK] surface-tuile-vs-fiche — fiche=tuile=25633
[OK] export-surface — export sert la contenance 25 633
[OK] export-cascade — export sert une cascade peuplée
[OK] export-disparue — export mentionne la disparition
[OK] partner-statut — 50/50 items avec statut servi
[OK] courrier-zone-bizone — zone unique « A »
[OK] compteurs-commune — compte = idus = stats sur 3 communes
[OK] accueil-totaux — accueil cohérent (433229)
[OK] prix-ancien-unique — projets = baromètre sur 24 communes (source unique)
[OK] sirene-etat — plus d'« actif » servi pour la SCI cessée
[OK] bodacc-fraicheur — fiche sert l'annonce vivante (2026-08-21) de bodacc_procedures
[OK] zero-menteur-nu — taux non mesuré → etat='non_mesure', hors filtre « Terrain nu »
[OK] cloche-fraicheur — cloche rejouée pour q_v18
[OK] digest-vs-cloche — digest et cloche sur le même run servi q_v18
[OK] courrier-surface — courrier sert la contenance 25 633 m²
[OK] disparue-documents — courrier refuse une parcelle disparue
[OK] comparatif-zone-dominante — comparatif sert la zone dominante « A »
[OK] simulplu-non-calculable — analogie non calculable servie comme telle (ratio None)
[OK] catnat-source-vs-zero — source disponible, 23 arrêtés
[OK] millesime-derive — RPLS/PM servis dérivés de la table
[OK] regles-plu-completes — gradation + formule H/2 + barème stationnement
[OK] ventes-100m-nature — « vente » = nature vente (l'échange n'en est plus une)
[OK] etude-zone-perimetre — rayon hors whitelist → isochrone (périmètre honnête)
[OK] ventes-12m-ancree — fenêtre ancrée : 57 ventes (≫ 13 du calendaire)

Bilan : 24 OK · 0 ECART · 0 SKIP (24 gardes)
```

## Commits (un par lot)

| Lot | Commit | Thème |
|-----|--------|-------|
| 1 | `73af6971` | une seule surface (contenance\|dessin) + drapeau partout |
| 2 | `d014195a` | une parcelle disparue est disparue partout |
| 3 | `95c08a23` | un seul run, une seule cascade |
| 4 | `7b76101c` | jamais un zéro qui ment |
| 5 | `14b9f948` | la donnée tierce à jour au point de lecture |
| 6 | `359ad26b` | les règles PLU fausses (vérité d'affichage) |
| 7 | `ad57ad0f` | une fenêtre, une formule, une étiquette juste |

## Les 83 écarts — disposition

Légende : **✅ fermé** (commit indiqué) · **🟡 motif** (laissé, raison).

### Lot C — même donnée, même valeur partout (45)

| # | notion | disposition |
|---|--------|-------------|
| C-01 | surface export md/html | ✅ L1 — tous les lecteurs via `surface_terrain()` |
| C-02 | disparue servie vivante (export) | ✅ L2 — export refuse + message |
| C-03 | cascade export (mauvais run) | ✅ L3 — `_build_fiche` lit la cascade résolue |
| C-04 | courrier « surface cadastrale » = dessin | ✅ L1 — contenance servie |
| C-05 | courrier surface incertaine | ✅ L1 — 2 chiffres + réserve |
| C-06 | comparatif zone = sous-zone calcul | ✅ L3 — zone dominante + parts |
| C-07 | courrier risques = cascade legacy figée | ✅ L3 — lit `dryrun_cascade_results` servi |
| C-08 | disparue servie par tous les documents | ✅ L2 — garde unique `cadastre_disparue` |
| C-09 | tuile surface = dessin | ✅ L1 — `mvt_parcels` bake la contenance |
| C-10 | tuile surface incertaine | ✅ L1 — drapeau baké dans la tuile |
| C-11 | partner statut null (run cascade) | ✅ L3 — jointure au run scoring |
| C-12 | /filtre compteur vs page vide (étage 0) | 🟡 L7 — latent : le front lit `.page` (pas `.compte` au-dessus d'une page vide) ; refactor compteur/idus risqué sans valeur client immédiate. Documenté. |
| C-13 | sdp ∅ (carte) vs 0 (fiche/liste) | ✅ L4 — une convention « — » + cause partout |
| C-14 | export surface = dessin | ✅ L1 |
| C-15 | export surface incertaine | ✅ L1 |
| C-16 | CSV projets surface = dessin | ✅ L1 — `COALESCE(contenance, surface_m2)` |
| C-17 | repère Bilan surface = dessin | ✅ L1 |
| C-18 | comparatif surface = dessin | ✅ L1 |
| C-19 | propriétaire PM absent des exports md/html | 🟡 motif : l'export md/html lit la prospection CRM, pas `parcelle_personne_morale` ; la PM EST servie par la fiche premium / le Dossier / le Courrier (cf. L5). Hors liste explicite du mandat ; gap de plomberie export md/html noté. |
| C-20 | prix ancien 2 formules | ✅ L7 — kanban/repères lisent `prix_ancien_communes` |
| C-21 | permis 12m deux fenêtres | ✅ L7 — ventilation sur la fenêtre ancrée du total |
| C-22 | n parcelles commune inclut disparues | ✅ L2 — `filtre_vivant_sql` |
| C-23 | copilote SDP double moteur | ✅ L3 — fourchette legacy hors contexte IA |
| C-24 | copilote surface = dessin | ✅ L1 |
| C-25 | copilote destination zone monozone | ✅ L3 — `zone_dominante` + parts |
| C-26 | digest surface = dessin | ✅ L1 — `COALESCE(contenance, surface_m2)` |
| C-27 | pagination partenaire sans départage | ✅ L3 — `ORDER BY … , p.idu` |
| C-28 | pied `doc-foot` jamais imprimé (PDF) | 🟡 L7 — limite WeasyPrint 70 (`string()`/`element()` non rendus), déjà constatée en base de code. Le @bottom-center STATIQUE du Dossier se rend ; généraliser aux autres PDF = refonte CSS @page (noté, non livré). |
| C-29 | /filtre bande/signal page seule | 🟡 L7 — latent : `getAnalyse` ne lit que `.page` ; piège pour appelant API direct. Documenté. |
| C-30 | tiers legacy filtre zéro | ✅ L7 — alias des deux vocabulaires |
| C-31 | digest aperçu fenêtre sans libellé | 🟡 L7 — param `periode` non rendu ; aujourd'hui 0 événement d'âge 2-7 j → invisible. Front/email. |
| C-32 | brief contredit suivis (cid None) | 🟡 L7 — ne touche que le mode pilote/dev (cid NULL) ; un compte client réel est cohérent. |
| C-33 | partage surface = dessin | ✅ L1 (0 token valide ⇒ non rejouable à vif, corrigé au code) |
| C-34 | radar moteur unique | ✅ L3 — vérifié : aucune divergence client (même producteur) |
| C-35 | KMZ disparue sans mention | ✅ L2 — description porte la disparition |
| C-36 | pied « Données au » = date génération | 🟡 L7 — la clé `donnees_labuse_au` n'a pas de producteur ; couplé à C-28 (WeasyPrint). Noté. |
| C-37 | étiquette « contenance » sur dessin | ✅ L1 — libellé conditionné à `surface_source=cadastre` |
| C-38 | RNU trois libellés | 🟡 L7 — choix DOCS-FIX-1 P5 assumé (le comparatif « hors zonage PLU » n'évoque pas le RNU) ; harmonisation de libellé, sans valeur fausse. |
| C-39 | opportunités deux périmètres | 🟡 L7 — endpoint `/projets/reperes` nb_opportunites sans appelant front (retrait entretien) ; exposition latente. |
| C-40 | accueil deux chiffres parcelles | ✅ L2 — parc vivant partout |
| C-41 | digest priorités déclassée sans nuance | 🟡 L7 — sélection digest sans filtre `declasse` ; nuance d'affichage mail. |
| C-42 | millésimes Étude de zone non imprimés | 🟡 L7 — le bloc PDF imprime une note statique ; relayer `zone['note']` = plomberie bloc (noté, non livré). |
| C-43 | digest q_score champ mort | 🟡 L7 — colonnes v1 éteintes jointes (null), NON rendues au mail ; nettoyage latent. |
| C-44 | cache point mort nocturne | 🟡 L5 — dérive ≤ 5 permis/j par ancrage `now()`, date du cache affichée (honnête) ; invalidation = job nocturne / purge `commune_contexte_cache` (reconstructible). |
| C-45 | cloche vs bascules servies | ✅ L5 — `detect_events` rejoué q_v16→q_v18 (54 bascules) |

### Lot D — la vérité face à la source (20)

| # | notion | disposition |
|---|--------|-------------|
| D-46 | SIRENE société cessée servie active | ✅ L5 — état unité légale lu de `owner_enrichment` |
| D-47 | BODACC fiche dernière annonce gelée | ✅ L5 — lit `bodacc_procedures` (vivante) |
| D-48 | hauteur graduée Saint-Joseph | ✅ L6 — gradation servie verbatim |
| D-49 | palier ≥ 2 500 m² Sainte-Rose | ✅ L6 — second palier servi |
| D-50 | recul H/2 réduit au plancher | ✅ L6 — formule « H/2, minimum 3 m » |
| D-51 | BODACC table owner gelée | ✅ L5 — même fix que D-47 (lecture de la table vivante) |
| D-52 | stationnement Étang-Salé UC | ✅ L6 — barème chiffré servi |
| D-53 | CatNat compte 23 vs 24 (dédoublonnage) | 🟡 motif : dédoublonnage COHERENCE-FIX-1 lot F avale un arrêté multi-événements (mars 2006) ; ingestion `catnat.py`, hors liste des lots du mandat — noté. |
| D-54 | RPLS millésime en dur | ✅ L5 — dérivé de `rpls_commune.millesime` |
| D-55 | OCSGE 2022 en dur (ingestion) | 🟡 L5 — JOIN millésime figé + contrôle qualité exigeant 2017/2022 ; ingestion, latent (correct aujourd'hui). |
| D-56 | front BPE/ZNIEFF 2025 en dur | 🟡 L5 — `layers.ts` porte son texte ; front (tsc non vérifiable ici), latent. |
| D-57 | PM `_MILLESIME_SERVI` en dur | ✅ L5 — `max(parcelle_personne_morale.millesime)` |
| D-58 | socle fiche sans Cadastre/BAN/CatNat | 🟡 L5 — panneau Sources bâti sur la cascade ; ajouter le socle hors-cascade = refonte `_data_sources_fiche`, noté. |
| D-59 | note GPU M40 périmée | 🟡 L5 — `plu_millesimes.yaml` fige une note contredite par `plu_depublies.yaml` ; réconciliation de config (données de référence), noté. |
| D-60 | BAN synchro 54 j | 🟡 L5 — fraîcheur opérationnelle (job BAN non rejoué) ; aucune divergence de valeur. Refresh = geste. |
| D-61 | DPE fraîcheur | 🟡 L5 — fraîcheur opérationnelle (sync ADEME) ; refresh = geste. |
| D-62 | CatNat étiquette millésime | 🟡 L5 — `source_millesime` (table de référence `data_sources`) non suivi par la re-moisson ; data-op / dérivation vitrine, noté. |
| D-63 | AZI/TRI étiquette millésime | 🟡 L5 — idem D-62. |
| D-64 | 17 vitrines sans millésime | 🟡 L5 — `data_sources.source_millesime` vide ; décision Vic à part (cf. Hors mandat). |
| D-65 | DVF ligne orpheline 2026 | ✅ L7 — exclue de l'ancre de fenêtre (timestamp ≠ minuit) |

### Lot E — étiquettes et absences (18)

| # | notion | disposition |
|---|--------|-------------|
| E-66 | ventes 12m étude zone calendaire | ✅ L7 — fenêtre ancrée (57 vs 13) |
| E-67 | état « Nu » sur emprise non mesurée | ✅ L4 — `non_mesure` (jamais « Nu ») |
| E-68 | filtre « Terrain nu » rend du bâti | ✅ L4 — prédicat `IS NOT NULL` |
| E-69 | étude zone rayon menteur | ✅ L7 — périmètre réellement calculé imprimé |
| E-70 | niveau de vie dit « médian » | ✅ L7 — « moyen » |
| E-71 | revenu médian zone = moyenne | ✅ L7 — « niveau de vie moyen » |
| E-72 | neuf « ventes récentes » | ✅ L7 — « ≤ 3 ans après achèvement » |
| E-73 | millésime médiane locale = année max | 🟡 L7 — `reference_locale` jette la période ; label (`Mon secteur` + radar). Front/étiquette. |
| E-74 | proximité « à pied » = vol d'oiseau | ✅ L7 — « à vol d'oiseau » |
| E-75 | ventes 100m toutes natures | ✅ L7 — `nature ILIKE 'vente%'` |
| E-76 | courrier périmètre sans rayon | 🟡 L7 — libellé statique omet le rayon 500 m ; texte courrier (noté). |
| E-77 | bornes rayon en dur divergentes (front) | 🟡 L7 — trois bornes front/back ; config servie à poser (front). |
| E-78 | assemblage max en dur front (8 vs 30) | 🟡 L7 — plafond front ≠ `config/moteurs.yaml` (30) ; à servir depuis la config (front). |
| E-79 | corpus modèle années en dur (front) | 🟡 L5 — `strings.ts` littéraux vs `/v2/modele` ; front, latent. |
| E-80 | CoSIA 2025 en dur (front) | 🟡 L5 — `ProspectionSolaire.tsx` littéral vs `data_sources` ; front, latent. |
| E-81 | filtre emprise ≤ X sans mesure | ✅ L4 — prédicat `IS NOT NULL` |
| E-82 | CatNat indisponible dit « aucun » | ✅ L4 — `disponible=True` réservé source présente |
| E-83 | SimulPLU ratio absent servi 0 | ✅ L4 — `calculable=false`, ratio None |

**Décompte : 55 ✅ · 28 🟡 = 83.**

## La question du run

**Aucune des 55 corrections livrées ne change une valeur de résiduel ou de score.** Tout est
lecture au point d'affichage, convention d'affichage, fenêtre d'agrégat, étiquette, ou garde de
cohérence. Détail par lot :

- **L1 (surface)** : CONTENANCE-1 avait déjà fait passer le RÉSIDUEL sur la contenance ; ici on
  n'a touché que les LECTEURS d'affichage (export, courrier, tuile-propriété, CSV, Bilan-repère,
  Comparatif, Copilote, digest, partage, Dossier). `mvt_parcels` reconstruite = matérialisation de
  tuiles (propriété `surface_m2` baked), pas un run.
- **L2 (disparue)** : refus de document + compteurs = parc vivant. Les parcelles disparues
  n'étaient déjà pas servies au run.
- **L3 (run/cascade)** : on LIT le bon run (scoring/cascade déjà servis) — aucun recalcul.
- **L4 (zéro)** : `non_mesure`, convention SDP « — »+cause, SimulPLU/CatNat — tout en lecture/CASE.
- **L5 (fraîcheur)** : SIRENE/BODACC/millésimes = lecture ; `detect_events` écrit `event_log`
  (notifications), pas le score ; `owner_enrichment` = cache reconstructible.
- **L6 (PLU)** : exceptions `modifie_calcul:false`, valeurs numériques du moteur INCHANGÉES → le
  résiduel ne bouge pas. Affichage seul.
- **L7 (fenêtres/formules)** : prix ancien, permis, ventes = agrégats au point de lecture.

**Faut-il un q_v19 avant déploiement ? NON** pour les corrections de cette chasse. Elles sont
déployables telles quelles (code + les gestes de cache/notifications déjà joués en local sont à
rejouer en prod : voir ci-dessous).

**Le SEUL chantier qui demanderait un q_v19** est l'APPLICATION MOTEUR des règles PLU du Lot 6
(faire que le RÉSIDUEL applique la hauteur graduée de Saint-Joseph U2 et le recul réel H/2 au lieu
du plancher) — explicitement NON fait ici (`modifie_calcul:false`). Si Vic le décide :
- parcelles en zone dominante concernées : **U2 Saint-Joseph 442 · Ua+1AUa Sainte-Rose 1 103** (D-52
  stationnement n'a aucun effet résiduel) ;
- il faudrait coder l'effet dans `plu_exceptions_effet.json` + le moteur `faisabilite`, relancer le
  résiduel puis le scoring, matérialiser, et basculer :
  ```
  PYTHONPATH=src .venv/bin/python -c "from labuse.cli import app; app()" residuel-run         # recalcul résiduel
  PYTHONPATH=src .venv/bin/python -c "from labuse.cli import app; app()" score-v2 --label q_v19  # scoring
  PYTHONPATH=src .venv/bin/python -c "from labuse.cli import app; app()" build-mvt --label q_v19  # tuiles
  PYTHONPATH=src .venv/bin/python -c "from labuse.cli import app; app()" golden promote q_v19      # bascule
  ```
  (commandes indicatives — à cadrer dans une chasse dédiée « PLU-MOTEUR », hors de celle-ci).

## Gestes DATA joués en local (à rejouer en prod au déploiement — reconstructibles, pas des runs)

- **mvt_parcels** reconstruite (`build-mvt`) + `mvt_meta` bumpé + `mvt_tile_cache` layer parcels purgé (L1).
- **owner_enrichment** rafraîchi pour les SIREN PM servis — cache recherche-entreprises (L5, D-46) ;
  en prod, rejouer le fetch (le cache local datait de juillet).
- **detect_events** q_v16→q_v18 (L5, C-45) — repeuple la cloche sur le run servi.
- **commune_contexte_cache** purgé (L7, C-21) — se reconstruit à la lecture (ou job nocturne).

## Hors mandat (chasses suivantes)
49 champs morts du payload · endpoints orphelins · `pdf_premium.py` · outil ZAN dormant (chasse
architecture) · 17 vitrines sans millésime D-64 (décision Vic) · PLU-MOTEUR (q_v19, cf. ci-dessus).
