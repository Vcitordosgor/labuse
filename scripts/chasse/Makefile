# CHASSE-1 — rejouable d'une commande :  make -C scripts/chasse chasse
# (le mandat n'autorise d'écrire que scripts/chasse/ et docs/audit-2026-10/CHASSE-1/,
#  d'où un Makefile ici plutôt qu'à la racine)
# Prérequis : base dev lisible (postgresql://openclaw@localhost:5432/labuse),
#             venv ~/Desktop/labuse/.venv, PYTHONPATH racine du repo.

PY      := /Users/openclaw/Desktop/labuse/.venv/bin/python
RACINE  := $(abspath $(CURDIR)/../..)
ENV     := cd $(RACINE) && LABUSE_RATE_LIMIT_OFF=1 PYTHONPATH=src:. $(PY)

chasse: echantillon invariants couverture intruses face_a_face filtres horloge

echantillon:
	$(ENV) -m scripts.chasse.echantillon

invariants:
	$(ENV) -m scripts.chasse.invariants

couverture:
	$(ENV) -m scripts.chasse.couverture

intruses:
	$(ENV) -m scripts.chasse.intruses

face_a_face:
	$(ENV) -m scripts.chasse.face_a_face

filtres:
	$(ENV) -m scripts.chasse.filtres

horloge:
	$(ENV) -m scripts.chasse.horloge

.PHONY: chasse echantillon invariants couverture intruses face_a_face filtres horloge
