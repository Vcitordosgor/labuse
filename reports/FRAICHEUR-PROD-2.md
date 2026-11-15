# FRAICHEUR-PROD-2 — la fraîcheur de bout en bout, lue sur la prod

**Mandat** : pour chaque donnée que le client lit, savoir si c'est la dernière disponible, et sinon
de combien elle retarde et où cela se voit. **Lecture seule stricte** : aucune écriture serveur,
aucun job lancé, aucun cron modifié, aucune table touchée, aucun cache vidé.
**Quand** : samedi 15/11/2026, 05 h 30 → 07 h (heure Réunion) — hors fenêtre sauvegarde (13 h 30–14 h)
et hors fenêtre de nuit (1 h–3 h 30). **Où** : prod `labuse-vps` (ssh, `psql` en lecture,
`statement_timeout` posé), sites des producteurs lus le jour même, code de la branche déployée
`ops/deploy-groupe-3` (worktree `~/Desktop/labuse-deploy3`, arbre propre, tête `af471f99b`).
**Livrables** : ce rapport + `reports/FRAICHEUR-PROD-2.csv` (les trois colonnes pour les 99 sources servies).

---

## Page 1 — ce qu'il faut savoir, en français simple

**Ce qui est à jour.** L'essentiel du socle l'est : le cadastre (dernier millésime Etalab
septembre 2026, ingéré 11/10), le bâti BD TOPO (édition du 15/09, ingérée 26/09), les hauteurs
LiDAR (aucun nouveau survol de la Réunion n'existe), les risques Géorisques/DEAL (témoins
inchangés), le DPE (le dernier DPE publié par l'ADEME pour la Réunion date du 23/09 — la prod
l'a), le BODACC (J-2, cycle normal), les taxes (taux d'aménagement 2026 et REI 2025 = derniers
publiés), SIRENE, les loyers DHUP, le zonage ABC, BPE, RPLS, OCS GE, BD ORTHO. Côté PLU,
19 communes sur 21 servies sont identiques au Géoportail de l'urbanisme (détail § A.2).

**Ce qui retarde, et de combien.**
0. **Le PLU de deux communes, dont Saint-Denis.** Le GPU sert pour **Saint-Denis** une version
   approuvée le **05/08/2026** (publiée au GPU le 24/08) — la prod sert celle du 23/04/2026,
   désormais archivée. Pour **La Possession**, le GPU sert la modification simplifiée n° 2
   approuvée le **25/06/2026** (application d'un jugement du TA, publiée le 29/10) — la prod
   sert la version du 17/12/2025. Et la sonde GPU n'a rien vu (témoin à « 0 », `sync-gpu` du
   15/11 : 0,2 s). C'est le seul retard de cette page que **le système ne détecte pas**.
1. **Les ventes (DVF) : 6 mois de retard.** Le fichier `full-2026-s1` (ventes jusqu'au
   30/06/2026) est publié depuis le 20/10. La prod sert des ventes arrêtées au **31/12/2025**.
   Partout où le client lit un prix (Estimer, Étude de zone, Comparer, fiche commune, PDF),
   il lit « aucune vente 2026 » (vérifié : 0 mutation 2026 en base). Le système **le sait** :
   le contrôle nocturne le signale chaque nuit depuis le 12/11, l'incident est ouvert, et la
   recharge partira au prochain cron hebdo (mardi 17/11) — le code de lecture du nouveau format
   Etalab est déployé.
2. **Les permis (SITADEL) : 1 mois.** Publié jusqu'au 30/09, servi jusqu'au **31/08**. L'outil
   Permis « Autorisés depuis 90 jours » ne montre en réalité que la fin août (145 permis, zéro
   depuis le 1ᵉʳ septembre). Signalé chaque nuit depuis le 12/11 ; le cron mensuel (le 10) n'a
   jamais tourné depuis sa pose du 13/11 — prochain créneau **10/12** sauf relance manuelle.
3. **Les dirigeants (INPI RNE) : ~4 stocks mensuels.** Le stock servi date du **05/07**. L'outil
   Successions calcule âges et gérants sur cette photo ; 5 sociétés passées en procédure
   collective depuis septembre y figurent avec leurs dirigeants d'avant. Cron mensuel (le 6)
   jamais tourné depuis sa pose — prochain créneau **06/12**.
