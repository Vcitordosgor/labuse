# RAPPORT DE RECETTE — RADAR V0 (pige d'annonces)

Branche `feat/radar-v0`. Commits par lot P0→P6. Doctrines §2 tenues comme lignes non négociables :
collecte 100 % humaine · zéro republication · Sourcé/Estimé/Absent sur le rattachement · anti-invention
sur l'extraction · Radar hors scoring · schéma `pige_*` isolé.

---

## P0 — Socle données + garde légale — **FAIT**

**Schéma isolé `pige_*`** (`src/labuse/pige/tables.py`, DDL idempotente FIX-GB-011, ensurée au boot
(`app.py` heal step « pige ») ET en base de test (`conftest.py`)) — 6 tables :
`pige_biens` (bien physique + rattachement niveau/confiance + statut de cycle + dates),
`pige_annonces` (occurrence portail : `bien_id`, `portail`, `url_sortante` UNIQUE, `date_saisie`),
`pige_faits` (faits validés, chaque champ étiqueté via `etiquettes` jsonb Sourcé/Estimé/Absent,
`valide_at` NULL = rien de publiable), `pige_prix_historique` (une ligne/changement de prix),
`pige_captures` (métadonnées : chemin privé + hash — jamais servi par le web),
`pige_clics` (clic sortant : client, bien, date → usage dashboard Produit).
**Isolation VÉRIFIÉE** : aucune FK `pige_*` ne référence une table existante (contrôle
`information_schema`), rien n'arrose le reste de l'app (réversibilité).

**Garde légale — collecte 100 % humaine.** Le SEUL endroit où un nom/URL de portail existe est
`src/labuse/pige/portails.py` (constantes d'affichage + préfixe pour reconnaître l'URL saisie ;
**aucun appel réseau**). Recette permanente `tests/test_pige_socle.py` :
- `test_aucune_requete_portail_dans_le_depot` — scanne `src/` + `frontend/src/` (.py/.js/.ts/.tsx) :
  **aucun** token portail sur une ligne d'appel réseau (`httpx`/`requests.`/`fetch(`/`.get(`/…), et hors
  commentaire un token n'apparaît QUE dans un fichier d'affichage allowlisté. (Les 3 mentions
  pré-existantes « SeLoger » de `faisabilite/bilan_calibration.py` sont des **commentaires** d'observatoire
  de prix → tolérées comme telles, jamais du code.)
- `test_le_paquet_pige_ne_fait_aucun_appel_reseau` — `pige/` n'importe même pas `httpx`/`requests`.

**Captures privées + backup.** Répertoire `pige_captures_dir` (config, défaut `/srv/labuse/pige/captures`,
surchargé `LABUSE_PIGE_CAPTURES_DIR`) — **hors racine publique**, jamais servi par le web (test
`test_repertoire_captures_est_prive_et_hors_racine_publique`). Inclus au backup :
`deploy/scripts/backup_postgres.sh` archive le répertoire (tar guardé par existence, même rotation KEEP).

**Événements** dans l'event_log UNIFIÉ (`journaliser()`, insert direct, `source='Radar'`) : les 7 kinds
`pige.nouvelle` · `pige.baisse_prix` · `pige.statut_change` · `pige.vendue_dvf` · `pige.signalement_client`
· `pige.digest_envoye` · `pige.intake_vide_48h` (tous ≤ 24 c, la limite `event_log.kind`). Ce sont des
faits de DOMAINE ; la livraison cloche/mail au client passera par la veille (P4).

**Recette P0** : `tests/test_pige_socle.py` 5/5 · imports OK · schéma dev créé + isolation prouvée ·
objets [RADAR-TEST] auto-nettoyés.

Findings : —
