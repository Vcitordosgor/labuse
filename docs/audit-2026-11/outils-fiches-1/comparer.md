# Comparer des parcelles

Clé interne : `comparer` (num A8) · composant : `frontend/src/components/compare/ComparePanel.tsx` (panneau `CompareModule` l.160, tableau `ComparePanel` l.214) · endpoint(s) : `GET /compare?idus=…` (`src/labuse/api/app.py:9498`) pour l'écran, `GET /comparatif.pdf?idus=…` (`src/labuse/api/documents.py:224`) pour l'export.

---

## 1. À quoi il sert, et pour qui
Mettre 2 à 3 parcelles côte à côte, critère par critère (surface, urbanisme, potentiel, risques), pour un prospecteur foncier qui hésite entre plusieurs terrains. Il ne calcule RIEN de neuf : il recopie, en colonnes, des valeurs déjà produites par la fiche servie et la faisabilité — avec une petite exception de recalcul signalée plus bas (doute 1).

## 2. Le parcours
- **Panneau gauche (`CompareModule`, l.160-211)** : texte « Jusqu'à 3 parcelles — barre ou clic carte » (l.185). L'utilisateur saisit une adresse/IDU dans `EntreeParcelle` (l.187) OU clique une parcelle sur la carte (le panneau arme le « picking », `setComparePicking(true)` l.172). Chaque parcelle ajoutée apparaît en puce numérotée retirable (chips `data-compare-chip`, l.192-197). Bouton « + Ajouter la parcelle courante » si une fiche est ouverte (l.201-205). Bouton « Comparer (n/3) » (l.206-208) ouvre le tableau ; actif dès 1 parcelle.
- **Tableau en surimpression (`ComparePanel`, l.214-358)** : appelle `getCompare(compareIdus)` (l.217). En-tête de chaque colonne : IDU, adresse (aperçu BAN), zone + surface, bouton « Ouvrir la fiche → » (l.283-293). Le corps affiche **11 lignes** groupées en 4 sections (Terrain / Urbanisme / Potentiel constructible / Risques et contraintes, l.113). Un point vert ● marque la meilleure valeur de chaque ligne chiffrée (`bestIdx`, l.139-150), une fine barre proportionnelle les lignes à barre (l.331-335). Chaque ligne porte un badge **sourcé** (vert) ou **estimé** (ambre) (`ProvBadge`, l.130-134). Bouton « Exporter en PDF » (actif à partir de 2 parcelles, l.248-252). Fermeture par la croix, par Échap ou par clic hors du tableau.
- **Quitter l'outil vide la sélection** (`clearCompare` au démontage, l.177) — plus de persistance.

## 3. Les données lues
Le Comparatif ne lit JAMAIS la base directement pour l'écran : il appelle `compare()` qui pour chaque IDU construit `_fiche_servie(...)` (fiche premium servie, cache `_FICHE_CACHE`) + `fiche_payload(...)` (faisabilité du même point de calcul), puis `_compare_row()` (`app.py:9198`) extrait ~30 champs. Les tables ci-dessous sont celles réellement lues PAR CES BRIQUES pour les champs AFFICHÉS.

