# RECETTE-11 — LiDAR sur toute l'île, Financier débloqué, restes de RECETTE-10

Branche `fix/recette-11` depuis `fix/recette-10` · worktree `~/Desktop/labuse-recette6`.
**Règle de preuve** : un travail n'est fait que prouvé sur l'artefact final (PDF régénéré ou capture
depuis le vrai chemin). Aucun merge, aucune bascule ; `:8020`/`q_v14` intouchés ; seule ingestion permise
= le LiDAR (lot A). Artefacts : `docs/audit-2026-09/captures-recette-11/`.

**Suite** : vitest 207/207 · tsc 0 · pytest ciblé 214 passed (8 skipped data-absente) · provenance 11/11 ·
1 fail **PRÉ-EXISTANT** `exports2_lot6::test_confidentiel_non_mandat_et_emission` (prouvé identique sur le
code committé, avant mes changements — titre `is_bati`, hors périmètre).

---

## Lot A — LiDAR HD par dalles sur toute l'île

**A1 — ingestion par dalles. FAIT.** Nouveau module `faisabilite/hauteur_lidar_dalles.py` + batch
`scripts/_recette11_lidar_dalles.py`. Une seule méthode pour les 24 communes (Saint-Denis compris) :
pour chaque dalle 1 km de la grille IGN, on télécharge MNS+MNT EN LOCAL (fichiers temporaires), on mesure
faîtage (p99) / égout (p25) de toutes les parcelles bâties de la dalle, on écrit dans
`batiment_hauteur_lidar` **commune par commune**, on SUPPRIME les fichiers. Plus aucune requête par
parcelle. Reprenable (état par dalle dans `lidar_dalle_grille.fait_le` : relancer saute les dalles finies).
Table autonome (un `pg_dump` de `batiment_hauteur_lidar` suffit à la porter au VPS). Arrêt seulement sur
disque < 3 Go ou 25 échecs consécutifs — jamais la durée.
- **Vérification (redonne-t-il les valeurs déjà mesurées ?)** `scripts/_recette11_a1_valide.py`, 50
  bâtiments de Saint-Denis, méthode par dalle vs méthode par parcelle (RECETTE-8 W23). **Tolérance
  écrite : ±0,5 m** (le rendu arrondit au 0,1 m). **Écart constaté : 50/50 dans la tolérance**, faîtage
  Δ médian 0,10 m / max 0,40 m, égout Δ médian 0,00 m / max 0,30 m — le reliquat vient seulement de la
  grille native vs la grille recentrée du fetch par parcelle.
- **Arbitrage (couche).** J'ai d'abord testé le produit MNH d'IGN (hauteur toute prête, **1 seul**
  téléchargement au lieu de 2) : il DIVERGE de la méthode servie sur terrain pentu (médian 0,4 m,
  extrêmes > 20 m — le MNS/MNT « HIGHRES » recale mal sur les pentes). **Rejeté** au profit des MÊMES
  couches que la méthode validée (`…HIGHRES.MNS` − `…HIGHRES`) pour ne pas changer les valeurs sous les
  pieds du client. Documenté dans le module.
- **Place disque** vérifiée (28 Go libres au départ, ~32 Mo/dalle supprimés après lecture → empreinte
  quasi nulle). **rasterio ne dépend pas de DYLD** (vérifié) → le batch tourne sous `nohup` sans DYLD.

**A2 — date de survol. FAIT.** Chaque mesure porte la date de survol de sa dalle, **lue dans les
métadonnées IGN** (`IGNF_LIDAR-HD_METADONNEE:metadata`, WFS Géoplateforme : `date_debut_acquisition` /
`date_fin_acquisition` par dalle), jamais supposée. **Dates rencontrées sur l'île** : mission unique
`23LHDREUNION`, **survol août–septembre 2023** (2 665 dalles) ; la date de FIN varie par dalle du
11/08/2023 au 23/09/2023 (143 couples debut/fin distincts) — donc NON uniforme au jour près, mais une
seule campagne. Affichée en « mois année » (`hauteur_lidar.survol_libelle`).

**A3 — la date s'affiche avec la mesure, partout. FAIT.** Servie depuis `hauteur_lidar_servie` →
`hauteur_batie` → `api/app._potentiel_transformation_block` (`hauteur_survol`). Rendu : fiche « Le bien »
(`leBien.tsx`, source « LiDAR HD (mesuré, survol de septembre 2023) »), fiche « Marge en hauteur »
(`constructibilite.tsx`), **Apporteur** (« 7,0 m au faîtage (mesuré au LiDAR HD, survol de septembre
2023) » — **plus d'« environ » devant une valeur mesurée**), **Dossier §3** (« 7,0 m au faîtage · 3,0 m à
l'égout — mesuré au LiDAR HD, survol de septembre 2023 »). **LiDAR HD cité dans les sources du §3 (note)
ET du §10** (« LiDAR HD (MNS) — hauteurs mesurées · IGN / Géoplateforme (survol de septembre 2023) ») — il
n'y était pas. Preuve : `A-D6-dossier-EL0157.pdf`, `A-D2-D7-apporteur-EL0157.pdf`. Faisabilité/Densifier
n'affichent PAS de hauteur mesurée (ils montrent la hauteur RÈGLE/gabarit PLU, pas une mesure — Densifier
a même retiré la surélévation en OUTILS-FIX-1) → rien à dater là (arbitrage).

