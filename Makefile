# LABUSE — cibles utilitaires.
# (Créé par l'audit PROPRETE-1 ; seule cible actuelle : les mesures de propreté.)

.PHONY: proprete
proprete: ## Rejoue toutes les mesures de l'audit propreté (lecture seule, sorties dans scripts/proprete/raw/)
	bash scripts/proprete/run_all.sh

# ── Tests par famille (CI-1 Lot 2) — voir docs/TESTS.md § « Familles de tests ». ──
# PYTHON surchargeable (défaut = venv du dépôt). PYTEST ajoute PYTHONPATH + cache off.
PYTHON ?= .venv/bin/python
PYTEST := PYTHONPATH=src $(PYTHON) -m pytest -p no:cacheprovider

.PHONY: test-unit test-db test-ci test-reel test-front
test-unit: ## Unitaires SEULES (aucune base) — rapide, famille du hook pre-push
	$(PYTEST) -m "not db and not local and not reel and not network" -q
test-db: ## Base de test (PostGIS vide + fixtures) — nécessite labuse_test accessible
	$(PYTEST) -m "db and not local and not reel and not network" -q
test-ci: ## Ce que joue la CI : unitaires + base de test (conteneur PostGIS)
	$(PYTEST) -m "not local and not reel and not network" -q
test-reel: ## Données réelles (base complète) — banc de nuit en prod, JAMAIS en CI
	$(PYTEST) -m "reel or local" -q
test-front: ## Front : tsc -b + vitest + vite build
	cd frontend && npx tsc -b && npx vitest run && npx vite build
