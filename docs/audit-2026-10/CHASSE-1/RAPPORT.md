# CHASSE-1 — chasse aux erreurs (audit lecture seule)

Branche `audit/chasse-1` · base `origin/main` = `3e3a2afa` (merge ORACLE-FIX-1) · worktree
`~/Desktop/labuse-chasse` · API 8705 éphémère (arrêtée en fin d'audit) · 2026-10-04 · Fable.

**Verdict en une ligne : 24 FAUX · 2 DISCORDANT · 12 TROMPEUR · 5 SALE · 2 à instruire
(45 lignes d'ECARTS.csv) — dont 5 bloquants : C01, C02, C06, C22, C23. Pas de jackpot,
mais le moteur de calcul, la bascule, les filtres, l'horloge et le Copilote sortent
blanchis ; les fautes sont dans les COMPTEURS DVF annexes, les LIBELLÉS et la lecture de
l'ABSENCE.**

## Méthode

Les audits précédents regardaient les mêmes témoins, famille par famille, avec les mêmes
recalculs. CHASSE-1 attaque par les angles qui leur échappent par construction : échantillon
tiré au sort (graine fixée), invariants sur toute l'île (SQL, 431 663 parcelles), lecteurs
mis face à face, absences lues comme des zéros, libellés remontés jusqu'à la requête,
bascule structurelle sur base de test. Quatre verdicts : **FAUX** (le chiffre affiché n'est
pas soutenu par la source), **DISCORDANT** (deux lecteurs, deux valeurs), **TROMPEUR**
(chiffre juste, libellé qui ment), **SALE** (donnée invalide en base, sans effet visible
prouvé). Chaque trouvaille d'`ECARTS.csv` porte sa commande ou requête de reproduction.

Acquis cités, pas rejoués : CALCULS-1 (1 185 recalculs, 0 écart), COHERENCE-FIX-2 (banc V6b
159 familles), ORACLE-1/ORACLE-FIX-1 (488 comparaisons externes), SOURCES-AUDIT-3 (617
données), PLU-VERIF-1 (2 031 règles), TEXTES-1 (références juridiques), CLOISONNEMENT-1.
Exploration : 7 sous-agents (4 inventaire lecteurs, 3 angles 3/4/5) ; **tout verdict FAUX ou
DISCORDANT du rapport a été contre-vérifié d'une seconde main** (requête ou lecture code
rejouée par l'agent principal — échantillon de contre-vérification 6/6 concluant, 2 faux
positifs d'agent écartés en route).

## Étape 0 — point de départ (vert)

- Arbre propre, base = `origin/main` du jour (`3e3a2afa`), `.env` copié, node_modules symlinkés.
- Banc V6b `--echantillon` : **3 210 comparaisons, 44 écarts** = exactement la baseline
  ORACLE-FIX-1 (familles pré-existantes : cache_fiche_commune_fraicheur 24, surface 6
  TOLERABLE, cinquante_pas 5, copro 3, prix_neuf 4, taxe_amenagement_taux 2).
- Les 5 oracles ORACLE-1 : **140 lignes · 70 vrai · 0 faux · 70 non vérifiable** (oracles à
  API externes injoignables depuis la session ; tout le vérifiable est vrai, 0 régression).

## Échantillon (`ECHANTILLON.csv`, graine 0.42)

**627 parcelles uniques** : 20 témoins ORACLE-1 + 200 stratifiées (24 communes × {U,AU,A,N}
× {nue,bâtie}) + pièges ≤20/classe (top50+flop50 du classement servi q_v11_m137, signal
fort, plus grandes, <50 m², multipolygones — 23 sur l'île, tous pris —, frontière de
commune, à cheval zone PLU, 50 pas, sans LiDAR, pseudo-SIREN, copropriété, indivision,
permis caduc, SUP AC1, PPR rouge partiel, PLU dépublié, sans adresse BAN). **3 classes
vides documentées** : `zac` (aucune couche en base, GEOPF-2), `regle_non_modelisee` (NULL
partout, PLU-CALIBRAGE-5 non mergé), `contenance_ecart` (surface_m2 = ST_Area(geom_2975)
partout, écart max 0 ; la contenance DGFiP n'est pas en base — oracle externe API Carto).

## Verdict par angle

### Angle 1 — face-à-face des lecteurs (`LECTEURS.csv`, `ECARTS-LECTEURS.csv`)
Inventaire : fiche (~30 blocs), fiche commune, 17 outils, 8 PDF (builder unique confirmé),
tuiles, filtres, exports, Copilote (3 chemins, liste blanche), Radar/Veille/digests.
Le banc V6b rejoué sur les 607 parcelles de l'échantillon (machinerie scripts/coherence
réutilisée telle quelle ; les 20 ppr_rouge_partiel ont rejoint l'échantillon après ce run) :
**14 225 comparaisons · 237 écarts · 0 nouvelle discordance produit bloquante**. Triage :
63 = familles pré-existantes V6b (cinquante_pas 33 + ravine 8 — même mécanique flags bruts
vs cascade arbitrée, l'info ravine EST servie en ligne « Proximité ~4 m » ; cache commune
24 ; prix_neuf 4 ; copro 1 ; taxe 1) ; 158 = arrondi entier de la fiche sur micro-parcelles
(« 0 m² » pour 0,145 m², C44 cosmétique) ; 8 = artefacts du banc innocentés à la main
(filiation multi-mères : la fiche sert LES DEUX mères, le banc comparait meres[0] à une
ligne arbitraire ; dénomination PM : la fiche sert le millésime 2025, la table historique
du banc s'arrête à 2024 — la fiche a raison).
Doubles chemins signalés même à valeurs égales : SDP lue à 2 temporalités (fiche au
service vs projet relu live, C37) ; « prix » sous 3 périmètres (section cadastrale / rayon
adaptatif / commune, C38) ; population 2 sources (API INSEE prioritaire, documenté) ;
part_proprietaires_pct dupliquée (app.py / solaire.py, même formule). L'Excel du Bilan
n'existe pas encore (BILAN-1 : moteur prêt, export non branché) — « Bilan Excel » du
mandat sans objet au jour de l'audit.

### Angle 2 — invariants île entière (`INVARIANTS.csv`)
29 invariants, **17 à zéro violation** (géométries 100 % valides, domaines bande/tier/zone,
rang unique, surfaces positives, pentes bornées, taux TA/TFPB légaux, INSEE de l'IDU =
commune, caducs ⊂ octroyés, DVF > 0, p_raw ∈ [0,1]…). Violations qualifiées :
- **C06 (DISCORDANT bloquant)** : 222 parcelles « AU fermée » avec SDP > 0 servie — la même
  fiche dit « modification du PLU requise pour ouvrir » ET « Fort potentiel, 2 852 m² ».
- C29 : 7 086 groupes de lignes DVF dupliquées (une mutation ×197 lignes) — le carburant de C01.
- C30 : emprise scoring > surface sur 19 728 parcelles (bâtiment à cheval non clippé, cap
  300 % ; aucun lecteur n'affiche le ratio brut — choix COHERENCE-FIX-2 documenté).
- C31 : 58 hauteurs LiDAR aberrantes, toutes badgées « Sources discordantes » (0 fuite).
- C32 : 7 médianes « hors bornes » = arrondi à l'euro (2 453 325 vs max réel 2 453 324,8).
- C34 : 754 parcelles « 50 pas » à plus de 200 m du trait de côte (Saint-Paul jusqu'à
  485 m) — la couche officielle DEAL fait foi, l'invariant naïf « ≤ 81,2 m » ne tient pas
  juridiquement : à instruire, pas un FAUX démontré.
- `taux_emprise_pct`/`pct_potentiel` > 100 : sémantique ASSUMÉE (dénominateur = emprise
  constructible max, pas la surface ; les lecteurs plafonnent l'affichage à « > 300 % »,
  COHERENCE-FIX-1) — requalifiés, pas des violations.

### Angle 3 — l'absence lue comme un zéro (`COUVERTURE.csv`)
La famille la plus dangereuse, et elle est bien là :
- **C22/C23 (TROMPEUR bloquants)** : « Aucun risque PPR/aléa intersecté » et « Aucune
  servitude recensée » (jusqu'au PDF) conclus dès que la couche existe QUELQUE PART en base
  — jamais de test de couverture par commune. Le gabarit correct existe (EnsLayer,
  `kind_present_commune`, M70) ; RisquesLayer, SupLayer, SolPollueLayer, FricheLayer ne
  l'utilisent pas. La matrice `COUVERTURE.csv` donne les communes où ça mord : cavités 10
  communes à 0, friches 2, assainissement 20, prescriptions GPU 3 (dont les 2 dépubliées).
- C24 : en-tête fiche « Particulier » pour un propriétaire NON RÉSOLU (le tiroir, lui, dit
  « non identifié »).
- C25 : seuil minimal DVF 5 en dur (4 fichiers) vs 8 au yaml — deux rigueurs pour la même
  question ; « sous 5 ventes ABSENT » faux pour le bâti (n ≥ 8).
- C26 : scoring p_v2 `fillna(0)` — SDP inconnue éliminée comme SDP nulle, sans trace.
- C27 : aucun mécanisme « PLU dépublié » (Saint-Leu, Saint-André servent zone et règles
  comme si de rien n'était ; prescriptions GPU à 0 → « aucune prescription »).
Côté sain (modèles à répliquer) : BAN (« Absent » honnête + compteur mesuré), DVF fiche
(« — » jamais 0 €/m², « échantillon insuffisant » motivé), bâti (« couche non ingérée —
occupation non vérifiée »), hauteur LiDAR (None jamais 0), 999 % supprimé.

### Angle 4 — libellés face aux requêtes
Inventaire complet (strings.ts + layers.ts intégraux, exports/, api/*.py, taxe, registre) :
**~200 libellés VÉRIFIÉ ÉGAL ou CONSTANTE DU REGISTRE** (dont tous les rayons DVF
post-ORACLE-FIX-1, « 24 communes » partout où c'est dit, 81,20 m des 50 pas, ZFANG, TA
yaml unique) — et **20 FAUX** (C07–C21, C39–C42), contre-vérifiés par sondage 4/4 :
le pire est le texte d'accueil qui décrit le protocole d'un run JAMAIS basculé (q_v14)
comme étant le modèle servi (C07) ; viennent ensuite « médian » qui est une moyenne (C11),
« à moins de 500 m » qui est une section cadastrale (C12), « HT au taux du régime » qui est
toujours 8,5 % (C13), les compteurs figés qui ont dérivé (C08 33 622→33 921, C09
227 545→257 340, C10 VEFA 36 mois/10 ventes→60 mois/seuil 8, C16 SIS 4→10), le registre
RAP périmé 0,68 €/m² (C19), « ~0,5 % » Sitadel qui vaut 18,3 % (C15), 2 sections PDF
mortes (C39). Plus un lot de chiffres figés sans sentinelle (C36 : enquête publique qui
périme sous 5 jours, « 2025-2026 provisoires », « 90,7 % » ×8 copies).

### Angle 5 — doublons et doubles comptes
- **C01 (FAUX bloquant)** : bloc fiche « Autour, à moins de 100 m » — 122 « ventes »
  affichées pour **2** mutations réelles (97411000BC0337) ; count(*) sur lignes brutes,
  médiane pondérée ~60× par une vente d'immeuble. Même mécanique au courrier (C03).
- **C02 (FAUX bloquant)** : prix/m² de la dernière mutation = valeur TOTALE de la mutation
  ÷ surface d'UNE parcelle — 41 % des parcelles en mutation multi-parcelles ; la fiche
  sert le drapeau `multi_parcelles`, le flash NON.
- C04 : surface_terrain = premier bout (ratio vrai ≈ 15×), volume servi faible.
- C05 : 303 576 bâtiments doublonnés inter-communes en base ; les consommateurs fiche sont
  immunisés (ORACLE-FIX-1 D) mais le module Division et division_or comptent double.
- Sain : permis (0 doublon, uq_sitadel), SIRENE (actifs seuls en base), pas de double
  compte BD TOPO+CoSIA+RNB+LiDAR dans l'emprise servie (MAX, jamais somme), pas de
  distance servie en degrés (doctrine geo.py 2975 tenue), multi-lots DVF dédupliqués P1-03.
- Jointures « touche = reçoit » sans seuil d'aire : contraintes_parcelle (dpu/sup/ANC),
  pm1 gabarit (EXISTS touch, « option 1 » assumée mais déclencheur 0 m²), assainissement
  ORDER BY LIMIT 1, liste RNB — SALE, listés dans ECARTS.

### Angle 6 — test de bascule (base de test `labuse_chasse1`, supprimée en fin d'audit)
Base jetable (copie de labuse_test + vue parcel_residuel de prod + 2 runs synthétiques
divergents : résiduel 500→1500 m², scoring q_v11_m137 « chaude » → q_v99b « brûlante »).
Bascule à chaud (is_served en base + manifeste/served_run.txt du worktree, restaurés par
git checkout) puis relecture SANS redémarrage : **tous les lecteurs jouables suivent** —
`/config/run` (≤3 s, TTL runs.current), fiche SDP 500→1500, fiche tier chaude→brûlante,
`/filtre` tiers et sdp_min (≤30 s, memo compteur — C45 cosmétique : clé de memo sans
empreinte du run). **0 DISCORDANT structurel.** Au passage, le fait que la fiche réponde
404 quand le run pointé n'a pas sa cascade prouve qu'aucun lecteur ne retombe en silence
sur l'ancien run. Limites du squelette (dites) : tuiles non jouées (table matérialisée, à
régénérer à la bascule par construction — documenté tiles.py), PDF non joués, millésime
DVF non observable sur la fixture (le mécanisme clé-de-cache fiche_ask inclut l'empreinte
millésimes — COHERENCE-FIX-1, cité ; états « Sources modifiées » couverts par les tests
DOCS-1, cités). ⚠ Trouvaille de passage : le squelette `labuse_test` porte encore
`parcel_residuel` en TABLE vide là où la prod sert une VUE — les tests qui s'y adossent ne
voient pas le chemin réel (consigné pour le mandat de correction, hors périmètre client).

### Angle 7 — le temps qui passe (`HORLOGE.csv`)
Fiches rejouées sous freezegun à +400 jours (8 parcelles dont permis caducs) : seuls
bougent les drapeaux de péremption (`fiscalite.perime`, `taux_communal_perime`,
`bareme_perime`, `signalement_fraicheur` — le produit DIT que ses barèmes 2026 périment)
et `anciennete_detention.depuis_ans` (recalcul à la requête). **Aucune discordance
deux-horloges.** Accroc fuseau unique : « 03:00 » du dashboard = UTC, 07:00 Réunion (C21).

### Angle 8 — les parcelles qui ne devraient pas être là (`INTRUSES.csv`)
Top 200 du classement servi passé aux cribles voirie/ravine/DPM/cimetière/équipements/
géométrie/commune/zone : **propre**, à un détail près — 10 parcelles de propriétaires
publics (Commune, État…) classées brûlante/chaude (C35, à confirmer produit : le filtre
PM existe à part, le score n'exclut pas la propriété publique).

### Angle 9 — filtres et Copilote (`FILTRES.csv`, `COPILOTE.csv`)
- Filtres : 30 combinaisons (graine 42) + lois ensemblistes : **33 tests, 0 écart**
  (compteur = liste d'IDU, A∧B ≤ min(A,B), monotonie surface ; total 430 813 = total hors
  slivers < 2 m², comportement documenté F2).
- Copilote : 60 questions sur 10 parcelles : **0 chiffre inventé** — 38 collent à la
  fiche, 12 refus explicites corrects, 10 alertes de mon comparateur toutes résolues
  (valeurs du contexte faisabilité servi, arrondis 48↔47,8, un faux positif d'extraction).

## Top 10 des trouvailles (par gravité)

1. **C01 — FAUX bloquant** : « 122 ventes à moins de 100 m » pour 2 mutations réelles
   (toute parcelle proche d'une vente d'immeuble en copropriété).
2. **C02 — FAUX bloquant** : prix/m² = mutation entière ÷ une parcelle (41 % des parcelles
   à mutation multi-parcelles), servi par le flash sans le drapeau.
3. **C06 — DISCORDANT bloquant** : 222 parcelles « AU fermée » avec « Fort potentiel —
   2 852 m² » sur la même fiche (le résiduel ignore parcel_au_statut).
4. **C22/C23 — TROMPEUR bloquant** : « Aucun risque » / « Aucune servitude » conclus sans
   test de couverture commune — jusqu'au PDF.
5. **C07 — FAUX** : l'accueil décrit le protocole d'un run jamais servi (train réel
   2017-2024, pas « 2025 tenue à l'écart »).
6. **C27 — TROMPEUR** : PLU dépublié (Saint-Leu, Saint-André) servi comme un PLU vivant,
   prescriptions « aucune ».
7. **C05 — FAUX** : 303 576 bâtiments doublonnés inter-communes, comptés double par le
   module Division en bande frontalière.
8. **C12/C13/C11 — FAUX PDF** : « 500 m » qui est une section cadastrale, « taux du
   régime » toujours 8,5 %, « médian » qui est une moyenne.
9. **C08/C09/C10/C16 — FAUX** : compteurs figés qui ont dérivé (PM, adresses, VEFA, SIS).
10. **C26 — TROMPEUR** : SDP inconnue = SDP 0 dans l'éligibilité du classement.

## Ce qui a été prouvé juste (autant que les écarts)

Géométries 100 % valides et surfaces = aires exactes ; aucun rang dupliqué, domaines de
bandes/tiers sains ; top 200 sans voirie/ravine/cimetière/école ; filtres exacts aux lois
ensemblistes près ; Copilote qui n'invente aucun chiffre et refuse proprement ; horloge
saine (les péremptions sont DITES) ; permis sans doublon ; SIRENE sans fermés ; emprise
servie sans double compte multi-sources ; aucune distance en degrés ; TA/TFPB dans les
bornes légales ; les 13 rayons DVF d'ORACLE-FIX-1 tiennent ; « 24 communes » juste
partout ; BAN et DVF exemplaires sur l'absence dite.

## Livrables

`ECARTS.csv` (43 lignes, chaque ligne reproduite par une commande) · `INVARIANTS.csv` ·
`COUVERTURE.csv` · `LECTEURS.csv` · `ECHANTILLON.csv` · `INTRUSES.csv` · `FILTRES.csv` ·
`COPILOTE.csv` · `HORLOGE.csv` · `ECARTS-LECTEURS.csv` · `BASCULE.csv` ·
`scripts/chasse/` rejouable : `make -C scripts/chasse chasse` (le mandat n'autorise pas
d'écrire un Makefile racine).

## Angles non joués ou partiels (dits, pas tus)

- Oracles externes (API Carto, Géorisques, BAN, RNB) : 70 lignes « non vérifiable » en
  étape 0 — réseau indisponible depuis la session ; le rejouable est fourni.
- Digests mail Veille : lus en inventaire (mêmes fonctions que le Radar), pas rejoués en
  dry-run dans cette session.
- Excel du Bilan : n'existe pas encore (BILAN-1) — sans objet.
- Tuiles : comparées via le banc V6b (décodage PBF) sur l'échantillon ; pas de
  re-génération de tuiles.
- Classe piège « règle non modélisée » et badge Estimé : PLU-CALIBRAGE-5 non mergé, rien à
  mesurer sur main.