**A4 — permis postérieur au survol. FAIT.** Si un permis autorisé sur la parcelle est daté **après la
date de survol** (comparaison à la date de survol, jamais à « permis récent »), la mesure le dit :
« mesure antérieure au permis du [date] — possiblement dépassée ». Servi (`hauteur_permis_posterieur`,
`p_model_permits`), rendu fiche + Apporteur + §3. **680 parcelles concernées** sur l'île. Preuve :
`A4-dossier-AH1057.pdf` — « 6,5 m au faîtage · 2,1 m à l'égout (mesuré au LiDAR HD, survol de septembre
2023 — mesure antérieure au permis du 31/07/2026, possiblement dépassée) ». Test `test_a4_*` (deux sens).

**A5 — sentinelle. FAIT.** La veille LiDAR HD ne regarde plus le jeu data.gouv **national**
(`mnh-lidar-hd`, qui bouge pour n'importe quelle republication en France), mais le **canal réellement
ingéré** — la grille de dalles (WFS metadata IGN) **bornée à l'emprise Réunion**, en `temoin` sur la
dernière édition (`COUNT=1&SORTBY=date_edition D`) : une nouvelle campagne ou re-diffusion sur le 974
bouge cette date → « la donnée amont a changé ». **URL réellement appelée** (probe via la couche `urllib`
de prod : baseline `ok` vu `2025-03-13`, changement simulé → `nouvelle_version`). Test `test_a5_*`.

**A6 🔴 — le verdict de surélévation retiré partout. FAIT (critère de non-merge de RECETTE-10).** Plus
aucun « Surélévation possible / non identifiée / pas de marge / à confirmer » : la phrase s'arrête aux
hauteurs mesurées, à la règle, à la marge et à la contrainte qui mord — le lecteur conclut. Corrigé dans
`exports/blocs/potentiel.py` (§3), `faisabilite/potentiel.py` (phrase du bloc), `api/pdf_premium.py`,
`frontend/constructibilite.tsx`. « surélévation possible » et « non identifiée » ajoutés aux **mots
interdits du test doré** (garde désormais INSENSIBLE À LA CASSE — attrape un « Surélévation possible »
capitalisé réintroduit). Preuve : Dossier EL0157 régénéré, §3 = « **3,0 m sous la hauteur réglementaire,
contrainte qui mord : le faîtage** (mesuré au LiDAR HD…). égout 3,0 m mesuré contre 7,0 m réglementaires
(marge 4,0 m) · faîtage 7,0 m mesuré contre 10,0 m réglementaires (marge 3,0 m). » — **0/8 mots interdits**
sur l'artefact. Test `test_a6_*`.

---

## Lot B — Financier

**B1 — la cause. FAIT.** Reproduit sur la saisie enregistrée d'`EL0157` : bailleur **5 500** > libre
**4 500** (saisie de la garde de RECETTE-10, cachée sous « Affiner ») → chaque export retombe sur la garde.
Confirmé : ce n'est pas un cache, c'est la saisie persistée.

**B2 — la garde vit dans le questionnaire, pas dans le PDF. FAIT.** Point de vérité unique
(`financier_bilan._hors_marche`) exposé par `POST /financier/{idu}/questionnaire/valider`
(`financier_questionnaire.valider_hors_marche`). Le front (`FinancierQuestionnaire.tsx`) l'appelle sur
« Continuer » ET « Enregistrer » : une saisie hors marché **bloque**, **saute à l'écran** concerné,
**ouvre l'accordéon** « Affiner » quand le champ y est replié, **surligne** le champ (bord rouge + message).
Défense : hors marché → le PDF est **REFUSÉ (422)**, plus jamais un PDF « bilan non établi ». Preuve sur
`EL0157` : bailleur 5 500 → **refusé, aucun PDF** (`B2-hors-marche-refuse.txt`) ; garde `écran 3`,
`affiner=True`, champ « Prix de vente au bailleur social ». Tests `test_b2_*`.

**B3 — rien de caché. FAIT.** En-tête « Affiner » : « **N modifiée(s)** ». Chaque champ modifié propose
« **↺ Revenir à la valeur sourcée** ». L'encart PDF « Hypothèses du porteur » liste désormais **TOUS les
champs du bilan (19), y compris ceux d'« Affiner »** (bailleur, part sociale, régime TVA, honoraires, VRD,
stationnement, aléas, taxe, frais d'acq., dépollution, portage, taux d'emprunt…). Test `test_b3_*`.

