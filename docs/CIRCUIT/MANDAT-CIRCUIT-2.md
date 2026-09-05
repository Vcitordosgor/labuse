LOT 0-BIS — RÉCONCILIATION AVEC EXPORTS-1 ET ZONE-1 (décisions prises, à appliquer, pas des questions)

Contexte : main contient ZONE-1 (src/labuse/faisabilite/zone_servie.py) et EXPORTS-1 (marche_service point d'appel unique des prix, faisabilite/potentiel.py, scripts/recette_exports1.py, archive JSON du Flash, 272 mutations DVF ré-étiquetées Immeuble). Le registre a été rempli depuis l'inventaire CIRCUIT-0, antérieur : il décrit du code qui n'existe plus pour une dizaine d'ids. Le compte-rendu de réconciliation de la session exports est dans docs/audit-2026-09/EXPORTS/RECONCILIATION-CIRCUIT.md s'il a été déposé ; sinon le code de main fait foi.

1. `git merge main` dans feat/circuit-1 ; conflits résolus en gardant le code de main pour les moteurs d'EXPORTS-1/ZONE-1 et le registre de la branche ; suite verte avant de continuer.

2. Registre — moteurs :
   - `marche_communes` est renommé `marche_service` (fichier src/labuse/marche_service.py), libellé « Prix : point d'appel unique (fiche, outils, PDF, Copilote) », et devient le moteur des ids prix_ancien_median_eur_m2, prix_terrain_zone_eur_m2, tranche_prix_vefa et des deux ids du neuf (point 3).
   - `sector_price` inchangé, mais prix_sortie_bati_eur_m2 passe calcul=front → moteur:sector_price servi au serveur (EXPORTS-1 l'a fait) ; fonction corrigée.
   - Nouveau moteur `potentiel` (faisabilite/potentiel.py, bloc « au sol / en hauteur / table rase » + verdict) : sdp_residuelle_m2, capacite_logements, classe_residuel pointent dessus (plus residuel.py:80 ni modules.py:faisabilite_sens1 en direct) ; le verdict du bloc reçoit son id.
   - Nouveau moteur `zone_servie` (faisabilite/zone_servie.py, zone dominante par surface, drapeau a_cheval, zone_parts) : zone_plu_famille passe de passe_plat (app.py:map_layers_geojson) à moteur:zone_servie. Ne PAS confondre avec registre/moteurs/zonage.py (parts communales, lot 2.1) : nommer les deux clairement (zone_servie = zone d'une parcelle ; zonage_commune = parts d'une commune).
   - `proprietaire_historique` : fonctions de type_proprietaire, n_parcelles_pm, acquisitions_pm_n mises à jour sur le fichier PM (EXPORTS-1 lot 5.4).
   - Permis : n_permis_proximite, permis_12m_n, permis_5a_n, depots_secteur_n, ventes_100m_n gardent chacun leur id, mais chaque libellé porte sa fenêtre et son rayon (ex. « Permis à 500 m sur 24 mois ») ; n_permis_proximite = le profil client 500 m · 24 mois (arbitrage Q7 de Vic), fonction sur le profil réellement transmis.
   - Mixité sociale (seuil, quota, EXPORTS-1 lot 5.1) : id créé, moteur nommé.
   - Toutes les `fonction` sont revérifiées contre main (grep) : aucune ne pointe vers un fichier:ligne qui n'existe plus.

3. Le prix du neuf — la seule contradiction, tranchée : DEUX ids.
   - `prix_neuf_vefa_acte_eur_m2` = VEFA à l'acte (neuf_vefa_commune, live, n ≈ 308 à Saint-Paul, 5 003 €/m²), usage : scoring (score_e, lot 2.2 de CIRCUIT-1 reste vrai).
   - `prix_neuf_observe_eur_m2` = neuf observé ≤ 3 ans après achèvement (resolve_prix_neuf_marche, n ≈ 54, 4 730 €/m²), usage : bilan et exports (arbitrage Q3 de Vic).
   - Chaque id porte dans sa définition l'usage qui lui est réservé ; la fuite prix_neuf_vefa_eur_m2 de fuites_mesurees.csv est soldée par scission (ligne conservée, statut solde, motif « deux définitions, deux ids »). Aucun robinet ne sert l'un sous le libellé de l'autre : la sonde vérifie que le scoring lit le premier et le bilan le second.
   - L'ancien id prix_neuf_vefa_eur_m2 disparaît (alias de transition vers _acte pendant un lot, puis retiré).

4. Registre — structure :
   - Nouveau champ `couverture` sur Valeur (n, non_couvert) : la garde de couverture d'EXPORTS-1 (lot 5.5) devient une règle du registre, portée par toute Valeur de type compteur, et la sonde refuse un compteur sans couverture.
   - Troisième portée `projet` (à côté de run et live) pour les saisies client du Financier (prix demandé, coût de construction, marge) : pas de réservoir, tampon = « saisi par le client le … ».
   - Compte réel des chiffres : 94 dans chiffres.py (pas 98) ; corriger le compte-rendu et le bandeau.

5. Sonde — ce que le lot 4 n'a pas couvert et qui est dû :
   - Les quatre témoins d'EXPORTS-1 entrent dans les parcelles golden : 97415000BO0852, 97401000AD0554, 97416000DY0106, 97411000AV0110.
   - La sonde appelle les VRAIS chemins, pas seulement les fonctions : endpoints HTTP avec ?trace=1, builders PDF en collecte, outils Copilote (c'était le 4.1 du mandat ; « non_couverts » n'est pas un verdict acceptable pour ces trois familles).
   - scripts/recette_exports1.py devient un cas de la sonde (génération des 24 PDF des 4 témoins, extraction, comparaison à fiche.json et à l'endpoint fiche), joué dans le passage nocturne coherence-robinets, pas à la demande.
   - Contrôle « mots interdits » (56 → 0 au terme d'EXPORTS-1) ajouté à la sonde comme contrôle distinct, avec sa liste versionnée.

6. Compte-rendu : chapitre « 4-bis Réconciliation » avec le tableau id → moteur avant/après, la scission du neuf, la liste des fonctions corrigées, et la note « 43 chiffres restent en sql_propre et 13 en passe_plat : un chemin unique, pas encore un moteur nommé — traité au lot 1.6 de CIRCUIT-2 ».


6. Compte-rendu CIRCUIT-2, chapitre « 0-bis Réconciliation » : tableau id → moteur avant/après, scission du neuf, fonctions corrigées, suite verte après merge. Puis le mandat, lot 1.

# MANDAT CIRCUIT-2 — Une donnée = une source

Branche : `feat/circuit-2`, dans le worktree `~/Desktop/labuse-audit`. Créée depuis `main` si `feat/circuit-1` y est mergée, sinon depuis `feat/circuit-1` (ordre de merge pour Vic : 1 → 2 → 3 → 4).
Dossier : `docs/CIRCUIT/`. Compte-rendu : `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-2.md`.
Prérequis : CIRCUIT-1 clos (lots 0 à 8), registre en place (`src/labuse/registre/`), manifeste de service, sonde `coherence-robinets`, page Circuit, traçage.
Objectif : que **toute donnée affichée** — pas seulement les nombres — ait une seule origine déclarée, un seul millésime, un seul chemin ; qu'un concept (le zonage, l'aléa, le transport, le permis, le prix) n'ait qu'une source canonique ; et que la fiche parcelle soit lisible donnée par donnée : d'où ça vient, quand, et où ailleurs ça s'affiche.

Vocabulaire : celui de CIRCUIT-0 et 1. Nouveau : **donnée** = tout ce qui s'affiche et qui vient d'une source (nombre, classe, texte, liste, géométrie, couche) ; **concept** = ce que l'utilisateur croit lire (« le zonage », « les permis ») quel que soit le chiffre ou la couche qui le porte.

---

## Ce que ce mandat ferme (et que CIRCUIT-1 laissait ouvert)

- CIRCUIT-1 a mis au registre les **chiffres**. La lettre de zone sur la parcelle, la classe d'aléa PPR, les lignes de transport, les points de permis, la couleur d'une couche sont restés « hors registre : géométries, textes ». Personne ne vérifie que la lettre de la fiche et la couleur de la couche PLU viennent de la même table au même millésime.
- Le registre accepte deux ids légitimes pour un concept (prix du secteur, prix de la commune, prix du neuf ; transport GTFS dans la fiche, TCSP OSM sur la couche). Il les montre, il ne tranche pas.
- La sonde compare des valeurs numériques. Elle ne sait pas dire « la fiche dit zone A, la couche peint U ».

---

## Autonomie

Mêmes règles que CIRCUIT-1 : aucune question à Vic, doutes tranchés par l'option la plus sûre et écrits dans « Décisions prises en autonomie », ce qui ne peut pas être fait est sauté et noté, branche jamais rouge (revert du lot fautif), push à chaque lot, reprise par « continue CIRCUIT-2 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-2.md ». Lecture seule autorisée sur `labuse-vps` avec les cinq commandes de CIRCUIT-1, rien d'autre.

**Règle qui tient tout l'édifice : la liste d'exceptions au registre reste vide sans l'accord de Vic.** Aucune donnée « en attendant », aucun `# TODO registre`. Si une donnée ne peut pas être déclarée, elle n'est pas affichée, et le compte-rendu dit pourquoi.

---

## Étape 0

1. `pwd` = `~/Desktop/labuse-audit`, arbre propre, sinon stop.
2. Branche `feat/circuit-2` (voir en-tête). Suite verte au départ, nombre de tests noté.
3. Lire `COMPTE-RENDU-CIRCUIT-1.md`, en particulier « Décisions prises en autonomie », « Non fait », et la liste des robinets `hors_registre` de `registre/robinets.py` : c'est le périmètre du lot 1.

---

## Règles

1. **Une donnée = un id = une source = un millésime = un chemin.** Vaut pour une lettre, une classe, une liste, une géométrie, une couche, comme pour un nombre.
2. **Un concept = une source canonique.** Deux sources pour un concept ne coexistent que nommées différemment à l'écran (« Transport public (OSM) », « Desserte GTFS ») ; jamais le même mot pour deux origines.
3. **Une couche est un robinet** : elle a un tampon (source, millésime, date de fabrication de ses tuiles ou de sa table matérialisée) et elle est sondée comme les autres.
4. **Un échec technique ne se déguise jamais en absence de donnée** (règle RETOURS-15) : trois états possibles pour une donnée non numérique — servie, « non déterminée » (la source ne dit pas), « non calculée » (la chaîne a échoué) — et le registre porte l'état.
5. Preuve, mesure sur témoins, test qui aurait attrapé, commit par lot, rien de mergé : comme CIRCUIT-1.

---

## Lot 1 — Le registre élargi

- 1.1 `registre/chiffres.py` devient `registre/donnees.py` (alias conservé pour ne rien casser) ; chaque donnée porte `type` ∈ {`nombre`, `classe`, `texte`, `liste`, `geometrie`, `couche`}, plus les champs de CIRCUIT-1 (définition, moteur ou passe-plat, réservoirs, portée, version). Une `classe` déclare son domaine (les valeurs possibles et leur source : zones PLU du GPU, classes DPE de l'arrêté, niveaux d'aléa du PPR). Une `couche` déclare sa table ou son tuilage, sa fabrication (`build-mvt`, `geom_simple`, vue) et sa portée.
- 1.2 **Vider la liste `hors_registre`** de CIRCUIT-1 : chaque entrée est soit déclarée (avec son type), soit reclassée « décor » avec la raison (un libellé statique, un pictogramme). Objectif : 0 donnée d'origine externe hors registre.
- 1.3 **Les 16 couches et les 10 fonds** : déclarés comme robinets de type `couche` et `fond` avec source, millésime, fabrication ; les fonds IGN déclarent le service et la version de tuiles interrogée (pas de sonde de contenu, une sonde de disponibilité).
- 1.4 **Tampon des données non numériques** : `Valeur` porte le type ; pour une classe ou une géométrie, le tampon porte la table, le millésime et, pour une couche, la date de fabrication. `?trace=1` le renvoie.
- 1.5 **Test de couverture élargi** : tout champ non numérique d'origine externe servi par un endpoint de `robinets.py` sans id échoue le test ; la liste d'exceptions est vide (règle d'autonomie).
- 1.6 **Un moteur nommé pour chaque chiffre** : à la fin de CIRCUIT-1, 43 chiffres restaient en `sql_propre` et 13 en `passe_plat` — un chemin unique, pas un moteur nommé. Chaque `sql_propre` est extraite dans `registre/moteurs/<domaine>.py` sous une fonction nommée ; les `passe_plat` restent des passe-plats mais déclarent la table et la colonne lues. Objectif : `calcul=sql_propre` = 0.
- 1.7 **Portée `projet`** (créée au lot 4-bis de CIRCUIT-1) : les saisies client (prix demandé, coût de construction, marge, démolition, VRD) sont des données du registre à portée `projet`, sans réservoir, tampon « saisi par le client le … », affichées en ambre (DA v3).
- 1.8 **Ids que les maquettes d'exports attendent** (compte-rendu de réconciliation exports du 05/09) : emprise bâtie, hauteur du bâti et nombre de bâtiments (BD TOPO + CoSIA), marge de surélévation à l'égout, surface vendable et surface de plancher (distinctes de `capacite_logements`), postes du bilan à rebours (chiffre d'affaires, coût de construction, VRD, démolition, marge, frais), sensibilité au coût de construction, écart au prix demandé, part des logements raccordés à l'égout (RP2022 EGOUL), nombre de ventes retenues / écartées du nuage (couverture visible). Les données réglementaires nouvelles (ER, EBC, DPU, PEB, zonage A/B/C) sont déclarées ici mais leurs réservoirs arrivent par CIRCUIT-3 lot 6.

Compte-rendu : nombre de données par type, robinets 100 % déclarés, exceptions = 0.

---

## Lot 2 — La fiche parcelle, donnée par donnée

Livrable `docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md`, généré par script depuis le registre (`labuse registre fiche parcelle`), puis relu à la main : pour chaque section-tiroir de la fiche parcelle et chaque donnée affichée dedans — id, type, libellé, source(s) et millésime, chemin (moteur ou passe-plat, fichier), portée, état possible, et **où ailleurs elle s'affiche** (couches, outils, fiche commune, PDF, Copilote, mails). Idem, plus court, pour la fiche commune, la fiche annonce, la fiche propriétaire, la fiche soleil (`FICHES-DONNEES.md`).

C'est le document que Vic lira. Il doit se lire sans le code : une ligne par donnée, en français.

---

## Lot 3 — Un concept, une source

- 3.0 **Deux moteurs à confirmer en tête** : `zone_servie` (zone d'une parcelle, ZONE-1) et `potentiel` (bloc au sol / en hauteur / table rase, EXPORTS-1) doivent être dans le registre depuis le lot 4-bis de CIRCUIT-1 ; s'ils n'y sont pas, c'est la première tâche de ce lot. `zone_servie` ≠ `zonage_commune` (parts communales) : deux concepts, deux noms.
- 3.1 **Inventaire des concepts** : CC dresse la liste des concepts que l'utilisateur lit (au moins : zonage PLU, règles de la zone, aléas et PPR, littoral et 50 pas, ZFANG, permis, logements engagés, prix (secteur / commune / neuf / affiché vs acté), SDP et résiduel, constructibilité, division, DPE, propriétaire et dirigeants, transport et TCSP, équipements, population, réseaux, solaire et toiture, occupation du sol, friches, QPV) et, pour chacun, toutes les données du registre qui le portent, avec leurs sources et chemins.
- 3.2 **Doublons de source** : pour chaque concept porté par ≥ 2 sources ou ≥ 2 chemins, `docs/CIRCUIT/CONCEPTS-CANONIQUES.md` — une ligne par concept : ce qui existe, la source canonique proposée, ce que deviennent les autres (`derivee`, `nommee_a_part`, `retiree`). Règle de défaut, appliquée tout de suite (autonomie) : la source canonique est celle que la fiche parcelle sert déjà par le moteur ; une seconde source légitime est **renommée à l'écran** avec son origine, jamais supprimée sans Vic. Exemple attendu : « Transport public (OSM) » sur la couche et « Desserte GTFS » dans l'étude de zone, ou fusion si les deux disent la même chose sur les témoins.
- 3.3 **Doublons de définition** : deux ids dont la définition est la même à l'arrondi près (mesuré sur les témoins) fusionnent ; deux ids différents pour un même libellé prennent deux libellés. Vic tranche plus tard depuis le tableau ; rien ne l'attend.

---

## Lot 4 — La sonde catégorielle

Extension du job `coherence-robinets` (CIRCUIT-1 lot 4), mêmes témoins (24 communes, 50 parcelles golden, clés zone / propriétaire / annonce) :

- 4.1 **Zonage** : lettre de zone de la fiche = zone de la couche PLU au centroïde = zone dans les 6 PDF = zone donnée par le Copilote. Sur les 50 parcelles, 0 écart attendu ; tout écart = ligne `circuit_ecarts` de type `classe`.
- 4.2 **Aléas** : niveau d'aléa de la fiche Pièges = couche PPR = Pièges et risques (outil) = PDF. Contrôle de distribution : les 484 zones « élevé / très élevé » ingérées en « moyen » (RETOURS-13) ne peuvent plus arriver sans qu'un écart de domaine apparaisse.
- 4.3 **Permis** : permis listés dans la fiche = points de la couche dans la parcelle = permis de l'outil Permis pour l'IDU ; un permis « localisation approximative » (RETOURS-14) n'est jamais un point sur une parcelle.
- 4.4 **Propriétaire, DPE, transport, équipements, réseaux, toiture** : même principe, fiche = couche = outil = PDF sur les témoins ; pour les lignes et arrêts, comparaison dans un rayon documenté.
- 4.5 **Géométries** : la parcelle de la fiche, celle de la carte et celle du PDF viennent de la même table cadastre au même millésime (tampon), et la table matérialisée `geom_simple` n'est jamais plus vieille que la source (sinon eau ancienne).
- 4.6 **Couches** : date de fabrication < millésime de la source ⇒ `circuit_eau_ancienne` avec le mécanisme (`build-mvt`, vue, cache).

Résultats dans les mêmes tables que CIRCUIT-1 ; la page affiche les écarts de type `classe` et `geometrie` comme les autres.

---

## Lot 5 — Page et traçage

- 5.1 La fiche du bas d'un robinet liste toutes ses données, par type, avec leur tampon ; une couche montre sa date de fabrication et son millésime.
- 5.2 Le traçage (CIRCUIT-1 lot 7) s'étend aux classes et textes : la lettre de zone, la classe DPE, le niveau d'aléa portent l'étiquette et ouvrent le tiroir. Sur la carte, le `i` d'une couche (déjà en français) affiche source, millésime, fabrication — c'est le traçage côté client, sobre, sans identifiant technique.
- 5.3 Les pastilles du bandeau comptent aussi les écarts de type `classe` et `geometrie`.

---

## Lot 6 — Les exports sur le registre

Les builders PDF (Dossier = Flash, PDF résumé, Financier, Apporteur, Pré-dossier PC — architecture tranchée le 04/09) ne gardent aucune requête propre : ils reçoivent des objets `Valeur` du registre pour toutes les données, y compris classes et géométries (cartes des PDF construites depuis les mêmes couches, même millésime). Le prix du neuf y est `prix_neuf_observe_eur_m2` (arbitrage Q3), jamais l'id VEFA à l'acte réservé au scoring. Le redessin des PDF vit dans le chantier EXPORTS, pas ici : ce lot ne change pas la mise en page, il change l'origine de chaque donnée. Si une branche EXPORTS est ouverte en parallèle, CC se limite à exposer l'API registre nécessaire et à sonder les PDF, et le note.

---

## Livrables

```
docs/CIRCUIT/MANDAT-CIRCUIT-2.md · COMPTE-RENDU-CIRCUIT-2.md
docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md · FICHES-DONNEES.md · CONCEPTS-CANONIQUES.md
src/labuse/registre/donnees.py (types, domaines, couches, fonds), tampons non numériques, ?trace=1 élargi
job coherence-robinets étendu (classe, géométrie, couche) · circuit_ecarts.type
frontend : fiche du bas par type, traçage des classes, i des couches
tests : couverture élargie (exceptions = 0), sonde catégorielle sur témoins, couches non périmées
```

## Définition de fini

- 0 donnée d'origine externe hors registre ; liste d'exceptions vide.
- `FICHE-PARCELLE-DONNEES.md` couvre chaque donnée de chaque tiroir, sans trou marqué « ? ».
- `CONCEPTS-CANONIQUES.md` : un canonique par concept, les doublons renommés ou fusionnés, rien de supprimé sans Vic.
- Sonde catégorielle : 0 écart sur les témoins, ou écarts listés avec cause et commit.
- Suite verte, au moins autant de tests qu'au départ, rien mergé.

## Ce qui reste à Vic, après

Lire `FICHE-PARCELLE-DONNEES.md` et `CONCEPTS-CANONIQUES.md`, corriger un choix canonique s'il ne lui va pas (depuis la page ou par un mot), merger 1 puis 2.

## Interdits

Ceux de CIRCUIT-1, plus : aucune source supprimée, aucun libellé identique pour deux origines, aucune donnée affichée hors registre même « en attendant ».
