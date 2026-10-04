# LABUSE — cibles utilitaires.
# (Créé par l'audit PROPRETE-1 ; seule cible actuelle : les mesures de propreté.)

.PHONY: proprete
proprete: ## Rejoue toutes les mesures de l'audit propreté (lecture seule, sorties dans scripts/proprete/raw/)
	bash scripts/proprete/run_all.sh