**B4 — pré-remplissage honnête. FAIT (par conception, vérifié).** `qf.prefill` n'émet **que des valeurs
sourcées** (chaque prefill porte sa source, montrée sous le champ) ; une valeur sans source n'est pas
pré-remplie. **Arbitrage cohérence** : ni le prix libre ni le prix bailleur ne sont pré-remplis — un
défaut bailleur ne peut être cohérent avec un prix libre inconnu ; la cohérence *bailleur < libre* est
donc **assurée par la garde B2**, pas par un défaut fixe. Test `test_b4_*`.

**Preuve B (moteur + PDF sur EL0157).** bailleur 5 500 → refusé (aucun PDF) · bailleur 3 800 < 4 500 →
**bilan établi** (`B-bilan-etabli-bailleur3800.pdf`) · prix de sortie 4 500 → charge **−197 771 €**,
prix 5 000 → charge **+13 105 €** (chiffres différents). Compte de test isolé, **purgé** après génération.

---

## Lot C — pagination des segments de l'Analyse LABUSE

**C1 — la règle 200 aux segments. FAIT.** Le « 2 sur 5 affichées » venait de segments filtrant la
**fenêtre globale** du listing (`shown`, 200) au lieu de leur propre liste — un petit segment était
tronqué par la fenêtre du listing entier. Correctif à la source : chaque segment (composant partagé
`SegmentList`, `ResultsSection.tsx`) filtre la liste **complète** et pagine par la règle 200 PARTAGÉE
(`usePagination` + `ListPaginationFooter`). Sous 200 : tout s'affiche, **aucun « charger plus »** ;
au-delà : 200 puis « Voir 200 de plus ». En mode île, le « charger plus » serveur n'apparaît que fenêtre
client épuisée ET serveur non épuisé (prédicat pur `segmentOffreChargerPlus`). **Test** `SegmentPagination.test.tsx`
(échoue si un segment < 200 propose de charger plus ; > 200 → « Voir 200 de plus »). Preuve = vitest vert
(le verrou est à la source, déterministe).

---

## Lot D — Dossier et Apporteur (relecture des PDF de EL0157)

**D1. FAIT.** §5 : le compte de permis écrit sa **maille** et sa **fenêtre** — « 19 permis autorisés sur
la **section cadastrale, sur les 36 derniers mois** » (constantes réelles servies par le bloc dépôts).
*Arbitrage* : le mandat évoquait « 500 m · 24 mois » ; le nombre du §5 est en fait le compte de la
**section cadastrale sur 36 mois** (`depots.secteur`, `DEPOTS_FENETRE_MOIS`). Plutôt que de changer
silencieusement la métrique (et le nombre), j'ai rendu la vraie définition EXPLICITE (maille + fenêtre) ;
basculer sur le profil 500 m/24 mois serait un changement de source à décider par Vic.

**D2. FAIT.** Le TYPE de bien s'imprime avec le prix partout — Apporteur « ancien **appartement** 2 903
€/m² ». Et le Dossier §5 **dit pourquoi** : « le prix « ancien {type} » est la référence de revente du
secteur pour ce type (segment le plus représenté à proximité), utilisée comme prix de sortie du programme
reconstruit — pas une estimation du bâti existant ». *Arbitrage* : la règle n'est **pas** fausse — une
parcelle de trois maisons se reconstruit en collectif, l'appartement est le comparable de sortie (segment
`sector_price` à rayon adaptatif). Rien à corriger dans le moteur, seulement à expliquer.

**D3. FAIT.** FRR « en partie » (les Hauts, infra-communale) : LABUSE connaît la position de la parcelle
(couche `spatial_layers` kind='frr') → TRANCHE « **Parcelle DANS / HORS** la zone spéciale d'action
rurale », « **non déterminé** » si le périmètre manque. Plus « dépend de la localisation exacte du
terrain ». Preuve EL0157 : « **Parcelle DANS la zone spéciale d'action rurale (les Hauts)** ». Test `test_d3_*`.

**D4. FAIT.** « **pleine terre — non réglementé, Art. Um.13** » (article cité → lecture SOURCÉE du PLU) et
le **taux de taxe d'aménagement** (source publique DGFiP/DELTA) passent de `estimé` à **`sourcé`**.
Preuve EL0157 : les deux lignes portent la pastille `sourcé`. Test `test_d4_*`.

