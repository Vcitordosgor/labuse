# PRÉ-VOL M7 — la moitié locale du déploiement (mode autonome total)

Branche `prevol/m7` · un lot = un commit [P1]…[P7] · Vic absent (zéro sollicitation) · STOP final à son
retour. Interdits tenus : aucun ssh VPS, aucun début de M7, aucun refactor des monolithes, aucune écriture
DB destructive hors la base de répétition P3.

---

## P1 · Câblage ingest-permits ✅

**Constat** : le **cron de prod était DÉJÀ sur la voie vivante** (`deploy/cron.d/sitadel` →
`python -m labuse.ingestion.permits_sdes --refresh`) — mais la **commande CLI `ingest-permits` appelait
encore la voie MORTE** (`permits.ingest_permits`, ODS Région, plus alimentée depuis 2023-09).

**Fix** : la commande CLI est rebranchée sur `permits_sdes.run(refresh, geocode)` (flux national
SDES/Dido, Sitadel3, dép. 974, MAJ mensuelle) — mêmes options que le cron (`--refresh` = delta avec
recouvrement 3 mois ; défaut = backfill complet). `geocode-permits` inchangée (helper cadastre VIVANT de
permits.py, générique). La voie ODS reste en legacy documenté, appelée par personne.

**Preuve du câblage final** (`tests/test_ingest_permits_cablage.py`, 4/4 verts) :
1. appel CLI mocké → `permits_sdes.run(refresh=True, geocode=True)` reçu (le chemin de code, prouvé) ;
2. défaut = backfill (`refresh=False`) ;
3. le cron.d pointe `permits_sdes --refresh` et jamais la legacy ;
4. grep : `ingest_permits(` (ODS morte) n'a plus AUCUN appelant dans src/.
