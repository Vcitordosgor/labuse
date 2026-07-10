# Notes de travail — mandat Wave Adresses, Courrier, Protection & Recherche IA

Notes intermédiaires (matière du rapport de fin). Branche `feat/wave-adresses-courrier-ia`.

## Phase 0 — comptes/sièges/plans (10/07/2026)

Vérifié en base : AUCUNE table comptes/sièges/plans (seule `api_keys` — quotas des clés
partenaires, pas des comptes utilisateurs ; l'auth app = mot de passe pilote unique).
Décision conforme au mandat : quotas + rate limiting au niveau **session/IP**, gating par
plan **stubbé** (constantes + branchements prêts), et **« mandat Auth & Plans » = prérequis
à la commercialisation** (à reprendre au rapport de fin).

## Lot 5 — CERFA vérifié (recherche 10/07/2026)

- **CERFA n° 13406\*17**, en vigueur depuis le **01/07/2026** (les guichets SVE rejettent
  les \*15/\*16 depuis la généralisation du dépôt dématérialisé au 01/01/2026).
- PDF officiel vendorisé : `data/cerfa/cerfa_13406-17.pdf` (source :
  https://www.formulaires.service-public.gouv.fr/gf/cerfa_13406.do — sert toujours la
  version courante). AcroForm remplissable, 20 pages, 376 champs (vérifié pypdf).
- Champs TERRAIN (page 5 du PDF = « 3/18 », cadre 3.1) :
  adresse `T2Q_numero`, `T2V_voie`, `T2W_lieudit`, `T2L_localite`, `T2C_code` ;
  parcelles 1-3 : `T2{F,S,N,T}_…`, `T2{F,S,N,T}P2_…`, `T2{F,S,N,T}P3_…`
  (préfixe/section/numéro/superficie) ; superficie totale `D5T_total`.
  Au-delà de 3 parcelles → annexe « références cadastrales complémentaires ».
- Identité demandeur (page 2/18) : `H1N_nom`, `H1P_prenom`, … — champs PROJET laissés
  vides par le pack (mandat).

## Lot 3 — anti-scraping (audit « front sobre » + clauses CGV)

**Audit des endpoints massifs (3.5)** :
- Bornés correctement : `/parcels` (limit ≤ 1000), `/discover` (≤ 2000), `/voisinage`
  (LIMIT servi), `/segments/query` (≤ 500, geojson ≤ 5000), `/segments/export` (≤ 10 000,
  désormais filigrané), tuiles MVT (par nature).
- **Point d'attention : `/map/parcels.geojson`** (UI Vue legacy « /app », transition) :
  jusqu'à 200 000 parcelles avec géométries en un GET. Non cassé (l'UI legacy en dépend)
  mais mis SOUS SURVEILLANCE : chaque appel est journalisé dans consultation_log (signal
  volume du scan quotidien) et soumis au rate limiting. À décommissionner avec l'UI Vue.
- Rate limiting : 60 req/min/sujet (config), défi arithmétique par épisode de burst,
  gel au 3e épisode du jour + alerte admin. Quota fiches : 300/jour/sujet, gel à minuit.
  Sujet = session sinon IP (Phase 0 — sans comptes). Scan quotidien abuse_scores
  (séquences d'IDU, cadence machinale, volume nocturne, ratio sans export) — JAMAIS de
  blocage auto, gel manuel via /protection/admin.
- Watermark exports : colonne `ref` (HMAC sujet+jour, clé = LABUSE_SECRET_KEY) + 2-3
  canaris (micro-variations de formatage de voies réelles) → export_fingerprints.

**Clauses CGV à faire rédiger (action Vic, hors mandat)** :
1. Interdiction d'extraction systématique ou massive (scraping, robots, contournement
   des quotas), y compris par partage de session.
2. Les exports sont tatoués (référence + enregistrements témoins) ; toute republication
   ou revente de données exportées est interdite et traçable.
3. Dépassements de quotas / détection d'abus → suspension immédiate puis résiliation
   sans remboursement ; responsabilité de l'abonné pour les accès sous ses identifiants.

## Lot 1 — BAN 974

- Export officiel : https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz
  (Licence Ouverte). Téléchargé 10/07/2026 : **340 771 adresses**, 0 sans voie ni lieu-dit.
- `cad_parcelles` (rattachement cadastral BAN natif) rempli à **35,3 %** seulement →
  jointure spatiale point-dans-parcelle = méthode principale (mandat), `cad_parcelles`
  en complément, plus proche parcelle < 20 m en dernier recours.
- `type_position` : entrée 155k, bâtiment 57k, parcelle 50k, segment 40k, logement 27k.
- RNIC : 287/2220 copropriétés sans `parcelle_idu` (12,9 %) — colonnes `adresse`,
  `insee`, `commune` disponibles pour le rattachement via la table `adresses`.