| Donnée affichée | Source (nom catalogue) | Table / endpoint réellement lu | Millésime servi | Cadence |
|---|---|---|---|---|
| Surface | Cadastre (API Carto PCI) / Cadastre Etalab | `parcels` (`surface_terrain_m2` servie, `app.py:9276`) | PCI Parcellaire Express « latest » | — |
| Bâti existant % | CoSIA + BD TOPO IGN | emprise bâtie (`residuel.emprise_batie_m2` / `surface`, `app.py:9245`) | CoSIA 2025 (PVA juil.-août 2025) ; BD TOPO® V3 | pluriannuelle |
| Propriétaire | DGFiP — parcelles des personnes morales | `parcelle_personne_morale` via `proprietaire_moral` (`app.py:9226-9240`) | Panel 2019→2025 (situation 1ᵉʳ janvier) | annuelle |
| Hauteur autorisée (R+N) · Emprise au sol max (CES) | Urbanisme PLU/GPU + `config/plu_destinations` | gabarit `residuel.niveaux_max` ; CES `resolve_zone().emprise_sol_pct` (`app.py:9315, 9599`) | GPU/PLU par commune (détail en fiche) | sur révision |
| Zone PLU (en-tête + constructibilité) | Urbanisme PLU/GPU (API Carto) | `parcel_zone_plu` via `zone_dominante` (`zone_servie.py:60-70`, `app.py:9574-9578`) | GPU/PLU par commune | sur révision |
| Assainissement | VRD/assainissement (SPANC) / GPU zonages assainissement | bloc `anc.libelle` de la fiche (`app.py:9319`) | GPU idurba 4/24 au 11/07/2026 (sinon constat de secteur statistique) | — |
| Contraintes relevées | DEAL Réunion — PPR/aléas (+ prescriptions PLU) | lignes de cascade `qv2.lines` filtrées HARD_EXCLUDE/SOFT_FLAG (`app.py:9216`) | PPR/PPRL 2011–2026 (arrêtés DEAL) | — |
| Adresse (en-tête colonne) | BAN PLUS (IGN) | `adresse_parcelles` ⋈ `adresses` (`app.py:9620-9623`) | BAN PLUS data.gouv 27/08/2026, moisson 13/09/2026 | — |
| (servi mais NON affiché) prix bâti/terrain | DVF / valeurs foncières | `dvf_parcelle.secteur` / `prix_ancien` (`app.py:9261-9270`) | géo-DVF Etalab 2026-S1 | semestriel |
| Classement LABUSE (bande, Signal — servi, non affiché dans ROWS) | Run servi | `score_labuse` (`app.py:9609-9615`) | run `runs.current()` | — |

Les lignes « estimé » (SDP résiduelle, SDP max, part du gabarit, charge foncière) ne viennent pas d'une table mais du **moteur de faisabilité** (`faisabilite/`), décrit §4.

## 4. Les calculs
Toutes les valeurs « sourcées » sont des recopies (pas de calcul dans Comparer). Les valeurs « estimées » sont lues du moteur de faisabilité servi, SAUF le prix terrain qui est recalculé localement (doute 1).

