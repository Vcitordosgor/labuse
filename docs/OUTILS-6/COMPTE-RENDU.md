# OUTILS-6 — Refonte de la fiche commune

Branche `feat/outils-1`. Référence : `docs/maquettes/fiche-commune-v1.html`.
**Règle transversale** : un seul moteur, une seule donnée, rien en dur au front. Postgres en lecture ;
aucune écriture DB (la population, agrégat coûteux, est **mémoïsée** — pas matérialisée). Golden non touché.

---

## C1 — Le zonage ne totalise plus 208 %

**Diagnostic.** Le moteur servi (`_foncier_commune`, table `parcel_zone_plu` en **PK sur `idu`** — une zone par
parcelle) sommait en réalité déjà à 100 % en **comptes de parcelles**. Le « 208 % » est la signature d'un
comptage de parcelles qui **intersectent** chaque famille de zone (une parcelle à cheval sur une limite est
comptée dans plusieurs familles) — reproduit en base au croisement `parcels × spatial_layers(plu_gpu_zone)`
(> 100 %). Mais des parts de **parcelles** ne représentent pas le **territoire** : à Saint-Paul U domine en
nombre (71,7 %) alors que A + N couvrent 83 % de la **surface**.

**Correctif.** `repartition_zonage` passe en **parts de SURFACE** (`sum(surface_m2)` par famille / surface
zonée), avec les hectares par famille. Barre empilée dans la fiche.

**Check (Saint-Paul, mesuré via l'endpoint et via l'UI) :**
```
U 13,5 %  ·  AU 3,5 %  ·  A 35,8 %  ·  N 47,2 %   →  SOMME = 100,0 %
ha :  U 3 098 + AU 808 + A 8 194 + N 10 816 = 22 916 ha  =  surface communale servie (surface_ha)
```
La somme des parts = 100 %, et la surface totale par zone = la surface communale servie ailleurs. ✓

## C2 — Un seul prix de l'ancien (commune entière)

**Diagnostic.** La fiche affichait la médiane **locale** (`sector_price`, secteur autour d'une parcelle
représentative = 3 322) via `<MarcheCommune>`, le comparateur la médiane **commune entière**
(`prix_ancien_communes`, baromètre DVF = 4 278). Deux moteurs pour un même chiffre — interdit.

**Correctif.** Création d'une **source unique partagée** `comparateur.raw_rows(db)` (indicateurs bruts par
commune, mémoïsée), lue par le comparateur ET la fiche → chaque chiffre commun est identique **par
construction**. Le composant `<MarcheCommune>` (médiane locale) est **retiré** de la fiche ; le bloc « Le
marché » sert désormais l'ancien commune-entière, le neuf, le stock foncier, le délai — tous du même run.

**Check (3 communes, fiche vs comparateur — mesuré) :**
```
Saint-Paul  : ancien 4278 · neuf 4730 · permis5a 1953 · délai 9,0 · stock 285   → IDENTIQUE
Saint-Denis : ancien 2469 · neuf 4275 · permis5a 1265 · délai 9,0 · stock 114   → IDENTIQUE
Le Tampon   : ancien 2259 · neuf 4318 · permis5a 1312 · délai 9,0 · stock 144   → IDENTIQUE
```
**Stock foncier** affiché EN PARCELLES ET EN HA depuis la même requête (285 parcelles / 49 ha), le compte
identique à la colonne « stock » du comparateur.

## C3 — « 11 QPV » et onze noms

**Vérifié contre la source (ANCT, `spatial_layers` kind=`qpv`).** Saint-Paul = **11 lignes, 11 noms, 11 codes
`code_qp` distincts** ; le front dérive déjà le compteur de la liste servie (`d.qpv.length`). Le bug maquette
« 11 vs 15 » venait d'un découpage naïf des **noms composés** (« Ermitage - Vue belle - Saline » compté 3) ;
le code servi affiche le nom composé entier → compteur = longueur de liste. **Déjà conforme, préservé** dans
la refonte (aucune valeur de compteur indépendante).

## C4 — La fiche en accordéons

