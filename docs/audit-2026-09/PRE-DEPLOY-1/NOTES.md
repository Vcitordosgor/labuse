# PRE-DEPLOY-1 — notes déposées par d'autres mandats

Notes à traiter/valider lors du mandat PRE-DEPLOY-1.

## FRONT-CHIFFRES-2 — le banc de cohérence ne doit JAMAIS dépendre de LABUSE_DEV_MODE
- **Contexte** : en DEV, rejouer le banc (`labuse coherence` / `scripts.coherence.banc`) pendant des
  redémarrages d'API déclenchait le **compteur anti-scraping** (rate-limit 60/min + gel, `api/protection.py`)
  → 429 en boucle, banc ralenti/bloqué. Le seul court-circuit existant était `LABUSE_DEV_MODE`, qui a
  d'AUTRES effets (« comme partout ») — le banc ne doit pas en dépendre.
- **Fait** : levier LOCAL dédié `LABUSE_RATE_LIMIT_OFF=1` (config `rate_limit_off`) qui court-circuite
  la protection anti-scraping (rate-limit + quotas de consultation) SANS les autres effets de dev_mode.
  Off par défaut ; la prod ne le pose pas ; explicite (jamais une détection localhost).
- **Garde-fou** : `tests/test_rate_limit_off.py::test_banc_ne_depend_pas_de_dev_mode` échoue si un
  fichier de `scripts/coherence/` référence `dev_mode`/`LABUSE_DEV_MODE`.
- **À VÉRIFIER en PRE-DEPLOY-1** : (1) `LABUSE_RATE_LIMIT_OFF` **absent** de l'environnement de PROD
  (c'est un flag dev/ops uniquement — sinon la protection anti-scraping est désactivée en prod) ;
  (2) le job nocturne `coherence-banc` tourne SANS dev_mode ni rate_limit_off en prod (il doit
  passer la protection légitimement — sujet allowlisté `LABUSE_QA_ALLOWLIST`, ou débit sous 60/min).

## CatNat — carte risques (Géorisques brut) vs compte servi (dédoublonné) — ARRÊTÉ pour décision Vic
- **Observation** : 97410 15≠17, 97418 20≠22 (écart constant −2).
- **Analyse** (FRONT-CHIFFRES-2) : nos trois lecteurs servis (fiche parcelle `fiche_blocs3.catnat.total`,
  fiche commune `fiche_commune`, page Sources `filtres/sources`) donnent TOUS **15/20** — `count(*)` sur
  `catnat_arretes`, table **dédoublonnée** à l'ingestion (contrainte UNIQUE `insee,type_peril,date_arrete,
  date_debut`). Le front affiche 15/20 PARTOUT (liste risques + compteur ContextePanel) : **aucune
  incohérence interne**. Le 17/22 est le **compte Géorisques BRUT** (GASPAR renvoie 2 arrêtés qui
  partagent péril+dates → dédoublonnés par DESIGN, décision COHERENCE-FIX-1 « CatNat dédoublonné GASPAR »).
- **Donc** : notre 15/20 est correct-par-choix ; le 17/22 réintroduirait les doublons GASPAR.
- **ARRÊTÉ** : si Vic veut aligner sur le brut Géorisques (17/22), il faut **re-ingérer `catnat_arretes`
  avec une clé de dédoublonnage incluant `code_national_catnat`** (recalcul de table) ET revenir sur le
  dédoublonnage COHERENCE-FIX-1. Recalcul de table → hors périmètre FRONT-CHIFFRES-2 (garde-fou : arrêté).
  À trancher : le doublon GASPAR est-il un vrai doublon (garder 15) ou 2 arrêtés distincts (passer à 17) ?
