# CHASSE-1 — rejouable d'une commande :  make -C scripts/chasse chasse
# (le mandat n'autorise d'écrire que scripts/chasse/ et docs/audit-2026-10/CHASSE-1/,
#  d'où un Makefile ici plutôt qu'à la racine)
# Prérequis : base dev lisible (postgresql://openclaw@localhost:5432/labuse),
#             venv ~/Desktop/labuse/.venv, PYTHONPATH racine du repo.
# ⚠ le décodage des tuiles (face_a_face) exige frontend/node_modules (symlink accepté) —
#   sans lui, chaque lecture tuile sort « erreur lecteur » (CHASSE-2 l'a mesuré : 3 358
#   faux écarts dans la baseline committée, 6 260 au premier rejeu).

PY      := /Users/openclaw/Desktop/labuse/.venv/bin/python
RACINE  := $(abspath $(CURDIR)/../..)
ENV     := cd $(RACINE) && LABUSE_RATE_LIMIT_OFF=1 PYTHONPATH=src:. $(PY)

chasse: echantillon invariants couverture intruses face_a_face filtres horloge chasse2

# CHASSE-2 — l'échantillon neuf et les nouveaux invariants s'ajoutent au rejeu
# (mandat CHASSE-2 : sorties dans docs/audit-2026-10/CHASSE-2/).
chasse2: echantillon2 invariants2 libelles2 plausibilite face_a_face2

echantillon2:
	$(ENV) -m scripts.chasse.echantillon2

invariants2:
	$(ENV) -m scripts.chasse.invariants2

libelles2:
	$(ENV) -m scripts.chasse.libelles2

plausibilite:
	$(ENV) -m scripts.chasse.plausibilite_run13

face_a_face2:
	$(ENV) -m scripts.chasse.face_a_face2

# repro du cas AD0554 (API lancée requise sur LABUSE_CHASSE2_API, défaut 8755) — hors
# cible `chasse` : dépend d'un serveur externe et du réseau IGN.
ad0554:
	$(ENV) -m scripts.chasse.ad0554_flash_dossier

.PHONY: chasse2 echantillon2 invariants2 libelles2 plausibilite face_a_face2 ad0554

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
