# RECETTE-4 — reprise de la recette Vic des 29 et 30/10

Branche `fix/recette-4` · worktree `~/Desktop/labuse-recette4` · API 9030 / front 6230 ·
base locale `labuse` (run servi `q_v20`). Pas de merge, aucun accès prod. Preuve = constat
navigateur (Playwright) ; captures sous `docs/audit-2026-10/recette-4/captures/` (hors git
par doctrine MENAGE-1 — livrées via l'app). Un commit par lot.

Légende : **AVANT** = constat Vic reproduit ici · **APRÈS** = après correctif, re-constaté.

---

## Lot 1 — T1 (état d'outil vidé au changement d'outil) + nettoyages Solaire / Assemblage

### T1 — « Changer d'outil vide tout l'état de l'outil quitté »

**Racine.** Le store vide bien l'état partagé (`setModule` remet `selectedIdu`,
`contexteCommune`, `moduleMap`… à null). Mais l'**état local React** des composants-outils
(sous-vue, commune choisie, onglet, champ saisi) ne tombe que si React **remonte** le
composant. Or `<Body />` dans `ModulePanel` n'était **pas keyé**. Quand deux clés d'outil
résolvent la **même fonction composant** — `communes`↔`barometre` → `Communes`,
`permis`↔`promesses` → `M03` — React **réutilise l'instance** à travers le changement
d'outil : la sous-vue (« Acquisitions récentes ») et sa commune survivaient.

**AVANT (reproduit).** Outil Communes → porte « Acquisitions récentes » → commune
Saint-Denis → bascule vers un autre outil → retour sur Communes : la sous-vue
« Acquisitions récentes » et « Saint-Denis » étaient **toujours là** (`select` encore monté).
→ `captures/t1-communes-AVANT.png`.

**Correctif (racine, mécanisme commun).** `frontend/src/components/outils/ModulePanel.tsx` :
`<Body key={def.key} />` aux deux points de rendu (branche normale + branche
`analyser-annonce`). React remonte **à neuf à chaque changement de clé d'outil** — garantie
uniforme pour TOUS les outils, pas seulement les paires aliasées.

**APRÈS (re-constaté).**
- Communes : `barometre` (acquisitions, Saint-Denis) → `communes` ⇒ retour à l'accueil
  (4 portes), plus de `select`. → `captures/t1-communes-APRES.png`.
- Scan patrimoine : porte « Un propriétaire » + saisie `TESTSTATE123` → PLU → retour
  `patrimoine` ⇒ accueil (2 portes), champ vidé.
- Les 5 outils cités (Communes, Scan patrimoine, Analyser une annonce, Prospection solaire,
  Successions) remontent désormais à neuf à tout changement d'outil.

### Prospection solaire — deux paragraphes retirés

**Mandat.** Supprimer les deux paragraphes sous le graphe mensuel (« Productible estimé… » et
« En clair… »).

**Correctif.** `ProspectionSolaire.tsx` — les deux `<p>` retirés ; le graphe mensuel et le
bloc annuel (qui porte déjà la maille) restent.

**APRÈS.** Parcelle `97410000AS1425` : graphe « Profil mensuel » présent, aucun des deux
paragraphes (`Productible estimé à la…` / `En clair : le potentiel…`). →
`captures/solaire-APRES.png`.

### Assemblage — encart d'en-tête retiré, noms de PM en entier

**Mandat.** Retirer l'encart d'explication en tête ; afficher les noms des personnes morales
en entier, sur plusieurs lignes si besoin.

**Correctif.** `moteurs.tsx` (M16) — `<Banner>` d'intro retiré ; `truncate` → `break-words`
sur la liste « PM : … » et sur la dénomination par parcelle.

