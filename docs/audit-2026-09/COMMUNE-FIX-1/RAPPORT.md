# COMMUNE-FIX-1 — fiche commune : 13 corrections après recette

**Branche** `fix/commune-fix-1` (worktree `~/Desktop/labuse-commune`, base `main ea6feb72`). App recette : API `:8155`, front `:5355`.
**Témoins** : Saint-Paul (97415), Saint-Denis (97411), Cilaos (97424).
**Captures** avant/après (1440 px, DSR 2) : `captures/{avant,apres}-{saint-paul,saint-denis,cilaos}.png`.

Doctrine respectée : *un seul moteur, une seule donnée* ; introuvable = « non disponible » sourcé, jamais un zéro
menteur ; chaque nouvelle ligne passe par `declarations/commune/` et le verrou **V5e** (resté vert).

---

## A · Faux ou trompeur

### A1 — Habitants : population LÉGALE INSEE (et non Filosofi)
Le bandeau et la carte Population affichaient **96 786 « INSEE »** = en réalité l'agrégat **Filosofi** (carreaux
fiscaux), qui sous-estime. On sert désormais la **population municipale légale INSEE** (`sudocuh_procedures.pop_mun`,
qui reporte les populations légales), avec son millésime. Les **ménages** viennent des **résidences principales du RP**
(`commune_insee_logement`, base cohérente avec la population légale). **Filosofi ne sert plus que le niveau de vie.**

| témoin | avant (Filosofi) | après (légale INSEE) | ménages (RP) | niveau de vie (Filosofi) |
|---|---|---|---|---|
| Saint-Paul | 96 786 | **105 240** (+ pop. totale 106 554, mil. 31/12/2024) | 42 756 | 22 018 €/an |
| Saint-Denis | — | **154 765** | 68 726 | 21 794 €/an |
| Cilaos | — | **5 390** | 2 092 | 16 138 €/an |

*Fichiers* : `api/fiche_commune.py:population`, `registre/donnees.py:habitants_n` (source corrigée), `registre/lectures.py`, `ContextePanel.tsx`.

### A2 — Écart demandé/acté : seuil Radar (30)
L'écart demandé/acté (−31,1 % à Saint-Paul) et le prix demandé médian étaient servis **sur 5 biens**. On applique le
**seuil Radar (30)** (`pige/signaux.SEUIL_REF_TYPE`) : sous 30 biens relevés, la fiche affiche **« sous le seuil
(N biens) »**, jamais un pourcentage. Saint-Paul (5 biens) → sous le seuil ; Saint-Denis (59 biens) → **+19,8 %** servi.
*Fichier* : `api/fiche_commune.py:marche_annonces` + carte Activité (`ContextePanel.tsx`).

### A3 — « 7 499 LLS » : dit ce que c'est + base du taux
La ligne SRU nomme désormais **« 7 499 logements sociaux (LLS) — stock au dernier inventaire SRU »** avec le millésime
(*inventaire LLS 01/01/2024*), et **écrit la base du taux** : les 18,33 % rapportent les LLS aux **résidences
principales retenues pour la SRU (≈ 40 900)** — base **différente** des ménages affichés plus haut. Cohérence vérifiée
(7 499 / 0,1833 ≈ 40 900). *Fichier* : carte Population (`ContextePanel.tsx`).

### A4 — « rafraîchis chaque nuit » : faux → la cadence est rendue VRAIE
**Cause** : le job nocturne `fiche-commune-cache` avait été **retiré du registre CRON** (« réchauffeur non
essentiel ») → aucune tâche ne rafraîchissait le cache ; le pied promettait « rafraîchis chaque nuit » alors
que plus rien ne le garantissait. La **date** affichée, elle, était vraie.
**Correctif** : plutôt que de mentir en creux (softener le pied), on **réinscrit le job au registre** pour que
la promesse redevienne exacte. `fiche-commune-cache` est de nouveau déclaré (`jobs.py`, quotidien `0 23 * * *`
UTC = 03:00 Réunion, timeout 1800 s), son implémentation existait déjà (`jobs_impl.fiche_commune_cache` :
précalcul isolé des 24 communes dans `commune_contexte_cache`, une ratée n'arrête pas le lot). Le crontab
généré depuis le registre le porte donc automatiquement (wrapper `run-job.sh` + verrou flock). Le pied peut à
nouveau dire *« Compteurs précalculés le {date} (rafraîchis chaque nuit). »* sans mentir. Le cache des 24
communes a par ailleurs été **recalculé** (date réelle = 25/09/2026).
*Test* : `test_commune_fix1.py::test_a4_job_cache_nocturne_enregistre` (job présent, quotidien, sort au crontab)
+ `test_cron1_lot3.py` (une ligne par job du registre : 19 → 20). *Fichiers* : `jobs.py`, pied (`ContextePanel.tsx`).

## B · Cassé

### B5 — « Voir ses parcelles » branché (zoom + filtre)
Le bouton posait bien le filtre commune, mais le **recadrage carte** reposait sur l'effet « fit au *changement* de
commune » — inopérant quand la fiche est ouverte via le clic-commune (la commune est **déjà** la courante) → le bouton
semblait mort. Ajout d'un nonce **`refitCommune()`** qui force le recadrage sur l'emprise de la commune. *Test*
`ficheCommune.test.ts` (COMMUNE-FIX-1 B5). *Fichiers* : `store/useApp.ts`, `map/MapView.tsx`, `ContextePanel.tsx`.

### B6 — jargon interne retiré + Foncier lit le run servi
Libellés de source rendus lisibles pour le client :
- `m10 (délais)` → **« SITADEL — délais d'instruction »** (`fiche_commune.py` : comparable, permis, repli).
- `M40 plu_millesimes` → **« GPU — millésime du PLU opposable »** (`config/veille_plu.yaml`, 7 sources).
- `Sourcé LABUSE · run q_v11_m137` → **« Analyse LABUSE · run servi »** (`marche_commune.py:ligne7_gisement` ; le
  libellé technique du run reste dans `date_amont`, interne).

**Foncier** : `ligne7_gisement` lit la **vue `parcel_residuel`** qui filtre dynamiquement sur `residuel_runs.is_served`
(= run **8**, = manifeste) — **aucun run codé en dur** (confirmé). *Test-garde* `test_commune_fix1.py`.

### B7 — contact mairie : vérifié conforme à l'annuaire
Vérification des **24 communes** contre l'**annuaire service-public en direct** : les e-mails et sites sont **déjà
identiques à l'annuaire** (ex. Saint-Paul = `maire@mairie-saintpaul.fr` **.fr** + `www.mairie-saintpaul.re` **.re**,
tous deux confirmés ; Saint-Denis : e-mail réellement absent). Le mélange .fr/.re est **réel dans l'annuaire** — rien
n'est faux. Décision Vic : accepter l'annuaire + **garde** (attrape une future inversion e-mail/site).

