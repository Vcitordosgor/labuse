# BACKLOG LABUSE — source de vérité

> Règles : CC met à jour ce fichier à la fin de chaque train (statuts + date).
> Vic arbitre, CC exécute, ce fichier fait foi.
> Statuts : [ ] à faire · [~] en cours · [x] fait · [!] bloqué (dire par quoi)

Dernière mise à jour : 2026-08-04 — train 1 (CC) : **pondération option B SERVIE** (GO Vic),
CX2555 levée, CH1893 pérennisée, golden 116/116 (référence régénérée), jetables purgés.
Rollback dispo : scripts/rollback_ponderation.py. Priorité train 5 : saturation p=1,0 (rangs 1-5).

## Régimes de supervision

- [S] Sensible — touche un chiffre servi. Points d'arrêt à chaque étape, arbitrage Vic.
- [A] Standard — features / refontes. UN point d'arrêt final, avec captures.
- [M] Autonome — mécanique. Zéro point d'arrêt, rapport de fin, Vic lit.

## Règles de décision par défaut (valables dans tout mandat)

1. Choix d'implémentation → option réversible, notée au rapport.
2. Chiffre servi touché → s'arrêter, rapporter, attendre Vic.
3. Cosmétique / interne → décider seul, noter au rapport.
4. Ressource ou appel réseau non désigné par le mandat → le dire avant.
5. Livrable annoncé = livrable vérifié (ls -la avant d'annoncer un chemin).
6. Jamais de merge. Commit + push sur branche dédiée. Vic merge en --no-ff.
7. Revue visuelle obligatoire avant toute exposition d'une surface servie.

## TRAIN 1 — PONDERATION [S] Fable — PRIORITAIRE
- [x] Option B : pondération au_sous_plancher ×(1−manque/seuil) — implémentée (facteur_ponderation + _pondere_au_sous_plancher, même point de calcul que la mention, kill-switch LABUSE_DISABLE_AU_POND), tests verts. **NON basculée** (point d'arrêt).
- [x] Mesure d'effet : population réelle 1 069 (les 708 + calibrations depuis). 117 mouvements : 38 sorties de tête sous-plancher, 0 entrée indue, 44 entrées mécaniques (rangs libérés), effectifs stables (brûlantes 120). Contrôle ≡ servi à 2 exceptions près (les manuelles). Cartes ortho IGN des 82 mouvements en tête. Rapport : docs/mandats/TRAIN1_PONDERATION_RAPPORT.md.
- [x] **Bascule pondération SERVIE (GO Vic 04/08, AB1908/AB1910 tiennent)** — remplacement sous label (scoring v2 épinglé Q_A_RUN_LABEL), archive par RENOMMAGE q_v8_calibre_pre_pond (rien détruit, rollback: scripts/rollback_ponderation.py), 5 gardes passées, conformité STRICTE à la mesure validée (écart unique = CH1893). Tiers servis : 119 brûlantes, 1 038 chaudes. MVT rebuildées. Golden 116/116 PASS (référence régénérée — elle était restée sur q_v7, dette v8 réparée ; 84 ancres préservées, diff versionné).
- [x] CX2555 **levée** (servie au naturel : a_creuser rang 427 206, plus d'exception au journal du run servi).
- [x] Dette #4 : 46 suspectes mesurées (13 brûlantes, 19 chaudes) — revue Vic APRÈS AB1908/AB1910, rien de déclassé d'ici là. Profil sectoriel mesuré (arbitrage 4) : 1 061 parcelles-trou (piscine × couche <20 m²), 456 secteurs, 24 communes — 39 secteurs = 25 % du volume, 111 = 50 % : points chauds réels (Saint-Paul 188) mais dette DIFFUSE → rechargement par commune plutôt que par secteur.
- [x] CH1893 : **pérennisée (validé Vic 04/08)** — motif mis à jour dans served_run_exceptions : « couche bâtiment lacunaire, vérifié ortho 04/08, à lever au rechargement de la couche », lié à la dette racine train 5.
- [x] Purge post-bascule faite : q_v9_pond_avant/apres + orphelin q_v9_avant (1,29 M lignes). L'archive q_v8_calibre_pre_pond est CONSERVÉE (c'est le rollback) — à purger quand Vic déclarera la pondération stable.
- [x] Inventaire des tables run-scopées mortes en silence (consigne Vic) : parcel_renouvellement (q_v7), entonnoir_motifs (q_v2/q_v6), ia_cache (q_v6/q_v7, cache) — consigné en tête du train 5, garde #6 posée côté golden. **TRAIN 1 CLOS.**

## TRAIN 2 — TECH [M] Opus — en parallèle de tout
- [x] Rebase + push EXPRESS-01 : EXPRESS-01 (485f7a9) déjà mergé dans main → fast-forward. 3 poses IDU (Fiche/Tinder/Kanban) déjà servies ; 4e pose (gen_tops) livrée avec les tops ci-dessous.
- [ ] Merge fix/m13-e (Vic merge), puis rebase EXPRESS-01 dessus — action Vic, non faite par CC.
- [x] Régénérer les tops : IDU complet + run servi (Q_A_RUN_LABEL au lieu de q_v2 gelé/absent). 25 HTML (24 communes + top50) régénérés sur q_v8_calibre, générateur + HTML commités ensemble.
- [x] Gardes de bascule → briques importables (module src/labuse/bascule_gardes.py) : 5 gardes extraites VERBATIM, bascule les importe, aucune logique recopiée. Tests verts.
- [x] **GARDE #6 (consigne Vic 04/08) : toute bascule régénère le golden dans le même geste** — check_golden_regenere ajoutée au module (refus BRUYANT si la référence cite un autre run que le servi), branchée dans bascule_ponderation.py et bascule_v8_calibre.py, 3 tests. Le golden resté sur q_v7 pendant la bascule v8 était une dette de process, pas un incident.
- [x] Requête A1.3 : 0 IDU manquant. Sans adresse BAN, mesuré sur le CHAMP adresse de la fiche (déf. Vic, API servie) : **brûlantes 39,3 % (46/117)**, **top-1000 rangs 41,0 %**, île 40,4 %. **PAS un non-sujet en tête** : 46 brûlantes affichent « Adresse non disponible ». Les 5,3 %/0 % provisoires ne se reproduisent pas. → train 4 (change d'ampleur). Détail : docs/mandats/A1_3_IDU_ADRESSES_MANQUANTS.md.
- [x] Purge des jetables q_v8_au_* : déjà absents des 11 tables run-scopées (vérifié par balayage) — rien à purger, scripts QA conservés.
- [x] Drapeaux EBC/ER sur fiche (dette #10) : badge « partiellement en EBC (~N%) » / « emplacement réservé n°X », information seule (jamais exclusion), dérivé du frontend. Captures avant/après : reports/train-tech/ebc_er/.

## TRAIN 3 — PROD-CHECKS [M] Opus
- [ ] Check sécurité : /docs, LABUSE_SECRET_KEY, en-têtes, endpoints
- [ ] Check vitesse (endpoints clés, top 5 lent)
- [ ] Test architecture mail : tous les mails, envoi + rendu
- [ ] Inventaire des API déconnectées + plan de réparation

## TRAIN 4 — FILTRES / RECHERCHE [A] Opus
- [ ] Inventaire filtres : lesquels existent, marchent, mentent
- [ ] Architecture 2 voies : filtrer soi-même OU analyse LABUSE
- [ ] Filtrer sur tout (toute variable exposée)
- [ ] Théâtre de l'analyse : compteur en direct
- [ ] Tout montrer : l'écarté consultable avec son motif
- [ ] Filtrabilité par motif de déclassement (dette des 427)
- [ ] Fiche (surface) : adresse absente — (a) afficher « Adresse : Absente (BAN) », jamais un champ vide ; (b) ampleur RÉELLE (mesurée) : 46/117 brûlantes et 41 % du top-1000 sans adresse → enrichissement adresse sur les têtes, pas qu'un habillage (cf. A1.3)
- [ ] Fiche (surface) : sous une surface plancher (à définir), dire « délaissé » au lieu de dérouler un bilan — anomalie AI1886 : bilan R+6 servi sur une parcelle de 9 m²
- [ ] Passe de clarté générale

## TRAIN 5 — SCORING [S] Fable
- [ ] **PRIORITÉ HAUTE (Vic 04/08) — Rebuild parcel_renouvellement sur q_v8_calibre** : actif unique du positionnement (68 445 parcelles, 0 concurrent), mort en silence depuis la bascule v8 (resté sur q_v7_defisc). Mesure avant/après, POINT D'ARRÊT. Même motif constaté sur : entonnoir_motifs (mort depuis q_v2/q_v6 — DEUX bascules ratées) ; ia_cache (q_v6/q_v7 — cache froid, se régénère seul, sévérité faible). Doctrine : toute table run-scopée entre dans le geste de bascule OU est déclarée cache.
- [ ] Étapes exactes de l'algo, écrites (parcelle brute → tier servi)
- [ ] Audit complet P et C
- [ ] Dette #4 : filtre client bâti + hiérarchie par année (DPE/BDNB)
- [ ] **Dette #4 RACINE (accepté Vic 04/08) : rechargement de la couche batiment** — 1 061 parcelles piscine-sur-couche-vide (456 secteurs, 24 communes ; Saint-Paul 188 en tête), dette diffuse → recharger par commune. Conditionne : la levée de l'exception CH1893 (motif en base l'y lie), l'arbitrage des 46 suspectes, et le filtre client bâti ci-dessus.
- [ ] **PRIORITAIRE (Vic 04/08) — Saturation p=1,0** : 5 parcelles à p_raw=1,0 exact aux rangs 1-5 → le sommet du classement est un ex aequo départagé par un tri arbitraire (sujet de CRÉDIBILITÉ : le « n°1 de l'île » doit être le meilleur, pas le premier d'une égalité). À mesurer AVANT tout autre chantier scoring : (a) combien de parcelles p_raw ≥ 0,99 et leurs rangs ; (b) « permis < 2 ans » (+1,30) seule cause ? ; (c) si on la plafonne, le top 20 change-t-il d'ordre ? ; (d) proposer un départage EXPLICITE des ex aequo (surface, faisabilité, charge foncière) plutôt qu'un tri implicite.
- [ ] Dette #9 : mérite/héritage servi sur la fiche
- [ ] Dette #11 : assemblage × propriété DGFiP
- [ ] Cartographie retenue/écartée : motif traçable par parcelle
- [ ] Anomalie AT1740 : « constructible N » + SDP 2 689 m² en zone N + 19-22 logts, ET deux SDP différentes sur la même fiche (2 689 vs 2 827). Mesurer : combien de zones N servent une SDP > 0 ? Localiser la violation du point de calcul unique.
- [ ] Revue de code intégrale (propositions, rien d'appliqué)

## TRAIN 6 — CALIBRATION-14 + ANNUAIRE [S] Fable — fil continu
- [ ] Re-télécharger les archives manquantes (parallèle, sha vérifié)
- [ ] Extraction exhaustive des 14 communes restantes
- [ ] Saint-Benoît : 19 fiches annexes une à une
- [ ] Saint-Paul → fermee + scan formulations (20 communes)
- [ ] Saint-Leu : calibrer depuis le règlement 2013
- [ ] OAP : extraire et brancher (prévalence)
- [ ] Annuaire PLU interrogeable (verbatim + article + page + lien)
- [ ] Garde-fou fraîcheur GPU-vs-mairie
- [ ] Rebuild + re-score final post-calibration (bascule, 5 gardes)

## TRAIN 7 — MODE B [A] Opus
- [ ] Bilan réhabilitation 24/24 (mandat + maquette prêts)

## TRAIN 8 — VPS / PRODUCTION [A] Opus — dernier avant client
- [ ] Déploiement VPS + Caddy + certificats + SECRET_KEY
- [ ] Licence nominative, session concurrente unique
- [ ] Stripe live + page tarifs réelle
- [ ] Site vitrine labuse.immo à jour
- [ ] Discours commercial

## Vic seul (hors trains)
- [~] Réponse mairie Saint-André (relancer si silence)
- [ ] Mairie Saint-Benoît : modifs n°2 et n°3
- [ ] Avocat CGU/CGV
- [ ] Appel promoteur : coût construction → Sourcé
- [ ] Décision exposition O12 · mode D · C5 · EnR

## Dettes (index)
#4 bâti · #9 mérite/héritage · #10 EBC/ER · #11 acquérabilité ·
geometrie_drapeau · fraîcheur GPU-vs-mairie · couche batiment lacunaire ·
exceptions actives : CX2555 (chaude), CH1893 (retirée)
