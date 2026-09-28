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
