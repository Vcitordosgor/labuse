# MANDAT AUDIT-NU-1 — Lot D : Outils 9 à 16, les 9 Docs et l'Étude de faisabilité

**Registre.** Audit LECTURE SEULE joué le 2026-10-31. Branche `audit/nu-1-d`, worktree `~/Desktop/labuse-nu-d`, API 9080 (venv PDF-capable `~/Desktop/labuse/.venv`, `PYTHONPATH` du worktree), front 6280 (`vite`, `npm ci` réel), run servi `q_v20`, base Mac `labuse` (434 582 parcelles, == données prod). Aucune écriture base (SELECT seuls), aucun merge, aucun accès prod. Le garde-fou n'a pas été contourné.

**Périmètre.** Les 8 outils du lot — **Gabarit réglementaire (dont le 3D), Taxe d'aménagement, Prospection solaire, Blocs fonciers, Successions à venir, Courrier propriétaire, Estimer un bien, Pièges et risques** — puis les **9 documents** de la catégorie Docs (chacun généré sur 3 parcelles, comparé à l'outil relié), puis l'**Étude de faisabilité** en entier (écran, variantes, PDF, verdicts).

> Méthode : 7 sous-audits parallèles (un par groupe d'outils + un pour les Docs + un pour l'Étude), chacun jouant les parcelles témoins par l'API (froid + chaud), recalculant chaque chiffre servi depuis les tables sources (PostGIS, SRID 2975) et lisant le code qui le produit ; plus un parcours navigateur réel (Playwright) pour les règles transversales de Vic, la console et le 3D. Les recalculs clés (PPR subtype `i`, fuite Blocs) ont été re-vérifiés à la main par l'orchestrateur.
>
> Captures : `.playwright-mcp/gabarit-3d.png`, `docs-grid.png`, `etude-porte.png` sont sur le disque mais **non versionnées** (le dépôt ignore `**/captures/` et `.playwright-mcp/` — politique MENAGE-1, binaires hors git). Les valeurs ont été vérifiées depuis les payloads API et les requêtes psql.

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Scénarios joués** | **~130** : 12 parcelles témoins jouées par l'API sur les 8 outils (froid + chaud), ~40 familles de chiffres recalculées indépendamment depuis les tables sources, 9 documents générés + lus (`pdftotext`) sur 3 parcelles chacun, l'Étude de faisabilité jouée sur 8 témoins (écran + variantes + PDF), 2 communes contrastées (Saint-Denis, Cilaos) pour les outils à zone, parcours navigateur réel (console, 5 outils, 3D, Docs, overlay Étude). |
| **Bloquant** | **3** |
| **Majeur** | **19** |
| **Mineur** | **22** |
| **Dette** | **8** |