**D5. FAIT.** Assainissement : quand la donnée vient de l'**INSEE à la maille IRIS**, c'est un fait de
**QUARTIER chiffré** — label « Assainissement (quartier) », valeur « 82 % des logements du secteur ne sont
pas raccordés au réseau collectif ». Le **zonage GPU** (cas d'EL0157), lui, reste un fait de **parcelle**
(« non collectif », sourcé) — c'est bien une donnée parcellaire, pas IRIS (arbitrage vérifié : la source
d'EL0157 est le GPU, pas l'INSEE).

**D6. FAIT.** Ajoutés au test doré : `rpls_sdes`, « « latest » ingérée », « année non pinnée », « propre
non public », `RPG.LATEST`, `[2022, 2025]`. Ces marqueurs **fuyaient réellement** dans le Dossier (§10
sources, §5 tendance, §1/§8 pieds) : nettoyés au **producteur unique du millésime**
(`millesime_source.composer`) + fournisseur, période rendue « **2022–2025** » (plus de repr de liste
Python), `rpls_sdes` nommé (« RPLS — logements locatifs sociaux »). Le catalogue `data_sources` partagé
n'est PAS modifié (nettoyage au bord de lecture). **0/8 marqueurs** sur le Dossier EL0157 régénéré.

**D7. FAIT.** Apporteur : (a) « Ce qui gêne » reprend la description du §4 — le **mouvement de terrain
revient** (« Zone bleue PPR inondation et mouvement de terrain », plus seulement « Inondation »). (b)
L'**ICPE** n'est signalée que si la **cascade la relève** (même moteur que le Dossier), fin du **faux
positif** qui déclenchait sur le simple mot « ICPE » du catalogue de sources ; sur EL0157 (ICPE la plus
proche à 760 m, cascade PASS) → **aucun des deux documents** ne la signale. *Arbitrage distance* : la
distance exacte reste dans l'analyse de risques du Dossier — l'imprimer au brief comme nombre nu casserait
le verrou de provenance (tout nombre imprimé doit être adossé au registre) ; le brief signale la présence,
l'apporteur vérifie sur place. (c) « **Cinq** vues : depuis la voie, puis aux quatre coins » (était
« Quatre » pour 1+4=5). (d) **4 « L'ESSENTIEL »** = maquette-apporteur-v3.html (Contact, Prix, Bail,
Voisines) — **vérifié 4=4**, déjà aligné. Preuve : `A-D2-D7-apporteur-EL0157.pdf`. Test `test_d7_*`.

---

## État du batch LiDAR (fin de session)

Lancé en arrière-plan (`nohup`), nom de processus contenant `lidar_dalles`. Instantané en fin de session :
- **~470 / 2 665 dalles traitées** (~385 avec bâti) · **~78 000 parcelles mesurées par dalle** · ~9,5 s/dalle.
- Table `batiment_hauteur_lidar` : **80 905 lignes, 80 905 avec date de survol** (backfill initial des
  mesures RECETTE-10 + écritures par dalle → **aucune mesure sans date**, garantie du critère A3).
- Communes déjà couvertes par dalle : Saint-Paul, Saint-Leu, La Possession, Le Port, Les Avirons,
  L'Étang-Salé, Les Trois-Bassins, Saint-Denis (+ tout l'Ouest ; le balayage suit la grille d'Ouest en Est).
- **Restantes ≈ 2 200 dalles** (dont beaucoup sans bâti → sautées vite). Disque libre 26 Go (stable).
  Quelques dalles isolées en `400 Bad Request` du WMS (bbox refusée) : non marquées finies → **reprises**
  au prochain lancement, aucun impact sur le reste.
- **Reprise / relance** : `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src nohup python
  scripts/_recette11_lidar_dalles.py > /tmp/lidar_dalles.log 2>&1 &` (saute les dalles `fait_le` renseignées).
- **Suivi de l'avancement** :
  ```
  tail -f /tmp/lidar_dalles.log
  # ou en SQL :
  SELECT count(*) FILTER (WHERE fait_le IS NOT NULL) faites, count(*) total FROM lidar_dalle_grille;
  SELECT count(*) FROM batiment_hauteur_lidar WHERE methode='dalle';
  ```

Le batch va au bout tout seul (reprenable, borné par disque/échecs, pas par la durée) ; il peut tourner
plusieurs heures encore. Toutes les parcelles servies portent déjà leur date de survol.

---

**Non-merge levé** : aucun verdict de surélévation ne subsiste (A6, prouvé 0/8 mots interdits), aucune
mesure LiDAR ne s'affiche sans date (A3, 80 905/80 905), le Financier ne produit plus de PDF quand la garde
mord (B2, prouvé 422 sur EL0157). **« Ne merge pas. »**
