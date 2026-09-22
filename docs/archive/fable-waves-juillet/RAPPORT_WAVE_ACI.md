# Rapport de fin — mandat Wave Adresses, Courrier, Protection & Recherche IA

**Branche** : `feat/wave-adresses-courrier-ia` (7 commits atomiques, jamais mergée — merge Vic `--no-ff`).
**Ordre exécuté** : Phase 0 → 1 → 3 → 4 → 6 → 2A → 5 → 2B. QA : 46 tests pytest verts + E2E Playwright 7/7 (`qa/e2e_wave_aci.mjs`).

---

## Phase 0 — comptes/sièges/plans

AUCUN système de comptes en base (auth pilote = mot de passe unique). Conformément à
l'ajout session : quotas et rate limiting au niveau **session/IP** (`sujet` = hash du
cookie de session, sinon de l'IP), gating par plan **stubbé** (`src/labuse/plans.py` :
constantes Essentiel/Intégral, `plan_courant()` lit `LABUSE_PLAN_DEFAUT`, branchements
posés dans Dossier/pré-dossier/NL). **⚠ Le « mandat Auth & Plans » est un PRÉREQUIS à la
commercialisation** : sans lui, tous les « sièges » d'un client partagent les quotas d'une
session, et le gel vise une session/IP, pas un compte.

## Lot 1 — Adresses BAN ↔ parcelles

- **339 941 adresses** (export officiel BAN 974, Licence Ouverte) → table `adresses`.
  **Taux de rattachement : 99,99 %** (critère SQL ≥ 0,9 : **0,9999**) — point-dans-parcelle
  319 391, assiette `cad_parcelles` BAN 1 420, plus proche < 20 m 19 109, 21 non rattachables.
