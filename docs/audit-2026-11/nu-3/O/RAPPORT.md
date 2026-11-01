# AUDIT-NU-3 — lot O : vérifier les faits jamais vérifiés

**Branche** `audit/nu-3-o` · worktree `~/Desktop/labuse-nu3-o` · ports 9360 (API)/6560 (front) · **LECTURE SEULE**
(aucun correctif, aucun merge, aucun accès prod). Lots L & M en parallèle.
**Source** : `docs/registre/FAITS.csv` (lot N, 1115 faits) — périmètre O = **les 402 faits marqués « jamais vérifié »**, et rien d'autre.
**Sortie registre** : `docs/registre/FAITS-verifies.csv` (colonne 12 remplie pour les 402, 0 autre colonne touchée).

---

## EN-TÊTE — faits encore jamais vérifiés après ce lot

| | début | après lot O |
|---|---:|---:|
| faits « jamais vérifié » | **402** | **0 non traités** |
| dont **vérifiés justes** | — | **352** |
| dont **en écart** (preuve + cause fichier:ligne) | — | **34** |
| dont **impossibles à recalculer en lecture seule** (raison documentée) | — | **16** |

**Les 402 ont tous été examinés.** Il ne reste **aucun fait non traité**. (Comptage par la colonne 12
du CSV ; 2 écarts « notionnels » de plus que le simple champ verdict des sous-auditeurs — OUT-CALC-003,
OUT-SECTEUR-004 — sont comptés en écart car ils divergent réellement même si la valeur brute est juste.)
Les **16 « impossibles »** ne sont pas
des trous d'audit mais des faits qui, par nature, ne se recalculent pas depuis la base en lecture seule
(service externe live GPU/IGN, paiement Stripe, branche latente sans témoin sur le run 17, pont UI pur) —
chacun avec sa raison ci-dessous ; pour chacun le **chemin de code / la config / le mapping a été confirmé**.
Le chef a lui-même **ramené 6 faits de « impossible » à « juste »** par recalcul SQL indépendant, génération
réelle de PDF, ou lecture de la source curée (détail § Impossibles).

