# NU5-E — Fiche commune, 24 communes × 10 cartes, chiffre par chiffre

**Branche** `audit/nu5-e` · worktree `~/Desktop/labuse-nu5e` · **Opus** · **LECTURE SEULE, aucune correction.**
**Date** 2026-11-05 (Réunion). **Base** LOCALE `labuse` (q_v20), cache `commune_contexte_cache` **recalculé le 2026-11-05** (frais).
**Prod** sondée en lecture seule uniquement sur `/readyz` (public, 200) — **aucune valeur servie lue sur prod** (voir Méthode), donc fenêtre 01 h–05 h Réunion respectée par construction.
**Périmètre** les 24 communes de La Réunion (= toute l'île), chacune via l'endpoint `GET /communes/{commune}/contexte`
(`src/labuse/api/app.py:2677`, assemblage `src/labuse/api/fiche_commune.py:build`).

---

## 1. Méthode & limites

**Valeurs servies.** L'endpoint sert le **payload figé** de la table `commune_contexte_cache` (job nocturne
`fiche-commune-cache`), rafraîchi à la lecture si la clé de fraîcheur a bougé. J'ai **exporté verbatim** les 24
payloads (`SELECT payload FROM commune_contexte_cache`) → `preuves/payloads/97401.json … 97424.json`. C'est
exactement ce que le front reçoit (le `_rafraichir_partages` live rejoue les mêmes moteurs sur un run stable).