- **Index inverse n-n `adresse_parcelles`** (une adresse dessert plusieurs parcelles :
  assiette cadastrale BAN + bâtiments à cheval sur 2 parcelles, seuil 15 m² de part et
  d'autre) : **86,7 % des parcelles bâties (emprise ≥ 20 m²) portent ≥ 1 adresse**.
  Le mandat visait ≥ 90 % : le déficit est l'ADRESSAGE BAN des hauts, pas le rattachement
  (Salazie 71,8 %, Saint-Leu 79,0 %, Sainte-Rose 79,1 % vs Sainte-Marie 91,6 %) ; le seuil
  d'emprise n'y change rien (89,3 % même à ≥ 80 m²). **Échantillon de 30 à valider
  visuellement par Vic** (critère d'acceptation) — je recommande de juger commune par commune.
- **Exports « à l'occupant »** : adresse BAN normalisée (Numéro/Voie/CP/Ville) prépendue
  D'OFFICE à tous les presets (résilient si table absente). Filtre `adresse_ban` ajouté au registry.
- **Copros RNIC** : 216/287 rattachées par adresse (match strict numéro+voie+INSEE unique) ;
  reste 71 « aucun » honnêtes (24 ambiguës, 47 sans correspondance). 2 149/2 220 copros liées (96,8 %).
- **Refresh mensuel** : `deploy/cron.d/ban` (le 5 à 03h30, avant Sitadel/CATNAT) — `labuse ingest-ban --download`.

## Lot 3 — Anti-scraping (seuils ACTIFS)

| Protection | Seuil actif (config) |
|---|---|
| Quota fiches parcelle | **300/jour/sujet** (`LABUSE_QUOTA_FICHES_JOUR`), dédup par idu, gel jusqu'à minuit, persisté |
| Rate limiting | **60 req/min/sujet** (`LABUSE_RATE_LIMIT_RPM`) sur les endpoints métier (jamais tuiles/statiques) |
| Burst | défi arithmétique par ÉPISODE ; **gel + alerte admin au 3e épisode/jour** (`LABUSE_RATE_BURST_GEL`) |
| Détection | job quotidien `labuse abuse-scan` (cron.d/abuse, 06h) : séquences d'IDU, cadence machinale, volume nocturne, ratio sans export → `abuse_scores` ; **alerte à 60**, JAMAIS de blocage auto — gel manuel via `/protection/admin` |
| Watermark | colonne `ref` (HMAC sujet+jour, clé `LABUSE_SECRET_KEY`) + 2-3 canaris (micro-variations de formatage de voies réelles) sur CHAQUE export → `export_fingerprints` (6 en base après QA) |

Audit « front sobre » : `/parcels` (≤ 1000), `/discover` (≤ 2000), `/segments/*` (≤ 500/5k/10k),
tuiles OK. **`/map/parcels.geojson` (UI Vue legacy, jusqu'à 200 k parcelles/GET)** : non cassé
mais journalisé + rate-limité — à décommissionner avec l'UI legacy.

**Clauses CGV à faire rédiger (action Vic)** : (1) interdiction d'extraction systématique/
contournement des quotas ; (2) exports tatoués, republication interdite et traçable ;
(3) suspension puis résiliation sans remboursement en cas d'abus, responsabilité de
l'abonné pour les accès sous ses identifiants.

## Lot 4 — Dossier parcelle PDF

`GET /dossier/{idu}.pdf` + bouton « Dossier » sur la fiche (Socle). Réutilise le générateur
Flash (mergé dans main par Vic) — libellé « Dossier parcelle · usage interne », mention
**« Généré via LABUSE pour [raison sociale] »** (`LABUSE_RAISON_SOCIALE`) sur chaque page.
Quota **20/mois** Essentiel / illimité Intégral (stub) ; `/dossier/statut` pour le front.
Génération mesurée : **~0,7-1,2 s** (critère < 30 s). Sans le module Flash → 501 honnête.

## Lot 6 — Recherche en langage naturel

- `POST /ia/segments-search` : question + registry sérialisé → claude-haiku-4-5 (temp. 0,
  AUCUNE donnée de la base) → JSON de filtres **validé contre le registry** (clé inconnue
  rejetée, valeurs au contrat du moteur, communes bornées aux 24) — jamais de SQL.
- Barre NL sur la page Segments → ouvre le **query builder standard**, filtres visibles/modifiables.
- **Score du jeu de test : 20/20** (`labuse nl-eval`, tests/nl_queries.txt ; acceptation ≥ 16).
  Deux échecs initiaux (18/20) corrigés par le prompt : « combien vaut ma maison » (le modèle
  renvoyait du texte non-JSON → out_of_scope explicite) et « passoires thermiques »
  (approximé en periode_construction → interdit d'approximer, listé hors registry).
  **0 champ hors registry exécuté** (garde-fou par construction).
- Quota **30/jour/sujet** ; log ANONYMISÉ `nl_query_log` (roadmap des filtres manquants :
  lire les out_of_scope). Gating plan : `plans.FILTRES_INTEGRAL` (vide — classification
  commerciale à trancher avec Auth & Plans, branchement prêt : grisé + CTA upgrade).

## Lot 2A — Publipostage

`POST /segments/publipostage` (bouton dans le builder) → ZIP : **CSV normalisé**
(Destinataire « À l'occupant » — jamais de nom de personne physique — Adresse L1/L2, CP,
Ville, IDU, ref) + **planches d'étiquettes PDF 63,5 × 38,1** (Avery L7160 3×7 ; 70x35 et
105x37 prêts, `LABUSE_ETIQUETTES_FORMAT`) + **gabarit de lettre** de la famille métier
(`config/gabarits_courrier.yaml`, 5 familles, textes éditables, hors scope juridique).
Adresse BAN exigée (filtre serveur) ; watermark Lot 3 appliqué. QA réelle : preset
pergolas-terrasses → 3 566 adresses, 170 planches.

## Lot 5 — Pré-dossier PC

- **CERFA vérifié : n° 13406\*17, en vigueur depuis le 01/07/2026** (les guichets SVE
  rejettent les \*15/\*16 depuis la généralisation du dépôt dématérialisé). PDF officiel
  vendorisé (`data/cerfa/`), AcroForm conservé.
- `GET /pre-dossier/{idu}.zip` (réservé Intégral) : CERFA pré-rempli des SEULS champs
  parcelle/terrain (cadre 3.1 : références cadastrales, adresse BAN, superficie — champs
  PROJET vides), plan de situation auto (fond OSM + contour), fiche des règles du zonage
  calibré + prescriptions + servitudes connues (ABF/ENS/QPV/aléas) + bordereau PCMI1-8.
- **Libellé préparatoire tamponné sur CHAQUE page** de chaque document.

## Lot 2B — Courrier par API : Merci Facteur retenu

**Constat structurant (sourcé)** : le 974 est du courrier INTÉRIEUR France (≤ 100 g égrené ;
flux industriel : +0,02-0,05 €/10 g dès 20 g — négligeable pour 3 pages). Le différenciateur
est l'API, pas le DOM.

**Grille de coûts (lettre 1-3 pages N&B, 2026)** :

| Prestataire | Éco/verte | LRAR | Fixe | DOM confirmé |
|---|---|---|---|---|
| **Merci Facteur (RETENU)** | ~2,19-2,69 € | 7,16 € | 19,95 €/mois (API prod) | acheminement oui (FAQ) ; tarif à confirmer en sandbox |
| MySendingBox | ~1,3-1,5 € (via `POST /letters/price`) | 5-7 € | 0 | contradictoire sur leur site — vérifier par l'API |
| Maileva (volume) | 1,44-2,02 € HT (G3) | ~1,0 € + affr. | 140-1 350 €/an | **contractuel (zone OM1)** |
| ClickSend / Lob / Quadient | — | — | — | écartés (fermé / US / pas de self-service) |

**Motif du choix** : seule offre avec doc API réellement publique + sandbox + webhooks
(preuve de dépôt, AR numérisé) + LRAR + self-service. Bascule Maileva pertinente > ~150 plis/mois.

**Implémenté** : `courrier_envois`, `POST /courrier/envois` (case « j'assume le contenu »
OBLIGATOIRE, plafond 100/jour/sujet, prix = coût × marge ×1,5 config), suivi, `/courrier/statut`.
Provider **stub** tant que le compte n'existe pas : rien ne part, **aucun bouton côté front**
(leçon TANIA). **Facturation : facture séparée mensuelle** (le plus simple — la table porte
coût/prix par envoi ; metered Stripe branchable quand Stripe Flash passera en production).

## Actions Vic (hors mandat)

1. **Mandat Auth & Plans** — prérequis commercialisation (quotas par siège, gel de compte,
   classification des filtres/features par plan).
2. **Échantillon de 30 adresses** à valider visuellement (acceptation Lot 1) + arbitrage du
   critère 90 % au vu du déficit d'adressage des hauts (86,7 % île, honnête).
3. **CGV** : 3 clauses anti-extraction à faire rédiger (détail §Lot 3).
4. **Compte Merci Facteur PRO** (19,95 €/mois) + valider en SANDBOX une adresse 97400 et le
   tarif réel, puis poser `LABUSE_MERCIFACTEUR_API_KEY/SECRET` et `LABUSE_COURRIER_PROVIDER=mercifacteur`.
5. Cron VPS : installer `deploy/cron.d/ban` et `deploy/cron.d/abuse`.

## Divers

- Fix transversal découvert en QA : les quotas utilisaient `CURRENT_DATE` (fuseau Postgres) —
  décalage d'un jour autour de minuit ; unifié sur l'heure locale python.
- Dette pré-existante inchangée : ~29 erreurs pyproj (env PROJ) sur les suites historiques,
  sans lien avec ce mandat (session dédiée déjà prévue).