## Méthode
- **Infra montée pour ce lot** (ce que le lot N n'avait pas pu faire — app non bootée) : API PDF-capable sur
  9360 (code identique à `main edffc61c4`, base `labuse` run 17 q_v20), front Vite réel sur 6560
  (proxy→9360), Playwright sur l'écran réel. Un **watchdog** a maintenu l'API (un worker unique, tombé
  ~1-2 min sous la charge des 6 sous-auditeurs concurrents — artefact de banc, pas un défaut produit).
- **6 sous-auditeurs en parallèle** (un par famille d'écrans) : pour chaque fait, **recalcul SQL indépendant
  depuis les tables sources** (pas une relecture du code), **≥5 cas variés** (parcelles/communes/projets
  différents ; pour les outils « à zone » au moins **une commune du littoral** — Saint-Paul/Saint-Pierre/
  Saint-Denis/Le Port — **et une des Hauts** — Cilaos/Salazie/Entre-Deux/Le Tampon), **comparaison à la
  valeur servie par l'API**, **confrontation réglementaire** au texte officiel, **vérif libellé**.
- **Confrontation à l'écran (chef, Playwright)** — ferme la réserve du lot N (libellés lus au JSX, jamais
  à l'écran) : captures réelles de la fiche parcelle, la fiche commune, le menu Outils, et des PDF générés
  (Dossier, Étude de zone, Comparatif). Voir `captures_ecran/` et `_chef_constats_ecran.md`.
- Résultats bruts par groupe : `resultats/*.json` ; agrégation `_finalize.py` → `FAITS-verifies.csv`.

---

## 1. Faits vérifiés justes (354)

L'arithmétique élémentaire est **juste partout**, confirmée par recalcul indépendant sur ≥5 cas. Principaux blocs prouvés :

- **Financier / Bilan (Doc) — 20/20 justes** : CA_HT, charge foncière, 8 postes, marge, sensibilité 3×3
  (9/9 cellules), bornes plancher/plafond, écart, seuil, prix de revient, garde hors-marché (3 bornes +
  relationnel bailleur>libre), **zonage A/B/C == `commune_zonage_abc`**. Recalcul au centime.
- **Taxe d'aménagement — barème 2026 EXACT** (fait fiscal critique) : valeur forfaitaire **892 €/m² hors-IdF /
  1 011 € IdF confirmée contre service-public.gouv.fr A15416** ; abattement 50 % / 100 m² par logement
  (CGI 1635 quater I), logement aidé (I-1°), parts communale (plafond 5 %) / départementale (2,5 % confirmée
  974), piscine 251 €/m², secteurs à taux majoré au grain parcelle. **écran == API == barème** sur 7+ surfaces.
- **TVA DOM** 8,5 % / 2,1 % social confirmée contre **CGI art. 296 / 296 ter** ; **CDAC seuil 1 000 m² = L.752-1** ;
  RTAA DOM 400/600 m, ZFANG art. 44 quaterdecies CGI, R.151-28 destinations : passe-plats fidèles.
- **Fiche parcelle / commune** : populations & ménages Filosofi (recalc centroïde-dans-zone exact),
  taux fiscaux REI, médianes DVF, KNN distances équipements, parts PPR/SIS, SDP résiduelle, capacité/70,
  ZAN, SRU, densité. Recalc exact à l'unité/au dixième.
- **Permis (Sitadel)** : partition exacte (récent + dormant + achevé + autre = total, invariant tenu),
  délai d'instruction = dépôt→autorisation, fiches permis (type/date/logements/surface/destination/statut,
  **état 4 = annulé bien dit**). **Comparateur de communes & baromètre** : vélocité/permis 5 ans/composite/
  rang, ancien/terrain/neuf VEFA (seuil 8) recalc==API 8/8.
- **Estimer / Comparer / Calculette** : **le doute historique grave est CORRIGÉ** — la valeur indicative
  d'une maison = surface bâtie DVF × €/m² du **bon type** (maison↔maison), PAS emprise × €/m² habitable ;
  nature lue sur la dernière mutation DVF ; fiabilité par bien (n + dispersion IQR). CA/charge/achat-max/
  négociation recalc à l'euro.
- **Scan patrimoine / Blocs / Veille / Successions / Assemblage (SDP)** : union-find des opérations reproduit
  à l'octet (CBO 21 ops/247 lgt, SHLMR 97/3869), SDP sur union insetée (pas somme des résiduels), zonages
  triés. **RGPD OK partout** : type de propriétaire servi, **nom de personne physique jamais exposé**,
  personnes morales (publiques/sociétés) seules nommées. **0 fuite** sur les faits de ce lot.
- **PLU / Étude de zone** : invariant 21 servables + 2 + 1 + 0 = 24, millésimes config==corpus, parts PLU
  (ST_Union ≤ 100 %), aléas+PPR, assainissement, espaces protégés, BPE dédup, fibre, acquisitions PM.

Détail fait-par-fait : colonne 12 de `FAITS-verifies.csv` (« vérifié nu-3-O, N cas, juste »).

---

## 2. Faits en écart (34) — preuve + cause fichier:ligne

Aucun écart n'est une **erreur d'arithmétique** : tous sont des **libellés qui sur-promettent, des périmètres
non homogènes d'un écran à l'autre, des fonctionnalités mortes (données calculées puis jetées), ou des
troncatures silencieuses**. Fil rouge identique aux audits NU précédents : *le calcul est juste, le danger est
l'assemblage, le libellé et le périmètre.*

### 2.a — Majeurs (ce que le client lit est faux, trompeur, ou une fonction annoncée absente)

| id | écran · libellé | écart prouvé | cause |
|---|---|---|---|
| **DOC-DOSSIER-045** | Dossier · SCOT | un SCOT `statut='en projet'` est rendu **« approuvé le 02/09/2024 »** (opposabilité trompeuse). Témoin 97424000AC0001 | `robinet_fiche.py:290-296` `_c_scot` écrit « approuvé le {date} » **sans lire `statut`** |
| **CA-002** | Carte · légende Verdict | palier **« Priorité » annoncé mais jamais affiché** : les ~500 parcelles `tier=priorite` peintes « À suivre » | `frontend/src/lib/status.ts:33` `PRIORITE_SERVIE=false` + légende à 3 éléments |
| **CF-013** | Carte · bandes A/B/C/D/0/NC | bande **« Hors classement » (6 659 parcelles, forêt publique) droppée** de la ventilation ; `bande_total` servi 425 691 vs réel 432 350 — **contredit le commentaire « rien n'est masqué »** | `app.py:4464,4487` clé HC absente de la liste de ventilation |
| **FP-B-039** | Fiche parcelle · Signal de marché | le bloc **ne s'affiche jamais** : le front lit `market_signal`, le builder servi ne l'émet pas (calcul sain mais non servi) | `marche.tsx:187` lit un champ absent de `_q_v2_fiche` (`app.py:7150`) |
| **OUT-ASSEMB-001/002/013** | Assemblage · surfaces | Assemblage sert la **surface de DESSIN** ; la fiche / le prefill taxe servent la **CONTENANCE cadastrale** → divergent sur **86,5 %** des parcelles (paire AY0248/AY0247 : 1 992 vs 2 048 m²) | `moteurs.py:205`, `assemblage.py:256` ne COALESCEnt pas la contenance (contrairement à `assemblage.py:56-58`) |
| **OUT-ZONE-032** | Étude de zone · Loyer médian commune | « loyer **médian** · commune » = en réalité **le secteur OLL le plus bas** (St-Denis 9,2 servi vs médian réel des 6 secteurs 11,5) | `zone.py:958-961` `ORDER BY annee DESC LIMIT 1` sans agrégation ni sélection secteur sur INSEE multi-secteurs |
| **OUT-SECTEUR-005** | Mon secteur · commune entière | « commune entière {X} €/m² » = `sector_price` **au centroïde**, pas la médiane communale (Tampon −28 %, St-Paul −19 %, St-Leu +16 %). Arithmétique écart/sens/phrase exacte 6/6 | `pige/signaux.py:127` `_dvf_bati` au centroïde servi comme « commune entière » |
| **OUT-CALC-006** | Calculette · VRD | le total VRD servi est juste (base × emprise **aménagée**) mais le front dit **« sur {terrain} m² »** : BV1609 « 8 190 € sur 3 110 m² » (90×3 110 = 279 900, ×34 d'écart apparent) | `frontend/.../constructibilite.tsx:364` phrase « sur {terrain_m2} m² » fausse |
| **OUT-COMPARER-009** | Comparer vs Calculette · charge foncière/m² | **même notion, 3,5× d'écart** selon l'écran : Comparer 37 €/m² (bilan calibré) vs Calculette 128 €/m² (défauts + neuf) sur AZ1645, hypothèses non signalées | `app.py:8779` (bilan servi) vs `bilan.py:compute_calculette` (défauts YAML) |
| **OUT-ZONE-013 / OUT-ZONE-016** | Étude de zone · médian bâti & par type | l'**instantané DVF servi** a un compte de ventes **systématiquement < la table `dvf_mutations` live** (maison 19<26/30<47 ; appart 27<43) → médiane déplacée. **Classe « instantané servi ≠ table live » (cf. PROD-VERIF-1 : le Mac n'est pas une image fidèle prod — à confirmer en prod)**. Bonus : champ JSON **`seuil:5` trompeur** alors que le seuil réel = **8** | `dvf_mediane.py:58-77` (snapshot) ; `zone.py:677` (`seuil:5`) vs `dvf_mediane.py:31` (SEUIL_N=8) |
| **OUT-PERMIS-009** | Permis · N à moins de 200 m | `LIMIT 100` **tronque silencieusement** : parcelle dense 185 réels → **100 affiché** (c200 aussi faussé), sans « sur N » | `modules.py:754` `ORDER BY dist_m LIMIT 100` |
| **OUT-PERMIS-011** | Permis · fenêtre | date exacte, mais le registre dit « 24 mois » tandis que l'écran rend **« 240 mois »** et l'endpoint **n'est pas fenêtré** | `ModulePanel.tsx:852` `Math.max(...MONTHS_RADAR)=240` + `modules.py:742-754` aucun prédicat de date |
| **OUT-PERMIS-017** | Permis · colonne | la branche **« {commune} »** du libellé n'est **jamais peuplée** (champ omis des items servis) | `modules.py:656-657` DROP `commune` (pourtant sélectionné l.594) |
| **OUT-PLU-008** | PLU · {n} extraits | « {n} extrait(s) » = **page plafonnée par `limit`** (q=construction : 2 340 réels → n=25/200 affichés), pas le total | `modules.py:2813` `n=len(res)` + `plu_ingest.py` LIMIT sans count |
| **OUT-SCAN-006** | Scan · blocs contigus | compte n=460 juste mais **liste tronquée à 12** sans le signaler | `modules.py:453` `brs[:12]` |
| **DOC-APPORTEUR-018** | Apporteur · §6 ICPE | le détail ICPE (nom/régime/distance) est **calculé puis jeté** (orphelin) : le PDF n'affiche que la phrase générique. Spec RECETTE-11 D7 non livrée. Témoin 97407000AZ0019 (SCI MILHAC, 93 m) | `builder.py:476,514` `icpe_detail` produit, `apporteur.py:262` `industriel` jamais consommé |
| **DOC-APPORTEUR-017** | Apporteur · §6 Ligne HT | question « Ligne électrique/pylône » **morte** (0/6 PDF) | `builder.py:513` `obs_ligne_ht=False` en dur |
| **DOC-ETUDEZONE-013** | Étude de zone · Risques/Assainissement | **deux lignes mortes** : la condition lit `.libelle`, clé absente des dicts producteurs → **jamais imprimées** alors que la donnée existe | `exports/blocs/etude_zone.py:131-135` vs `zone.py:746,789` (pas de clé `libelle`) |

### 2.b — Mineurs (valeur juste, libellé imprécis / cas limite / fuite cosmétique)

| id | écart | cause |
|---|---|---|
| **DOC-DOSSIER-063** | fibre non raccordable → **enum technique brut `aucun_immeuble`** servi au client au lieu du `detail` lisible | `miroir.py:541-543` fallback `str(etat)` |
| **DOC-ESTIMER-009** | exposition Estimer (moteur `faisabilite`) **≠** exposition fiche en-tête (moteur `enrichment`) sur 3/5 cas (rejoint NU-3-J « pente/exposition latente ») | `robinet_fiche.py:124-135` vs `enrichment.py:154-187` (deux calculs d'azimut) |
| **DOC-ETUDE-029** | libellé « Espaces libres · dont pleine terre » n'affiche **que** `pleine_terre_m2` (ambigu) | `etude_faisabilite.py:676` |
| **FP-B-060** | libellé « logements + **% QPV** » mais le % QPV **n'est pas servi** (strippé car mal ingéré = 100 %) | `app.py:4841` retire `pct_qpv` |
| **OUT-SCAN-003** | « surface totale » = somme des surfaces de **dessin**, pas la contenance (Δ ~0,07 %) | `modules.py:386` |
| **OUT-ZONE-007** | « postes salariés **déclarés** » = somme des **bornes de tranches d'effectif**, pas l'emploi localisé | libellé `zone.py:274` |
| **OUT-COMMUNE-010** | légende « terrain nu sous **5** ventes » mais suppression réelle à **n<10** (part neuf <8 juste) | `blocB.tsx:294` vs `dvf_profils.yaml terrain_cellule_commune:10` |
| **OUT-COMMUNE-018** | barre de progression = **clamp front-only** `max(4,…)` graphant le % **restant** ; réf registre `rarete.py:414` inexistante | `blocB.tsx:414-415` |
| **OUT-COMMUNE-019** | triple vocabulaire de statut rareté (brief ≠ API « tension forte/modérée » ≠ écran « {N} ans ») ; seuils couleur ≠ paliers API | `blocB.tsx:413,426,434` vs `rarete.py:86-89` |
| **OUT-SECTEUR-007** | « {n} extrêmes **(5 %)** » inclut aussi le garde-fou de domaine [1000;12000] (Cilaos 17,8 %) | `bilan.py:149` + libellé `MonSecteur.tsx` |
| **OUT-SECTEUR-009** | note dit seuil **8** mais la cellule par-type vide affiche « échantillon < **5** » (vestige) | `MonSecteur.tsx:43` vs `mon_secteur.py:163` |
| **OUT-CALC-003** | Calculette · terrain = surface de **dessin** (909 m²) alors que Comparer/Estimer/Dossier servent la **contenance** (986 m²) — surface non homogène inter-outils | `modules.py:2445` (dessin) vs `app.py:8751`/`api.py:1666` (contenance) |
| **OUT-SECTEUR-004** | libellé « Tendance **12 m** » = en réalité un **split demi-années sur 5 ans**, pas 12 mois glissants | `pige/signaux.py` (fenêtre tendance) |

### 2.c — Hors-402 mais remonté par le banc (fiscal) — à signaler
- **Taxe, exonération petites surfaces : borne STRICTE `< 5` au lieu de `≤ 5`** (`taxe_amenagement.py:256`).
  À **5 m² pile** l'app taxe (assiette 4 460 €) ; 4,99 m² → 0 €. Or CGI art. **1635 quater D, 10° = « inférieure
  ou égale à 5 m² »** (confirmé **BOFiP BOI-IF-TU-10-20-30-160** + Légifrance, confronté par le chef). Cas limite,
  mineur, mais écart réglementaire réel.

---

## 3. Faits impossibles à recalculer en lecture seule (16) — et pourquoi

Non pas des trous, mais des faits dont la valeur **ne se recompute pas depuis la base** ; pour chacun le
chemin de code a été lu et confirmé cohérent.

| id | pourquoi impossible | ce qui a quand même été confirmé |
|---|---|---|
| **DOC-DOSSIER-010** | secteur/lieu-dit BD NYME (rayon 600 m) = passe-plat, clé vide sur mes cas | chemin `builder.py`, fallback conforme |
| **DOC-DOSSIER-016** | `divisible_classe` non servi sur run 17 (« à rebrancher » confirmé) | rendu = « non évaluée » (pas de faux 0) |
| **DOC-DOSSIER-032** | aucun témoin d'établissement **non-diffusible** → branche de masquage RGPD non exerçable | la liste SIRENE elle-même est servie |
| **DOC-FLASH-002** | fulfillment Flash **derrière un paiement Stripe** (statut 'payée') | machine à états code-confirmée (token 30 j, idempotent) ; doute confirmé : échec → `statut='erreur'` sans message chiffré (`facturation.py:271`) |
| **FP-A-027** | note « vif≠gelé » **non déclenchable** : 0 parcelle run 17 avec `surface_run ≠ contenance_live` | logique code saine |
| **FP-B-063** | `temps_min` = **isochrones IGN externes** (aucune table source) | mapping buckets correct ; valeurs servies plausibles |
| **OUT-ASSEMB-005** | avertissement **front pur** (`filter sdp_m2<=0`) | `sdp_par_parcelle` back cohérent |
| **OUT-BLOCS-013 / 014** | **ponts UI purs** (setPrefill SIREN / IDU membres → autre module) | SIREN / IDU sous-jacents vérifiés corrects |
| **OUT-ESTIMER-027** | le Radar **ne conserve pas** la description d'annonce (doctrine « faits + lien », `api.py:1194` titre=None) | tuile masquée par conception |
| **OUT-PLU-006 / 007** | pack .zip résolu **en direct sur le GPU** (geoportail-urbanisme, réseau externe injoignable ici, http=000) | pour communes servables, nom document sourcé en base |
| **OUT-SCAN-014** | badge « annonce Radar rattachée » dépend de l'**état live** Radar/`pige_biens` | logique `EXISTS` opération active confirmée |
| **OUT-ZONE-009** | `emplois_couverture='non_couverte'` seulement si `sirene_etablissements` vide — **table = 155 505 lignes → branche jamais atteinte** (latente) | code correct, non déclenchable |
| **OUT-ZONE-036** | dégradé **isochrone-KO** non forçable (l'IGN répond) | code correct (`zone.py:1006-1009`), non déclenchable |
| **OUT-TEMPS-006** | contour blanc + étiquette IDU = rendu carte (pin) | géométrie servie correcte ; affichage à voir écran |

**Faits ramenés de « impossible » à « juste » par le chef (hors des 16) :**
`FC-034` (lecture de `config/veille_plu.yaml` : 24/24 `date_acte=ABSENT` → `date_reglement=None`, mapping
`fiche_commune.py:267` exact, API 5/5 None) · `OUT-COMPARER-019` (`/comparatif.pdf` généré, contenu ==
comparateur) · `DOC-DOSSIER-080` (recalcul Filosofi centroïde-dans-rayon-2 km = **2 125 == servi 2 125**) ·
`DOC-ESTIMER-002/003` & `DOC-ETUDEZONE-002` (cartes **présentes** au PDF, légende/source correctes ; pixels
tuiles IGN live hors byte-vérif) · `OUT-TEMPS-001/002/003` (libellés statiques `basemaps.ts` confirmés exacts).

---

## 4. Confrontation des libellés à l'écran (réserve lot N fermée)

Captures réelles (`captures_ecran/`) : **fiche parcelle** Saint-Paul, **fiche commune** Saint-Paul, **menu
Outils**, **PDF Dossier / Étude-zone / Comparatif**. Constats de libellé propres à l'écran (en plus des écarts) :

- **Fiche parcelle — deux surfaces à l'écran** : en-tête « SURFACE 11,62 ha » (= contenance cadastre
  116 225 m², correct, `surface_source=cadastre`) mais cartouche carte « 115 449 m² » (= dessin géométrique) —
  Δ 0,67 %, aucun libellé ne distingue « cadastre » vs « dessin ». Mineur ; cohérent avec la famille Assemblage.
- **Sélecteur Fiche commune — code POSTAL, pas INSEE** : « Saint-Paul 97460 », « Saint-Leu **97424** » (= Piton-
  Saint-Leu ; le bourg est 97436). La fiche commune, elle, affiche bien l'INSEE « 97415 ». Écho du mineur NU-1-B.
- **Gotcha routing confirmé** (remonté par le groupe FICHES) : `/communes/{commune}/contexte` est indexé par
  **nom**, pas par INSEE — un appel par code renvoie silencieusement des zéros/None.

## 5. Limites de ce lot
- **Pas d'accès prod** : les faits classés « instantané servi ≠ table live » (OUT-ZONE-013/016) sont à
  **confirmer en prod** — le Mac sert un snapshot DVF qui diverge de `dvf_mutations` (artefact PROD-VERIF-1,
  pas nécessairement un défaut prod).
- **Un seul worker API** sous 6 sous-auditeurs → coupures ~1-2 min (watchdog) ; tous les agrégats critiques
  recapturés serveur vivant. Les PDF via WeasyPrint (venv `labuse-main`, code identique à `main`).
- **16 faits** restent non-recomputables en lecture seule par nature (§3) — leur chemin de code est confirmé.

## 6. Fil rouge
Arithmétique **juste** (fiscal, DVF, Filosofi, SDP, permis, bilan — tout recalculé exact), RGPD **propre** sur
ce lot (0 nom de personne physique exposé). Le risque réel, constant depuis NU-1 : **le libellé qui sur-promet
(SCOT « approuvé », « médian » qui ne l'est pas, « sur {terrain} m² », fenêtre « 24 mois »), la surface non
homogène entre écrans (dessin vs contenance), les fonctions annoncées mais mortes (ICPE, Ligne HT, Signal de
marché, Risques Étude-zone), et les troncatures/paliers silencieux (LIMIT 100, [:12], HC droppé, Priorité
jamais peinte).** 34 écarts, 0 bloquant, 0 erreur de calcul.

---
*Fichiers : `docs/registre/FAITS-verifies.csv` (col.12) · `RAPPORT.md` · `resultats/*.json` (recalculs bruts) ·
`captures_ecran/` (écran réel + PDF) · `_chef_constats_ecran.md` · `_ecarts_detail.json` · `_finalize.py`.*