- **Bâti existant %** (`app.py:9245-9246`) : `round(100 × emprise_batie_m2 / surface_terrain)`. Dénominateur = surface de TERRAIN servie (contenance/dessin), identique à la fiche (commentaire NU-3-J#8). Arrondi entier.
- **Hauteur autorisée** (front l.69) : affiche `R+{max(0, niveaux_max − 1)}`, + « combles » si `gabarit_combles`. `niveaux_max`/`combles` viennent de `residuel` servi.
- **Emprise au sol max (CES)** (`app.py:9595-9602`) : la VRAIE règle PLU, **uniquement** si une valeur numérique est validée dans `plu_destinations` (via `resolve_zone`). Sinon `null` → affiche « non réglementée ». Badge sourcé.
- **SDP résiduelle (« Plancher possible · bâti conservé »)** (`app.py:9301`) : lit `potentiel_transformation.sdp_residuelle_m2` servi par la fiche (réconcilié hors_classement), sinon `residuel.sdp_residuelle_m2`. Commentaire SDP-UNIQUE-1 : explicitement la MÊME valeur que la fiche, pas un recalcul live. Badge estimé.
- **SDP max (« reconstruction »)** (`app.py:9298`) : `fourchette.surface_plancher_m2` de la faisabilité (SDP réglementaire terrain libéré). Badge estimé.
- **Part du gabarit déjà occupée** (`app.py:9299`) : `residuel.taux_emprise_pct` (disponible seulement si `residuel.disponible`). Rendu par `fmtTauxEmprise` (front l.87), « Saturé » au-delà de 100 %. Badge estimé.
- **Charge foncière €/m²** (`app.py:9304`) : `bilan.charge_fonciere.par_m2_terrain`, du bilan de faisabilité. Peut être NÉGATIVE (−20, −112 sur les témoins) = l'opération ne dégage rien pour le foncier. Badge estimé. Arrondi entier à l'affichage.
- **Meilleure valeur (point vert)** : calcul FRONT (`bestIdx`, l.139-150) — gagnant UNIQUE (pas d'égalité), jamais sur valeur absente ni négative ; `best:'hi'` (surface, capacité) ou `best:'lo'` (bâti, part gabarit).

Constantes : seuil d'échantillon prix `SEUIL_N = 8` (config, `dvf_mediane.py:31`, origine config servie, « plus jamais 5 en dur »). Plafond de 3 colonnes codé en dur (`ids = _dedup[:3]`, `app.py:9517`).

## 5. Chaque chiffre affiché
Les 11 lignes de l'écran (ordre et libellés exacts du tableau). Les champs servis mais sans ligne dans `ROWS` (prix bâti/terrain, bande LABUSE, Signal) sont notés à la fin.

| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| Surface | `parcels` (surface terrain servie) | **sourcé** |
| Bâti existant | emprise bâtie CoSIA/BD TOPO ÷ surface terrain | **sourcé** (calcul de ratio sur donnée mesurée) |
| Propriétaire | `parcelle_personne_morale` (DGFiP) ; défaut « particulier » | **sourcé** |
| Hauteur autorisée | `residuel.niveaux_max` (règlement PLU) | **sourcé** |
| Emprise au sol maximale | `plu_destinations` via `resolve_zone` ; sinon « non réglementée » | **sourcé** |
| Plancher possible · bâti conservé | faisabilité `potentiel_transformation.sdp_residuelle_m2` | **estimé** |
| Plancher possible · reconstruction | faisabilité `fourchette.surface_plancher_m2` | **estimé** |
| Part du gabarit déjà occupée | faisabilité `residuel.taux_emprise_pct` | **estimé** |
| Charge foncière | faisabilité `bilan.charge_fonciere.par_m2_terrain` | **estimé** |
| Assainissement | bloc `anc` de la fiche (souvent constat de secteur) | **sourcé** (mais parfois statistique de secteur, cf. §6) |
| Contraintes relevées | lignes cascade `qv2.lines` HARD_EXCLUDE/SOFT_FLAG (PPR, PLU, DPU…) | **sourcé** |
| *(non affiché dans ROWS)* prix bâti/terrain secteur | DVF `dvf_parcelle`/`prix_ancien` | sourcé (recopié / recalculé) |
| *(non affiché dans ROWS)* bande LABUSE + Signal | `score_labuse` | estimé (score LABUSE) |

## 6. Les limites
- **Prix NON affiché à l'écran** : `prix_secteur_bati_m2`, `terrain_zone_eur_m2`, `bande`, `signal_niveau` sont servis par `/compare` mais `ROWS` (front, l.58-111) **n'a aucune ligne de prix ni de classement** (retirés par FIX-ORFEVRE-1 / OUTILS-FIX-3 C1, cf. commentaires l.18-25). Le PDF non plus (`_LIGNES`, `comparatif.py:148-173`, mêmes 11 lignes). Donc le travail de calcul de prix est payé mais invisible côté comparateur.
- **Capacité / nombre de logements retirés** : logements_min/possibles ne sont plus servis (`app.py:9247-9251`) — renvoi à l'Étude de faisabilité.
- **Assainissement trompeur** : le libellé peut être un **constat de secteur statistique**, pas un raccordement vérifié à la parcelle (AK0804 : « 51 % des logements du secteur ne sont pas raccordés »). L'infobulle front le dit (l.94), mais la valeur ressemble à un fait parcellaire.
- **CES « non réglementée »** affiché aussi bien quand le PLU n'en fixe pas que lorsque la valeur n'est **pas encore calibrée** dans `plu_destinations` — l'utilisateur ne distingue pas les deux (ex. AK0804/DH0076 : `emprise_ces_pct = null`).
- **Seulement 3 colonnes** : au-delà, les IDU sont tronqués (annoncés via `tronques`), introuvables ignorés (`ignores`), doublons retirés (`doublons`) — mais le front `ROWS` n'exploite pas ces champs pour un message (seul le PDF imprime une note de limite, `documents.py:238`).
- **Résultat faux possible** si la faisabilité/fiche servie est elle-même fausse : Comparer ne fait que recopier, il n'a aucun garde-fou propre.

## 7. Les tests
- `tests/test_lot_d.py:32` `test_compare_row_source_servie` : garantit que `_compare_row` lit la source SERVIE (tier_v2/rang_v2/fraction/raison M135, SDP, charge foncière, zone, contraintes) et PAS la fiche legacy ; vérifie l'absence de clés de score internes (`opportunity_score`). `tests/test_lot_d.py:50` `test_compare_endpoint_ne_leve_pas` : un IDU bogus/vide → `count:0`, aucun crash.
- `tests/test_docs1_ecran_egale_pdf.py:95` `test_comparatif_ecran_egale_pdf_et_verrou` : l'écran = le PDF (mêmes surfaces imprimées) + verrou anti-fuite. **C'est la garantie-clé de parité écran/PDF.**
- Front : `frontend/src/components/compare/CompareAncrage.test.tsx` : ancrage dans Outils (panneau ≠ tableau), picking ON, chips retirables, bouton « Comparer (n/3) » ouvre l'overlay. Teste le PLOMBAGE UI, pas les valeurs.
- **Attention** : `tests/test_comparateur.py` concerne un AUTRE comparateur (composite stock/vélocité 24 communes, `scoring/comparateur.py`), **pas** cet outil A8.
- **Non testé** : aucun test ne vérifie la valeur numérique de SDP/charge/bâti%/CES pour une parcelle réelle ; aucun test ne couvre `bestIdx` (choix du gagnant) ni le recalcul `terrain_zone_eur_m2` (doute 1) ; aucun test ne vérifie les champs `ignores/tronques/doublons` côté front.

## 8. Les documents liés (PDF, exports)
Le PDF `GET /comparatif.pdf` (`documents.py:224`) appelle **la même fonction** `compare()` (l.252) puis `construire_comparatif(ids, data.parcels)` (l.255) → `blocs/comparatif.rendu` qui parcourt `_LIGNES` (`comparatif.py:148-173`). Ces `_LIGNES` sont les **mêmes 11 libellés** que l'écran, avec les mêmes badges s/e. Donc : **PDF = écran, mêmes valeurs, même source** (test `test_comparatif_ecran_egale_pdf_et_verrou` l'impose). Différences du PDF : page paysage, carte de situation de la parcelle de tête (`_plan_situation_html`), note imprimée si > 3 parcelles demandées, refus si une parcelle est disparue du cadastre (`documents.py:244-249`). L'export CSV a été RETIRÉ (commentaire l.220-222). Le bouton PDF exige ≥ 2 parcelles.

## 9. Trois cas rejoués
`curl "http://127.0.0.1:7300/compare?idus=97411000BZ1065,97409000AK0804,97415000DH0076"` → HTTP 200, `count:3`, `ignores/tronques/doublons` vides. Sorties brutes (résumé) :

| Ligne | BZ1065 (Saint-Denis, Uh) | AK0804 (Saint-André, UB) | DH0076 (Saint-Paul, U2b) |
|---|---|---|---|
| Surface | 1 567 m² | 27 862 m² | 19 513 m² |
| Bâti existant | 12 % | 0 % (aucun) | 24 % |
| Propriétaire | particulier | **public** | particulier |
| Hauteur (niveaux_max) | 1 (R+0 + combles) | 4 (R+3 + combles) | 5 (R+4 + combles) |
| Emprise CES | 30 % (`Art. Uh.9 · p.73`, calibré) | null → « non réglementée » | null → « non réglementée » |
| SDP résiduelle | 35,0 m² | 35 086,0 m² | null (contrainte « SDP 0 m² ») |
| SDP max (reconstruction) | 212 m² | 34 243 m² | 30 733 m² |
| Part gabarit (taux_emprise) | 40 % | 0 % | 34 % |
| Charge foncière | **−20 €/m²** | 7 €/m² | **−112 €/m²** |
| Assainissement | Assainissement non collectif | 51 % du secteur non raccordé *(constat statistique)* | Tout-à-l'égout (collectif) |
| Contraintes (n) | 7 (dont PPR bleu, DPU, SDP 35 m²) | 10 (dont PPR rouge 12 %, aléa inondation fort) | 13 (dont PPR rouge 2 %, SDP 0 m²) |
| *(servi, hors écran)* prix bâti | 3 821 €/m² (n=30, r=500 m) | 2 024 €/m² (n=45) | 6 275 €/m² (n=79) |
| *(servi, hors écran)* prix terrain | 369 €/m² (n=15) | 271 €/m² (n=28) | **null** (n=null) |
| *(servi, hors écran)* bande LABUSE / Signal | D / faible | A / faible | 0 / moyen |

Note d'adaptation témoin : l'IDU `97415000DH0076` résout en commune **Saint-Paul** (« 104 Avenue de Bourbon, 97434 Saint-Paul »), pas Saint-Pierre/Joseph comme indiqué au briefing — gardé tel quel car c'est l'IDU exact fourni.

## 10. Tes doutes (par gravité)
1. **(grave) `terrain_zone_eur_m2` est recalculé localement SANS le seuil d'échantillon, contrairement à la fiche.** `_compare_row` (`app.py:9266-9270, 9326`) prend `max(_terr, key=n_ventes)["mediane_prix_m2"]` sur `dvf_parcelle.secteur`, **sans** appliquer `SEUIL_N=8`. La fiche (`robinet_fiche.py:701-713`) applique ce seuil et renvoie « échantillon insuffisant » en dessous. Les commentaires du code (l.9323-9326) affirment pourtant « vient de l'id de la fiche (mode_b.terrain_nu.prix_m2), lu tel quel » : **le commentaire est périmé, le code recalcule.** Un prix terrain fondé sur 1-2 ventes peut donc sortir dans `/compare` là où la fiche l'aurait masqué. Atténué aujourd'hui par le fait que cette valeur n'est PAS affichée à l'écran ni au PDF (ROWS/_LIGNES sans ligne prix) — mais elle est servie et consommable.
2. **(moyen) Du calcul coûteux servi puis jeté.** `/compare` construit 3 fiches complètes + bilan + score + DVF + BAN en parallèle, mais ~1/3 des champs renvoyés (prix bâti, prix terrain, bande, Signal, rang, fraction) n'ont **aucune ligne** dans l'écran ni le PDF. Pour une comparaison de 3 parcelles jamais ouvertes, c'est le coût d'un calcul de fiche pour un affichage de 11 lignes principalement sourcées.
3. **(moyen) « Assainissement » mélange parcellaire et statistique de secteur** dans la même ligne/même badge « sourcé » : AK0804 affiche « 51 % des logements du secteur ne sont pas raccordés » (donnée RP/secteur) à côté de DH0076 « Tout-à-l'égout (collectif) » (verdict parcellaire). Rien à l'écran ne distingue les deux niveaux de fiabilité hors l'infobulle du libellé.
4. **(mineur) CES « non réglementée » ambigu** : ne distingue pas « le PLU ne fixe pas de CES » de « CES pas encore calibrée dans `plu_destinations` ». Deux témoins sur trois tombent dans ce cas.
5. **(mineur) `ignores`/`tronques`/`doublons` non exploités par le front** : seul le PDF imprime la note de limite. À l'écran, 5 IDU demandés → 3 colonnes sans message explicatif (le champ est pourtant renvoyé par l'API).
