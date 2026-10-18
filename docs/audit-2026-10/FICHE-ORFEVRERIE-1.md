# FICHE-ORFEVRERIE-1 — fiche parcelle : vérité des données, rangement, finitions

**Branche** `fix/fiche-orfevrerie-1` (worktree `~/Desktop/labuse-fiche-orf`, ports 8820/6020) · base `origin/main` (`fa03c59e`).
Témoin principal : **HR0025** (`97411000HR0025`, Saint-Denis, Moufia). Pas de merge. Scoring / run / panneau
Faisabilité / exports NON touchés. DA existante respectée (primitives fiche-v6, règles RETOURS-19).

## Commits (un par lot, Lot A en premier)

| Commit | Lot |
|---|---|
| `51d516bb` | LOT A — données vraies et bien raccordées |
| `d4e5b1bb` | LOT B — un fait, une place (fiche à 10 sections) |
| `998135dc` | LOT C + LOT D — textes propres et UI alignée |

## Vérification

- **Front** : `tsc -b` **0 erreur** · `vitest run` **259/259 verts** (1 snapshot `formes` mis à jour — chevron d'accordéon).
- **Back** : `pytest` ciblé (le_bien, bâti, aléas, potentiel, contenance) **49 passés, 1 skip**.
- **Banc** `scripts.coherence.banc --en-process` (120 parcelles / 24 communes, 3 791 comparaisons) :
  **63 écarts réels — TOUS des familles PRÉ-EXISTANTES documentées** (tiers_hauts_n 22, n_parcelles_commune 24,
  cinquante_pas 5, surface arrondie 4 TOLERABLE, copro 3, prix_neuf 3, taxe 2 — baseline ORACLE-FIX-1/CHASSE-FIX-1).
  **0 écart ne touche un champ modifié par ce mandat** (les 4 écarts `surface_parcelle_m2` sont des arrondis sur
  `fiche:surface_m2` = dessin, non modifié). Les 1 198 autres lignes du CSV sont un **échec d'environnement du
  décodeur de tuiles Node** (`decode_tile.mjs` → `ERREUR(Expecting value…)` sur CHAQUE tuile), sans rapport avec
  les changements (aucune tuile touchée).
- **Captures** avant/après par section : `docs/audit-2026-10/FICHE-ORFEVRERIE-1/captures/{avant,apres}/` (vrai navigateur, 1440×900).

---

## Les 30 points

### Lot A — données fausses ou mal raccordées (HR0025)

| # | Point | État | Détail |
|---|---|---|---|
| 1 | Surface : un seul chiffre = contenance, retirer « surface utile » | **Fait** | `bati.py le_bien_block` : surface = `surface_terrain(dessin, contenance)` = **1 024** (contenance) partout (`surface_parcelle_m2`, base CoSIA). Aucun libellé « Surface utile » n'existait dans la fiche (le nombre géométrique 1 026 vivait via `surface_libre`/`surface_parcelle_m2`, désormais unifiés sur la contenance). |
| 2 | « 875 m² au sol libre » → **873** (1 024 − 151) | **Fait** | Même correctif : `surface_libre = contenance − emprise = 1 024 − 151 = 873`. Vérifié JSON + capture Terrain. |
| 3 | Recul limites « — » / Pleine terre « — » : afficher, distinguer non réglementé / non calibré | **Fait** | `blocs.tsx` : une formule (recul calculé, Art. Um.7) s'affiche abrégée (**« L ≥ h/2 »**) ; « non réglementé » (état *absent*, article lu) se dit ; « non calibré » réservé à une règle non lue. Plus de « — » muet. |
| 4 | Marge en hauteur « ~3.5 m » : dire quelle règle mord | **Fait** | `constructibilite.tsx` : **« ~3,5 m sous la règle à l'égout (7 m) »** (`hauteur_contrainte`/`hauteur_regle_m` déjà servis). Format `3,5`. |
| 5 | Pente : une seule unité, axe < parcelle expliqué, dénivelé une décimale, « 7,9 ° » | **Fait** | % équivalent ajouté au verdict Terrain (**« 7,9° (≈ 14 %) »**, comparable au profil) ; note du profil explique axe unique ≠ pente d'ensemble ; dénivelé `+0,4 m / −3,4 m` (une décimale) ; espace avant `°` retiré partout. |
| 6 | Bâti : « 3 bâtiments » + « Présence à vérifier » | **Fait** | 3 BD TOPO ≠ 2 RNB → **« Sources discordantes : 3 BD TOPO · 2 RNB »** (plus de « à vérifier » muet) ; faîtage 5,0 m annoté **« bâtiment principal »**. Sous-titre du tiroir aligné. |
| 7 | Potentiel : 11 étapes des 318 m², étape limitante nommée | **Fait** | Backend `_potentiel_transformation_block` expose un `calcul` (recalcul LECTURE SEULE, attaché seulement s'il retombe sur la SDP servie). Repli **« comment on arrive à 318 m² »** : SDP maximale (461, emprise 512 · R+1, net) − bâti conservé (143) = 318 ; **étape limitante nommée**. La chaîne évite le piège « 512 × R+1 » (la SDP max n'est pas un simple produit). |
| 8 | PPR zone bleue : aléa + niveau + prescription en une ligne | **Fait** | `risques.tsx` sert le **libellé complet** : « Zone bleue PPR inondation et mouvement de terrain (toute la parcelle) — constructible SOUS PRESCRIPTIONS (règlement DEAL). » |
| 9 | Le « 100 % » doit être mesuré | **Fait (vérifié)** | `servitudes.aleas_parcelle` calcule `part_pct` par **intersection géométrique** (`ST_Area(ST_Intersection…)/ST_Area(parcelle)`) — déjà mesuré. Tooltip ajouté qui le dit. |
| 10 | Stationnement « 1 / logt » → plafond TCSP ≤ 800 m | **Fait (câblé) ; écart assumé sur HR0025** | La tuile Stationnement étiquette **« plafond TCSP ≤ 800 m »** (L151-36, loi 2025-1129) quand une station en **site propre** est servie sous 800 m (`proximites.tcsp.sous_800m`). Sur HR0025, `tcsp = null` : la couche TCSP site-propre ne place aucune station sous 800 m (le pôle d'échange Moufia à 528 m est un hub bus, non marqué site-propre) → l'étiquette n'apparaît pas, « 1 / logt » reste la règle du PLU. Câblage correct, prêt pour les parcelles concernées. |
| 11 | Fiscalité : FRR à la source, QPV testé à la parcelle | **Fait** | QPV = fait **géométrique** de la parcelle (`ST_Intersects` au back) : la pastille QPV sort des « dispositifs de la commune », remplacée par un statut parcelle **« QPV (parcelle) : hors QPV — à moins de 500 m (bande TVA) »**. FRR vérifié (commune FRR *en partie*, parcelle DANS la ZSAR les Hauts via `frr_position`). |
| 12 | Quartier : « dernier 01/01/2024 » = précision annuelle → « 2024 » | **Fait** | `DepotsBlock` passe de `fmtDateNum` à `fmtDateSitadel` → **« dernier 2024 »**. Périmètre déjà correctement nommé « section cadastrale ». |

### Lot B — un fait, une place

| # | Point | État | Détail |
|---|---|---|---|
| 13 | SDP / assainissement dédupliqués, vocabulaire « SDP restante » | **Fait** | Réseaux : l'assainissement vit à deux endroits VOULUS (valeur d'en-tête + « case » CasesEtat) ; doublons retirés (sous-titre « Assainissement : collectif », contexte du Verdict). |
| 14 | DPU & SUP PM1 en double : une ligne Urbanisme, Risques renvoie | **Fait** | DPU & PEB retirés de « Situation » (ils vivent dans « Dispositifs et périmètres ») ; la SUP en Risques devient un **renvoi** « détail en « Urbanisme » », le détail reste dans Urbanisme. |
| 15 | Prix de l'ancien (secteur) = tuile Appartement → retirer ; deux prix du neuf | **Fait** | Ligne « Prix de l'ancien (secteur) » retirée (répétait la tuile Appartement). Prix du neuf : une écriture par échelle — VEFA **commune** en Marché, prix de sortie **local** en Potentiel (label « médiane locale », base du bilan). |
| 16 | Simulation fusionnée dans Potentiel → 10 sections | **Fait** | Section Simulation supprimée. « Prix de sortie retenu 4 275 €/m² » = **ligne du Potentiel** ; boutons Calculette foncière + Assemblage rejoignent **un seul « Étude de faisabilité »** + Densifier ; bilan & réhabilitation en sous-groupe. `SECTION_LABELS`, recherche, replis, kicker « Le projet » mis à jour. **10 tiroirs** vérifiés au DOM. |
| 17 | Quartier : 4 échelles + deux « niveau de vie » | **Fait** | Chaque bloc porte son échelle (**« Revenus du secteur · carreau INSEE 200 m »**, **« Parc social · commune entière »**, IRIS « maille quartier ») ; parc social SORTI du bloc secteur. « Niveau de vie moyen » **vérifié** : le champ servi est la **moyenne** du carreau (`nivvie_moyen_eur`, CHASSE-DONNEES-FIX-1 E-70), « moyen » est exact — *pas* la médiane Filosofi. |
| 18 | Retirer verdicts déduits (SDP résiduelle « petit collectif / 2-4 lots », badge « Fort ») | **Fait (partiel documenté)** | Badge « Fort / Modéré… » retiré du Potentiel de transformation (ne restent que les états opératoires *différé*/*non retenue* + les faits : SDP consommée, marge en hauteur). La mention « petit collectif / 2-4 lots » **n'existe pas** dans le code actuel (recherche front+back infructueuse — déjà absente/supprimée antérieurement). |

### Lot C — textes : zéro jargon, zéro troncature, zéro code brut

| # | Point | État | Détail |
|---|---|---|---|
| 19 | Retirer le jargon | **Fait (en grande partie)** | Retirés : « deux canaux, jamais un conflit », « Information de fiche, jamais un signal de classement », « bloc D du modèle P » (→ « ratio de densité »), « aplat commune » (→ « à l'échelle de la commune »), « Contexte informatif — hors scoring ». **Restent** (écart assumé, budget) : « faisceau viabilisation (le test au contact strict… » et « millésime… DEAL Lizmap » (nom de portail source légitime). |
| 20 | Codes bruts → libellés | **Fait (en grande partie)** | `vefa_neuf` → « Logement neuf (VEFA) » ; `dpu`/« GPU typeinf 04 » supprimés (dédup Lot B pt 14) ; « code hydro 10B… » retiré de l'affichage ; `PM1` → « Plan de prévention des risques naturels · PM1 » ; « SCOT DE LA CINOR » → **« SCoT de la CINOR »**. **Reste** : « M-VIA » (interne CLI, non affiché fiche) ; noms BPE en capitales ne sont pas affichés dans la fiche actuelle (cat + distance seulement). |
| 21 | Troncatures → valeur à la ligne, jamais d'ellipse | **Fait (partiel)** | « (PLU » réparé (retrait propre du parenthétique, plus de coupe à la virgule) ; « p.68 » → « p. 68 » ; bassin versant en paragraphe qui passe à la ligne. **Restent** (écart assumé, budget) : Destinations, compétence CINOR, DSP eau/assainissement, courriel EDF, bruit routier, raccordement, solaire, DVF archives (la primitive `Ligne` tronque par ellipse ; un passage global en valeur-longue dépasse le périmètre de finition). |
| 22 | Formats français | **Fait** | `3.5`→`3,5` · `4878`→`4 878` · `100%` déjà `100 %` (helpers) · `7,9 °`→`7,9°` · `p.68`→`p. 68` · `5 op.`→`5 opérateurs`. Reste `2026-07`→texte : non localisé dans la fiche (les millésimes affichés sont déjà en toutes lettres). |
| 23 | Paragraphes gris de Réseaux → ligne ou repli | **Écart assumé (budget)** | Le paragraphe « Accès voirie… » reste un paragraphe gris ; non ré-agencé en repli « 4 indices » faute de budget. |
| 24 | Ligne MT → distance ; Fibre « 0 m » | **Fait** | « Ligne moyenne tension » → **« ~14 m »** (plus de « à proximité » muet) ; Fibre « 0 m » → **« sur place »** (vérifié : l'immeuble Arcep est au contact de la parcelle). |

### Lot D — UI

| # | Point | État | Détail |
|---|---|---|---|
| 25 | En-tête : valeurs clés, retirer « isochrone » & « DVF · DVF » | **Fait** | Réseaux → valeur **« assainissement collectif »** ; Quartier → **« commerces 24 m »** (plus de badge « isochrone ») ; Marché → **« DVF »** une fois (plus de « DVF · DVF »). Le badge « bilan » a disparu avec la section Simulation (pt 16). |
| 26 | Replis : flèche à gauche → accordéon standard (droite fermé, bas ouvert) | **Fait** | Le chevron partagé (`Chevron`) aligné sur RETOURS-19 : **fermé → droite (▶), ouvert → bas (▼)** ; `Repli` utilise désormais ce composant (plus de glyphe ◀ bespoke). Vérifié sur les replis (CatNat « › », détail du bâti, dispositifs…). |
| 27 | Ligne SUP « Plan de prévention… » casse la grille → valeur-longue | **Fait** | Les servitudes passent en **forme valeur-longue** (libellé en tête, valeur dessous qui passe à la ligne) : « Plan de prévention des risques naturels · PM1 » ne casse plus la grille mono. |
| 28 | Acquéreur PM : SIREN cliquable Pappers, casse normale | **Fait** | `casseSociete` → **« SCCV Le Jardin de la Bourgogne »** + **SIREN cliquable** (composant `Siren` → Pappers). |
| 29 | Bassin versant sort des vigilances → info ; bandeau/badge à 3 | **Fait** | Bassin versant = **ligne d'information** (hors vigilances) ; badge Risques **4 → 3** (vérifié au DOM). |
| 30 | Icônes d'en-tête : triangle/globe reconnaissables + liens sur la bonne parcelle | **Fait (liens) ; écart assumé (logos)** | Liens vérifiés : Google Earth = `/parcels/97411000HR0025.kmz` (bonne parcelle) ; État des risques (Errial) par adresse/commune (limite de l'outil Errial). Les deux pictos portent `Tip` + `aria-label` explicites (sens au survol). Les **logos de marque** (Géorisques / Google Earth) à la place des SVG génériques dépassent le périmètre (travail d'assets) — écart assumé. |

---

## REPRISE (5 points + 2 questions) — commit `fix/fiche-orfevrerie-1` (pas de merge)

Les écarts assumés de la première passe ont été repris — zéro troncature est une règle.

- **pt 4 — l'égout.** Bâti affiche désormais **faîtage ET égout mesurés** côte à côte (tuiles « Faîtage (LiDAR) 5,0 m · survol septembre 2023 » et « Égout (LiDAR) 3,5 m · bord de toit · commande la surélévation »), le verdict dit la **date de survol** et **lequel des 3 bâtiments** (« bâtiment principal », le plus grand — `hauteur_parcelle_lidar`). La mention **« Mesure possiblement périmée »** s'affiche si un permis a été autorisé après le survol (`hauteur_permis_posterieur`) — absente sur HR0025 (aucun permis postérieur).
- **pt 9 — TCSP, activé.** Le **Téléphérique Papang** (Moufia, 531 m) est un **transport public GUIDÉ** (câble urbain), couvert par l'art. **L151-34 à L151-36** du code de l'urbanisme (« gare ou station de transport public **guidé** ou de transport collectif en site propre », loi n° 2025-1129). À 531 m (< 800 m), il déclenche le plafond : la tuile Stationnement affiche **« 1 / logt · plafond TCSP ≤ 800 m (531 m) »** et le « i » cite l'article + le mode. Le pôle d'échange bus Moufia (528 m) n'était pas marqué « site propre » dans la couche TCSP ; c'est le **téléphérique** (guidé) qui qualifie. Activé plutôt que justifié non-applicable.
- **pt 18 — « petit collectif / 2-4 lots ».** Trouvé au back (`cascade/layers/etage0_ext.py`, barème `SOCLE_TIERS` de la couche de **scoring** `residuel_socle`). Comme le scoring ne se touche pas, la couche continue de scorer ; sa ligne — un **verdict déduit + du jargon de barème (« socle +5 »)** qui fuitait en Situation — est **retirée de l'affichage de la fiche** (filtre `residuel_socle`, comme DPU/PEB). La SDP restante, elle, vit déjà au bandeau et en Potentiel. Vérifié : plus de « petit collectif / 2-4 lots » en Urbanisme → Situation.
- **pt 19 / 21 / 23 — zéro troncature, zéro jargon (Réseaux et ailleurs).** Primitive `Ligne` dotée d'un mode **`long`** (valeur pleine SOUS le libellé, passage à la ligne, **jamais d'ellipse**) ; `SourceRef` ne tronque plus (wrap). Appliqués : compétence **CINOR** (nom complet), **DSP eau** et **DSP assainissement** (complets), **raccordement**, **solaire**, **bruit routier** (plein), **DVF archives** (« géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 », complet), **accès voirie** (plein). Jargon retiré : **« faisceau viabilisation »** et le détail de méthode interne (`served_cascade.py`, libellés en clair) ; **« faisceau de preuves »** → « indices » ; **« aplat commune »** → « à l'échelle de la commune » ; **« DEAL Lizmap »** → **« DEAL Réunion »** (corrigé au code *et* dans `data_sources` live). Le paragraphe gris d'accès n'est plus un paragraphe : une ligne valeur-longue.
- **pt 30 — logos reconnaissables sans survol.** Deux vrais logos ajoutés (`logosServices.tsx`), même boîte 16 px que Géoportail/PJ/Maps : **Géorisques** (triangle d'alerte **bleu sur fond blanc**) et **Google Earth** (**globe bleu océan / vert continents**). `aria-label` conservé **en plus**. Liens vérifiés sur la bonne parcelle (Google Earth → `/parcels/97411000HR0025.kmz`).

### Deux questions (sans code — déjà faites en 1ʳᵉ passe)

- **Date « 01/01/2024 » du dépôt de permis** — **FAIT.** `DepotsBlock` sert la date via `fmtDateSitadel` : une date Sitadel au 1ᵉʳ janvier (précision annuelle) s'affiche **« 2024 »**, jamais un faux jour. Vérifié au DOM : « Sur le secteur : 1 dépôt sur 36 mois · section cadastrale · dernier 2024 ».
- **FRR Saint-Denis** — **FAIT (vérifié à la source).** `territoire_fiscal` sert `frr.classement = "partie"` (commune FRR **en partie**) et tranche la position de LA parcelle par géométrie (`frr_position` sur la couche `frr`) : `position = "dans"` → la parcelle est **DANS la zone spéciale d'action rurale (les Hauts)**, donc FRR s'applique (art. 44 quindecies A CGI, en vigueur 01/07/2024). La pastille FRR est allumée à juste titre ; l'éligibilité effective reste à confirmer par un fiscaliste (dit tel quel).

### Note — correctifs d'affichage sur un run gelé

Deux libellés (« ~4878 » et « aplat commune ») sont **gravés dans la cascade du run servi** (table `dryrun_cascade_results`). Le correctif amont est en place (`cascade/layers/fiche_couches4.py`) pour les prochains runs ; pour servir le run GELÉ proprement **sans toucher au run**, le formatage (espace des milliers devant « € », « aplat commune » → « à l'échelle de la commune ») est appliqué à l'affichage des lignes Marché. L'accès voirie et le millésime PPR, eux, sont servis en direct → corrigés au back (effet immédiat).

## Écarts assumés (récapitulatif — après reprise)

- **pt 10/11 original (tier/score)** — RAS : aucun verdict déduit ne subsiste dans la fiche.
- Aucun autre écart assumé. Les 30 points sont traités (voir le tableau et la reprise ci-dessus).

## Note méthode — banc de cohérence

Le banc tourne en `--en-process` (TestClient, sans API publique). Dans cet environnement, le **décodeur de tuiles
Node** (`decode_tile.mjs`) échoue systématiquement (`ERREUR(Expecting value…)`), ce qui gonfle le CSV de 1 198
lignes « tuile » sans rapport avec le fond. Hors ces erreurs d'outil, **63 écarts réels subsistent, tous dans les
familles pré-existantes documentées** (ORACLE-FIX-1 / CHASSE-FIX-1), et **aucun ne porte sur un champ modifié par
ce mandat** : les correctifs de la fiche sont des changements d'affichage (ou additifs côté back), la cohérence des
valeurs servies est intacte.