**APRÈS.** Assiette contiguë `97422000BW1992 + BW2857 + BW2858` (bloc SA HLM) : en-tête =
directement « Étape 1 » (plus d'encart) ; « PM : SOCIETE ANONYME D'HABITATIONS A LOYER
MODERE DE LA REUNION » affiché **en entier sur 2 lignes**, non tronqué. →
`captures/assemblage-APRES.png`, `captures/assemblage-pm-nom-APRES.png`.

_tsc -b : 0 erreur._

---

## Lot 2 — Étude de zone (menu Activité) · Permis (« Tous ») · Courrier (référence)

### Étude de zone — menu « Activité (destination) » retiré (outil + Docs + PDF)

**Mandat.** Supprimer le menu « Activité (destination) » de l'outil, de Docs et du PDF.

**Correctif.**
- Outil `EtudeZone.tsx` : `DestinationSelect` retiré, `sous_destination` n'est plus envoyé, le
  bloc verdict `DestinationsBloc` et la condition `res.destinations` supprimés (+ imports morts).
- Docs `DocumentsView.tsx` : le `DestinationSelect` de la fenêtre Étude de zone retiré ; l'URL
  PDF n'emporte plus `sous_destination`.
- PDF `exports/blocs/etude_zone.py` : le bloc « Activité étudiée » (verdict par zone) supprimé.

**APRÈS.** Outil Étude de zone : plus de libellé « Activité (destination) », plus de
`[data-destination-select]`. PDF `/etude-zone.pdf?idu=97410000AS1425&rayon_km=1` (HTTP 200,
132 Ko) : `pdftotext` ⇒ 0 occurrence de « Activité étudiée » / « Destinations ». →
`captures/etudezone-APRES.png`.

### Permis — « Tous » réellement appliqué à l'arrivée

**AVANT (racine).** Le segment par défaut est « Tous » (`seg='tous'`), mais la fenêtre `months`
était initialisée à **24** (init state + effet de montage) — la fenêtre « Récent » — alors que
`choisirSeg` applique **240** pour « Tous ». D'où le constat Vic : chip « Tous » affiché actif,
données « Récent » appliquées.

**Correctif.** `ModulePanel.tsx` (M03) : `months` initial `240` (hors `promesses`) et l'effet de
montage aligné sur `choisirSeg` (`'tous' → 240`).

**APRÈS.** À l'arrivée : chip « Tous » actif (`aria-pressed`) ET « **50 808** dans la sélection »
(toute la base), plus 5 640 (Récent). Compteur et sélection cohérents. →
`captures/permis-tous-APRES.png`.

### Courrier — référence non séquentielle

**Mandat.** Plus de « Demande n° 2 ». Une référence lettres + date, non séquentielle (ex. C-2610-KD).

**Correctif.** `courrier.py` : `_reference(id, ts)` = `C-DDMM-XX` (DDMM = date de la demande ;
XX = 2 lettres dérivées de l'id par md5→base26, non devinables, sans révéler le volume ni le
rang). Champ `reference` ajouté à la réponse `creer_demande` (branche neuve + dédup). Front
(`api.ts`, `ModulePanel.tsx`) : la confirmation affiche `demande.reference` (repli rang/id).

**APRÈS.** `POST /courrier/demande` ⇒ `"reference":"C-3010-IW"` (id 51, rang 21 — jamais montrés).
Parcours complet navigateur ⇒ « ✓ Demande **C-3010-VB** transmise. » →
`captures/courrier-ref-APRES.png`.

_tsc -b : 0 erreur._

---

## Lot 3 — Copilote (cartes exemples) + Notifications (intro retirée)

### Copilote — grille d'exemples à 2 colonnes, cartes larges, rien de tronqué

**Mandat.** Grille à 2 colonnes de cartes larges, icône à gauche, texte 13 px sur 2–3 lignes,
rien de tronqué.

**Correctif.** `AccueilCopilote.tsx` : `grid-cols-5` → `grid-cols-2` ; texte `text-[12px]
leading-tight` → `text-[13px] leading-snug` ; padding/gap élargis ; pas de `line-clamp`.

**APRÈS.** Mesuré navigateur : `gridTemplateColumns` = **2 colonnes**, cartes **296 px** de
large, police **13 px**, `anyTruncated = false` sur les 10 cartes. →
`captures/copilote-cards-APRES.png`.

### Notifications — paragraphe d'intro retiré

**Mandat.** Supprimer « Ce qui bouge sur vos parcelles suivies … réellement détecter. ».

**Correctif.** `Header.tsx` : le `<p>` d'intro retiré (ternaire `prefsOpen ? … : <p>` → `prefsOpen
&& …`) ; la requête `entete-cloche` (qui l'alimentait) et son import retirés.

**APRÈS.** Panneau Notifications ouvert : en-tête « NOTIFICATIONS · 1045 », puis directement la
liste — plus aucune occurrence de « Ce qui bouge sur » / « réellement détecter ». →
`captures/notif-sans-blurb-APRES.png`.

_tsc -b : 0 erreur._

---

## Lot 4 — Gabarit 3D (vérification du volume vert) + Taxe d'aménagement (vérification barème 2026)

### Gabarit réglementaire — volume vert vérifié

**Vérification (mandat).** La hauteur du volume vert doit être la hauteur autorisée, mesurée
depuis le terrain naturel, le sommet suivant la pente le cas échéant ; afficher la hauteur retenue.

**Constat.**
- Hauteur du volume = **hauteur réglementaire PLU** : l'extrusion (`Gabarit.tsx` `fill-extrusion-height
  = res.hauteurReglementaireM`) prend exactement la hauteur sourcée (ex. `97415000CX1395` → 12 m,
  base « faitage », status `integrated`). ✓
- **Depuis le terrain naturel** : un vrai MNT (`raster-dem terrarium`) est chargé et
  `setTerrain({source:'dem'})` actif ⇒ l'extrusion part du sol du MNT (`base:0` posé sur le relief),
  pas d'un plan à 0 m. ✓ Le volume vert rend bien depuis le sol (capture 3D).
- **Sommet / pente** : un `fill-extrusion` a un **sommet plat** (limite MapLibre) — le toit ne suit
  PAS la pente. C'est une simplification, désormais **dite explicitement** (voir ci-dessous). Un toit
  drapé sur la pente demanderait un maillage WebGL par sommet — hors proportion de cette recette.
- **Hauteur retenue affichée** : oui.

**Correctifs (honnêteté + explicite, bas risque).**
- `Gabarit.tsx` : la tuile « Hauteur réglementaire » affiche désormais « **hauteur retenue (faitage)
  — depuis le terrain naturel** » (la hauteur retenue, sa base faitage/égout, et son origine).
- `api/gabarit.py` : `terrainNote` reformulée — « la hauteur réglementaire est **mesurée depuis le
  terrain naturel**, mais le **sommet est représenté à plat** (il ne suit pas la pente du terrain) ».

**APRÈS.** `/outils/gabarit/97415000CX1395` ⇒ H 12 m, base faitage, status integrated, nouvelle
`terrainNote`. Écran : panneau « Hauteur réglementaire · 12 m · hauteur retenue (faitage) — depuis
le terrain naturel » ; en 3D (« Relief seul »), volume vert posé sur le relief + note de sommet à
plat. → `captures/gabarit-3d-APRES.png`.

**Verdict : le volume n'est pas faux** (hauteur = hauteur autorisée, depuis le terrain naturel,
hauteur retenue affichée) ; la seule réserve (sommet à plat sur pente) est maintenant dite
clairement. Le drapage du toit sur la pente reste un chantier séparé (hors recette).

### Taxe d'aménagement — barème 2026 vérifié à l'euro près

**Vérification (mandat).** Chaque calcul confronté à la formule officielle 2026 (valeur forfaitaire
hors Île-de-France, abattement 50 % sur les 100 premiers m² en résidence principale, piscines,
stationnement, taux communal et départemental 974), un test par combinaison de filtres.

**Constat : aucun écart.** `config/taxe_amenagement.yaml` est sur le bon millésime 2026 (sources
service-public A15416 / construires.fr) :
valeur forfaitaire hors IdF **892 €/m²**, piscine **251 €/m²**, stationnement **2 928 €/place**
(→ 5 857 € sur délibération), PV au sol 10 €/m², éolienne 3 000 €, abattement **50 % / 100 m² PAR
LOGEMENT**, part départementale 974 **2,5 %** (confirmée DELTA), part communale votée (jamais
inventée), exonération < 5 m². Le front (`TaxeAmenagement.tsx`) ne calcule rien : il affiche les
lignes servies par le back ⇒ aucune divergence front↔back.

**Correctif.** Aucun code à corriger. Ajout d'un **verrou de recette** `tests/test_recette4_taxe.py`
(10 tests) : config officielle + **un test par combinaison de filtres** confronté à la formule
calculée à la main — non-RP, RP 1 logement, RP collectif 3 logements, logement aidé, piscine,
stationnement, surface < 5 m² exonérée, combo (RP + piscine + stationnement), sans taux communal.

**APRÈS.** `pytest tests/test_recette4_taxe.py` ⇒ **10 passed**. Exemples vérifiés à l'euro :
200 m² non-RP com 3 % ⇒ assiette 178 400, total 9 812, RAP 713,60 · combo 150 m² RP + piscine 30 +
2 places com 4 % ⇒ assiette 102 586, total 6 668,09.

_tsc -b : 0 erreur · pytest taxe : 10 passed._

---

## Lot 5 — Radar : compteur de jours (date absente ≠ 1970)

**AVANT (reproduit).** Un bien dont la date de publication est ABSENTE mais stockée comme sentinelle
`1970-01-01` (époque) affichait « **en vente depuis 20 756 j** ». Reproduit sur le bien 1 passé à
`date_publication='1970-01-01'` : l'ancien `COALESCE(date_publication, date_premiere_saisie)` donne
**20 756**.

**Racine.** Deux compteurs calculaient une durée depuis l'époque :
1. Back `pige/marche.py` (`bien_vs_marche`, panneau « Ce bien » + sa médiane) — `COALESCE` prenait la
   date 1970 au lieu de retomber sur la 1re saisie.
2. Front `RadarEcran.tsx` `joursDepuis` — ne gardait que `null`/`NaN`, pas l'époque
   (`new Date('1970-01-01')` est une date valide → 20 756 j).

**Correctif (racine + autres compteurs).**
- Back `marche.py` : `COALESCE(CASE WHEN date_publication > 2005-01-01 THEN date_publication END,
  date_premiere_saisie)` — toute date avant 2005 (= sentinelle) est ignorée ⇒ retombe sur la 1re
  saisie, sinon NULL ⇒ aucune durée. JAMAIS depuis zéro. Appliqué au bien ET à la médiane.
- Front `RadarEcran.tsx` : `joursDepuis` rejette les dates < 2005 et illisibles (→ null) ; essai des
  deux dates (publication puis saisie) INDÉPENDAMMENT.
- Intake `pige/intake.py` : `_clamp_date_publication` nulle aussi les dates avant 2005 (défense à
  l'ingestion, en plus du futur déjà géré).

**APRÈS (re-constaté).** Même bien à `1970-01-01` : expression gardée = **62** (jours depuis la 1re
saisie 2026-08-29) ; API `/radar/biens/1/vs-marche` ⇒ `anciennete_j = 62` (plus 20 756). Bien
restauré à sa date d'origine. Verrou front `RadarEcran.joursDepuis.test.ts` : 4 tests verts
(1970 → null, < 2005 → null, illisible → null, date récente → nombre).

_tsc -b : 0 erreur · vitest joursDepuis : 4 passed._

---

## Lot 6 — « Estimer un bien » : renommage + écran + pont Radar

### Renommage « Analyser une annonce » → « Estimer un bien » (partout)

**Mandat.** Renommer partout (menu Outils, Docs, titres PDF, textes). Identifiants internes
inchangés ; verrous mis à jour avec traçabilité.

**Correctif (libellés seulement — clés/kind/endpoints inchangés).**
- Menu : `registry.ts` (`label`). Écran : `AnalyserAnnonce.tsx` (titre de l'en-tête).
- Docs : `catalogue.ts` (`nom`), `DocumentsView.tsx` (onglet bibliothèque).
- PDF : `exports/builder.py` (titre), `exports/blocs/annonce.py` (bandeau + encart).
- Bibliothèque : `api/documents_bibliotheque.py`. Verrous registre : `registre/robinets.py`
  (libellé `_r("outil", "Estimer un bien", …)`, clé `outil_analyser_annonce` inchangée).
- Verrou test MAJ : `tests/test_annonce_pdf.py` (doc_title attend « Estimer un bien »).

**APRÈS.** Menu Outils : carte « Estimer un bien » (plus « Analyser une annonce » nulle part dans
le DOM). PDF : `doc_title` contient « Estimer un bien » (28 tests backend annonce/pige verts).

### Écran « Estimer un bien » (variante adresse)

**Mandat.** Comparables sans défilement horizontal ; « Le foncier » supprimée, « Ouvrir la fiche
parcelle → » remonté sous les tuiles ; tuile « Classement LABUSE » → « Dernière vente » (date +
prix DVF, sinon « aucune depuis 2014 »), écran ET PDF.

**Correctif.** `AnalyserAnnonce.tsx` : tableau `table-fixed text-[10px] tabular-nums`, colonnes
resserrées, prix/€m² `whitespace-nowrap` (plus d'`overflow-x-auto`). Section « Le foncier »
retirée ; « Ouvrir la fiche parcelle → » placé sous la grille de tuiles. Tuile « Dernière vente »
lue de `fiche.dvf_parcelle.derniere_mutation`. PDF : `pige/api.py` ajoute `derniere_vente` au
rapport ; `exports/blocs/annonce.py` remplace la tuile « Classement » par « Dernière vente ».

**APRÈS.** Parcelle `97403000AH0307` : tuile « Dernière vente · 12/2025 · 60 000 € » ; plus de
tuile « Classement LABUSE » ni de section « Le foncier » ; « Ouvrir la fiche parcelle → » sous les
tuiles ; tableau comparables `scrollWidth == clientWidth` (261 px, **0 défilement horizontal**). →
`captures/estimer-ecran-APRES.png`, `captures/estimer-comparables-APRES.png`.

### Radar — panneau « Ce bien » = mêmes chiffres qu'Estimer + bouton « Estimer ce bien → »

**Mandat.** « Ce bien » lit le même point de données qu'Estimer (mêmes chiffres) + bouton
« Estimer ce bien → » qui ouvre l'outil sur ce lien.

**Correctif.**
- Back `pige/marche.py` (`bien_vs_marche`) : la médiane ACTÉE provient désormais de
  `marche_commune_bloc` (la MÊME que le rapport lien d'« Estimer un bien »), au lieu de
  `_dvf_bati_type` qui divergeait. Repli sur l'ancien calcul si le bloc manque le type.
- Front : `store/useApp` ajoute `annonceLienPrefill` (consommé-puis-reset au montage) ;
  `AnalyserAnnonce` lit le prefill et lance l'analyse du lien ; `RadarMarcheColonne` ajoute le
  bouton « Estimer ce bien → » (pose le prefill + `setModule('analyser-annonce')`).

**AVANT.** « Ce bien » affichait « vs acté **+41 %** » alors qu'Estimer affichait « **+36 %** · 3 797
€/m² · 104 ventes » pour le même bien (deux médianes DVF différentes).

**APRÈS.** Bien leboncoin `3226754959` (Saint-Leu, 832 000 €, 5 168 €/m²) : « Ce bien » affiche
« vs acté **+36,1 %** » (médiane 3 797, n 104) = chiffres d'Estimer. Bouton « Estimer ce bien → »
ouvre l'outil qui ré-analyse le lien et montre **832 000 € · 5 168 €/m²** (identiques) + « +36 %
face aux maisons de la commune : 3 797 €/m² ». → `captures/radar-cebien-estimer-APRES.png`.

_tsc -b : 0 erreur · vitest docs/outils/radar : 17 passed · pytest annonce/pige/marche/radar :
237 passed, 7 skipped (DVF)._

---

## Lot 7 — En-tête : sélecteur commune retiré → bouton « Fiche commune ▾ »

**AVANT (constat Vic).** Le sélecteur « Toute l'île ▾ » de l'en-tête appelait `setCommune` en
choisissant une commune → pose le périmètre actif `commune` (→ `getParcelsGeojson` charge TOUT le
parcellaire de la commune) + pré-coche le filtre + cadre la carte : « ça mouline puis bloque ».

**Correctif.** `Header.tsx` : le sélecteur « Toute l'île ▾ » (et le bouton doublon « ⓘ Fiche
commune ») sont remplacés par un **seul bouton « ⓘ Fiche commune ▾ »**. Il ouvre la liste des 24
communes ; choisir une commune appelle `setContexteCommune` (ouvre le volet FICHE de la commune) —
**jamais `setCommune`** : aucun filtrage, aucun rechargement de carte. Le filtre par commune reste
dans le panneau Filtres.

**APRÈS.** En-tête : bouton « ⓘ Fiche commune », plus aucun « Toute l'île » dans le DOM. Le menu
liste **24 communes** ; choisir « Saint-Paul » ouvre le volet « FICHE COMMUNE · Saint-Paul » tandis
que la carte reste sur l'île entière et `filters.communes` reste `[]` (aucun filtrage). →
`captures/entete-fiche-commune-APRES.png`.

**Vérification du filtre commune du panneau Filtres (mandat : noter sans corriger).** Sélection de
« Saint-Denis » (CP 97400) dans le panneau Filtres : l'app **reste fluide** — sonde de réactivité du
fil principal sur 5 s = **écart d'image max 19 ms** (aucun gel). Raison : le panneau pose seulement
le FILTRE (`filters.communes`, param `cs`), pas le périmètre `commune` (param `c`) qui déclenche le
`getParcelsGeojson` responsable du gel de l'en-tête. **Pas de blocage à noter.**

**Note verrou (Lot 1 / Prospection solaire).** Le retrait des deux paragraphes solaire a rendu
obsolète l'assertion « A1 » (inclinaison 15° dans « En clair… ») : le test est mis à jour pour
verrouiller le RETRAIT (`ProspectionSolaire.test.tsx`).

_tsc -b : 0 erreur · vitest header + solaire : 14 passed._

---

## Lot 8 — Projets « Nouveau projet » : chemins reformulés, « programme » retiré

**Mandat.** Les deux chemins deviennent « Partir d'une sélection filtrée » et « Partir de zéro ».
Le premier ne parle plus d'analyse LABUSE ni de probabilité de mutation : ce sont les mêmes filtres
que le panneau Filtre de la carte, appliqués à la base, rien d'autre. La section « programme »
(Logement libre, social…) est supprimée.

**Correctif.** `ParcoursProjet.tsx` :
- Portes renommées : « Partir du vivier LABUSE » → « **Partir d'une sélection filtrée** » (desc =
  « Les mêmes filtres que le panneau Filtre de la carte, appliqués à la base — rien d'autre. ») ;
  « Projet de zéro » → « **Partir de zéro** ».
- Textes du wizard reformulés : plus de « classé par probabilité de mutation », « exclusions
  automatiques du moteur », « les mieux d'abord » ni lien « pourquoi ? » (scoring). Récap :
  « N parcelles correspondant à vos filtres ».
- Section « programme » SUPPRIMÉE : les chips de type de logement (`data-projet-type`), l'état
  `type`/`types`, `getProjetTypes`/`TypeLogement`, `type_logement` (identité), et les lignes
  récap/trail associées retirés. L'étape CONTEXTE ne garde que le budget indicatif.

**APRÈS.** Écran 0 : « Partir d'une sélection filtrée » / « Partir de zéro », desc du premier =
filtres de la carte, rien d'autre (aucune mention LABUSE/mutation). Étape CONTEXTE : plus de
`data-projet-type` (programme absent), seul le budget indicatif subsiste. →
`captures/projet-chemins-APRES.png`, `captures/projet-contexte-sans-programme-APRES.png`.

_tsc -b : 0 erreur._

---

## Lot 9 — Étude de faisabilité : « aucune voie classée » ne bloque plus (accès à confirmer)

**AVANT (constat Vic).** Quand la classification ne trouve **aucune limite classée « voie »** sur
l'assiette, le moteur renvoyait « simulation impossible : aucune limite classée voie » → verdict
**Impossible**, aucun scénario : l'étude s'arrêtait alors que la parcelle a un accès.

**Racine.** `implantation/terrain.py` : sans voie classée, `voie_edges` est vide → le contrôle
géométrique « accès sur voie » échoue pour tout candidat → aucun faisable → `_message_impossible`
(moteur.py) renvoie « aucune limite classée voie » → `verdict_global` = Impossible.

**Correctif (continue sous « accès à confirmer »).**
- `terrain.py` : quand `not has_voie`, on **promeut l'arête la plus longue** (frontage le plus
  probable) en ACCÈS HYPOTHÉTIQUE (`voie_hypothese=True`) → l'implantation se trace. `has_voie`
  reste False (l'accès n'est pas établi). `note_limites` dit « accès supposé… à confirmer ».
- `controles.py` : nouveau contrôle **« Accès (voie) »** = « À confirmer » quand `voie_hypothese`
  (ajouté à `_A_CONFIRMER_BLOQUANTS` → interdit « Exploitable », n'interdit pas l'étude).
- `moteur.py` : `_message_impossible` ne parle plus d'« aucune voie » (une arête existe toujours) ;
  il ne signale l'impossibilité que si AUCUNE arête n'est exploitable.
- `rendu.py` / `service.py` : `voie_hypothese` exposé au payload (écran + PDF).

**APRÈS (re-constaté, parcelle sans voie `97422000AD1237`).**
- API `/modules/etude` : `verdict` = **À compléter** (plus Impossible) · **1 scénario** (l'étude
  continue) · contrôle « **Accès (voie) : À confirmer** » · `note_limites` « aucune limite classée
  « voie » : accès supposé sur l'arête la plus longue — à confirmer ».
- Écran : « Verdict de l'étude : **À compléter** » + « **Accès (voie)** · aucune limite classée
  « voie » · accès supposé sur l'arête la plus longue · **À confirmer** ». →
  `captures/etude-acces-confirmer-APRES.png`.
- PDF `/modules/etude/pdf` (HTTP 200) : contient « accès supposé… à confirmer » (`pdftotext`).

_IDUs sans voie trouvés (golden) : 97410000CD0905, 97411000KA0296, 97422000AD1237,
97418000AT2379, 97408000AP1647, 97415000CX1395 — tous continuent désormais._

---

## Bilan — 18 points, 9 lots (tous commités, AUCUN mergé)

| # | Point | Lot | État |
|---|---|---|---|
| 1 | T1 — état d'outil vidé au changement (5 outils) | 1 | ✅ `key={def.key}` sur Body |
| 2 | Copilote cartes 2 colonnes, rien tronqué | 3 | ✅ 2 cols 13px, 0 tronqué |
| 3 | Notifications — intro « Ce qui bouge… » retirée | 3 | ✅ |
| 4 | Étude faisabilité — accès à confirmer (plus Impossible) | 9 | ✅ verdict À compléter |
| 5 | Radar — date absente ≠ 1970 (« 20 756 j ») + autres compteurs | 5 | ✅ 20756→62 |
| 6 | Radar « Ce bien » = mêmes chiffres + « Estimer ce bien → » | 6 | ✅ +36 % aligné |
| 7 | Projets « Nouveau projet » reformulé, « programme » retiré | 8 | ✅ |
| 8 | Étude de zone — menu « Activité » retiré (outil+Docs+PDF) | 2 | ✅ |
| 9 | Prospection solaire — 2 paragraphes retirés | 1 | ✅ |
| 10 | Assemblage — encart retiré, noms PM en entier | 1 | ✅ |
| 11 | Permis — « Tous » appliqué à l'arrivée | 2 | ✅ 50 808 |
| 12 | Renommer « Analyser une annonce » → « Estimer un bien » | 6 | ✅ partout |
| 13 | Estimer un bien — écran (comparables, foncier, Dernière vente) | 6 | ✅ |
| 14 | Gabarit 3D — volume vert vérifié | 4 | ✅ pas de bug, dit explicite |
| 15 | Courrier — référence non séquentielle | 2 | ✅ C-DDMM-XX |
| 16 | Taxe d'aménagement — barème 2026 vérifié | 4 | ✅ 0 écart, 10 tests |
| 17 | En-tête — sélecteur commune retiré → « Fiche commune ▾ » | 7 | ✅ (filtre Filtres : fluide) |

**Qualité.** `tsc -b` 0 · **vitest 305/305** · pytest ciblés verts : taxe 10, étude-accès 3,
annonce/pige/marche/radar 237, implantation (distance/ppr/contenance/gabarit/study) 179.
Pre-commit hook (garde gros fichiers) vert sur les 9 commits.

**Reste à Vic.** Merge (geste de Vic) puis déploiement groupé. Recharger l'extension n'est pas requis
(aucune modif extension).