En-tête permanent (nom, EPCI, signal, surface, nb parcelles, **quatre chiffres qui décident** : terrain nu
zone U · ancien médian commune · horizon ZAN · délai d'instruction) + boutons « Voir ses parcelles »
(comportement OUTILS-4 inchangé) et « Comparer ». Puis **neuf sections repliables** dans l'ordre de la
question d'un promoteur : Le foncier (ouvert) · Le marché (ouvert) · Le marché des annonces · Construire ici ·
La règle & les contraintes · Les risques · Population & logement · Continuer avec un outil (ouvert) · Contacts.

- Chaque section **fermée porte son chiffre-clé** sur la ligne (mesuré : « 49 ha repérés », « 5 biens · −31,1 % »,
  « 314 permis / 12 mois », « ZAN 4,2 ans · SRU déficitaire », « PPR sur 34,4 % », « 51 317 logts · 9,4 % vacants »).
- Chaque section garde sa **ligne de sources datées**.
- L'état ouvert/fermé est **mémorisé d'une fiche à l'autre** (`localStorage` clé `labuse.fiche.acc`, par section).

## C5 — Les blocs qui manquaient (chacun depuis son moteur)

Tableau de provenance — aucune donnée recalculée, chaque bloc consomme le point de calcul de son outil :

| Bloc | Moteur d'origine | Point de calcul |
|---|---|---|
| Marché des annonces (Radar) | Radar LABUSE | `pige.marche.stats` (seuil `SEUIL_N`=5) ; écart demandé/acté = demandé (annonces) vs acté (baromètre DVF) |
| Les risques | Pièges & risques / Géorisques | `spatial_layers` (ppr, mvt, parc_national) + `catnat_arretes` (GASPAR) |
| Population & revenu | Étude de zone / Filosofi | `filosofi_carreaux_200m` agrégé sur la commune (mémoïsé) + `commune_insee_logement` |
| Le PLU (statut) | veille PLU | `veille_plu.entry` + `rnu.is_rnu_insee` (statut **calculé**, jamais en dur — cf. A5 OUTILS-1) |
| Permis au point mort | Permis | `pc_caducs` (accordés sans DAACT) + `ligne6_offre_engagee` + comparateur (délai) |
| Parcelles densifiables | Densifier l'existant | `ligne7_gisement` (SDP résiduelle, tiers servables) |
| Loyer médian **sourcé** | Marché commune | ligne loyer de `build_marche_commune` (DHUP, carte des loyers) — plus jamais un chiffre nu |

Valeurs mesurées Saint-Paul : Radar 5 biens / demandé 2 949 / écart −31,1 % · Risques PPR 34,4 % / mvt 0,1 % /
CatNat 10 / Parc National oui · Population 96 786 hab / 36 431 mén / niveau de vie 22 018 € / 51 317 logts
(9,4 % vacants) · PLU « à jour » · Permis 314/12 m · 330 point mort · Densifiables 21 527 / 11,4 M m² · Loyer 18,86 €/m².

**Résilience** : chaque bloc est isolé (`_safe` + rollback) — une source absente dégrade CE bloc (repli valide,
« introuvable = null »), jamais la fiche entière (vérifié : la base de test sans `pc_caducs` sert quand même la fiche).

## C6 — Les passerelles vers les outils

Section « Continuer avec un outil » (ouverte), huit outils qui s'ouvrent **avec la commune déjà
sélectionnée** (`ouvrirOutil` : pose commune + filtre, ouvre le module, ferme la fiche ; PLU reçoit son INSEE
en prefill). **Chaque libellé porte son chiffre** (mesuré) :

```
PLU · Étude de zone · Comparer aux 24 communes  (toujours pertinents)
Permis · 314 en cours · 330 au point mort
Densifier l'existant · 21 527 parcelles à capacité résiduelle
Radar · 5 biens en vente
Scan patrimoine · 12 539 parcelles détenues par une personne morale
Prospection solaire · 1 616 piscines détectées
```
Un outil à **compteur 0 est absent** (jamais grisé à zéro). Vérifié : cliquer « Densifier » **ouvre l'outil sur
Saint-Paul et ferme la fiche** (`densifier_ouvre_commune=true`, `fiche_fermee=true`). Raccourcis contextuels au
fil des sections (Densifier sous Le foncier, Permis sous Construire ici, Étude de zone sous Population).

---

## Vérif finale

| Contrôle | Résultat |
|---|---|
| `tsc` (noUnusedLocals) | **0 erreur** |
| `vite build` | **vert** |
| `pytest tests/` | **1999 passed, 43 skipped, 0 failed** (8 min 33) |
| Golden | **intact** — 0 fichier `scoring/` / `qa/` / golden modifié |
| Périmètre d'écriture | lecture Postgres partout ; **aucune écriture DB** |
| Zonage somme | **100,0 %** (capture `03`) |
| C2 identité fiche/comparateur | **identique sur 3 communes** (mesuré + captures `01`/`02`) |
| QPV compteur = liste | **11 = 11** (source ANCT) |
| Console navigateur | **0 erreur** (recette Playwright) |

**Fichiers**
```
 M src/labuse/api/app.py            (C1 zonage surface + stock ; câblage blocs ; insee au payload)
 M src/labuse/api/comparateur.py    (C2 source unique partagée raw_rows)
?? src/labuse/api/fiche_commune.py  (C5/C6 — les blocs ajoutés + compteurs, chacun depuis son moteur)
 M frontend/src/lib/api.ts          (types : zonage surface, comparable, 6 blocs, outils)
 M frontend/src/components/contexte/ContextePanel.tsx  (C4 accordéons + en-tête + C6 passerelles)
?? frontend/qa/outils6_captures.mjs (script de recette)
?? docs/OUTILS-6/                    (compte-rendu + 5 captures)
```

**Captures** (`docs/OUTILS-6/captures/`) — API (uvicorn :8000) et front (build servi sous /socle/) redémarrés
avant recette :
- `01-comparateur-table-C2.png` — le tableau des 24 communes (colonne ancien, référence C2).
- `02-fiche-defaut-accordeons.png` — fiche par défaut : en-tête 4 chiffres + accordéons, chiffres-clés sur lignes fermées.
- `03-fiche-tout-ouvert.png` — fiche entière dépliée (zonage surface = 100 %, tous les blocs).
- `04-fiche-passerelles.png` — « Continuer avec un outil » : 8 passerelles avec leurs compteurs.
- `05-passerelle-densifier-commune.png` — Densifier ouvert sur Saint-Paul (la fiche s'est fermée).

**Provenance** — lectures Postgres uniquement ; population mémoïsée (pas d'écriture) ; golden non touché.
