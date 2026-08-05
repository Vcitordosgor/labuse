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
- [x] Check sécurité : /docs, LABUSE_SECRET_KEY, en-têtes, endpoints — M31 : posture saine (docs local-only, secret fail-closed, admin middleware-gated, CORS restreint prod, .env jamais commité) ; garde test admin ajoutée. Voir qa/m31/M31_RAPPORT.md §PC2.
- [x] Check vitesse (endpoints clés, top 5 lent) — M31 : 5 endpoints servis < 1 s ; pas de N+1 fiche. Reste `/map/parcels.geojson` commune = 2,2 s sur Saint-Denis (candidat MVT commune). §PC3.
- [~] Test architecture mail : M31 — SPF ✓ ; **DMARC ABSENT** (à créer, `p=none` d'abord) ; **DKIM non aligné** (envoi Gmail perso `d=gmail.com` ≠ From `labuse.immo`). DNS/ops, hors code. Preuve qa/m31/preuve_dns_mail.txt. §PC4.
- [~] Inventaire des API déconnectées — M31 : cross-réf textuelle NON fiable (faux positifs massifs, ma propre erreur sur /map/parcels.geojson) → PAS de liste publiée. Exige une passe de **traçage par helper** api.ts. Seul candidat avéré : `/api/v1/*` (API partenaire externe, caller-less par conception — ne pas retirer sans savoir si un partenaire consomme). §PC4.
- [x] **[S] Vic — bascule run servi (révélé + CORRIGÉ M31)** : point de vérité UNIQUE versionné `config/served_run.txt = q_v8_calibre`, lu par backend + bundle (vite) + build-mvt. `LABUSE_SERVED_RUN` = override dev loggé WARNING. Suite verte sans env, golden 117/117, run servi identique (plomberie). §ANNEXE CORRECTION RUN SERVI.
- [ ] **[A] Passe helper-tracing des routes mortes** (déférée de M31) : résoudre chaque fn api.ts → chemin, tracer les appels, + fetch directs + cron/webhook/PDF, avant tout retrait.

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
- [ ] Vocabulaire produit (revue M30, 05/08/2026) — 5 libellés consignés, arbitrage Vic requis
      avant tout geste (3 autres corrigés au geste M30-revue : fermée à l'urbanisation,
      inconstructible (géométrie), AU statut suffixé) :
      · « Réserve foncière » (PRIORITAIRE : collision avec l'emplacement réservé PLU — c'est un tier)
      · « À creuser » (générique — garder si assumé)
      · « Viabilisation confirmée par les faits » (« confirmée » = faisceau ≥70 pts, pas certitude)
      · « Brûlante » (métaphore assumée produit)
      · « Potentiel ≥ /100 » (potentiel de QUOI = Score Q ; tip E1 M12 déjà présent)

## TRAIN 5 — SCORING [S] Fable
- [~] **N°1 — COUCHE BATIMENT : pilote CoSIA rendu, cartes DATÉES servies — attend contre-revue Vic des 14 + arbitrage GO.** Rappel brut 79 % / ajusté 100 % (les 8 « ratées » = erreurs de vérité terrain, contre-revue : pilote_cosia_discordances.pdf, cartes datées). **Correction 2ᵉ passe : l'ortho de revue N'ÉTAIT PAS périmée** (graphe de mosaïquage : les 14 zones = PVA 2025, vols 21/07-02/08/2025) — les divergences sont des différences de LECTURE (chantier/dalle vs Bâtiment ; produit-parlant CoSIA a raison), le 38 % reste LE taux. **Seuil 50 RÉFUTÉ par la mesure** (rappel 63 %, perd 6 vraies maisons à 23-45 m²) → seuil 20 conservé, cas limites à l'adjudication. Architecture validée : p_model_bati_cosia datée, max des deux emprises. AB1908 : à re-trancher par Vic (structure visible carte datée, CoSIA 160 m²) ; AB1910 confirmée nue (CoSIA 0). Effet Saint-Paul : 73/169 (43 %). Inventaire rétroactif : 0 revue à refaire pour cause d'ortho. RIEN branché.
- [~] Les 90 têtes vues bâties par le cadastre (2026-06) : revue-exceptions SANS déclassement automatique — cartes O12 en génération pour revue Vic (le cadastre ne voit que 3 % de l'angle mort et peut se tromper dans l'autre sens).
- [ ] Entretien (validé Vic, APRÈS le pilote) : BD TOPO trimestrielle avec dates conservées (code fait : ingest_batiments garde date_creation/date_modification/date_d_apparition/date_de_confirmation) + RNB pour l'ID pivot.
- [ ] **N°2 — Saturation p=1,0** : 5 parcelles à p_raw=1,0 exact aux rangs 1-5 → le sommet du classement est un ex aequo départagé par un tri arbitraire (sujet de CRÉDIBILITÉ : le « n°1 de l'île » doit être le meilleur, pas le premier d'une égalité). Mesures : (a) combien de parcelles p_raw ≥ 0,99 et leurs rangs ; (b) « permis < 2 ans » (+1,30) seule cause ? ; (c) si on la plafonne, le top 20 change-t-il d'ordre ? ; (d) départage EXPLICITE des ex aequo (surface, faisabilité, charge foncière).
- [ ] **N°3 — Rebuild parcel_renouvellement sur q_v8_calibre** : actif unique du positionnement (68 445 parcelles, 0 concurrent), mort en silence depuis la bascule v8. Mesure avant/après, POINT D'ARRÊT. Même motif : entonnoir_motifs (mort depuis q_v2/q_v6), ia_cache (cache). Doctrine : toute table run-scopée entre dans le geste de bascule OU est déclarée cache.
- [x] Étapes exactes de l'algo : docs/mandats/ALGO_ETAPES_EXACTES.md (9 étapes, fichier:ligne, 4 parcelles témoins, seuils vivants).
- [x] PHASE 2 RENDUE (6 audits, lecture seule, rien modifié — docs/mandats/train5/) : AUDIT1 saturation (3 à p=1,0 MAIS **top 1000 = 19 valeurs de p, 988/1000 ex aequo, palier de 514 — coupures de tiers en plein palier** ; départage explicite proposé) · AUDIT2 renouvellement (rebuild à blanc : 67 258, ~2 min, sans risque) · AUDIT3 entonnoir (317 lignes, secondes) · AUDIT4 P/C (+ bâties-connues : 8 brûlantes + 432/1043 chaudes (41 %), portées par tenure/permis et même la feature piscine +0,41 — le filtre doit être une règle produit, pas un poids) · AUDIT5 cartographie (motifs 100 % reconstructibles sur 50 000 testées ; trous : params de coupure non persistés, ordre intra-palier) · AUDIT6 SDP bâties (5 132 parcelles affichent 3,48 M m² de SDP terrain-nu-théorique ; recalcul = bascule complète type v8). **POINT D'ARRÊT — phase 3 sur arbitrages.**
- [ ] Dette #4 : filtre client bâti + hiérarchie par année (DPE/BDNB)
- [x] Dette #9 FERMÉE (signal servi, arbitrage b, 05/08) : parcel_entree_tete (514 entrées tracées via la chaîne d'archives), libellé factuel « entrée en tête à la bascule du JJ/MM — signal inchangé/en progression » (Sourcé), fiche seule, 0 effet de classement. À recalculer au geste de chaque bascule.
- [x] Dette #11 FERMÉE pour la part PM (signal servi, arbitrage b, 05/08) : parcel_acquerabilite 3 états factuels (même propriétaire PM 329 / distincts 46 / non déterminable 685) sur la mention assemblage, Sourcé SIREN DGFiP-Cerema (millésime amont non tracé → Estimé affiché, champ prévu). 0 effet de classement.
- [ ] Dette #11-PP (DISTINCTE, maintenue) : acquérabilité des personnes physiques NON déterminable — manquant nommé : source de propriété PP inexistante en open data (anonymisation DGFiP). Structurel.
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
geometrie_drapeau · fraîcheur GPU-vs-mairie · couche batiment lacunaire · #12 voirie surfacique absente (HE0234, M-C.4) ·
exceptions actives (run servi) : CH1893 + les 14 bâties de la revue dette #4
(CX2555 levée le 04/08 à la bascule pondération)

## Doctrine (leçons gravées)
- **Frontière modèle/règles (Vic 04/08, prouvée par la mesure piscine)** : « Le modèle prédit
  la mutation, il ne juge pas l'état de la parcelle. Tout ce qui relève de l'état (bâti,
  zone, statut) est une règle explicite, jamais un poids. »
- **RÈGLE DE CONCEPTION (Vic 04/08, 3 occurrences en une semaine — PLU GPU-vs-mairie, bâti
  BD TOPO-vs-cadastre triennal, ortho de revue) : « La fraîcheur d'une donnée est celle de sa
  source amont, jamais celle de son ingestion ni celle du moment où on la regarde. »
  EXIGENCE TRANSVERSE : toute couche servie porte la date de sa source amont, AFFICHÉE.**
  Audit 04/08 + mesures DVF (DVF_FRAICHEUR_MESURES.md) : **DVF est À JOUR au dernier millésime
  publié** (7 184 = 7 184 mutations 2025, vérifié au fichier ; le « retard » est le cycle
  semestriel de la source, ~3 273 mutations S1-2026 en attente d'octobre) MAIS **la tuile
  Marché sert la médiane SANS étiquette de fraîcheur** (le bandeau « ventes jusqu'à… » n'est
  que dans le tiroir Bilan) — et un cycle déplace les médianes de ±10-20 % dans plusieurs
  communes. Sitadel : parse corrigé (validation date, future→NULL tracée+compteur bruyant,
  ligne fautive neutralisée, 0 date future en base). DPE/BODACC sains. **SPEC millésime amont
  RÉDIGÉE (SPEC_MILLESIME_AMONT.md) — attend lecture Vic, rien d'implémenté.**
  Corollaire outillé : dates BD TOPO conservées à l'ingestion (fait) ; date de prise de vue
  affichée sur toute carte de revue (fait — helper qa/dette4/ortho_dates.py).
- **« Une détection d'indice ne prouve pas l'absence d'indice. »** (Vic 04/08 — le filet
  piscine/PV/DVF a ses propres trous, cas #079.) Ne jamais conclure « pas d'indice donc
  pas de bâti ».
