# CHASSE-DONNEES-FIX-1 — RAPPORT (verdict)

Branche `fix/chasse-donnees-1`, worktree `~/Desktop/labuse-chasse-fix`, local q_v18, ports 8750/5950.
Exécution du `MANDAT-FIX.md` sur les 83 écarts de `ECARTS.md`, PUIS deux suites (règles PLU au
moteur + q_v19 ; fermeture des 28 motifs). **On a corrigé les CAUSES, pas les lignes** : un seul
chemin de code par notion, verrouillé par une garde du banc `scripts.coherence.chasse_donnees`.

## Verdict en 5 lignes (après les 7 lots + 2 suites)

1. **Banc : 25 OK · 0 ECART · 0 SKIP (25 gardes)** — exit 0.
2. **76/83 écarts FERMÉS en code** + **D-64 fermé par décision** (dates des sources réservées à l'admin). 6 restants = gestes PROD (voir plan de déploiement) dont C-38 (libellé RNU assumé, aucune valeur fausse).
3. **Suite 1 (PLU au moteur)** : les 4 règles du Lot 6 appliquées au MOTEUR (D-49 majoration ≥2 500 m², D-48/D-50 portées « non modélisées », D-52 hors-SDP). Run q_v19 (run_seq 16 = copie run 15 + delta 1 545) ⇒ **0 parcelle change SDP/cause/score** vs q_v18 (D-49 ne franchit aucun palier d'étage ; D-48/D-50 non modélisables sans sur/sous-estimer). **q_v19 ≡ q_v18, rien servi/basculé.**
4. **Suite 2** : 19 des 28 motifs fermés en code (PDF pied qui s'imprime enfin + date de donnée, propriétaire PM en export, /filtre carte=page, étiquettes/bornes front servies, socle de sources, digest, note GPU…). Front : `npm install` + `tsc -b` = **0 erreur**.
5. **AUCUN correctif livré (lots + suites) ne change le résiduel ni le score** — tout est lecture/affichage/fenêtre/étiquette/moteur-sans-effet. **Pas de q_v19 à déployer.**

> Note : le corps ci-dessous est le verdict des 7 LOTS initiaux (24 gardes). Les SUITES et le plan
> de déploiement sont en fin de document (« ## SUITES » et « ## PLAN DE DÉPLOIEMENT »).

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

---

# SUITES (12/10, même branche)

## SUITE 1 — règles PLU AU MOTEUR + run q_v19 (commit `bbfd4fc4`)

Les 4 règles du Lot 6 (affichage seul) sont entrées au MOTEUR de capacité, pour que la fiche ne
montre jamais une règle en calculant avec une autre. Mécanisme = `plu_exceptions_effet.json`
(déjà en place pour 81 exceptions) + `faisabilite/zonage.py` + `faisabilite/db.py`.

| Règle | Traitement moteur | Effet SDP |
|-------|-------------------|-----------|
| D-49 Sainte-Rose Ua/1AUa ≥ 2 500 m² | `majoration_surface` he_m 9→11, hf_m 12→14 (decision=applique) | APPLIQUÉE mais +2 m ne franchit AUCUN palier d'étage (3 m) → 0 |
| D-48 Saint-Joseph U2 (gradation profondeur) | `non_modelisee` : moteur à hauteur UNIQUE ; PORTÉE sur la fiche, garde le palier >12 m (13/11 = headline) | 0 |
| D-50 recul H/2 | NON couplé : inseter H/2 sur TOUTES les limites effondre la SDP (BW2262 503→131, AL1115 →exigu) car la mitoyenneté par limite est inconnue → PORTÉE « non modélisée », recul = plancher 3 m (borne haute) | 0 |
| D-52 stationnement | hors-SDP | 0 |

**Run q_v19** = `run_seq 16` : copie intégrale de run 15 (433 229 lignes) + recompute en delta des
**1 545** parcelles (U2 Saint-Joseph 442 + Sainte-Rose Ua/1AUa 1 103), `--into-run 16
--assiette-clippee` (comme le run 5 = copie run 3 + delta). **Comparaison à q_v18 (run 15)** :

- **SDP qui change : 0 · cause : 0 · score : 0** (le scoring ne lit que sdp/cause/taux/capacité, pas `regles_non_modelisees`).
- Seul delta : **412** parcelles portent la MÉTADONNÉE « règle non modélisée » (transparence fiche, SDP identique). 5 exemples : 97412000BO0219 (13 029 m²), BO0528 (2 939), BO0085 (466), BO0086 (682), BO0082 (226) — tous SDP INCHANGÉE.
- `run_seq 16` is_served=**false**, manifeste toujours sur run 15. **RIEN servi, RIEN basculé.**

**Verdict run** : appliquée FIDÈLEMENT, la règle PLU ne change aucune valeur servie. q_v19 ≡ q_v18.
Capture : `captures/CHASSE-DONNEES-FIX-1/suite1/RESULTAT.md`.

## SUITE 2 — fermeture des 28 motifs (commits `fd123682`, `c13471c3`, `d37eeb51`, `514565e9`, `c0e1dbfb`)

**19 fermés en code**, 9 restants (gestes prod + 1 libellé assumé).

| Écart | Fix |
|-------|-----|
| C-12 /filtre compteur vs page | la liste d'IDU (carte) = périmètre de la PAGE (hors étage 0 par défaut). Garde `filtre-carte-page`. |
| C-19 propriétaire PM export | `_pm_block` partagé → l'export md/html NOMME la société (SCI ALOE…) + état. |
| C-28 pied PDF non rendu | pied INJECTÉ en contenu LITTÉRAL `@page` (string() non rendu par WeasyPrint) → s'imprime sur les 4 PDF. |
| C-29 bande/signal page seule | bande/signal appliqués aussi à la liste d'IDU (bande=A → 612, plus 22 665). |
| C-31 digest période | la fenêtre est ÉCRITE dans le mail (param `periode` enfin rendu). |
| C-32 brief vs suivis (cid None) | `_mes_communes` lit les suivis du compte NULL (IS NOT DISTINCT FROM). |
| C-36 pied « Données au » | = date de la DONNÉE servie (`served_manifest.promoted_at` = 11/10/2026), plus la génération. |
| C-39 opportunités 2 périmètres | `/projets/reperes` = brûlante+chaude (Saint-Leu 14 465→29), notion unique. |
| C-41 digest déclassée / C-43 q_score mort | top digest = vrais prospects (hors étage 0, SDP>0, cause nulle) ; q_score/a_score retirés. |
| C-42 millésimes Étude de zone PDF | la note relaie les sources DATÉES servies (Filosofi 2021 · BPE 2025…). |
| D-56 / E-80 millésimes front | BPE/ZNIEFF (layers.ts) + CoSIA (ProspectionSolaire) : année en dur retirée, renvoi au millésime servi (page Sources). |
| D-58 socle fiche | Cadastre/BAN/CatNat ajoutés au panneau Sources (drapeau `socle`). |
| D-59 note GPU M40 | neutralisée quand la commune est dépubliée (Saint-André/Saint-Leu) — plus deux notes opposées. |
| E-73 millésime médiane locale | période réelle « 2022–2025 », plus l'année max seule. |
| E-77 / E-78 bornes front | NOUVEL endpoint `/moteurs/config` (source unique) sert rayons + plafond assemblage ; le front les lit. |
| E-79 corpus modèle (strings.ts) | contradiction « 2017-2025 » vs « 2017-2024 » levée (= /v2/modele). |

## PLAN DE DÉPLOIEMENT

### A. Gestes DATA/caches à rejouer en PROD (reconstructibles — PAS des runs de scoring)
Joués en local, à refaire sur le VPS après déploiement du code :
1. `build-mvt` (surface terrain bakée) + purge `mvt_tile_cache` layer parcels — L1.
2. refresh `owner_enrichment` (cache recherche-entreprises de juillet → état sociétés à jour) — L5 (D-46).
3. `detect_events q_v16 → q_v18` (repeuple la cloche sur le run servi) — L5 (C-45).
4. purge `commune_contexte_cache` (se reconstruit à la lecture) — L7 (C-21) / clôt C-44.

### B. Écarts RESTANTS — chacun dépend d'un geste PROD (aucun n'est un défaut de code servi)
| # | Reste | Geste prod requis |
|---|-------|-------------------|
| C-44 | cache point mort nocturne (dérive ≤ 5 permis/j) | job nocturne / purge `commune_contexte_cache` (fait en A4) ; date du cache affichée (honnête). |
| D-60 | BAN synchro (54 j) | rejouer le job de synchro BAN (aucune divergence de valeur constatée). |
| D-61 | DPE fraîcheur (ADEME) | rejouer le sync DPE ADEME. |
| D-62 | CatNat `source_millesime` étiquette | rafraîchir `data_sources.source_millesime` id 97 (ou le dériver de `max(ingested_at)`) — UPDATE table de référence. |
| D-63 | AZI/TRI `source_millesime` étiquette | idem id 114 (`max(maj_at)`). |

### B.bis — CODE corrigé avant déploiement (re-moisson en prod = Phase 9.4), TESTÉ en local
- **D-53 — FERMÉ (code)** : `ingestion/catnat.py` dédoublonne désormais sur `(code, péril, date_arrete,
  date_debut_evt)` = identité de ligne GASPAR. Vérifié par ré-ingestion locale : Saint-Paul **23→24**
  (= GASPAR, l'arrêté multi-événements INTE0600904A conservé), Saint-Denis 19→21 ; les « doublons »
  à même `date_debut` (noise GASPAR, ex. INTE1401216A) restent dédoublonnés (plus juste que GASPAR).
  **Prod : re-moissonner (`labuse ingest-catnat`).**
- **D-55 — FERMÉ (code)** : `ingestion/ocsge.py` lit le millésime le PLUS RÉCENT (`dernier_millesime_sol`
  = `max`) au lieu de « 2022 » figé (`precalcul_parcelles` + `construire_couche`, subtype/libellés
  dérivés) → un OCS GE ultérieur sera LU. Vérifié : en dynamique (max=2022) la couche est **identique**
  à la version figée (12 107 polygones, mêmes subtypes). **Prod : re-ingérer au prochain OCS GE.**

- **D-64 — FERMÉ (décision)** : les 17 vitrines sans millésime restent telles quelles — les **dates
  des sources sont réservées à l'ADMIN** (circuit/registre), pas exposées au client, **rien à changer
  côté client**.

### C. Libellé assumé (pas un geste prod, pas une valeur fausse)
- **C-38** : le Comparatif dit « hors zonage PLU », la fiche « commune au RNU » — MÊME fait (pas de
  PLU local), phrasé différent, aucune valeur fausse. Choix assumé DOCS-FIX-1 P5 ; laissé tel quel
  pour ne pas rouvrir une décision réglée.

### D. PLU au moteur (q_v19) — décision séparée
Le run q_v19 (suite 1) prouve que les règles PLU, appliquées fidèlement, ne changent AUCUNE valeur
servie. **Aucun q_v19 à servir.** Si un jour la gradation/le recul H/2 devaient entrer dans la SDP,
il faudrait d'abord doter le moteur d'une géométrie par limite (mitoyenneté) et d'un band-ing de
hauteur par profondeur — un chantier « PLU-MOTEUR » distinct, pas un simple recalcul.