### B8 — ORT + FRR
- **ORT** : le libellé distingue les 3 états réels — **« ORT — commune signataire »** (Saint-Paul, `ort_signee=true`),
  **« ORT dans l'EPCI — commune non signataire »**, **« Aucune ORT »**. Fini le trompeur « ORT (autre commune
  signataire) ». *Fichier* : carte Fiscalité (`ContextePanel.tsx`).
- **FRR** : décision Vic — **libellé conservé** (« classée en partie (les Hauts) » peut être réel : à La Réunion le FRR
  s'appuie sur la ZSAR infra-communale, arrêté 19/06/2024 visant le décret 78-690). **Garde** verrouillant la
  classification sourcée du seed (3 en totalité : Cilaos/Salazie/Plaine-des-Palmistes ; Le Port hors ; 20 en partie).
  ⚠ La vérification ligne à ligne contre le fichier officiel « La Réunion par communes 2025 » de l'Observatoire des
  territoires (+ arrêté modificatif 14/04/2025) **reste à faire à la main** : le jeu n'est pas exposé par une API.

## C · DA des outils proposés

### C9 — section « Étudier cette commune » (composant partagé)
Les 3 raccourcis en tête **et tous les liens texte « → » des cartes** (Ouvrir Permis, Densifier, Voir le PLU, Étude de
zone, Voir les annonces Radar, Voir tous les outils) sont **supprimés**. À leur place, une section **« Étudier cette
commune »** qui reprend **exactement** le composant partagé de la fiche parcelle (`GrilleOutils`/`OutilCase`, tuiles
icône-dans-un-carré + survol vert plein) : tuiles **PLU · Permis · Densifier · Étude de zone · Communes**, pré-remplies
sur la commune. Aucune nouvelle DA.

## D · Ce qui manque

### D10 — Taxe d'aménagement communale ✅
Ajoutée à la carte Fiscalité, **même source que l'outil Taxe** (`taxe_amenagement.taux_communal_public`,
`taxe_amenagement_taux`, DGFiP/DELTA). Saint-Paul **5 %**, Saint-Denis **3 %**, Cilaos **5 %**. Pas de taux **sectoriel**
à La Réunion dans la source (aucun inventé). Déclarée (`regles.yaml`) + robinet `fiche_commune_fiscalite` + V5e vert.

### D11 — Tendance de population 2017-2023 (RP) ⚠ pas de source en base
**Cas non rangé** : aucune **série temporelle** de population n'existe en base — seulement des instantanés (Sudocuh
`pop_mun`, géographie 01/01/2024 ; SRU `population_2025`), pas un 2017 **et** un 2023. Conformément à la doctrine, **rien
n'a été inventé**. À faire : ingérer un millésime RP historique (populations légales INSEE 2017) pour calculer la tendance.

### D12 — Procédures PLU en cours + contact urbanisme
- **Procédures PLU** ✅ : la carte Urbanisme affiche la **procédure au dernier relevé Sudocuh** (état détaillé, date de
  prescription, millésime). Saint-Paul : *« révision de PLU », prescrite le 16/12/2021 (Sudocuh 31/12/2024)*. Déclarée
  (`plu_procedure_en_cours`) + robinet + V5e vert.
- **Contact service urbanisme** : l'annuaire service-public **ne fournit pas** de contact « service urbanisme » distinct
  par commune (Saint-Paul : 0 résultat ; Saint-Denis : seulement des organismes régionaux CAUE/DEAL/ADIL). La carte
  Identité conserve le contact mairie déjà **libellé « Mairie & service urbanisme »** (+ contacts nommés admin). Rien à
  ajouter honnêtement.

### D13 — Acquéreurs récents (PM) ✅
La carte Activité affiche les **5 premiers acquéreurs PM** (endpoint dédié `/communes/{c}/acquisitions-pm`, qui existait
sans carte), chacun **cliquable → Scan patrimoine** (SIREN), + lien « Tous les acquéreurs » vers l'outil Communes.
Constat sourcé (changement de millésime PM, n'affirme pas une vente), hors scoring.

---

## Vérifs
- **tsc / build / vitest** : verts (vitest **188**, dont B5). 
- **pytest** : garde COMMUNE-FIX-1 (7) verte ; **V5e** vert ; V5b corrigé (`plu_procedure_en_cours` en type `texte`).
  Échecs pré-existants (order-pollution de la base réelle, hors périmètre) : `test_garanties` G2/G4/G5/G6,
  `test_verrous_lot1_passent_sur_la_base_reelle` — passent en isolation.
- Cache des 24 communes recalculé (date réelle 25/09/2026).