**Verdict de synthèse.** Comme au Lot A, **l'arithmétique élémentaire est très majoritairement juste** — forfaits de taxe d'aménagement 2026 au centime (892 €/m² hors-IdF, taux communaux 24/24), plafond d'emprise = CES × contenance (R.420-1) exact, dimensionnement solaire (kWc, productible) conforme à l'irradiance réunionnaise, % PPR rouge/bleu exacts au `ST_Intersection`, agrégation des Blocs exacte, bilan surfacique de l'Étude **clos à 0 m²**, et l'identité **Docs == outil prouvée pour les 9 documents** (mêmes helpers d'URL, déterminisme `pdftotext`). **Le danger est ailleurs, et il est grave :** (1) la **lecture des PPR** est fausse de trois façons différentes dans trois outils — un code de zone rouge non reconnu qui fait **dessiner 42 logements dans une zone inondation 100 % rouge** (Étude), un seuil de scoring confondu avec une règle de droit (Risques/Gabarit), une parcelle inconstructible à 58 % servie « constructible ✓ » (Gabarit) ; (2) l'outil **Estimer un bien** sert une **valeur de tête double du prix réel** (emprise au sol × €/m² habitable) et estime une **maison au prix d'un appartement** ; (3) l'outil **Blocs fonciers fuit ~250 noms de particuliers** (indivisions successorales) à l'écran et au CSV, là où son outil jumeau Successions les protège ; (4) **le même fait (surface, SDP) prend deux valeurs selon le document**. Le mal n'est pas le calcul, c'est **l'assemblage, la classification et les sources multiples** — exactement le motif du Lot A, mais ici sur des outils qui dessinent, estiment et démarchent.

---

## Les 12 parcelles témoins

| rôle | IDU | commune | surface géom | contenance |
|---|---|---|---|---|
| nue zone U | 97411000IN0347 | Saint-Denis | 942 m² | 941 |
| bâtie maison (référence, DVF 2024) | 97411000IE0241 | Saint-Denis | 630 m² | 625 |
| copropriété (16 lots) | 97411000HC0139 | Saint-Denis | 340 m² | 346 |
| zone A/N | 97424000AE0050 | Cilaos | 1 705 m² | 1 720 |
| zone AU | 97424000AM0893 | Cilaos | 471 m² | 465 |
| PPR rouge / aléa fort | 97421000AB0133 | Salazie | 2 284 m² | 2 266 |
| très petite (< 150 m²) | 97411000AO0753 | Saint-Denis | 152 m² | 149 |
| très grande (> 1 ha) | 97411000EY0173 | Saint-Denis | 10 006 m² | 10 024 |
| RNU / sans PLU calibré | 97417000BI0076 | Saint-Philippe | 5 955 m² | 5 730 |
| plusieurs bâtiments (11) | 97411000AB0785 | Saint-Denis | 1 846 m² | 1 838 |
| vente DVF récente (maison 2025) | 97411000HN0074 | Saint-Denis | 395 m² | 393 |
| disparue du cadastre (2026-09-01) | 97411000DR0042 | Saint-Denis | 90 m² | — |

(Témoin additionnel pour le bloquant Étude : `97417000AH0053`, Saint-Philippe, 1 309 m², 100 % en PPR subtype `i`.)

---

## Trouvailles

### Étude de faisabilité

#### NU-D-001 — BLOQUANT — Un code de PPR rouge non reconnu fait dessiner 42 logements sur une parcelle 100 % en zone inondation rouge (1 237 parcelles concernées)
- **Où** : moteur Étude, classification PPR par couleur ← `src/labuse/implantation/terrain.py:91-110` (`_ppr_par_couleur`).
- **Repro** : `POST /modules/etude {"idus":["97417000AH0053"]}` (Saint-Philippe, 1 309 m²). Servi : `verdict:"À compléter"`, `statut_global:"exploitable en pré-faisabilité"`, `terrain.ppr_rouge_m2:0.0`, **`capacite_maximale.logements:42`**. Recalcul PostGIS : la parcelle est à **100 %** dans un polygone `kind='ppr'` subtype=**`i`** (« PPR inondation »).
- **Affiché vs juste** : `_ppr_par_couleur` classe le rouge par sous-chaîne `"interdict"`/`"rouge"` sur `subtype`. Les PPR de Saint-Philippe portent le code court **`i`** → ne matche NI rouge NI bleu → `unary_union(rouges)=None` → la zone rouge n'est jamais retranchée de l'assiette et le contrôle « PPR zone rouge » tombe en `NON_APPLICABLE`. **Preuve d'incohérence interne** : `service.py:842` (`_sous_sol_dispo`) classe correctement `'i'` comme rouge (`lower(subtype) IN ('interdiction','i')`) — le MÊME fait est « rouge » pour le sous-sol et « absent » pour l'implantation. Périmètre confirmé par l'orchestrateur : les subtypes en base sont `PRESCRIPTION` (88), `INTERDICTION` (74), **`i` (2)**, et **1 237 parcelles de Saint-Philippe** touchent un polygone `i`.
- **Cause probable** : `terrain.py:104` — `"interdict" in s or "rouge" in s` ne reconnaît ni `i` ni `p`.
- **Amélioration** : un référentiel de classification PPR unique (codes `i`/`b`/`r` + libellés longs) partagé par `_ppr_par_couleur` et `_sous_sol_dispo` ; tant que la couleur n'est pas certaine, traiter en rouge par prudence — **jamais dessiner dans un PPR non classé**.

#### NU-D-002 — MAJEUR — « Ce qui limite : stationnement aérien » affirmé alors que le stationnement ne limite rien (0 place, facteur `limitant:false`), écran ET PDF
- **Où** : `src/labuse/implantation/service.py:127-141` (`_facteur_limitant_phrase`), rendu page 1 du PDF et en tête d'écran.
- **Repro** : `POST /modules/etude {"idus":["97424000AE0050"]}` (Cilaos). Payload : `facteur_limitant:"stationnement aérien"` mais `facteurs_limitants[0]={"limitant":false,"impact_logements":0,"mesure":"aucune place dessinée"}`, `capacite_maximale.places:0`. PDF page 1 : « Ce qui limite : stationnement aérien. »
- **Affiché vs juste** : le facteur nommé est explicitement non limitant ; le seul motif récurrent des candidats écartés est « largeur de la zone après reculs ». `service.py:134` prend `facteurs_limitants[0]["facteur"]` sans vérifier `limitant` ; quand tous les impacts valent 0, le tri stable laisse « stationnement aérien » en tête.
- **Amélioration** : ne nommer un facteur que si `f0["limitant"]` (ou `impact_logements>0`), sinon « aucun facteur isolé ne limite ».

#### NU-D-003 — MAJEUR — L'Étude renvoie 503 « relancez » au bout de 60 s sur une parcelle témoin légitime ; calcul froid 11–48 s partout
- **Où** : borne du processus enfant tuable ← `src/labuse/api/modules.py:2264-2281` (`LABUSE_ETUDE_TIMEOUT_S=60`) ; coût dans `moteur.etudier_complet` + LiDAR `terrain._pente_lidar`.
- **Repro** (`curl -w %{time_total}`, froid) : `97417000BI0076` (RNU) → **HTTP 503 à 60,08 s** ; `97417000AH0053` → 200 à 47,7 s ; `97411000EY0173` (>1 ha) → 28,4 s ; Cilaos N 22,8 s ; nue U 15,1 s ; Salazie 14,3 s ; lotissement 11,2 s. Relancer ne change rien.
- **Affiché vs juste** : toutes les études dépassent largement la borne 2 s (plancher 11 s), et une parcelle du jeu témoin tombe carrément en 503. Grille `3 formes × 5 niveaux × 15 fractions = 225` candidats (`moteur.py:207-212`) + Shapely + LiDAR réseau par assiette, **sans cache**. Caveat base-Mac : le LiDAR réseau gonfle le froid vs prod, mais 11 s de plancher restent.
- **Amélioration** : cache d'étude par (idu, run) ; élagage de la grille (sortie anticipée) ; à défaut relever la borne et dire « calcul en cours » au lieu d'un 503 sec.

#### NU-D-004 — MAJEUR — 24 logements R+5 / emprise 49 % non plafonnée servis sur une parcelle en-tête « zone N », CES et hauteur « non validées »
- **Où** : `src/labuse/implantation/controles.py:239-247, 470-487` (emprise `NON_EFFECTUE` ne bloque pas) + `moteur._rechercher` qui remplit la zone jusqu'à la grille.
- **Repro** : `POST /modules/etude {"idus":["97424000AE0050"]}` (Cilaos, zone dominante N). PDF en-tête « 802 m² · **zone N** · logement collectif », « 24 logements en R+5 », `bilan_surfacique.emprise_batie_m2:389.4` (**49 %** de 802 m²), tandis que le même PDF dit « CES — Non validée » et « Plafond d'emprise : règle non validée ».
- **Affiché vs juste** : la part constructible (U/AU 46,6 %) autorise une implantation, mais le document étiquette « zone N » et dimensionne un R+5 de 24 logements avec une emprise de 49 % qu'**aucune règle de CES ne borne**. Une capacité non contrainte présentée comme « maximum du terrain » sur une parcelle « N » trompe l'acheteur. L'arithmétique SDP tient (389,4 × 6 × coef ≈ 2 085) ; le défaut est l'**absence de garde-fou** et l'en-tête sur la zone dominante.
- **Amélioration** : quand la zone constructible est minoritaire et que CES/hauteur sont non validées, baisser le verdict et dire « capacité non bornée » ; nommer l'en-tête sur la zone constructible avec sa part.

#### NU-D-005 — MAJEUR — Le moteur n'essaie jamais R+0 : toute zone plafonnée < 6 m rend « Impossible », y compris une zone Uh de Saint-Denis qui autorise R+1
- **Où** : grille de niveaux ← `src/labuse/implantation/moteur.py:28` (`_NIVEAUX=[2,3,4,5,6]`), plafond = hauteur à l'égout `regles.py:231-235`.
- **Repro** : `POST /modules/etude {"idus":["97411000IN0347"]}` (nue, zone **Uh** Saint-Denis) → `verdict:"Impossible pour cause établie"`, message « la hauteur réglementaire (4 m) n'autorise pas un niveau habitable ». Règles Uh servies : égout **4,5 m**, faîtage **7 m**, CES 30 %.
- **Affiché vs juste** : le plus petit candidat testé = 2 niveaux × 3 m = 6 m > 4,5 m → tous rejetés ; le moteur ne tente jamais R+0/R+1. Une zone Uh à 7 m au faîtage autorise manifestement une maison/petit collectif. Déclarer « Impossible » sur une parcelle urbaine constructible est faux, et borner le nombre de niveaux par l'**égout** (4,5) au lieu du **faîtage** (7) est une erreur de doctrine.
- **Amélioration** : ajouter 1 niveau à la grille et/ou borner par le faîtage ; produire au moins un scénario R+0/R+1.

#### NU-D-006 — MINEUR — « hauteur réglementaire (4 m) » affiché pour une règle de 4,5 m (arrondi `.0f` au pair, pas de format FR)
- **Où** : `src/labuse/implantation/moteur.py:669-671` (`f"{r.valeur:.0f}"`).
- **Repro** : témoin Uh → « (4 m) » alors que la ligne de règle du même payload dit « 4,5 m ». `format(4.5,'.0f')=='4'`.
- **Amélioration** : afficher la valeur exacte avec virgule (« 4,5 m ») via le formateur FR partagé ; ne jamais ré-arrondir une hauteur réglementaire.

#### NU-D-007 — MINEUR — Contraintes EBC / emplacement réservé / servitude toujours à 0 (kinds absents), affichées « absentes du terrain » (faux négatif systématique)
- **Où** : `src/labuse/implantation/terrain.py:23,283-289` + `controles.py:460-466`.
- **Repro** : sur tous les témoins `contraintes.ebc=0`, `emplacement_reserve=0`, `servitude=0`. `spatial_layers` ne contient AUCUN `kind IN ('ebc','emplacement_reserve','servitude')` (seul `sup` existe, 417 lignes) → le contrôle lit des `kind` manquants, ignore `sup`, et affiche « absentes ».
- **Affiché vs juste** : l'étude affirme l'absence partout alors que les couches ne sont pas ingérées (impossible de conclure) et ignore 417 SUP réels. Caveat base-Mac, mais le code lit des `kind` inexistants.
- **Amélioration** : brancher le contrôle sur les couches réellement ingérées (dont `sup`) ; distinguer « non ingéré → à vérifier » de « absent → confirmé ».

#### NU-D-008 — DETTE — PPR rouge et bleu se recouvrent (Salazie) ; les deux surfaces servies brutes sans mention du recouvrement
- **Où** : `src/labuse/implantation/terrain.py:276,305-306`.
- **Repro** : `97421000AB0133` → `ppr_rouge_m2:345.9`, `ppr_bleue_m2:480.1` (recalc exact), mais rouge ∪ bleu se recouvrent partiellement → l'addition mentale sur-compte. Seul le rouge est retranché (correct) ; le bleu reste signalé.
- **Amélioration** : afficher l'union PPR à côté des deux détails, ou noter « zones pouvant se recouvrir ».

### Estimer un bien

#### NU-D-009 — BLOQUANT — La « valeur indicative » = emprise au sol × €/m² HABITABLE → le double du prix réel, en chiffre de tête
- **Où** : `_valeur_indicative(emprise, median, …)` ← `src/labuse/pige/api.py:1644-1645, 1553-1564`.
- **Repro** : `GET /radar/annonce/estimation/97411000IE0241` (maison référence). PDF/API : « Ordre de grandeur du bien · emprise au sol BD TOPO (196 m²) × 2 152 €/m² = **422 000 €** (fourchette 350 000 – 493 000) ». Dernière vente réelle, **affichée sur la même page** : **205 000 €**. Sur la nue `97411000IN0347` : 326 m² × 2 875 = **937 000 €** (jusqu'à 1 200 000 €) sur une parcelle de 942 m².
- **Affiché vs juste** : le `median` €/m² vient de DVF `valeur_fonciere / surface_reelle_bati` (surface **bâtie/habitable**), mais il est multiplié par l'**emprise au sol** (footprint BD TOPO, sans les étages). Deux surfaces hétérogènes → 422 000 € = **2,06×** le dernier prix acté, sans réconciliation. Pour l'outil dont le cœur de métier est d'estimer un prix, servir une valeur de tête double de la réalité est un défaut rédhibitoire (la mention « ordre de grandeur » ne sauve pas un chiffre deux fois faux auquel le client s'ancre).
- **Cause probable** : mélange emprise au sol × €/m² habitable (`pige/api.py:1644`).
- **Amélioration** : ne pas multiplier par l'emprise au sol ; servir le €/m² + la dernière vente comme ancre, ou estimer la SHAB (emprise × niveaux plausibles) et le dire ; si une dernière vente existe, afficher l'écart avec l'ordre de grandeur.

#### NU-D-010 — MAJEUR — Une MAISON estimée au prix d'un APPARTEMENT (type déduit du secteur, pas du bien) : −34 %
- **Où** : `comparateur_bien` ← `src/labuse/marche_service.py:341-348`.
- **Repro** : `GET /radar/annonce/estimation/97411000IE0241` → `type_bien:"appartement"`, `median:2152 €/m²`, `nature_label:"Parcelle bâtie, appartement"`. La parcelle a pourtant vendu **en Maison** (DVF 2024-09-13, 63 m², 205 000 € = **3 254 €/m²**, visible sur le même rapport). Médiane maison 500 m (recalc psql) = **3 270 €/m²** → maison **sous-évaluée de −34 %**. Même piège sur `97411000HN0074`. Le badge devient « Moyenne ±17 % » (segment appartement) alors que la dispersion maison réelle est ~28 %.
- **Affiché vs juste** : le secteur 1 000 m est dominé par l'appartement (65 % ≥ seuil 55 %) → le comparateur déduit « appartement » et ignore 44 ventes de maison à < 500 m ; la nature réelle du bien n'est pas lue. (Confirmé live, écho ESTIMATION-BANC-1.)
- **Amélioration** : quand la parcelle a une vente DVF en propre (type connu) ou un bâti pavillonnaire isolé, forcer le `type_bien` à ce type ; à défaut afficher les deux repères (maison / appartement).

#### NU-D-011 — MAJEUR — Le comparateur « ancien » inclut le NEUF (VEFA) — filtre `nature_mutation ILIKE 'vente%'`
- **Où** : `comparateur_bien._fetch` ← `src/labuse/marche_service.py:328`.
- **Repro** : la base contient **1 407** mutations `nature_mutation='Vente en l'état futur d'achèvement'` (VEFA = neuf) ; `ILIKE 'vente%'` les capte toutes, alors que le PDF libelle « biens anciens 2021–2025 ». Non pollué sur IE0241 (0 VEFA à 500 m) mais faux positif latent partout où il y a du programme neuf (le neuf tire la médiane « ancien » vers le haut).
- **Amélioration** : restreindre à `nature_mutation='Vente'` (exclure VEFA / terrain à bâtir / échange / expropriation), comme le profil `neuf_vefa` isole déjà le neuf.

#### NU-D-012 — MAJEUR — Parcelle non mesurée affirmée « bâtie, maison » et estimée comme un bien bâti
- **Où** : `_nature_parcelle` ← `src/labuse/pige/api.py:1480-1484` ; usage `estimation_annonce:1636-1660`.
- **Repro** : `GET /radar/annonce/estimation/97411000IN0347` (témoin nue) → `nature:"inconnue"` MAIS `nature_label:"Parcelle bâtie, maison"`, ordre de grandeur 937 000 €. `parcel_residuel.taux_emprise_pct` est **NULL** → `_nature_parcelle` retourne `"non_mesure"` → tombe dans la branche BÂTIE.
- **Affiché vs juste** : quand la part bâtie n'est pas mesurée (NULL), le code suppose « bâtie » et fabrique un prix de bâti alors qu'on ne sait pas si la parcelle est bâtie — doctrine Vic « jamais un verdict déduit là où il faut une mesure » inversée.
- **Amélioration** : sur `non_mesure`, ne pas affirmer « bâtie » ni fabriquer un ordre de grandeur bâti ; afficher « nature non mesurée » et se limiter au repère foncier.

#### NU-D-013 — MINEUR — PDF : « comparé aux ventes de appartements » (élision manquante)
- **Où** : `src/labuse/exports/blocs/annonce.py:232` — le helper `_de()` (« d'appartements ») existe (l.72-74) et sert la branche copro (l.228) mais pas la branche bâti (l.232 code « de » en dur). Faute de français sur un document à 349 €/mois.
- **Amélioration** : remplacer « de <b>{pl}</b> » par `_de(pl)`.

#### NU-D-014 — MINEUR — PDF estimation lent : 17–28 s (vs 17–67 ms pour le JSON)
- **Où** : `GET /analyse-annonce/{idu}.pdf` → WeasyPrint ← `src/labuse/api/documents.py:248`. IN0347 27,5 s, IE0241 21,1 s, HC0139 17,8 s.
- **Amélioration** : réutiliser le cache tuiles / l'offload process comme l'Étude (ETUDE-ASYNC-1), ou servir un squelette (trois points verts) pendant le rendu.

#### NU-D-015 — MINEUR — Badge copro « Moyenne ±17 % » sur-vend la précision (étage/surface du lot inconnus)
- **Où** : `_fiabilite_mot` ← `src/labuse/pige/api.py:1626,1633`. Le badge reflète le segment appartement, pas l'incertitude propre à la copro (lot exact non identifié).
- **Amélioration** : abaisser le badge copro à « Limitée » ou ajouter un cran d'incertitude « lot exact inconnu ».

#### NU-D-016 — DETTE — €/m² bâti = valeur_fonciere entière / surface d'UNE ligne (surestimation si mutation multi-biens)
- **Où** : `src/labuse/marche_service.py:323` (`valeur_fonciere / NULLIF(surface_reelle_bati,0)`), sans `GROUP BY id_mutation` (contrairement au comparateur terrain, l.404-414).
- **Amélioration** : agréger le bâti par `id_mutation` (somme surfaces, prix total) pour un €/m² homogène.

### Blocs fonciers · Successions à venir · Prospection solaire

#### NU-D-017 — BLOQUANT — Blocs fonciers sert ~250 indivisions de particuliers avec leur nom de famille (fuite RGPD), à l'écran et au CSV
- **Où** : `GET /modules/blocs` + `/blocs/{id}`, front `Blocs.tsx:109` (`{it.denomination ?? '—'}`) ← builder `src/labuse/blocs.py:77` (`WHERE p.siren IS NOT NULL AND p.siren <> ''`), `:130-135`.
- **Repro** : `GET /modules/blocs?commune=Saint-Denis` → `denomination="SUCCESSION BANA AHMED"`, `siren="U23718700"`, `is_public=false` (servi) ; `/blocs/33782` ouvre les 10 parcelles sous ce nom. Recalcul île (vérifié par l'orchestrateur) : **11 222 blocs**, dont **1 197 (10,7 %) à pseudo-SIREN « U… »** (code DGFiP d'indivision, forme `AUPM`) et **~250 dont la dénomination nomme une personne physique** (SUCCESSION / INDIVISION / CONSORTS) — ex. « SUCCESSION NOEL FRANCOIS » (21 parcelles), « SUCCESSION JEAN-BAPTISTE JEAN ROSY ».
- **Affiché vs juste** : l'avertissement de l'outil et la règle privacy partagée (`modules.py:860-864`) disent « uniquement des personnes morales ; un particulier n'est JAMAIS nommé ». Ici le nom complet d'un défunt et de son hoirie est servi à l'écran ET exporté en CSV. `blocs.py:77` groupe sur tout `siren` non vide sans exclure les pseudo-SIREN « U » ; le filtre de forme qui protège **Successions** (`VEILLE_SUCCESSION_FORMES`, exclut AUPM — 0 fuite constatée) n'existe pas dans Blocs. Exposition juridique directe pour l'exploitant.
- **Cause probable** : `blocs.py:77` ; `classify_dgfip(...).indivision` existe (`proprietaire_type.py:28`) mais n'est utilisé que pour `public`, pas pour écarter.
- **Amélioration** : écarter du build les SIREN non numériques (`^[0-9]{9}$`) ou `classify_dgfip(...).indivision`, comme Successions écarte AUPM ; à défaut ne jamais servir la `denomination` d'une indivision (« Indivision (non nommée) »).

#### NU-D-018 — MAJEUR — Successions : 8,7 s à froid / 3,4 s à chaud (Saint-Denis), 4,6 s pour 22 lignes (Cilaos)
- **Où** : `GET /modules/successions` ← `src/labuse/api/modules.py:1125-1142` (sous-requête corrélée `dirigeant_nom` par ligne + batch BODACC).
- **Repro** : `curl -w` → **8,72 s froid, 3,35 s chaud** (Saint-Denis) ; Cilaos **4,56 s** pour 22 résultats. Blocs 0,16 s, solaire 0,95–2,7 s. Le coût n'est pas le volume mais la sous-requête corrélée exécutée par ligne.
- **Amélioration** : LATERAL joint une fois, ou précalculer `dirigeant_nom` au build (comme `dirigeant_age`) ; indexer `pm_dirigeants(siren, type_personne, date_naissance)`.

#### NU-D-019 — MINEUR — Prospection solaire ne filtre pas les propriétaires publics : 40 % du top-500 Saint-Denis = Commune/État/Département
- **Où** : `GET /modules/prospection-solaire` ← `src/labuse/api/modules.py:917-919` (pas de clause `is_public`).
- **Repro** : 1ʳᵉ ligne « COMMUNE DE SAINT DENIS » ; recalcul sur les 500 servis SD : **198 (≈ 40 %) de dénomination publique**. Blocs écarte les publics par défaut (démarchage de privés) ; Solaire, qui sert le même démarchage par CSV, ne le fait pas.
- **Amélioration** : même écartement public par défaut + option `inclure_publics`, via `classify_dgfip` ; afficher le nombre d'écartés au bandeau.

#### NU-D-020 — MINEUR — Successions : âges de dirigeants aberrants (jusqu'à 114 ans) servis comme « succession probable »
- **Où** : `parcel_veille_succession.dirigeant_age` ← `src/labuse/score_v.py:129` (garde `0 ≤ age ≤ 130`).
- **Repro** : `max(dirigeant_age)=114` ; **102 lignes ≥ 100 ans**. Ex. « SCI MAKBOULE · 114 ans ». Un dirigeant vivant de 114 ans est une erreur de date de naissance RNE, pas un signal.
- **Amélioration** : plafonner à ~95-100 ans et flagger « date RNE douteuse » au-delà.

#### NU-D-021 — MINEUR — Successions : âge et nom du dirigeant viennent de deux sources → « 77 ans · — » (nom manquant)
- **Où** : `modules.py:1130` (`dirigeant_age` figé au build) vs `modules.py:1133-1137` (`dirigeant_nom` lu LIVE de `pm_dirigeants`).
- **Repro** : **140 / 969 lignes SD (14 %)** ont un âge mais aucun nom ; le nom servi peut aussi ne pas être la personne dont l'âge porte le signal (aîné par `date_naissance` vs `age_max`).
- **Amélioration** : figer `dirigeant_nom` au build à côté de `dirigeant_age`, issu du même dirigeant.

#### NU-D-022 — MINEUR — Prospection solaire : présence de piscine lue de deux sources (8 299 vs 12 289)
- **Où** : liste `modules.py:925,939` (`parcel_equipements.piscine`) vs fiche solaire `modules.py:1015-1017` (source `piscines` statut 'servie').
- **Repro** : `count FILTER(e.piscine)` = **8 299** ; `count(DISTINCT idu) piscines servie` = **12 289**. Même fait, deux sources → une parcelle peut porter piscine dans la fiche mais pas dans le filtre de la liste.
- **Amélioration** : brancher le filtre piscine de la liste sur la même source `piscines` que la fiche.

#### NU-D-023 — DETTE — Prospection solaire : date de gel « 11/07/2026 » en dur dans les docstrings, donnée réelle 23/08/2026
- **Où** : `modules.py:883-884, 1001-1002` vs `parcel_solar.source_millesime='… relevé 2026-08-23'`. Le bandeau sert la date LIVE correcte (pas de donnée périmée servie comme fraîche) ; seuls les commentaires mentent.
- **Amélioration** : retirer la date en dur ; la source de vérité est `source_millesime`.

### Gabarit réglementaire (+ 3D + PDF)

#### NU-D-024 — MAJEUR — Le recul séparatif « h/2 minimum 4 m » est aplati au seul plancher → zone d'implantation sur-estimée de +15,4 % sur la maison de référence
- **Où** : `src/labuse/gabarit/builder.py:257` (`recul_sep = getattr(zr,"recul_limites_sep_m")`) ignore `ZoneRules.recul_limites_formule` (`faisabilite/zonage.py:50`).
- **Repro** : `GET /outils/gabarit/97411000IE0241` (zone Um Saint-Denis). Règle Um : recul séparatif `max(4 m, h/2)`. Faîtage 10 m → h/2 = 5 m → recul exigé = **5 m**. Le gabarit applique **4 m** (écran « Limites séparatives 4,0 m » + PDF). Recompute à 5 m : zone d'implantation 309,7 m² → **262,0 m² (−47,7 m² = −15,4 %)**. La capacité affichée est trop généreuse ; touche toute zone Um où h/2 > 4.
- **Cause probable** : le builder ne lit jamais `recul_limites_formule`, ni ne la liste en « règle non intégrée » → disparition silencieuse (même défaut que la fiche, CHASSE-DONNEES-FIX-1 D-50).
- **Amélioration** : `recul_sep = max(min_m, h/2)` quand la formule porte un terme h/2 ; à défaut servir la formule en règle non intégrée.

#### NU-D-025 — MAJEUR — Parcelle à cheval : l'écran affiche la portion constructible sous le nom de la zone DOMINANTE (non constructible)
- **Où** : `Gabarit.tsx:334-337` (`${surfaceParcelleM2} m² en ${raccZone?.code}`) ; `raccZone.code` = zone dominante ← `api/gabarit.py:205`.
- **Repro** : `GET /outils/gabarit/97424000AE0050` (Cilaos). PostGIS : 53,4 % zone **N** (dominante, non constructible) + 46,6 % **Ub** ; le gabarit est calculé sur le morceau **Ub**. L'écran rend « Surface parcelle 1 720 m² · dont **795 m² en N (47 %)** ». Or le morceau servi est Ub (795,3 m²), pas N ; `multizone.servie_sur="Ub (46.6 %)"` et le `surfaceNote` disent correctement « Ub » → **l'écran contredit le back**.
- **Amélioration** : l'étiquette « à cheval » doit citer `multizone.servie_sur` (zone constructible calculée), et nommer la part dominante inconstructible.

#### NU-D-026 — MAJEUR — Le PDF Gabarit perd entièrement la mise en garde « parcelle à cheval » (contenance, zone, part inconstructible)
- **Où** : `src/labuse/exports/blocs/gabarit.py:104-121` — ni `surfaceNote`, ni la contenance, ni la part en zone non constructible.
- **Repro** : PDF `97424000AE0050` (`pdftotext`) : « Zone d'implantation 346 m² · Plafond 398 m² · Hauteur 11 m » — enveloppe constructible nette. L'écran, lui, dit la parcelle est à 53 % N + 58 % PPR rouge. **Le document imprimé — celui qui circule — masque que l'essentiel est inconstructible.**
- **Amélioration** : imprimer « Surface parcelle X m² — dont Y m² en zone Z (part à cheval) » et la part non constructible dès que `raccordement.zone.a_cheval`.

#### NU-D-027 — MAJEUR — Parcelle 58 % en PPR zone rouge (cascade HARD_EXCLUDE « inconstructible ») servie comme un gabarit constructible, famille « risques » cochée vérifiée
- **Où** : `src/labuse/gabarit/builder.py:379-411` + `Gabarit.tsx:251` (`risques: res.coverage.risques && !pprNonIntegre`) + PDF « Vérifié : … risques ».
- **Repro** : `GET /outils/gabarit/97424000AE0050`. Cascade `risques = HARD_EXCLUDE — Exclue : PPR zone rouge (inconstructible) — 58 %`. Le gabarit renvoie status ok, zone 346 m², plafond 398 m², hauteur 11 m, écran « Risques intégrés ✓ » / PDF « Vérifié : risques ». La fiche §risques et le score_v2 (« Écartée », « zone N ») disent l'inverse.
- **Affiché vs juste** : la part rouge dans le morceau Ub n'est que 103 m² (géométrie cohérente pour le morceau), mais la **présentation globale** « constructible ✓ » est trompeuse pour une parcelle que la cascade déclare inconstructible à 58 %. Rien ne hiérarchise un HARD_EXCLUDE dominant au-dessus du résultat chiffré.
- **Amélioration** : quand `risques` est HARD_EXCLUDE (> ~50 % rouge) ou zone dominante A/N, bandeau de tête « parcelle majoritairement inconstructible — gabarit servi sur la seule part constructible », écran ET PDF.

#### NU-D-028 — MAJEUR — Parcelle disparue du cadastre : l'outil interactif sert un gabarit complet sans avertissement ; le PDF renvoie HTTP 500
- **Où** : `api/gabarit.py:75-162` (aucun appel à `cadastre_disparue.info_disparue`) ; PDF 500 à `cadastre_disparue.py:47-51` (table `parcel_cadastre_remplacement` absente → exception non gardée).
- **Repro** : `GET /outils/gabarit/97411000DR0042` → status ok, gabarit complet 3D. `GET /gabarit/97411000DR0042.pdf` → **HTTP 500** (confirmé dans le log API : seul 500 de toute la session, 2 occurrences, `UndefinedTable parcel_cadastre_remplacement`). `cadastre_disparue_le=2026-09-01`.
- **Affiché vs juste** : la parcelle est sortie du cadastre ; l'outil présente une enveloppe comme si elle existait, et le PDF — censé refuser proprement (422) — plante en 500 brut. ⚠ caveat : la table existe probablement en prod (en prod le PDF ferait 422), mais l'absence de garde interactif (a) reste réelle partout. Même racine que Lot A NU-A-003.
- **Amélioration** : garde `info_disparue` dans `/outils/gabarit/{idu}` (bandeau « parcelle disparue ») + `to_regclass`/`try` autour de `parcel_cadastre_remplacement` pour un 422 propre.

#### NU-D-029 — MINEUR — PDF : deux lignes « zone d'implantation » (435 « terrain libéré » + 192 « bâti déduit ») là où l'écran n'en montre qu'une (192)
- **Où** : `exports/blocs/gabarit.py:113-115` vs `Gabarit.tsx:340`. PDF `97411000IN0347` : « terrain libéré 435 m² » + « bâti déduit 192 m² » (435 = 192 + 243) ; écran : « Zone d'implantation 192 m² ». Un client pressé lira 435 sur le PDF, 192 à l'écran.
- **Amélioration** : aligner l'ordre et le chiffre mis en avant entre écran et PDF.

#### NU-D-030 — MINEUR — « Zone d'implantation » déduit le bâti existant → sous-estime le potentiel d'une parcelle démolissable, titre ambigu
- **Où** : `gabarit/builder.py:648-706` (`deduire_bati_de_zone`), appliqué service ET PDF. IN0347 192 m² (bâti déduit 243) ; le chiffre-accent est l'emprise restante AUTOUR du bâti, pas l'assiette d'une opération neuve (435 m²).
- **Amélioration** : nommer « Reste à bâtir autour de l'existant » vs « terrain libéré » comme vraie enveloppe neuve.

#### NU-D-031 — MINEUR — PDF Gabarit lent (2–9 s) et dépendant d'un appel réseau externe (IGN data.geopf.fr) pour la vue 3D
- **Où** : `exports/blocs/gabarit.py:138-146` → `plan_svg.gabarit_svg_3d` (MNT HD via `data.geopf.fr/wms-r`). PDF froid AE0050 **9,0 s**, IN0347 4,4 s ; chaud 2,37 s. 16 requêtes WMS par rendu.
- **Amélioration** : cache du relief par emprise, timeout borné sur l'appel IGN.

#### NU-D-032 — DETTE — Copropriété refusée avec motif urbain inadapté (« ravine, littoral ou domaine public non routier »)
- **Où** : `gabarit/limites.py:49` ; `builder.py:583-585`. `GET /outils/gabarit/97411000HC0139` → refus HONNÊTE (arête non classée en centre-ville) mais le motif « ravine/littoral » déroute sur une copro urbaine.
- **Amélioration** : affiner le motif (« limite non rattachée à une voie ni à un voisin cadastré — à qualifier ») hors contexte ravine/littoral.

### Pièges et risques

#### NU-D-033 — MAJEUR — L'aléa ne montre que le niveau le plus fort : « fort ~3 % » masque ~100 % d'exposition
- **Où** : `GET /servitudes-invisibles/{idu}` → `aleas_parcelle` ← `src/labuse/api/servitudes.py:297-315` (`best[typ]`, un seul niveau par type).
- **Repro** : Salazie `97421000AB0133` sert « mvt de terrain **fort ~3 %** » ; recalcul `ST_Intersection`/`ST_Area` : fort 2,7 % + **moyen 33,4 % + faible 63,8 % = ~100 %**. Cilaos `97424000AE0050` : « fort ~14 % » cache moyen 86 % → 100 %. St-Philippe `97417000BI0076` : « fort ~38 % » cache moyen 62 % → 100 %.
- **Affiché vs juste** : l'acheteur lit « 3 % » et conclut « 97 % sûr », alors que la parcelle entière est en aléa. Pour l'outil dont la promesse est le danger, c'est l'information inverse de la vérité terrain (l'étude géotechnique G2 se déclenche sur du moyen, pas que du fort). Arbitrage M73 « un niveau par aléa » appliqué tel quel à un outil d'information foncière.
- **Amélioration** : lister chaque niveau avec son % (« fort 3 % · moyen 33 % · faible 64 % → ~100 % exposé »), ou au minimum le % « au moins moyen ».

#### NU-D-034 — MAJEUR — Zone rouge PPR de 2 à 50 % → « pas d'exclusion automatique » (contraire à C. env. L562-1)
- **Où** : `src/labuse/api/servitudes.py:278-291` (3 paliers, seuil `config/cascade_rules.yaml:164-165` `ppr_red_exclude_pct:50`).
- **Repro** : `97411000EY0173` sert « zone rouge sur **24 %** : vigilance forte, constructibilité à vérifier (**pas d'exclusion automatique**) ». Une zone rouge PPR est une **interdiction de construire** sur la part rouge, quel que soit le % (L562-1 II 1°). À 58 % (`97424000AE0050`) le libellé bascule enfin sur « inconstructible » → la rédhibition dépend du %, pas du régime juridique. Le seuil 50 % est une convention de **scoring LABUSE** sans valeur juridique pour le verdict servi.
- **Amélioration** : pour la zone rouge, dire systématiquement « partie en zone rouge = inconstructible (L562-1), quelle que soit la surface » ; réserver le % à l'ampleur, « vigilance » au bleu.

#### NU-D-035 — MINEUR — Le drapeau `redhibitoire` n'atteint jamais l'écran : une interdiction s'affiche comme une simple note
- **Où** : `servitudes.py:371-373` jette `redhibitoire`/`part_pct` à l'aplatissement ; l'écran (`blocB.tsx:95-104`) n'affiche que `effet`, tout en carte grise identique. Sur `97424000AE0050`, « zone rouge (inconstructible) 58 % » a le même style qu'un « Droit de préemption ». La fiche, elle, sert `redhibitoire:true`.
- **Amélioration** : propager `redhibitoire`/gravité jusqu'à l'écran, marquer la ligne bloquante (puce rouge / tri en tête).

#### NU-D-036 — MINEUR — Le même PPR est servi deux fois (SUP enveloppe pm1 + zonage live), gonflant le compteur « n servitudes »
- **Où** : `servitudes.py:84/357` (assiette SUP pm1) + `:289-296` (zones PPR live). Salazie : le même plan apparaît comme SUP et comme zonage rouge/bleu → le PPR compte pour 3. Règle Vic « un fait = une section » enfreinte ; dédup `:346` aveugle entre `sup` et zonage.
- **Amélioration** : quand les zones PPR live sont servies, masquer l'assiette SUP pm1 redondante.

#### NU-D-037 — MINEUR — Parcelle disparue du cadastre servie comme vivante, sans alerte (faux « tout va bien »)
- **Où** : `servitudes.py:400` vérifie l'existence (`SELECT 1 FROM parcels`) mais ignore `cadastre_disparue_le`. `97411000DR0042` (disparue 2026-09-01) → HTTP 200, DPU servi normalement, aucune mention. Dans un outil « pièges », le piège « cette référence n'existe plus » n'est pas dit.
- **Amélioration** : si `cadastre_disparue_le` non nul, servir une ligne de tête « Parcelle disparue du cadastre le JJ/MM/AAAA ».

#### NU-D-038 — MINEUR — Zone AU conditionnée à une opération d'ensemble non signalée comme piège
- **Où** : `servitudes.py:381` — la branche AU dormante exclut `conditionnelle_operation`. Cilaos `97424000AM0893` (AUb, constructible seulement dans une opération d'ensemble) ne porte aucune mention → un acheteur d'une AUb isolée ne peut pas construire une maison seule.
- **Amélioration** : ajouter `conditionnelle_operation` (« Zone AU ouverte sous condition d'opération d'ensemble — pas de construction isolée »).

#### NU-D-039 — DETTE — Requêtes 2–4 s sur parcelles en PPR (scan `spatial_layers` non subdivisé, mémo per-session)
- **Où** : `servitudes.py:336-344` interroge `spatial_layers` (et non `tuyau_subdivise`) pour SUP/PPR-assiette. Salazie 2,34–2,60 s à chaud, une parcelle de 90 m² jusqu'à 4,31 s — précisément les parcelles PPR, les plus consultées dans un outil de risque.
- **Amélioration** : router le scan SUP/PPR-assiette sur `tuyau_subdivise` (comme `aleas_parcelle`), ou mémoïser côté serveur partagé.

### Les 9 documents (catégorie Docs)

> **Identité Docs == outil : JUSTE pour les 9.** Preuve structurelle : écrans d'outil et porte Docs appellent les mêmes helpers d'URL (`docDossierUrl`, `docGabaritUrl`, `docComparatifUrl`, `docEtudeZoneUrl`, `docAnalyseAnnonceUrl`, `ETUDE_PDF_URL`…), aucun chemin parallèle. Déterminisme vérifié (même route 2× → `pdftotext` identique). Formats FR corrects, aucun code brut / None / champ vide / troncature. Refus Gabarit copro 422 légitime. Le mécanisme Docs lui-même est sain ; le danger est l'**incohérence inter-documents** non détectée par le harnais.

#### NU-D-040 — MAJEUR — La « surface » d'une même parcelle diffère selon le document (contenance 625 vs géométrie 630)
- **Où** : Dossier/Comparatif/Apporteur/Étude-faisabilité (contenance) CONTRE Estimer un bien (géométrie) ← `exports/robinet_fiche.py:68` vs `exports/blocs/annonce.py:128,174`.
- **Repro** : maison IE0241 : Dossier/Comparatif/Apporteur/Étude « 625 m² » vs Estimer « 630 m² » ; copro HC0139 : Comparatif « 346 » vs Estimer « 340 » (écart 6 m²). La fiche API sert les deux (`surface_m2`=630, `surface_terrain_m2`=625). Deux documents vendus sur la même parcelle annoncent deux « surfaces ».
- **Amélioration** : un champ « surface » canonique (contenance) pour les 9 docs ET la fiche, sinon étiqueter « contenance (cadastre) » vs « emprise du dessin » — jamais les mélanger sous « SURFACE ».

#### NU-D-041 — MAJEUR — Le Dossier étiquette toujours la contenance « surface (plan) » (garde-fou mort)
- **Où** : page de garde ← `exports/miroir.py:1177-1178`. Le ternaire `"contenance" if surface_source=="cadastre" else "surface (plan)"` écrit toujours « surface (plan) » car `surface_source` n'est **jamais collecté** (absent des CSV `config/circuit/*` → hors `miroir.ids_declares()` → `None` → branche else). La valeur imprimée (625) EST la contenance cadastrale ; l'étiquette « (plan) » est fausse. Le garde-fou CHASSE-DONNEES-FIX-1 est mort.
- **Amélioration** : déclarer `surface_source` dans le registre fiche (ou le lire depuis `fiche`) pour que l'en-tête dise « contenance ».

#### NU-D-042 — MAJEUR — SDP résiduelle du même bien contradictoire entre documents (0 m² vs 92 m²)
- **Où** : Dossier §10 + Estimer (0 m²) CONTRE Comparatif (92 m²) ← blocs `potentiel`/`annonce` vs `comparatif.py`.
- **Repro** : maison IE0241 — Dossier « 0 m² SDP RESTANTE », « capacité nulle », « densité consommée 151 % » ; Estimer « SDP restante 0 m² » ; Comparatif « SDP résiduelle, bâti conservé **92 m²** » + « rien à construire 92 m² ». Même fait, même jour, même run, deux valeurs. (Écho direct de Lot A NU-A-001 : deux instantanés désynchronisés du même calcul.)
- **Amélioration** : un point de donnée unique de SDP résiduelle pour tous les documents ; tant que ce n'est pas le cas, Comparatif et Dossier ne peuvent pas être montrés au même client.

#### NU-D-043 — MAJEUR — Le harnais `docs_coherence.py` (« 0 écart ») ne couvre pas « Estimer un bien » (8 docs sur 9)
- **Où** : `scripts/docs_coherence.py:81-104`. La fonction `documents()` génère 8 docs ; « Estimer un bien » est absent. Le seul document qui utilise la géométrie (NU-D-040) et porte des libellés de nature faux (NU-D-010) **échappe au contrôle**. De plus `_surface` (l.149-156) code en dur « surface = contenance » → le harnais consacre la contenance comme vérité alors que la fiche et Estimer servent la géométrie.
- **Amélioration** : ajouter `/analyse-annonce/{idu}.pdf` au set `documents()` ; trancher contenance vs géométrie comme surface canonique.

#### NU-D-044 — MINEUR — Catalogue : commentaire « l'export Excel n'existe pas » FAUX — l'Excel est servi
- **Où** : `frontend/src/components/documents/catalogue.ts:46-48` vs `api/documents_bibliotheque.py:48,148` + `api/bilan.py:414`. `_EXCEL_DISPONIBLE={"bilan"}` (non vide), la bibliothèque marque `excel:true`, la route `/bilan/{idu}.xlsx` existe (openpyxl, formules vivantes). L'Excel est atteignable depuis « Mes documents » mais pas depuis la carte Docs, et le commentaire désinforme.
- **Amélioration** : corriger le commentaire ; décider si le bouton Excel doit aussi apparaître sur la carte Bilan.

#### NU-D-045 — MINEUR — « Apporteur » : le catalogue promet « une page », le PDF en fait 4
- **Où** : `catalogue.ts:56` (« en une page ») vs PDF 4 pages (brief + questionnaire `forms=True`). Contenu propre (surface 625, dernière vente 205 000 €), mais la desc sur-promet.
- **Amélioration** : reformuler la desc (« brief apporteur à remplir » + pages réelles).

#### NU-D-046 — MINEUR — « Étude de zone » : section Équipements = annuaire SIRENE brut non borné (~600 lignes, 24 pages)
- **Où** : `/etude-zone.pdf` ← `blocs/etude_zone.py`. IE0241 rayon 2 km → 24 pages, dont ~18 énumèrent nominativement ~600 établissements. Requête sans borne côté PDF ; agrégats cohérents par ailleurs (prix médian 2 225 €/m² == Dossier/Comparatif).
- **Amélioration** : plafonner (top 5 par catégorie + « +N autres ») ; garder les compteurs agrégés.

#### NU-D-047 — DETTE — Performances de génération : plusieurs docs très au-delà de 2 s
- **Où** : `/dossier` 13–26 s, `/etude-zone` **43 s**, `/analyse-annonce` 33–40 s, Comparatif 8,8 s, Étude-faisabilité POST 7,6 s. Jamais de cache (`no-store` voulu). Caveat base-Mac (I/O froids, VITESSE-3) mais l'ordre de grandeur reste problématique pour Étude de zone / Estimer.
- **Amélioration** : mesurer en prod (`?trace=1`) ; cache de rendu court-vivant par (idu, run, params) invalidé au déploiement ; fermer NU-D-046.

### Taxe d'aménagement

> **L'arithmétique fiscale est JUSTE** (valeurs 2026 officielles, formule correcte, recalculs concordants au centime). Les défauts sont de présentation/libellé. Pas de PDF autonome (la taxe n'apparaît en PDF qu'au Bilan — hors lot).

#### NU-D-048 — MINEUR — Taux en pourcentage affichés avec un point décimal (« 2.5 % » au lieu de « 2,5 % »)
- **Où** : `frontend/src/components/outils/TaxeAmenagement.tsx:296,388,408,433` — interpolation directe de la valeur JS, les % court-circuitent tout formateur FR (les montants € passent bien par `fmtEur`).
- **Amélioration** : router ces taux par un formateur décimal français.

#### NU-D-049 — MINEUR — Libellé d'abattement collectif juxtapose deux nombres irréconciliables
- **Où** : `src/labuse/taxe_amenagement.py:278` — « dont 250 m² à −50 % : 100 m² × 3 logements » colle la surface abattue réelle (250) et la décomposition du plafond (300). Calcul juste, texte trompeur pour qui vérifie poste par poste.
- **Amélioration** : « dont 250 m² à −50 % (plafond 100 m² × 3 logements = 300 m²) ».

#### NU-D-050 — MINEUR — Cents du total et de la RAP silencieusement arrondis à l'écran (l'API les porte) dans un outil « vérifiable poste par poste »
- **Où** : `TaxeAmenagement.tsx:418,436` ← `fmtEur`→`Math.round` (`lib/format.ts:12`). API `total_eur=3 481,83 €`, écran « 3 482 € ». L'assiette et les parts affichées ne resomment pas exactement au total.
- **Amélioration** : afficher les cents, ou arrondir assiette et parts du même geste.

#### NU-D-051 — DETTE — Motif d'exonération absent/inconnu fait disparaître la surface exonérée sans un mot
- **Où** : `taxe_amenagement.py:289-294` — `surface_exoneree_m2>0` sans motif reconnu : aucune ligne, aucun avertissement (défaut sûr = 0 € d'assiette). Non atteignable via l'UI (set fermé de cases), risque API/intégration.
- **Amélioration** : émettre « surface exonérée ignorée : motif manquant ou non reconnu ».

#### NU-D-052 — DETTE — Plafonds légaux des parts non contrôlés (communale 5/20 %, départementale 2,5 %)
- **Où** : `taxe_amenagement.py:327-328` — un taux saisi aberrant (ex. 40 %) produit un total 8× trop élevé sans alerte ; les plafonds sont en config mais jamais confrontés à la saisie.
- **Amélioration** : signaler (pas forcément bloquer) « taux au-dessus du plafond légal de X % », au calcul et à la saisie.

### Courrier propriétaire

> **Aucun bug trouvé.** La composition est déterministe, sans placeholder `{…}` résiduel ni particulier nommé (PP → « À l'occupant », PM → raison sociale = donnée publique) ; la surface servie = contenance de l'acte ; référence IDU avec zéros de tête ; parcelle disparue → refus propre ; émetteur = `comptes.marque` (défaut LABUSE) ; pied STOP (C. env.) + droits RGPD ; encodage latin-1 propre (œ→oe, jamais « ? »). Point unique partagé `/composer` et `/pdf`.

---

## Ce qui est JUSTE (recalculs indépendants concordants)

- **Taxe d'aménagement 2026** : forfait 892 €/m² hors-IdF (DOM correctement traité), piscine 251, PV 10, éolienne 3 000, stationnement 2 928/5 857 ; abattement 50 % par logement ; taux communaux 24/24 (Saint-Denis 3 %, Cilaos 5 %, secteurs majorés par parcelle) ; part dép. 2,5 % ; RAP 0,40 % ; exonération < 5 m² ; aucune division par zéro (surface vide → total `null`, jamais 0 € trompeur). Cohérence outil ↔ fiche §7 parfaite.
- **Gabarit** : plafond d'emprise = CES × contenance (R.420-1) exact (IN0347 282,3 ; IE0241 312,5 ; HN0074 196,5) ; géométrie zone d'implantation == géojson recalculé ; valeurs PLU fidèles au règlement sourcé ; **volume 3D cohérent avec le chiffre 2D** (extrude le faîtage, bâti à sa hauteur LiDAR, aucun nombre 3D contredisant la fiche/PDF) ; refus honnêtes sans invention de gabarit sur RNU / A-N / zone non calibrée ; classification des limites vérifiée (enclave IN0347 à 100 % de périmètre voisin).
- **Pièges et risques** : % PPR rouge/bleu exacts au `ST_Intersection` (EY0173 24/76, AE0050 58, AB0133 15/21) ; ≥ 50 % rouge bascule correctement en « inconstructible » ; % du niveau d'aléa servi exact ; cohérence fiche ↔ outil (même `aleas_parcelle`, pas de mismatch de compteur) ; 8 familles SUP décodées ; filtre ANC correct ; bloc « NON COUVERT » honnête.
- **Étude de faisabilité** : PPR correctement classé là où subtype = INTERDICTION/PRESCRIPTION (160/162 polygones) ; **PDF == écran, verrou `nombres_hors_payload`=[]** ; **bilan surfacique CLOS** (lotissement > 1 ha écart −0,0 m², collectif sans chevauchement) ; min-lot ALUR correct ; accès hypothétique (RECETTE-4 Lot 9) fonctionnel et `verdict_global` sain (un « À confirmer » bloquant empêche « Exploitable ») ; plafond L151-35/36 conforme (RPA ≠ 1/3 codé en dur, 44 stations TCSP réelles, capacité réduite seulement si le stationnement plafonne) ; contiguïté graphe ; filtre de Pareto et variantes corrects (absences expliquées).
- **Prospection solaire** : dimensionnement exact (3 053 m² × 0,2 = 610,6 kWc × 1 559 = 951 925 kWh ✓, somme mensuelle = annuel), productible 950–1 598 kWh/kWc conforme à l'irradiance réunionnaise, convention hémisphère sud (plein nord) correcte.
- **Blocs fonciers** : agrégation surface/SDP exacte (Σ membres), contiguïté `ST_DWithin` (buffer 0,5 m en 2975) saine, écartement public honnête.
- **Successions** : compte exact (969 SD, 22 Cilaos), plancher d'âge 70 respecté, **0 pseudo-SIREN « U » servi** (filtre de forme efficace, contrairement à Blocs), vocabulaire prudent (« succession PROBABLE », jamais « est en succession »).
- **Estimer un bien** : écran == API == PDF chiffre pour chiffre (3 PDF vérifiés) ; copro sans ordre de grandeur (C4-003) ; badge décidé une fois au back.
- **Docs** : identité Docs == outil prouvée pour les 9 ; formats FR, aucun code brut / champ vide ; prix médian bâti et terrain nu cohérents Dossier/Comparatif/Étude-zone.
- **Transversal navigateur** : **console à 0 erreur / 0 avertissement sur tout le parcours** ; un seul 500 de toute la session (le PDF Gabarit de la disparue, cf NU-D-028) ; « Changer de parcelle » présent ; chaque outil repart vide au changement (« changer d'outil vide tout ») ; pas de défilement horizontal ; chargement = trois points menthe ; DA de la charte respectée (en-têtes, pilules, 3D).

---

## Hors lot (croisé, non instruit)

- `parcel_residuel.taux_emprise_pct` dépasse 100 % (313, 136, 177 % sur HC0139/IE0241/HN0074) — table résiduel, à instruire par le lot fiche/potentiel.
- La **nature fausse d'Estimer** (NU-D-010) et la **SDP 0 vs 92** (NU-D-042) prennent leur racine dans l'estimateur / le calcul résiduel (lots ANNONCE/BANC et fiche) ; elles sont instruites ici dans leur manifestation Lot D (outil Estimer, documents Docs).
- Témoin Cilaos `97424000AE0050` : le prefill Taxe sert zone PLU « N » là où le contexte le note « A/N » — à instruire par le lot zone PLU / fiche.
- Entrée LIEN d'annonce (`/radar/annonce/analyser`) : `pige_annonces` = 428 lignes sur base Mac (tables pige minces) ; non exercée par fetch externe (règle anti-fetch).
- Caveat base-Mac : les couches EBC / ER (Étude) et la table `parcel_cadastre_remplacement` (Gabarit/Risques disparue) sont peut-être présentes en prod ; à reconfirmer. Les bugs de **logique** (subtype `i`, recul séparatif, valeur indicative, fuite Blocs, estimation nature) sont indépendants de la base.

---

## Les 5 trouvailles les plus graves

1. **NU-D-001 (BLOQUANT) — L'Étude dessine 42 logements dans une zone inondation 100 % rouge.** Un code de PPR rouge (`i`) non reconnu par le classificateur fait disparaître l'interdiction ; 1 237 parcelles de Saint-Philippe sont concernées, et le code se contredit lui-même (le sous-sol classe `i` en rouge, l'implantation non). Un promoteur à qui on dessine un collectif sur une parcelle inconstructible prend une décision d'achat sur un faux.
2. **NU-D-009 (BLOQUANT) — « Estimer un bien » sert une valeur de tête double du prix réel.** Emprise au sol × €/m² habitable = 422 000 € affichés à côté de la dernière vente 205 000 € (×2,06), sans réconciliation ; 937 000 € sur une parcelle quasi nue. Le cœur de métier de l'outil (estimer un prix) est faux d'un facteur deux.
3. **NU-D-017 (BLOQUANT) — Blocs fonciers fuit ~250 noms de particuliers (indivisions successorales), à l'écran et au CSV.** L'outil promet « uniquement des personnes morales » ; son jumeau Successions protège ces noms, Blocs ne le fait pas. Exposition RGPD directe pour l'exploitant.
4. **NU-D-027 (MAJEUR) — Le Gabarit sert « constructible ✓ » une parcelle inconstructible à 58 % (PPR rouge HARD_EXCLUDE),** écran et PDF, en contradiction avec la fiche §risques et le score. Et le PDF (NU-D-026) efface la mise en garde « à cheval » : le document qui circule présente une enveloppe nette.
5. **NU-D-033 / NU-D-034 (MAJEUR) — Dans l'outil où l'acheteur vient CHERCHER le danger, l'aléa « fort ~3 % » masque 100 % d'exposition et une zone rouge PPR < 50 % est annoncée « pas d'exclusion automatique »** (contraire à L562-1). La réassurance est l'inverse de la vérité terrain.

## Ce que je changerais en premier (si j'étais le développeur)

**Un référentiel de classification PPR unique, partagé, prudent.** Les trois trouvailles de tête du cluster « risque » (NU-D-001 Étude, NU-D-027 Gabarit, NU-D-034 Risques) viennent toutes de la même racine : **chaque outil lit et interprète les zones PPR à sa façon**, avec des codes non normalisés, des seuils de scoring pris pour du droit, et aucun garde-fou « rouge = inconstructible, quoi qu'il arrive ». Je créerais un module `ppr.py` qui (a) normalise les codes (`i`/`b`/`r` + libellés longs) en un seul endroit, (b) traite tout code non reconnu **en rouge par prudence** (jamais dessiner/vendre une parcelle non classée), (c) pose la règle métier « la part en zone rouge est inconstructible au titre de L562-1, indépendamment du % », et (d) est consommé à l'identique par l'Étude, le Gabarit, Pièges et risques et la fiche. Cela ferme d'un coup la trouvaille la plus dangereuse et deux majeures, et supprime la divergence d'un outil à l'autre.

Ensuite, dans l'ordre : **(2)** réparer l'estimation d'« Estimer un bien » — ne plus multiplier l'emprise au sol par un €/m² habitable, et choisir le type de bien à partir de la nature réelle de la parcelle (sa vente DVF) plutôt que de la dominance du secteur ; **(3)** poser le filtre de forme d'indivision de Successions dans Blocs fonciers (une ligne) pour fermer la fuite RGPD ; **(4)** servir la **surface et la SDP résiduelle par un point de donnée unique** à tous les documents et rebrancher le harnais `docs_coherence` sur les 9 docs, pour qu'une divergence inter-documents casse la CI au lieu de circuler chez le client.

---

*Audit joué le 2026-10-31 — branche `audit/nu-1-d`, commit sur la branche, pas de merge, pas de push. API et navigateur arrêtés, ports 9080/6280 libérés avant de rendre la main.*
