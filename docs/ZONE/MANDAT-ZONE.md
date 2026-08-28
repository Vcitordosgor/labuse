# MANDAT — ÉTUDE DE ZONE : UN MOTEUR, DEUX VISAGES
Régime AUTONOME. Commits par lot (Z1→Z5). RÈGLES COMMUNES. Findings ZN-001→.
**Référence : docs/ZONE/maquette-zone-v1.html** (validée par Vic). Structure, hiérarchie, wording : fidèle.
**L'enquête Z0 est FAITE — lis docs/ZONE/RAPPORT-Z0.md avant tout et pars de ses conclusions.** Elle établit ce qui existe déjà (BPE, équipements OSM, GTFS, Filosofi carreaux 200 m, IRIS, parcel_amenites, DVF, voisinage_proche, BAN) et ce qui manque réellement : isochrones, SIRENE établissements géolocalisés, MOBPRO, et le moteur d'agrégation.
Honnêtetés non négociables : chaque chiffre sourcé et daté · revenus étiquetés ESTIMÉ · temps « hors trafic » affiché · **AUCUNE prévision de chiffre d'affaires, aucun score, aucune note d'attractivité**, jamais.

## Z1 — INGÉRER CE QUI MANQUE (et rien d'autre)
Trois sources seulement, CLI rejouables, registre des sources mis à jour avec millésime :
- **SIRENE établissements actifs géolocalisés**, périmètre 974 : code NAF, dénomination/enseigne, adresse, coordonnées. **Statut de diffusion respecté** : les unités en diffusion partielle (personnes physiques opposées) ne sont NI stockées en clair NI affichées — obligation légale, prouvée par test. Attention : le SIRENE déjà présent enrichit les propriétaires par SIREN, ce n'est PAS un annuaire d'établissements adressés — c'est une table distincte.
- **MOBPRO** (mobilités domicile-travail), mailles communes du 974.
- Rien d'autre. Filosofi, BPE, OSM, GTFS existent : tu les réutilises tels quels.

## Z2 — LE MOTEUR DE ZONE
- **Isochrones via l'API IGN Géoplateforme** (à pied / voiture, 5 à 15 min). CACHE obligatoire (une zone demandée deux fois ne rappelle pas l'API). Échec API → dégradé honnête et nommé, JAMAIS un cercle substitué en silence. La mention « hors trafic » accompagne chaque temps affiché.
- **Entrées** : parcelle (IDU), adresse (BAN), ou polygone (le back du dessin de zone conservé en R8 — réutilise-le).
- **Agrégateur** : pour un polygone donné, chaque couche se compte dedans — carreaux Filosofi (règle d'inclusion documentée, ex. centroïde dans la zone), établissements SIRENE par NAF, équipements BPE/OSM **dédupliqués entre les deux sources** (règle écrite au rapport), DVF, annonces Radar, permis. Les « plus proches » portent leur **temps de trajet**, pas leur distance en mètres.
- **UN SEUL POINT DE CALCUL pour Filosofi** (finding Z0 le plus important) : la fiche sert déjà du revenu au centroïde via marche_secteur.filosofi_200m. Il ne doit JAMAIS y avoir deux « revenus de secteur » divergents à l'écran. Soit tu réutilises ce point de calcul, soit tu l'unifies — dis ton choix et prouve qu'aucun écran n'affiche deux valeurs contradictoires.
- Carreaux imputés → chiffre étiqueté ESTIMÉ. Zone sans population (océan, hauts) → « zone inhabitée », digne, pas un zéro brut ni un crash.

## Z3 — LE BLOC FICHE « AUTOUR DE CETTE PARCELLE » (maquette, écran 1)
- Tiroir de la fiche parcelle, automatique, sans réglage. Segmenté « À pied · 15 min / Voiture · 5 min ».
- Quatre stats de population (habitants, ménages, revenu médian ESTIMÉ, part des moins de 25 ans) + équipements et commerces les plus proches AVEC leur temps.
- **Zéro doublon** (décision 02 de la maquette) : les ventes DVF, transports et réseaux restent dans leurs tiroirs existants (« Marché et secteur », « Réseaux et accès », bloc proximités) — le bloc porte le renvoi de la maquette, pas une copie. Le bloc « proximités » actuel en mètres : soit tu le convertis en temps, soit tu l'absorbes — pas deux blocs qui disent la même chose autrement. Dis ton choix.
- L'isochrone se dessine sur la carte existante (module-extra, comme le Radar — pas une carte parallèle), retiré à la fermeture.

## Z4 — L'OUTIL « ÉTUDE DE ZONE » (maquette, écran 2)
- Menu Outils. **Entrée = recherche IDU + adresse** (réutilise le composant de la barre principale). Un IDU centre sur la parcelle, une adresse sur le point BAN. Le polygone dessiné est la troisième entrée.
- Activité : liste NAF avec recherche par libellé français (« boulangerie » trouve 1071C — table de correspondance extensible).
- Temps 5/10/15 min, voiture / à pied. Isochrones concentriques sur la carte, concurrents en pins ambre.
- Résultats conformes à la maquette : population de la zone · concurrents listés avec leur temps (+ « N habitants par concurrent ») · générateurs de flux (écoles, gares, marchés — BPE/GTFS) · marché immobilier de la zone (ventes DVF, médian €/m², annonces Radar actives, permis).

## Z5 — RAPPORT ET RECETTE
- Export PDF depuis l'outil, mise en page de la maquette (écran 3). Utilise la chaîne PDF existante si elle s'y prête ; sinon endpoint JSON complet prêt à consommer + finding pour labuse-pdf (dépôt séparé, tu n'y touches pas).
- **Parcours /flash** : ajoute la recherche par adresse à côté de l'IDU (un commerçant a une adresse, pas un IDU). L'intégration de la section au PDF Flash = mandat suivant, note-le.
- Recette : parcelle de centre-ville (Saint-André), parcelle des hauts, une adresse, un polygone. Deux activités au moins. Cas limites : zone océan/inhabitée · carreaux imputés (ESTIMÉ visible) · échec API IGN (dégradé honnête) · NAF sans concurrent (digne) · adresse introuvable.
- Mobile 390 : bloc fiche et outil utilisables — dis ton choix. [ZONE-TEST] purgés (vérifié SQL). Captures 390 + 1440, nombre annoncé.

## FIN
Critères : maquette respectée · aucune couche ré-ingérée en double · statut de diffusion SIRENE respecté (prouvé par test) · un seul point de calcul Filosofi (prouvé) · ESTIMÉ sur tout chiffre issu de carreaux imputés · « hors trafic » sur tous les temps · aucune prévision de CA ni score nulle part · cache isochrones effectif (prouvé) · sources au registre avec millésimes · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · [ZONE-TEST] purgés.
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/etude-zone). Tu ne merges pas.