4. **Les propriétaires personnes morales : le millésime 2026 attend.** La DGFiP a publié le
   04/11 la situation au 01/01/2026 ; la prod sert celle au 01/01/2025. Même chose pour la
   filiation **DFI** (situation d'octobre publiée le 04/11, servie : 19/06).
5. **Le classement : figé au 21/10.** Le run servi q_v20 a été calculé le 21/10 et promu le
   27/10. Le calcul de nuit est **gelé depuis le 13/11 sur ordre de Vic** (risque OOM + il fait
   s'abstenir le banc de cohérence) ; avant le gel il échouait (q_v23 ne classe que 64 % des
   parcelles, q_v24 tué au bout de 2 h). Toute évolution de terrain depuis le 21/10 (zonage,
   bâti, permis) n'est **pas** dans le rang que lit le client.
6. **Retards secondaires** : BAN (~3 mois, autocomplétion d'adresses), fibre Arcep (T1 servi,
   T2 publié), conso ENAF (édition 2011-2025 publiée, servie 2021-2024), RNB (~2 mois),
   contours IRIS (géographie 2024 servie, 2026 publiée), GTFS (2 réseaux sur 7), loyers OLL
   (2024 servi, 2025 publié le 27/10), QPV (génération outre-mer 2025 applicable, 2024 servie),
   et le **RP2023 de l'INSEE, paru aujourd'hui même** (15/11) — la bascule paramétrée existe.
7. **Blocs fonciers : construits le 07/09**, avant le cadastre du 11/10 et sur les propriétaires
   2025 — l'Assemblage lit un état de septembre.

**Ce qui ne tourne pas.**
- `calcul-nuit` : **gelé volontairement** (13/11, commentaire dans le crontab). Conséquence :
  le point 5.
- `purge-runs` : gelé (MENAGE-1) — assumé.
- `radar-cloche` et `digest` : gelés (notifications OFF) — assumé.
- `ingest-sitadel` (le 10) et `ingest-inpi-rne` (le 6) : posés au crontab du 13/11, **jamais
  encore exécutés** ; leurs créneaux sont passés avant la pose. Les incidents « jamais réussi /
  en retard » sont ouverts et escaladés — mais la prochaine exécution automatique est à ~1 mois.
- `verite-permanente` : échec le 14/11 (harnais F = accessibilité axe-core, pas un sujet de
  données).
- La **surveillance, elle, tourne et dit vrai** : sonde des sources chaque matin (07 h 00),
  contrôle de fraîcheur chaque matin (07 h 50) — il remonte exactement « 2 retards : DVF,
  SITADEL » chaque nuit depuis le 12/11, les incidents s'ouvrent, s'escaladent et partent en
  mail. Ces retards-là ne sont pas invisibles ; ils attendent leurs crons. L'exception est le
  PLU (point 0) : ce retard-là, la sonde ne le voit pas.

**En une phrase** : les trois gros retards de flux (ventes, permis, dirigeants) sont détectés
et affichés par le système lui-même — mais deux n'ont leur prochaine exécution automatique
qu'en décembre, le classement restera du 21/10 tant que le calcul de nuit reste gelé, et le
seul retard **invisible** du système est le PLU de Saint-Denis et de La Possession, que la
sonde GPU ne voit pas.

---

## LOT A — les sources, en trois colonnes

Le détail complet des 99 sources servies (+ hub/interne) est dans `reports/FRAICHEUR-PROD-2.csv` :
col. 1 = dernière version chez le producteur **lue le 15/11** (30 sources vérifiées une à une sur
le site du producteur ; les autres : dernière lecture de la sonde, 13/11), col. 2 = contenu prod
(millésime, horizon, dernière ingestion), col. 3 = où le client le voit. Ici : ce qui nourrit un
verdict ou un calcul.

### A.1 Synthèse des sources à verdict

| Source | Producteur (15/11) | Prod | Client | Verdict |
|---|---|---|---|---|
| **Cadastre** | Etalab millésime 01/09/2026 ; PCI Express D974 juin 2026 | « latest » ingéré 11/10 | fiche, carte, tous calculs — aucun millésime à l'écran (M70), PDF § Sources | **à jour** |
| **PLU 24 communes** | GPU lu commune par commune (§ A.2) | zones (13-27/10) + règlements extraits (07/08) | fiche, Analyse, Étude, pièces PDF | **en retard sur 2 communes** (Saint-Denis, La Possession) — non détecté par la sonde |
| **PPR / aléas** | témoins DEAL/Géorisques inchangés 13/11 | passes 09/2026 | fiche risques, documents | **à jour** |
| **Ventes DVF** | `full-2026-s1` (→ 30/06/2026) publié 20/10 | max(date_mutation)=**31/12/2025**, 102 551 mutations | Estimer, Étude de zone, Comparer, fiche commune, PDF « DVF — 31/12/2025 » | **en retard de 6 mois** — détecté, recharge mardi 17/11 |
| **Permis SITADEL** | couverture → 30/09/2026 | max(date)=**31/08/2026**, 50 810 | outil Permis, veille, PDF | **en retard de 1 mois** — détecté, cron au 10/12 |
| **Bâti BD TOPO** | édition 15/09/2026 | sync 26/09 | fiche, Gabarit, solaire | **à jour** |
| **Hauteurs LiDAR HD** | aucun re-survol 974 (2023 = seul) | survol 2023 | Gabarit, solaire | **à jour** |
| **Propriétaires PM (DGFiP)** | millésime **2026** publié 04/11 | situation 01/01/**2025** (ingérée 12/07) | Courrier, Successions, blocs | **en retard d'un millésime** (publié il y a 11 jours) |
| **Filiation DFI** | situation octobre 2026 publiée 04/11 | situation 19/06 | historique de filiation | **en retard de 1-2 situations** |
| **Dirigeants INPI RNE** | stocks mensuels (site en 403, SFTP sous compte) | max(ingested_at)=**05/07** | Successions, Courrier | **en retard ~4 stocks** — cron au 06/12 |
| **SIRENE géoloc** | fichier d'octobre publié 21/10 (pas de novembre) | sync 07/11 | concurrents, PM | **à jour** |
| **BODACC** | parution du 15/11 | données au 13/11 (quotidien 06 h 40) | procédures collectives | **à jour** (J-2 normal) |
| **Taxe d'aménagement** | taux 2026 (03/03) = derniers ; taux 2027 **non parus** chez la DGFiP | 24/24 communes, relevé 08/09 | Calculette (« Valeur forfaitaire 2026 ») | **à jour** — surveiller la parution 2027 |
| **Taxe foncière REI** | REI 2025 (11/05/2026) = dernier | REI 2025 | Calculette | **à jour** |
| **DPE ADEME** | dernier DPE **974** publié : 23/09 (vérifié ce jour par tri décroissant — le flux national va au 11/11, pas la Réunion) | max=23/09, ingéré 12/11 | fiche (étiquette) | **à jour** |
| **BAN adresses** | export quotidien, dernier 13/11 | sync **19/08** | autocomplétion, rattachements | **en retard ~3 mois** |
| **Fibre Arcep** | 2026_**T2** publié 14/09 | 2026_T1 | fiche (raccordable) | **en retard d'un trimestre** |
| **RP INSEE** | **RP2023 paru le 15/11 (aujourd'hui)** | RP2022 | fiches communes, IRIS | **en retard depuis aujourd'hui** — bascule paramétrée prête |

Invérifiables assumés : 8 sources manuelles (rappel de cadence), INPI RNE côté site (403
Datadome), ZNIEFF (INPN hors service — cyberattaque MNHN ; rien de plus récent que le servi
n'est téléchargeable). Sondes en anomalie : Parkings OSM / TCSP / pôles OSM marquées
`injoignable` (TimeoutError, 16-18 échecs consécutifs au 10/11) alors que FRAICHEUR-FIX-1 les
a passées en « rappel » — l'ancien statut de sonde n'a pas été nettoyé ; BD ORTHO sonde
`illisible` (couche ORTHO-EXPRESS absente du GetCapabilities) — le millésime 2025 reste le
dernier publié, donc sans conséquence.

### A.2 PLU des 24 communes — GPU du jour contre version servie

Comparaison faite le 15/11, commune par commune (API GPU `document?grid=<insee>&status=
document.production`, historiques sans filtre, PDF de procédure sur `data.geopf.fr/annexes/gpu`,
API Carto `municipality`/`zone-urba`). Convention CNIG : la date de l'idurba = approbation de la
dernière procédure intégrée.

**19 communes sur 21 servies : idurba identique au GPU** (Les Avirons 20241206, Bras-Panon
20260428, Entre-Deux 20240924, L'Étang-Salé 20250917, Petite-Île 20230609, La Plaine-des-
Palmistes 20230527, Le Port 20241209, Saint-Benoît 20200206, Saint-Joseph 20251210, Saint-Louis
20251218, Saint-Paul 20251217, Saint-Pierre 20240625, Sainte-Marie 20251126, Sainte-Rose
20190504, Sainte-Suzanne 20250929, Salazie 20220524, Le Tampon 20230811, Les Trois-Bassins
20220602, Cilaos 20240213). Aucun PLUi ni carte communale sur l'île.

**2 communes en retard — non détecté par la sonde :**

| Commune | GPU en vigueur au 15/11 | Prod sert | Écart |
|---|---|---|---|
| **Saint-Denis** (97411) | `97411_PLU_20260805` — approuvé **05/08/2026**, publié au GPU le 24/08/2026 | `97411_PLU_20260423` (modif. simplifiée n° 9), **archivée au GPU** | ~3 mois ; les zones prod (rebâties 13-27/10) et les extraits de règlement (07/08) lisent la version archivée |
| **La Possession** (97408) | `97408_PLU_20260625` — modif. simplifiée n° 2 (application d'un jugement du TA), approuvée **25/06/2026**, publiée le 29/10/2026 | `97408_PLU_20251217`, **archivée** | publication GPU postérieure à l'ingestion prod ; rien ne l'a rattrapée depuis le 29/10 |

**1 vigilance** : **Le Port** (97407) — même idurba `20241209`, mais le GPU a **republié** le
document le 18/11/2025 avec le statut `PARTIALLY_ANNULLED` (jugement du TA joint :
`97407_jugement_20241209.pdf`). Les extraits prod (07/08/2026) et les zones (13-27/10) sont
postérieurs à cette republication — a priori conformes — mais vérifier que les zones annulées
sont bien neutralisées dans ce qui est servi.

**3 communes sans règlement en prod — explicables :**
- **Saint-André** (97409) : aucun document au GPU (0, tout statut ; `zone-urba` vide). Le PLU de
  février 2019 en vigueur n'a jamais été téléversé (révision générale en cours, avis MRAe 2025).
  Trou du GPU, pas de la prod.
- **Saint-Leu** (97413) : idem — vieux PLU hors GPU ; révision générale en phase finale (enquête
  publique close le 09/10/2026, approbation attendue fin 2026) → **à surveiller : le nouveau PLU
  apparaîtra au GPU prochainement**.
- **Saint-Philippe** (97417) : **RNU** (POS caduc). L'absence est correcte sur le fond ; un
  affichage « RNU » explicite serait plus juste qu'un silence.

La **sonde GPU n'a rien vu de tout cela** : la ligne de veille de la source 3 (méthode `temoin`)
porte `dernier_vu = « 0 »` et `sync-gpu` du 15/11 s'est terminé en 0,2 s. Le témoin choisi ne
capte pas un changement d'idurba — c'est l'angle mort n° 1 de la sentinelle (cf. LOT C).
Nota : la veille des procédures **en cours** (révisions non approuvées) relève de
`config/veille_plu.yaml` (curaté, confiance SOURCE), hors de cette comparaison.

---

## LOT B — ce qui est calculé à partir des sources

| Dérivé / cache | Calculé | Entrées changées depuis ? | Périmé ? | Où le client le lit |
|---|---|---|---|---|
| **Classement servi q_v20** (433 229 classées) | 21/10 14:39, promu 27/10 | oui — cadastre (11/10 avant, mais PLU/permis/BODACC depuis), + défaut connu « 257 éclats U/AU » (§K quater) | **oui — 25 jours**, et aucun run sain complet depuis (q_v23 : 64 % des rangs ; q_v24 : tué) | accueil, carte, fiche (« rang N / 433 229 »), Flash |
| **Cascade servie q_v19_sources** (21,1 M lignes) | 18/10 | oui (mêmes entrées) | **oui — 28 jours** | motifs de score, fiche, documents |
| **Run résiduel** seq 17 (q_v20) | 21/10 | oui | oui — suit le classement | reste à bâtir |
| **parcel_constructibilite** (11 404 lignes) | 12/11 | non (PLU inchangé) | non sur ses lignes, mais couverture partielle (2,6 % des parcelles) — écart déjà relevé (CHIRURGICAL-1 E3) | carte (`api/tiles.py`, couche fermée), Flash |
| **Tuiles carte** (`mvt_tile_cache`) | reconstruites chaque nuit (dernière 14/11), version `q_v20.<injection>` | — | non (collées au run servi + injection du jour) | carte |
| **fiche_cache** (161 lignes) | au fil de l'eau, clé de fraîcheur (`cle_fraicheur`), dernière 15/11 | — | non (auto-invalidé) | fiche parcelle |
| **Fiche commune** (`commune_contexte_cache`) | chaque nuit 03 h 00 (15/11 ok, 775 s) | — | non, **mais** ses entrées DVF/ENAF/RP retardent (§ A) | fiche commune |
| **Médianes prix** (`dvf_secteur_medianes`, 2 359) | 02/11, `millesime_dvf=2025-12-31` | **oui — DVF S1 2026 publié** | **oui** — prix de secteur sans aucune vente 2026 | Estimer, fiche, Étude de zone |
| **Calibration Estimer** (`estimer_precision_calibration`) | banc quotidien 04 h 30 (15/11) | — | non (mais rétro-teste sur ventes ≤ 2025) | « ± » affiché d'Estimer |
| **Blocs fonciers** (`parcel_blocs`, 11 225) | **07/09** | **oui** — cadastre 11/10, PM 2025 (2026 publié) | **oui — 69 jours** | Assemblage, blocs |
| **Successions** (`parcel_veille_succession`, 6 266) | 13/10 (règle outils-s2-lotA) | entrée INPI inchangée depuis le 05/07 (elle-même en retard) | cohérent avec son entrée, qui retarde | outil Successions |
| **Solaire** (`toiture_lidar`, 33) | à la demande (LiDAR 2023 stable) | non | non | Prospection solaire |
| **Radar** (pige) | dépôts manuels — dernier **15/11** ; cycles quotidiens 04 h-04 h 30 ok ; rapprochement DVF borné aux ventes ≤ 31/12/2025 | — | le rapprochement « vendue » ne peut pas voir une vente 2026 | Radar |
| **Signal instantané** | 01/11 (mensuel, le 1ᵉʳ) | — | conforme à sa cadence | mesure forward |

Le fil rouge : **les caches « vivants » (fiche, tuiles, fiche commune) tournent bien** ; ce qui
est périmé l'est par **gel du calcul de nuit** (classement, cascade, résiduel) ou par **retard
d'une source amont** (médianes DVF, successions, blocs).

---

## LOT C — les automates

Registre = `labuse.jobs` (CRON-1), crontab généré `/etc/cron.d/labuse` (posé le **13/11 04:03**),
historique `job_runs` (rétention ~30 j), verrou flock, incidents par la porte d'alerte unique.

### Tournent et réussissent (dernier passage · durée)
`healthcheck` (15 min, 3 s) · `sante-endpoints` (30 min, 8 s) · `mail-queue-consommer` (5 min, 1 s) ·
`backup-postgres` (14/11, 1 034 s — vert depuis MENAGE-PROD-1) · `pg-maintenance` (dim., 15/11) ·
`injection-nuit` (15/11, 0,6 s) · `fiche-commune-cache` (15/11, 775 s) · `coherence-banc` (15/11,
701 s) · `estimer-banc-precision` (15/11, 17 s) · `coherence-robinets` (14/11, 944 s) ·
`sonde-sources` (14/11, 07 h 00) · `fraicheur-nuit` (14/11, 07 h 50, 3 s) · `filtres-sources`,
`detect-events`, `evaluer-suivis`, `abuse-scan`, `purge-sessions`, `essai-fin-proche`,
`copilote-purge`, `john-veille` (03 h 00) · `ingest-bodacc` (quotidien, 14/11, 395 s) ·
`ingest-dpe` (mensuel le 12, 12/11, 273 s) · `ingest-sirene` (mensuel le 7, 07/11, 347 s) ·
`sync-gpu` (mensuel le 15, **15/11 04:00**, 0,2 s) · `radar-cycle`/`-dvf` (15/11) ·
`radar-cycle-mensuel` (01/11) · `signal-instantane` (01/11) · `restore-test` (05/11 — restauration
de contrôle verte) · `verite-sources` (15/10 ; prochain : aujourd'hui 06 h 00).

### En échec
- **`calcul-nuit`** — échecs 11/11 et 12/11 (q_v23, `rebuild_features` code 1), 13/11 (q_v24,
  tué code -15 après 2 h 09) ; dernier succès **09/11** (29 s = no-op). **Gelé le 13/11 sur
  ordre de Vic** (commentaire au crontab : abstention du banc de cohérence + risque OOM).
  Incidents ouverts + escalade (4 j) actifs.
- **`verite-permanente`** — échec 14/11 : harnais F (accessibilité axe-core/Playwright). Vert
  le 13/11. Sans effet sur les données.

### Jamais exécutés (depuis la pose du crontab 13/11)
- **`ingest-sitadel`** (le 10, 04 h 30) — aucun run journalisé sur 30 j ; incident « jamais
  réussi » ouvert 08/11, escaladé 13/11. Prochain créneau **10/12**.
- **`ingest-inpi-rne`** (le 6, 05 h 00) — aucun run journalisé. Prochain créneau **06/12**.
- `ingest-dvf` (hebdo mardi 05 h 00) — dernier run 03/11 (5 s : l'ancien lecteur n'a rien vu) ;
  **pas de run le mardi 10/11** (incident « job en retard » ouvert 13/11, 2 rappels). Prochain
  créneau **mardi 17/11** — c'est lui qui doit charger `full-2026-s1` avec le nouveau lecteur.

### Gelés volontairement
`calcul-nuit` (13/11, Vic) · `purge-runs` (MENAGE-1, purge à valider avant dégel) ·
`radar-cloche` et `digest` (LABUSE_RADAR_NOTIFS=off).

### La sentinelle (sonde + contrôle)
- `sonde-sources` 07 h 00 : 95 lignes actives ; dernier passage complet 13/11 (le 14/11 :
  0 échues, 16 rappels). Échecs persistants : Parkings OSM / TCSP / pôles OSM (`injoignable`,
  16-18 échecs — reliquat d'avant leur passage en « rappel ») ; BD ORTHO (`illisible`, 3 échecs).
- `fraicheur-nuit` 07 h 50 : depuis le 12/11, chaque nuit : **« total 99 · retards 2 (DVF,
  SITADEL) · à vérifier 0 »** → incidents `fraicheur-retard:*` ouverts (2 rappels), John
  informé, page Données alimentée (`fraicheur_controle_nuit`). Les alertes **sont parties**
  (mail + cloche via la porte unique).
- Nouvelles versions notifiées par la sonde (dedup par millésime) : SITADEL 30/09 (`notifie=t`),
  PPR/CatNat/SUP/mouvements (témoins, notifiés), Recherche d'entreprises, annuaire, FRR, EnR.
  DVF : la sonde voit `full-2026-s1` ; la notification « nouvelle version » n'était pas marquée
  sur la ligne de veille mais le **contrôle de nuit** porte l'alerte depuis le 12/11 — le canal
  qui fait foi (FRAICHEUR-FIX-1) fonctionne.
- **Angle mort n° 1 — le PLU** : la ligne de veille de la source GPU (méthode `temoin`) porte
  `dernier_vu = « 0 »` ; ni elle ni `sync-gpu` (15/10 et 15/11, 0,2 s) n'ont vu que le GPU a
  publié une **nouvelle version du PLU de Saint-Denis** (24/08) et de **La Possession** (29/10).
  Le témoin choisi ne capte pas un changement d'idurba ; le PLU n'est pas non plus dans le
  contrôle de millésime à preuve (qui ne couvre que DVF, SITADEL, RP). C'est le seul retard de
  cet audit que le système ignore.

---

## LOT D — dix lectures client faussées par un retard, constatées en prod

1. **Rang d'une parcelle (fiche, Sainte-Marie `97418000BD0420`)** — servie « rang 428 217 /
   433 229 » (q_v20 du 21/10). Le run du 10/11 (q_v23, non promu) la met au rang 74 237 — mais il
   ne classe que 64 % des parcelles, signe que le calcul lui-même est malade. Valeur à jour :
   inexistante — aucun run complet depuis le 21/10. Source : scoring interne (calcul-nuit gelé).
2. **Zonage PLU de Saint-Denis** — toute fiche, Analyse ou Étude d'une parcelle dionysienne lit
   le zonage et le règlement de la version du **23/04/2026**, archivée au GPU : la version
   approuvée le **05/08/2026** (en vigueur, publiée le 24/08) n'est pas ingérée. Toute parcelle
   dont la règle a changé entre les deux reçoit un verdict de constructibilité calculé sur un
   document abrogé. Idem **La Possession** (modif. du 25/06/2026 appliquant un jugement du TA,
   servie : version du 17/12/2025). Source : GPU.
3. **« Ventes 2026 » = zéro, partout** — `dvf_mutations_parcelle` : 0 mutation ≥ 01/01/2026
   (vérifié). Toute fiche commune, Étude de zone ou Estimer affiche un marché qui s'arrête au
   31/12/2025, alors que l'amont publie le S1 2026 depuis le 20/10 (~1 600 ventes Réunion
   d'après le banc local FRAICHEUR-FIX-1). Et les **médianes de secteur** (`dvf_secteur_medianes`,
   recalculées le 02/11 sur `millesime_dvf=2025-12-31`) font du « prix du secteur sur 12 mois »
   les 12 derniers mois **connus en 2025**. Écrans : Estimer, Étude de zone, Comparer, fiche
   commune ; PDF : « DVF — 31/12/2025 ».
4. **Outil Permis, « Autorisés depuis 90 jours »** — fenêtre réelle 17/08→15/11 : la prod sert
   **145 permis, tous ≤ 31/08** (0 depuis le 1ᵉʳ septembre, vérifié). Le compteur « 90 jours »
   ne couvre que 2 semaines ; l'amont publie septembre. Source : SITADEL.
5. **Successions : dirigeants du 05/07** — 5 SIREN en procédure collective depuis septembre
   (ex. **821053840**, redressement judiciaire ouvert le 13/11 — BODACC en base) apparaissent
   dans Successions/Courrier avec leurs dirigeants d'avant la procédure ; tout changement de
   gérant depuis juillet est invisible. Source : INPI RNE.
6. **Courrier / blocs : propriétaires 2025** — la situation au 01/01/2026 (publiée 04/11) n'est
   pas injectée : toute cession 2025 d'une personne morale laisse le pli adressé à l'ancien
   propriétaire. Source : DGFiP parcelles des personnes morales (+ DFI du 19/06 pour la
   filiation : une division récente n'apparaît pas).
7. **Assemblage / blocs fonciers du 07/09** — `parcel_blocs` construit le 07/09, avant le
   cadastre du 11/10 : les parcelles remaniées depuis (fusions/divisions du millésime de
   septembre) et les mutations de PM n'y sont pas. Écran Assemblage, outil blocs.
8. **Autocomplétion d'adresse** — BAN synchronisée le **19/08** (339 915 adresses) ; l'export
   quotidien du 13/11 existe. Une adresse créée ou corrigée depuis fin août ne se trouve pas.
   Écrans : omnibox, rattachement adresse→parcelle.
9. **Fibre « raccordable »** — la fiche sert l'état Arcep **T1 2026** (31/03) ; le T2 (30/06)
   est publié depuis le 14/09 : un immeuble passé raccordable au 2ᵉ trimestre est encore servi
   « non raccordable ». Source : Ma connexion internet.
10. **Fiche commune, conso d'espaces (ZAN)** — la prod sert la série ENAF **2021-2024** ; le
    portail de l'artificialisation publie **2011-2025** depuis le 30/06. Le « rythme observé »
    du scénario ZAN ignore le flux 2024-2025. (Idem, depuis aujourd'hui : tout ce qui lit le
    RP2022 — le RP2023 est paru le 15/11.)

---

## LOT E — mon Mac contre la prod

| Axe | Prod (`labuse-vps`) | Mac (base `labuse`) | Écart |
|---|---|---|---|
| **Code** | `/opt/labuse/app` déployé depuis `ops/deploy-groupe-3`, crontab régénéré 13/11 04:03 ; tête de branche `af471f99b` (13/11) | audits sur worktrees de **main** (`e269abaa0`, 14/11) | **main = 100 commits non déployés** ; la branche prod porte 33 commits à elle (hors main) |
| **Run servi** | q_v20, manifeste promu **27/10** (« cli DEPLOY-1027, division q_v19 ») | q_v20, manifeste promu **21/10** (« Vic — bascule q_v20 ») | même run, manifestes d'époques différentes (division/cascade identiques) |
| **Classement** | q_v20 : 433 229 classées | q_v20 : 433 229 | identique |
| **DVF** | 31/12/2025 · 102 551 | 31/12/2025 · 102 551 | identique |
| **SITADEL** | 31/08 · 50 810 | 31/08 · 50 809 | ±1 ligne |
| **Dirigeants** | 05/07 · 27 146 | 05/07 · 27 037 | prod +109 (enrichissements prod) |
| **SIRENE** | ~157 672 | ~155 522 | prod +2 150 (resync 07/11 non répliqué) |
| **parcels / adresses** | ~437 469 / 339 915 | ~436 692 / 339 915 | parcelles : +777 en prod (estimateurs) |
| **spatial_layers** | ~1 924 854 | ~1 933 838 | ~0,5 % (couches de travail locales) |
| **parcel_constructibilite** | 11 404 (12/11) | 11 782 | runs locaux d'essai |
| **Sources** | 94 connecte · 3 live · 2 manuel · 6 retirée | idem, 5 retirée | 1 retrait non répliqué |

**Ce qui rend un audit local non valable pour la prod** :
1. **Le code d'abord** : 100 commits de main (CAPACITE-1, CHIRURGICAL, OUTILS-P0/P1, GABARIT-3D,
   ESTIMER-3…) ne sont pas déployés — tout audit local qui exerce ces chemins (surface retenue,
   Étude déterministe, écrans outils corrigés) décrit un comportement que la prod **n'a pas** ;
   inversement les 33 commits propres à `ops/deploy-groupe-3` (déploiement, §K) ne sont pas dans
   main.
2. **SIRENE et dirigeants** : la prod a resynchronisé SIRENE le 07/11 (+2 150 établissements) —
   un audit local des outils entreprises travaille sur octobre.
3. **Les données clés (DVF, SITADEL, INPI, q_v20) sont en revanche identiques** : sur ces axes,
   un constat local vaut pour la prod — et réciproquement, le retard DVF/SITADEL/INPI mesuré ici
   vaut aussi en local.

---

## Méthode et limites

- Prod lue via `ssh labuse-vps` + `sudo -u postgres psql -d labuse` (motif documenté des mandats
  précédents), `SET statement_timeout` 20–300 s par requête, aucune écriture, fenêtres horaires
  respectées (requêtes 05 h 30–07 h Réunion).
- Producteurs lus le 15/11 : API data.gouv / data.economie / data-fair ADEME / Géoplateforme
  (flux Atom) / INSEE / GPU ; geoservices IGN et Géorisques web bloquent le fetch → flux Atom et
  API qui font foi. INPI : 403 Datadome (invérifiable en ligne, stock mensuel connu).
- Vérification contradictoire faite sur le DPE : le « retard » apparent (national 11/11) tombe
  quand on filtre la Réunion (dernier DPE 974 publié : 23/09) — la prod est à jour.
- `job_runs` ne conserve qu'environ 30 jours : « jamais exécuté » signifie « aucun run journalisé
  sur la fenêtre ET créneau postérieur à la pose du crontab du 13/11 ».
- Comparaison PLU : documents d'**approbation** GPU vs servis ; les procédures en cours (PADD,
  révisions non approuvées) relèvent de la veille curatée, hors périmètre de la preuve SIG.