**Prod.** `/communes/{c}/contexte` exige une **session nominative + 2FA** (401 sans cookie ; le jeton de banc
`v1.…` n'est émis par aucune route HTTP — `api/auth.py:13`). Faute de compte nominatif prod, et comme les
audits frères NU-5-A/B/C, je travaille sur la **base LOCALE q_v20** (socle identique). **Dette :** rejouer les
24 fiches contre la prod authentifiée (notamment pour les millésimes PLU, cf. E-8, où la prod peut être plus fraîche).

**Fidélité du harnais (prouvée).** J'ai **recalculé depuis les tables sources** les chiffres les plus mécaniques
(ppr_pct, mouvement_terrain_pct, compte CatNat, n_parcelles, surfaces, répartition zonage, identité logements,
parc social vs SRU) et comparé aux payloads : **0 écart** → les valeurs servies sont fidèles à la base locale.
Les écarts ci-dessous sont donc soit des **données sources** fausses/lacunaires, soit des **libellés/choix de
présentation**, pas des bugs de calcul du robinet.

**Vérification externe.** Chaque chiffre vérifiable en ligne a été confronté à sa source officielle (INSEE
populations légales/RP/Filosofi, DVF, Sitadel, GPU/Sudocuh, Géorisques/GASPAR/DEAL, DHUP zonage ABC & SRU,
DGFiP REI, décrets ZFANG/FRR, SCOT). Les DVF « médiane commune entière » ne sont **pas reproductibles à l'exact**
(fenêtre/méthode) → vérifiés en **ordre de grandeur + classement**, marqués comme tels.

**Harnais** (`harnais/`) : `extraire.py` (payloads → `faits.csv`, `comparaison.csv`, `structure.txt`) ;
`recompute.sql` (recomputes de cohérence). **Relecture rejouable.**

---

## 2. Tableau commune × carte (10 cartes)

Légende : **V** conforme/honnête · **O** imprécision, libellé, comparabilité ou donnée mince · **R** chiffre faux/aberrant · **–** carte sans chiffre (raccourci Étude de zone).
Les **défauts transversaux** (SCOT jamais servi `E-1`, Parc national 24/24 `E-3`, loyer OLL/DHUP mélangés `E-4`) se surajoutent à ce tableau et sont décrits au §3 ; ils ne sont pas re-coloriés colonne par colonne pour ne pas masquer les défauts localisés.

| Commune | Identité | Population/log. | Prix | Activité | Permis | Foncier/rareté | Urbanisme | Fiscalité | Risques | Équip./desserte |
|---|---|---|---|---|---|---|---|---|---|---|
| Bras-Panon | V | V | V | V | V | V | V | V | V | – |
| Cilaos | V | V | V | V | V | V | V | V | V | – |
| Entre-Deux | V | V | V | V | V | V | V | V | V | – |
| L'Étang-Salé | V | V | V | O | V | V | V | V | V | – |
| La Plaine-des-Palmistes | V | V | V | V | V | V | V | V | V | – |
| La Possession | V | V | V | V | V | V | V | V | V | – |
| Le Port | V | V | V | V | V | V | V | V | V | – |
| Le Tampon | V | V | V | V | V | V | O | V | V | – |
| Les Avirons | V | V | V | V | V | V | V | V | V | – |
| Les Trois-Bassins | V | V | O | O | V | V | V | V | V | – |
| Petite-Île | V | V | O | O | V | V | V | V | V | – |
| Saint-André | V | V | V | V | V | V | V | V | V | – |
| Saint-Benoît | V | V | V | O | V | V | V | V | V | – |
| Saint-Denis | V | V | V | V | V | V | O | V | **R** | – |
| Saint-Joseph | V | V | V | V | V | V | V | V | V | – |
| Saint-Leu | V | V | V | V | V | V | V | V | V | – |
| Saint-Louis | V | V | V | V | V | V | O | V | V | – |
| Saint-Paul | V | V | V | V | V | V | V | V | V | – |
| Saint-Philippe | V | V | V | V | V | O | V | V | V | – |
| Saint-Pierre | V | V | V | V | V | V | V | V | V | – |
| Sainte-Marie | V | V | V | O | V | V | V | V | V | – |
| Sainte-Rose | V | V | V | V | V | V | V | V | V | – |
| Sainte-Suzanne | V | V | V | V | V | V | V | V | V | – |
| Salazie | V | V | V | V | V | V | V | V | V | – |

**Comptage** : 204 **V** · 11 **O** · 1 **R** · 24 **–** (carte raccourci). Zéro **R** sur les cartes de données chiffrées hors Saint-Denis/Risques.

---

## 3. Trouvailles classées

### ROUGE

**E-2 — Saint-Denis : « mouvement de terrain 0,1 % », risque réel sous-estimé.** La carte Risques de
Saint-Denis sert `mouvement_terrain_pct = 0,1 %` alors que **les 23 autres communes sont à 87–100 %**
(Sainte-Marie 100 %, Saint-Paul 90,2 %, voisines à ~100 %). Recompute sur la base : seules **39 parcelles / 38 557**
intersectent la couche aléa `georisque_alea/mouvement_terrain`, et cette couche ne couvre que **0,06 km² des
134,5 km²** de la commune (**0,04 %**) — un **trou de couche** propre à Saint-Denis (Sainte-Marie voisine : 99,95 %).
La valeur servie est **fidèle à la base** (cache recalculé aujourd'hui → ce n'est **pas** une péremption), mais la
**base est lacunaire** : Saint-Denis a un **PPR multirisques « inondations ET mouvements de terrain » approuvé**
(aléas documentés DEAL/BRGM : chutes de blocs La Montagne/Grande Chaloupe/route du Littoral, glissements,
ravinement). La fiche affiche donc ~0 % de mouvement de terrain **sur la commune la plus peuplée de l'île**, là où
le risque est notoire. **Fidèle à la base ≠ vrai.** Preuve : `harnais/recompute.sql` §2 ; Géorisques 97411 ;
note PPR Saint-Denis (reunion.gouv.fr). *(À noter : le `ppr_pct` de Saint-Denis, lui, est correct à 72,2 %.)*

### MAJEUR structurel (transversal, toutes communes)

**E-1 — Le SCOT est calculé puis jeté : la carte Urbanisme n'affiche jamais le SCOT.**
`fiche_commune.build()` calcule `blocs["scot"]` (`fiche_commune.py:274`, requête réelle sur
`spatial_layers kind='scot'`), **mais `_compute_commune_contexte` ne le remet pas dans le payload**
(`app.py:2906-2934` : aucune clé `scot`). Le front, lui, lit `d.scot.nom` pour la ligne SCOT
(`ContextePanel.tsx:674-678`). Résultat : `scot` **absent des 24 payloads** (`structure.txt`), `d.scot`
toujours `undefined` → **la ligne SCOT ne s'affiche sur aucune fiche**, alors que la donnée **existe**
(3 périmètres en base : TCO, CINOR, Grand Sud) et que le SCOT est une source explicitement demandée au mandat.
Même classe que les bugs « calculé mais non rendu » déjà corrigés sur cette fiche (tendance 12 mois,
acquisitions PM — COMMUNE-RANGEMENT). **De plus la donnée SCOT stockée est partiellement fausse** (invisible
tant qu'E-1 n'est pas corrigé, mais elle le deviendrait) :
- **SCOT Grand Sud** : stocké `statut="en projet"`, date `2024-09-02`. En réalité **approuvé le 18/02/2020** ;
  le 02/09/2024 = approbation d'une **modification simplifiée**. Et comme le front affiche « approuvé le {date} »
  dès qu'une `date_approbation` existe, un correctif d'E-1 **afficherait « approuvé le 02/09/2024 » pour un SCOT
  étiqueté « en projet »** — exactement le défaut « en projet affiché approuvé » visé au mandat.
- **SCOT TCO** : date stockée `2022-10-03` = **modification simplifiée n°1**, pas l'approbation de base
  (21/12/2016) ; SCOT par ailleurs **en révision** depuis 2022.
- **SCOT CINOR** : `approuvé` **sans date** (manque 18/12/2013), révision générale en cours non mentionnée.

### ORANGE

**E-3 — « Parc national : oui » pour les 24 communes (indicateur non discriminant).** Le flag `parc_national`
vaut **true pour les 24 communes** (`recompute.sql` §3). La couche `parc_national` réunit **cœur** (1 055 km²,
vraie contrainte) **et aire d'adhésion** (642 + 235 km², aucune contrainte). Presque toute commune touchant les
Hauts, toutes ressortent « oui » — y compris **Le Port** (port urbain : 6 parcelles de bord, 0,02 ha en aire
d'adhésion). Pour un outil foncier, « Parc national : oui » suggère une contrainte ; servi partout, il n'informe
rien et induit en erreur sur les communes littorales. À distinguer cœur / aire d'adhésion.

**E-4 — « Loyer médian » : deux instruments mélangés d'une commune à l'autre.** Sous un même libellé « Loyer
médian », 14 communes portent **OLL 2024, « tous types », valeur ZONALE** (dont **9,2 €/m² répété à l'identique sur
9 communes « zone 6 »** : Entre-Deux, Petite-Île, Plaine-des-Palmistes, Saint-André, Saint-Joseph, Saint-Philippe,
Sainte-Rose, Salazie, Cilaos) et 10 communes portent **DHUP 2025, « appartement »** (Saint-Paul 18,86 ; Saint-Denis
15,09). Les valeurs OLL correspondent à l'observatoire publié (plancher zonal 9,20 légitime) et les DHUP sont
plausibles pour de l'appartement, **mais les deux moitiés ne sont pas comparables** (année, type de bien, charges).
Comparer Saint-Paul (DHUP appart 18,86) à Entre-Deux (OLL tous types 9,2) = comparer deux choses. La source est
honnêtement citée par fiche ; le défaut est la **comparabilité inter-communes**. Un seul socle, ou afficher
`type`/source par commune dans le comparateur.

**E-5 — Écart demandé/acté servi sur une population différente des « biens en vente ».** L'écart est calculé sur
`prix_demande_n` (annonces avec prix bâti), **pas** sur `biens` (annonces actives). D'où des écarts servis alors
que la carte dit « sous le seuil, N biens » : **Les Trois-Bassins +66,0 %** (sur 7 annonces, mais « 2 biens en
vente »), Petite-Île +29,9 % (5 vs « 3 biens »), L'Étang-Salé +8,1 %, Sainte-Marie +15,6 %, Saint-Benoît −4,0 %
(7 vs « 1 bien »). Deux populations derrière une même carte ; un **+66 % sur 7 annonces** est un signal fragile.
Aligner l'écart sur le même effectif/seuil que les « biens en vente », ou masquer l'écart quand les actives sont sous le seuil.

**E-6 — VEFA neuf peu représentatif sur les petites communes (Prix).** Médianes VEFA servies **Les Trois-Bassins
6 370 €/m²** et **Petite-Île 5 277 €/m²** — **au-dessus de Saint-Paul (4 745), Saint-Denis (4 878), Saint-Leu
(4 958)**. Elles **passent le seuil d'effectif** de l'app (8 ; Trois-Bassins ~39 mutations VEFA brutes) donc ce
sont de **vraies médianes**, mais tirées par un **mix produit premium** (programmes vue mer) sur échantillon
modeste → non représentatives du « neuf de la commune ». Un drapeau « faible échantillon » (même esprit que les
audits DVF antérieurs) serait honnête.

**E-7 — Millésime zonage ABC trompeur.** Les **valeurs de zone sont exactes 24/24** (B1 partout sauf A pour
Les Avirons, L'Étang-Salé, Saint-Leu, Saint-Paul — reclassement Ouest confirmé). Mais le **millésime servi**
« arrêté du 23/06/2026 — en vigueur 26/06/2026 » renvoie à un arrêté qui **ne concerne qu'Alfortville (94)** ; le
classement A de La Réunion découle de l'**arrêté du 02/10/2023**. Défendable comme « dernière version consolidée
de l'arrêté du 1er août 2014 », trompeur lu comme la date de reclassement de l'île.

**E-8 — Millésimes PLU légèrement en retard (statut juste).** Statuts PLU corrects (dont RNU Saint-Philippe,
révisions Saint-André/Saint-Leu/Trois-Bassins, ré-approbations Saint-Paul 17/12/2025 & Sainte-Marie 26/11/2025
exactes). Imprécisions de **millésime/procédure** : Saint-Denis servi « PLU opposable 23/04/2026 » alors que le
document opposable au GPU serait **05/08/2026** (une version de retard) ; Saint-Louis servi 18/12/2025 vs GPU
26/09/2025 ; **Le Tampon** « aucune procédure » alors qu'une **révision générale (prescrite 12/2024)** est en cours
(postérieure au snapshot Sudocuh 31/12/2024). *(À relativiser : base locale q_v20 possiblement plus ancienne que la prod — à rejouer sur prod.)*

**E-9 — Saint-Philippe (RNU) : « répartition zonage N 100 % » sur 9 parcelles / 621 ha.** La carte Foncier affiche
`surface_ha = 11 415` (commune entière) et, juste à côté, une **répartition du zonage « N 100 % »** calculée sur
**621 ha / 9 parcelles seulement** — car Saint-Philippe est **RNU** (4 171 / 4 173 parcelles « sans zonage,
non publié au GPU »). « N 100 % » donne l'illusion d'une commune 100 % naturelle, alors que 99,8 % des parcelles
sont simplement **non zonées**. La fiche porte bien par ailleurs le bandeau RNU et le compte `sans_zonage` ; la
ligne « répartition » reste trompeuse juxtaposée à la surface communale.

### Observations mineures (non colorées)

- **E-10 — `point mort` > `permis 5 ans` sur 10 communes** (Salazie 278 vs 171 ; Saint-André 1 111 vs 759 ;
  Saint-Paul 2 598 vs 1 953). Métriques distinctes (PC sans DAACT 36 mois sur parcelle non bâtie vs autorisations
  5 ans), donc arithmétiquement possible, mais **contre-intuitif** (« plus de permis au point mort que de permis
  accordés en 5 ans »). Mérite une note d'explicitation sur la carte Permis.
- **E-11 — Signal marché « rouge » à −0,3 %/12 mois** (Saint-Denis) : seuil de tonalité très sensible (tout trend
  négatif → rouge) ; un −0,3 % en rouge est alarmiste à côté de Petite-Île −11,6 %.
- **catnat_detail** plafonné à 12 arrêtés (le **compte** `catnat_arretes` reste exact — vérifié) : sous-ensemble
  d'affichage, pas un chiffre faux.
- **Libellés AZI** (bassins de risque nommés : Le Port « Cirque de Mafate », Sainte-Rose « Le Volcan ») :
  d'abord suspects, en fait **plausibles** (nommés par bassin hydrographique/aléa, pas par commune) — non retenu.

---

## 4. Points solides confirmés (VERT)

- **Population légale : 24/24 EXACTES**, millésime **2023** correct (en vigueur 01/01/2026), libellé
  « Population légale 2023 (INSEE) » juste. Aucune dérive > 1,5 %, aucun mélange de millésime.
- **Ménages / logements / vacants** : à **±0,5 %** sur toutes les communes testées ; identité comptable
  **logements = résidences principales + vacants + secondaires** vérifiée (Δ ≤ 1, arrondi) sur les 24.
- **Niveau de vie « moyen » : libellé DÉFENDABLE** (contre un soupçon initial de « moyenne qui n'en est pas une »).
  Le robinet calcule une **vraie moyenne** pondérée de carreaux Filosofi `sum(ind_snv)/sum(ind)`, explicitement
  étiquetée « Niveau de vie moyen (Filosofi) » — distinct du médian publié par l'INSEE, et proche de lui car le
  niveau de vie Filosofi est winsorisé. **Pas un défaut.**
- **Logement social cohérent sur deux sources** : parc social RPLS ≈ LLS inventaire SRU à **±10 %** sur les 24 ;
  taux SRU plausibles ; **Cilaos 2,94 % / Salazie 2,8 %** bas car **communes exemptées** (cirques isolés) — correct.
- **CatNat : 6/6 comptes EXACTS** vs l'API Géorisques GASPAR (Saint-Denis 21, Saint-Paul 24, Cilaos 16,
  Sainte-Rose 10, Le Port 11, Plaine-des-Palmistes 12).
- **PPR % plausibles** (communes à ~100 % ont bien un PPR multirisques approuvé — DEAL : Salazie, Étang-Salé,
  Entre-Deux, Saint-Paul, Saint-Pierre, Saint-Denis…).
- **Fiscalité solide, 0 rouge** : **TFPB 5/5 exact** DGFiP (dont **Saint-Louis 68,40 % — CORRECT**, taux communal
  consolidé incluant l'ex-part départementale transférée depuis 2021 ; ce n'était pas une anomalie) ; taxe
  d'aménagement **toutes dans la bande légale 1–5 %** (Sainte-Rose 1 % confirmé) ; **ZFANG « renforcé » = exactement
  les 6 communes de l'Est** (décret 2026-421 du 29/05/2026, post-Garance) — donnée très à jour ; **ORT : 4 villes
  ACV** exactes, aucune commune « hors » prise en défaut ; FRR cohérent.
- **Zonage ABC : valeurs 24/24 exactes** (y compris B1→A de 4 communes Ouest, souvent manqué par les tiers).
- **PLU : statuts corrects** (RNU, révisions, ré-approbations récentes bien déduites « approuvee_probable »).
- **Prix ancien DVF** : ordre de grandeur et **classement corrects**, aucune inversion côte/cirque (Saint-Paul
  4 278 > … > Salazie 1 474) ; léger **biais bas systématique** attendu (médiane d'actes DVF < agrégateurs
  d'annonces) ; **Cilaos 1 622** le plus proche d'un orange (vs ~2 000 publics) — exact non vérifiable (n/v).
- **Permis Sitadel** : classement par taille de commune correct, somme île cohérente avec le total Sitadel.
- **Cohérence interne** : répartition zonage ≈ 100 % ; `total_ha` zonage ≈ `surface_ha` (sauf Saint-Philippe RNU, E-9) ;
  répartition permis par type = `permis_12m` (± annulés). Harnais recalc → **0 écart** vs servi.

---

## 5. Harnais (relecture rejouable)

- `harnais/extraire.py` — payloads servis → `faits.csv` (commune × champ : valeur, millésime, source),
  `comparaison.csv` (une ligne/commune, chiffres clés inter-communes), `structure.txt` (clés présentes/absentes
  → prouve l'absence de `scot`).
- `harnais/recompute.sql` — recomputes de cohérence (risques par parcelle, trou aléa Saint-Denis, parc national
  24/24, SCOT en base, volumes VEFA).
- `preuves/payloads/*.json` — les 24 payloads servis (dump `commune_contexte_cache`, cache 2026-11-05).
- `faits.csv`, `comparaison.csv`, `matrice.md`, `structure.txt` — sorties.

**Rejeu** : `psql "postgresql://openclaw@localhost:5432/labuse"` + `python3 harnais/extraire.py`.

---

## 6. Synthèse

Socle **fidèle et largement juste** : 204/216 cellules chiffrées vertes, **populations légales 24/24 exactes**,
**CatNat 24/24 fidèles à Géorisques**, **fiscalité 0 rouge** (dont l'« anomalie » Saint-Louis 68,4 % qui est en
fait correcte), recomputes de cohérence **0 écart**. Un seul **chiffre faux servi** : **Saint-Denis « mouvement de
terrain 0,1 % »** (trou de couche aléa → risque majeur sous-estimé sur la commune la plus peuplée, `E-2`, ROUGE).
Un défaut **structurel transversal** : le **SCOT est calculé mais jamais servi** (`E-1`, + donnée SCOT stockée
partiellement fausse, dont un « en projet » qui s'afficherait « approuvé » si rebranché). Le reste est de
l'**imprécision honnête mais perfectible** : indicateur Parc national non discriminant (24/24), loyer OLL/DHUP
non comparable d'une commune à l'autre, écart demandé/acté sur une autre population que les biens affichés, VEFA
non représentatif sur deux petites communes, millésimes zonage ABC et PLU un cran en retard, et la répartition de
zonage trompeuse de Saint-Philippe (RNU). Aucune invention de risque ni de vente ; les libellés « médian/moyen »
sont fidèles.
