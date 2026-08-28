# RADAR-DIGESTS · LOT 0 — INVENTAIRE (avant tout code)

## Que fait `radar-digests` aujourd'hui ?

`pige/digests.py::envoyer(db, base_url, dry_run)` (CLI `radar-digests`) fait DÉJÀ deux envois de fin de
journée : (a) **digest** à tous les comptes actifs si des biens ont été validés aujourd'hui ; (b)
**alerte** à chaque client dont une veille Radar matche. MAIS :
- les DEUX passent par **un seul template Brevo « radar » (ID 12)** — le 13 n'est pas branché ;
- les params passent `items` en **LISTE**, ce qui suppose une boucle `{% for %}` côté template — or la
  contrainte Brevo (constatée en test réel) l'INTERDIT (la boucle rend à vide). **C'est le défaut à
  corriger** : construire le HTML des cartes CÔTÉ CODE et le passer dans un seul param `CARTES` (| safe).

## Chemin d'envoi

Un SEUL chemin : `brevo.envoyer_template(to, key, params)` → POST `api.brevo.com/v3/smtp/email` avec
`templateId`. Pas de second chemin. `template_id(key)` lit `brevo_tpl_<key>` (setting `LABUSE_…` ou env
`BREVO_TPL_…`). Clé API : `_api_key()` = `LABUSE_BREVO_API_KEY` **ou** repli `BREVO_API_KEY` (le correctif
RV-013 est en place ; un test doit prouver la lecture effective).

## Veilles Radar

Table `veilles` (type='radar') : `compte_id`, `commune`, `criteria` (jsonb), `actif`. **Pas de colonne
de libellé** donné par le client. `veille.lister(db, compte_id)` → [{id, commune, criteria}]. `matche(
criteria, bien)` teste : `commune`, `type_bien`, `prix_min/prix_max`, `surface_terrain_min`,
`surface_hab_min`, `particulier_only`. → Le **libellé VEILLE** sera `criteria.nom` s'il existe, sinon
DÉRIVÉ des critères (jamais inventé) ; **CRITERES** sera reconstruit depuis ces clés exactes.

## Champs d'un bien Radar (pour la carte)

| Carte | Colonne |
|---|---|
| type (+ copro) | `pige_biens.type_bien` / `est_copro` |
| commune | `pige_biens.commune` |
| prix | `pige_faits.prix` (à formater « 349 000 € ») |
| prix/m² | calculé `prix / surface_hab` (ou terrain) |
| surface | `pige_faits.surface_hab` / `surface_terrain` |
| **baisse de prix** | `pige_prix_historique` (nouveau_prix < ancien_prix, dernier constat) |
| parcelle | `pige_biens.idu` (NULL → « Non rattaché à une parcelle ») |
| **date de relevé** | `pige_annonces.date_saisie` (jamais la date d'envoi) |
| **portail** | `pige_annonces.portail` (slug → `portails.nom()`) |
| **lien** | `pige_annonces.url_sortante` (lien exact du portail) |

## Échec d'envoi : déjà BRUYANT

`_envoyer` : succès → `journaliser(EV_DIGEST)` ; échec → `log.error` + `creer_notification(kind='systeme',
source='Radar')` visible au dashboard. Bon. À CONSERVER (le message mentionnera 12 **et** 13).

## Ce qui reste à faire (LOTs 1-5)

1. **Constructeur de cartes** unique (HTML par code, échappement systématique, structure exacte LOT 1).
2. **Template 12 (digest)** : params PRENOM/DATE/NB_BIENS/LIEN_RADAR/CARTES ; jamais vide ; plafond 10 +
   « et N autres ».
3. **Template 13 (alerte)** : un mail PAR VEILLE ; params +VEILLE/CRITERES/LIEN_VEILLE ; même plafond.
4. **Idempotence par jour** (ne pas ré-envoyer le même digest/alerte deux fois) + **dry-run** qui écrit
   le HTML produit dans un fichier.
5. **Doc** EXPLOITATION-CRON : « template 12 » → « 12 et 13 », cron À POSER.

**Ordre des 10 (plafond)** : baisse de prix D'ABORD (le signal le plus actionnable pour un démarcheur),
puis récence (bien_id décroissant). Justifié : une baisse est une opportunité datée ; un nouveau bien
sans baisse vient ensuite.
