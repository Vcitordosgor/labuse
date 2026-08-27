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

---

## P2 — Rattachement à la parcelle (cascade) — **FAIT** (moteur + verrou)

`src/labuse/pige/rattachement.py` — `rattacher(db, *, commune, lon, lat, adresse, surface_hab,
surface_terrain, dpe_classe, piscine, geocode)` en cascade, chaque étage étiquetant sa confiance :
1. **GPS** — point exploitable → `ST_Contains` sur `parcels` de la commune → **Sourcé** (0,95).
2. **BAN** — adresse → géocodeur **injecté** (`geocode`, api-adresse.data.gouv.fr — un géocodeur, PAS
   un portail ; injecté pour rester testable hors réseau) → parcelle contenante → **Sourcé** (0,90/0,75).
3. **DPE ADEME** (déjà ingéré) — classe + surface + INSEE → parcelles candidates. **Anti-invention** :
   le DPE ingéré ne porte PAS la consommation (colonnes réelles `etiquette_dpe`/`surface_habitable`) →
   on ne filtre que sur ce qui existe ; `dpe_conso` reste un fait affiché, jamais un critère inventé.
4. **Morphologie** — emprise bâtie (`p_model_bati`) + surface terrain (aire parcelle) + piscine
   (`parcel_equipements`) → candidates plausibles de la commune.

**Verdict doctrinal** : GPS/BAN contenant unique = **Sourcé** · 1 à 3 candidates DPE/morpho = **Estimé**
(toutes rendues, avec confiance, deux étages concordants → confiance relevée) · 0 candidate OU **> 3**
(trop ambigu) = **Non rattachée**, commune seule. **Jamais un pin unique faussement sûr** — le faux
positif est le péché cardinal. Aucune requête réseau dans le moteur (géocodeur injecté).

**Recette P2** : `tests/test_pige_rattachement.py` 5/5 (GPS→Sourcé, BAN injecté→Sourcé, DPE+morpho→Estimé,
hors-parcelle→Absent, commune inconnue→jamais de pin). [RADAR-TEST] auto-nettoyés.

---

## VARIABLES DU TEMPLATE BREVO ID 12 (pour P4 — à monter par Vic, sans deviner)

Le mail Radar passe par la fonction unique `envoyer_mail`/`envoyer_template` (clé `"radar"` → env
`LABUSE_BREVO_TPL_RADAR` = ID 12). Deux envois distincts partagent CE template, différenciés par la
variable `type_envoi`. Vouvoiement, signé Victor, cohérent avec les templates 4→11. **Jamais de lien
portail dans le mail** : chaque item pointe vers la fiche LABUSE (le clic est mesuré).

| Variable (params) | Type | Contenu |
|---|---|---|
| `prenom` | texte | prénom du destinataire (vouvoiement) |
| `type_envoi` | texte | `digest` (nouveautés du jour) OU `alerte` (critères de veille correspondent) |
| `date_jour` | texte | date du jour, heure Réunion (ex. « 28 août 2026 ») |
| `n_items` | entier | nombre de biens dans la liste (un mail ne part JAMAIS vide → ≥ 1) |
| `intro` | texte | phrase d'accroche selon `type_envoi` (nouveautés / correspondance de vos critères) |
| `items` | liste d'objets | chaque bien : `{type, commune, prix, surface, rattachement, url_fiche}` |
| `items[].type` | texte | maison / terrain / immeuble / appartement (+ « copro » si appart.) |
| `items[].commune` | texte | commune du bien |
| `items[].prix` | texte | prix formaté « 245 000 € » ou « — » si Absent (jamais 0) |
| `items[].surface` | texte | « 95 m² hab. » / « 1 200 m² terrain » ou « — » |
| `items[].rattachement` | texte | « Sourcé » / « Estimé » / « Non rattachée » (étiquette assumée) |
| `items[].url_fiche` | URL | lien vers la **fiche LABUSE** du bien (JAMAIS le portail) |
| `lien_preferences` | URL | gestion des préférences / désinscription (List-Unsubscribe) |

---

## ÉTAT DES LOTS — HONNÊTETÉ DE LIVRAISON

RADAR V0 est un chantier full-stack de 7 lots. Livré et **testé** dans cette session : **P0** (socle +
garde légale, la fondation qui grave les doctrines §2) et **P2** (moteur de rattachement Sourcé/Estimé/
Absent). Les lots restants sont des chantiers substantiels, NON faits ici (rien n'est prétendu livré) :

- **P1 — Intake admin + extraction vision + validation** : page admin React entière + upload capture +
  **extraction VISION IA** (le cœur). Constat technique : `ai/core.complete` est TEXTE seul aujourd'hui
  (`context: dict|str`, messages construits en texte) → l'extraction image→JSON exige d'**étendre le
  cœur IA au vision** (bloc image base64 vers l'API Anthropic, compté dans `ia_budget`) — un sous-chantier
  à part entière. Reste : dropzone, dédoublonnage URL/inter-portails, contrôle commune ∈ 24, files de
  re-vérif à 2 niveaux, checklist ≤ 15 min.
- **P3 — Écran client** (filtres + carte = rattachés seulement + listing = tout avec pastille + fiche +
  bouton « Voir l'annonce sur [portail] » + `pige_clics`) : gros lot React sur le patron des outils.
- **P4 — Veille + 2 digests** : type de veille « Radar », deux envois fin de journée, template Brevo 12
  (variables ci-dessus, à monter par Vic), cloche in-app.
- **P5 — Cycle de vie automatisé** : jobs quotidiens (statuts par ancienneté), job DVF (vendue + écart
  prix si Sourcé), job mensuel `retiree_sans_vente` (garde : jamais déduit d'un lien mort).
- **P6 — Onglet « Marché »** : stats par commune, honnêteté statistique (n affiché, « — » si n < 5).

Recommandation de séquencement : P1 (dont l'extension vision du cœur IA) avant P3 ; P4 après le template
Vic ; P5/P6 en dernier (ils consomment du volume réel). Captures des écrans (390 et 1440) à produire
quand P1/P3 seront réalisés.
