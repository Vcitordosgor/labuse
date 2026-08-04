# BACKLOG LABUSE — source de vérité

> Règles : CC met à jour ce fichier à la fin de chaque train (statuts + date).
> Vic arbitre, CC exécute, ce fichier fait foi.
> Statuts : [ ] à faire · [~] en cours · [x] fait · [!] bloqué (dire par quoi)

Dernière mise à jour : 2026-08-04 — train-tech (CC, branche org/train-tech) : tops régénérés
(run servi), gardes de bascule en module, A1.3 mesurée, purge q_v8_au_* vérifiée, drapeaux EBC/ER servis.

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
- [ ] Option B : pondération au_sous_plancher ×(1−manque/seuil)
- [ ] Mesure d'effet sur les 708, re-revue des mouvements en tête
- [ ] Lever l'exception CX2555 une fois la pondération servie
- [ ] Dette #4 : mesure à blanc des 41 têtes suspectes (batiment≈0 vs ortho)
- [ ] Lever l'exception CH1893 selon résultat

## TRAIN 2 — TECH [M] Opus — en parallèle de tout
- [x] Rebase + push EXPRESS-01 : EXPRESS-01 (485f7a9) déjà mergé dans main → fast-forward. 3 poses IDU (Fiche/Tinder/Kanban) déjà servies ; 4e pose (gen_tops) livrée avec les tops ci-dessous.
- [ ] Merge fix/m13-e (Vic merge), puis rebase EXPRESS-01 dessus — action Vic, non faite par CC.
- [x] Régénérer les tops : IDU complet + run servi (Q_A_RUN_LABEL au lieu de q_v2 gelé/absent). 25 HTML (24 communes + top50) régénérés sur q_v8_calibre, générateur + HTML commités ensemble.
- [x] Gardes de bascule → briques importables (module src/labuse/bascule_gardes.py) : 5 gardes extraites VERBATIM, bascule les importe, aucune logique recopiée. Tests verts.
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
- [ ] Étapes exactes de l'algo, écrites (parcelle brute → tier servi)
- [ ] Audit complet P et C
- [ ] Dette #4 : filtre client bâti + hiérarchie par année (DPE/BDNB)
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
