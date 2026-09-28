# RADAR-CHAINE-1 — la chaîne Radar de bout en bout, une annonce témoin suivie du portail au mail

**Branche** `audit/radar-chaine-1` · worktree `~/Desktop/labuse-radar2` · **lecture seule sur `src/`**,
aucune donnée modifiée en base **hors** un compte + une veille de test préfixés `[RC-TEST]` (inventaire
de purge en fin de document). API et navigateur **non démarrés** : tout est prouvé par `psql` sur la base
prod-dev (`postgresql://openclaw@localhost:5432/labuse`) et par l'appel direct des **vraies** fonctions du
code (venv partagé `~/Desktop/labuse/.venv`, `PYTHONPATH` = ce worktree). Références : `RADAR-AUDIT-1.md`,
`RAPPORT-RADAR-AUTO-1.md`.

## L'annonce témoin

Le dossier `docs/RADAR/captures/auto-1/` de l'extension est **vide** (`.gitkeep` seul) : l'extension
n'a **encore jamais produit de capture**. La dernière capture RÉELLE en base est donc un dépôt de la
recette RADAR-AUTO-1 — le fichier île-entière de Saint-Denis rejoué le **2026-09-26** (passe `nouvelles`
puis 20 pages `relecture`). J'y prends un témoin idéal, **actif et rattaché à une parcelle** :

| | témoin |
|---|---|
| `bien_id` | **142** |
| annonce (`list_id`) | **3240289488** · leboncoin · `…/ad/ventes_immobilieres/3240289488` |
| type / commune | maison · **Saint-Denis** (quartier Montgaillard-Colline des Camélias, 97400) |
| prix / surface / pièces | **395 000 €** · 130 m² hab. · 4 pièces · particulier |
| position | `lat -20.90925 / lng 55.45815`, `source_position = address` (point rue, pas quartier) |
| dates portail | 1ʳᵉ publication **2026-09-25 20:43**, expiration **2026-11-24**, statut portail `active` |
| parcelle | **97411000EO0132** — rattachement niveau `source`, confiance 0,75, preuve `certain` |
| statut LABUSE | `active` · saisi 2026-09-26 00:23 · vu la dernière fois 2026-09-26 00:23 |

---

## Le tableau des 8 étapes

| # | Étape | Ce qui se passe pour le témoin | Preuve | Verdict |
|---|---|---|---|---|
| 1 | **Capture** | Dernière capture réelle = **2026-09-26** (`nouvelles · page 1`, hash `3529d0ca`, puis 20 pages `relecture`, hash `9e6eb62dc3`). Page **riche** (`json_riche`). Lot = **35 annonces/page**. Règle d'arrêt par date = côté **extension** (`index_date` max de la page ≤ dernière capture − 1 h) — invisible en base. | `pige_depots` #9-81 (2026-09-26 00:23→02:40) ; lot du 26 : plus ancienne 1ʳᵉ pub 2025-06-02, plus récente 2026-09-25 23:13 | **OK** (mais l'**extension n'a jamais tourné** : tout vient de dépôts manuels/recette) |
| 2 | **Parseur** | Extrait : prix 395 000, 130 m², 4 pièces, maison, Saint-Denis, `lat/lng` (address), 1ʳᵉ pub 2026-09-25, particulier. **Manquent** : adresse exacte (jamais donnée par le portail — seul le point `lat/lng`), DPE (`absent`), surface terrain (`absent`). | `pige_faits` bien 142 : `provenance=json_riche`, `etiquettes` par champ (`prix/surface_hab/…=source`, `dpe_classe/ges/owner_siren/surface_terrain=absent`), `a_verifier` NULL | **OK** |
| 3 | **Dédup** | Clé unique = **`list_id`** seul (aucun dédoublonnage « même bien physique » sur le chemin HTML). Le témoin n'a pas de jumeau. Mais **5 groupes / 10 biens** portent un couple (commune, prix, surface) identique sous des `list_id` **différents** = même bien recompté (re-publication / 2ᵉ portail). | Requête : 5 groupes `having count(distinct bien_id)>1`, ex. Saint-Denis 799 000 €/168 m² = biens {18, 38} ; 374 500/200 = {74, 75} ; 329 000/63 = {10, 40} | **KO** |
| 4 | **Rattachement + carte** | Rattaché à **EO0132** par **2 critères** (emprise bâtie 177 m² ∈ [78-182] + DPE ADEME 122 m²) à 84,5 m ; les 9 autres pistes n'ont qu'**1** critère → une seule parcelle à ≥2 ⇒ `rattachee` niveau `source`. Carte : **rond PLEIN** = rattaché à une parcelle (le témoin) ; **rond CREUX** = position de quartier. | `pige_biens.rattachement_criteres`/`_pistes` ; `MapView.tsx:712-720` (`circle-opacity` quartier→0 sinon 0,8 ; stroke 2,5 vs 1,5) | **OK** (nuance : la distinction plein/creux n'a **pas de légende sur la carte** — elle est dite par la puce « Quartier » du listing et le panneau fiche) |
| 5 | **Cycle de vie** | Témoin `active`, vu 2026-09-26. Les 3 jobs `radar-cycle` / `-dvf` / `-mensuel` **existent, sont idempotents ET planifiés** (corrigé depuis RADAR-AUDIT-1 §6c par RADAR-AUTO-1 lot C). **Actives non vues depuis > 8 j = 0** (la recette a tout revu hier). | `jobs.py:389-407` ; `labuse jobs crontab` génère bien les 5 lignes (`radar-cycle` 04:00, `-dvf` 04:30, `-mensuel` 05:30 le 1er, `radar-cloche` 07:05, `digest` 07:15) | **OK** (cf. KO-C : jamais exécutés en continu sur cet env) |
| 6 | **Service** | Le témoin est **servi** : listing (`client.lister` Saint-Denis → 142 présent, `rattachement.niveau=source`), **carte** (n_carte=9, rond plein), stats commune (`radar_stats(Saint-Denis, maison)` : 9 actives, médiane **2 989 €/m²**) sous le libellé **« prix demandés (Radar) »**. | appels directs `client.lister` / `marche.radar_stats` (`marche.py:130`) | **OK** |
| 7 | **Veille** | Veille `[RC-TEST]` (commune Saint-Denis · maison · 390 000-400 000 €) → `veille.matche` = **True**. Critères réellement évalués : commune(s), type, prix min/max, surface min/max (surface pertinente), particulier. **Ignorés** : les événements cochés (`nouvelle/baisse/retour`) — jamais appliqués et **retirés** de `criteria`. ⇒ **tout** bien du jour qui matche notifie, quel que soit le type d'événement. | `veille.py:75-117` ; `copilote_v2/veilles.py:61` (« le filtre `evenements` n'a jamais été appliqué ») + `:65` (`UPDATE … criteria - 'evenements'`) | **OK** (nuance : pas de filtre par type d'événement) |
| 8 | **Notification** | Le morning **digest** (07:15, planifié) reprend les événements Radar posés à la **cloche** par `radar-cloche` (07:05, planifié). Le template **Brevo 13** `radar_alerte` (`digests.envoyer`) est **CLI-seul** (`radar-digests`), **pas au CRON**. Les deux producteurs sont **bornés aux biens saisis LE JOUR MÊME** (`_biens_du_jour` : `date_premiere_saisie ≥ aujourd'hui`, heure Réunion). **Run réel aujourd'hui (2026-09-27) : `radar-cloche` → 0 event, `radar-digests` → 0 envoyé** (témoin saisi le 26, pas « du jour »). **Mécanisme prouvé en réel sur le témoin** (fourni hors filtre calendaire) : cloche OK + mail template 13 réellement **parti** (Brevo `recu`). | voir §« Preuve de mécanisme » ci-dessous | **KO** (le canal marche pièce par pièce, mais l'auto-notification d'un client est **fragile** : cf. KO-A/B/C) |

### Preuve de mécanisme (étape 8) — sur le témoin, transport RÉEL

En appelant les vraies fonctions (`creer_notification`, transport `mailfile.envoyer_mail(key="radar_alerte")`)
avec le témoin fourni directement — le seul écart avec le job étant le contournement du filtre « du jour » :

- **Cloche** : `creer_notification(kind="radar", compte_id=80, …)` → `event_log` **id 9756**, relu comme la
  cloche du client le fait (kind `radar`, compte-scopé, `lu=false`) : titre *« Nouvelle annonce pour votre
  veille — Maison à Saint-Denis »*, détail *« 395 000 € · [RC-TEST] maison Saint-Denis 390-400k »*, lien =
  l'annonce leboncoin. ✅ **La cloche reçoit l'événement.**
- **Mail template 13** : envoi **réel** vers `kampusreunion+rctest@gmail.com` → `mail_queue` id 16,
  `template_id=13` (`LABUSE-13-RADAR-ALERTE`), **`etat=recu`** (« Reçu par Brevo »),
  `message_id=<202609271801.77344104574@smtp-relay.mailin.fr>`, `erreur=null`, `parti_at` posé. ✅
  **Le mail part.** Contenu : une carte *« Maison — Saint-Denis · 395 000 € · 3 038 €/m² · 130 m² hab. ·
  Parcelle 97411000EO0132 · Repéré le 26 septembre 2026 sur Leboncoin · Voir l'annonce → »*, params
  `VEILLE / NB_BIENS=1 / CRITERES="Maison · Saint-Denis · plus de 390 000 € · moins de 400 000 €"`.
  ⚠️ Un **avertissement** est renvoyé par le transport : *« Les liens des mails pointent sur
  `http://127.0.0.1:8000` — aucun client ne pourra cliquer »* (base URL non configurée en dev).

Autrement dit : **la cloche et le template 13 fonctionnent réellement** ; ce qui empêche un client d'être
notifié n'est pas le transport, mais **le déclenchement** (cf. KO ci-dessous).

---

## Les KO, classés par gravité (ce qui empêche un client d'être notifié d'abord)

### 🔴 KO-A — Le digest ne regarde que les biens saisis « le jour même » ; la capture du soir tombe la veille
`_biens_du_jour` (`digests.py:61-84`) borne cloche **et** digest à `date_premiere_saisie ≥ (aujourd'hui,
heure Réunion)`. Or l'extension capture le **soir** (alarme 21:00 + aléa 0-180 min, cf. RAPPORT-AUTO-1 §2) :
un bien saisi le **jour D à 21:00** n'est **pas** « du jour » pour le digest du **jour D+1 à 07:15** → il est
**silencieusement exclu**. La recette du 26 « marche » seulement parce qu'elle a tourné **après minuit**
(00:23-02:40). Preuve directe aujourd'hui : témoin saisi le 26, `radar-cloche` et `radar-digests` lancés en
réel le 27 renvoient **0**. **C'est le trou le plus grave : la majorité d'une capture du soir n'atteint
jamais le client.**

### 🔴 KO-B — Les jobs de notification n'ont jamais tourné en continu sur cet environnement
Fichiers d'état (`~/Desktop/labuse/.local/state/jobs/`) : `radar-cycle` et `radar-digests` = **un seul
lancement manuel le 2026-08-31** ; **`radar-cloche`, `digest`, `radar-cycle-dvf`, `radar-cycle-mensuel` =
aucun fichier d'état → jamais exécutés**. Le crontab est bien **généré** depuis le registre (prouvé), mais
rien ne prouve qu'il soit **installé et actif** (la machine de dev n'a pas `/run/lock` inscriptible — le
wrapper refuse le verrou). Sans exécution réelle chaque nuit, cloche + digest ne partent jamais, quels que
soient les correctifs de registre.

### 🟠 KO-C — Le template 13 `radar_alerte` n'est pas planifié (CLI seulement)
Le « mail par veille » (template 13, `digests.envoyer`) n'est appelé que par la commande `labuse
radar-digests` ; il **n'a aucune entrée au CRON** (le crontab généré ne le contient pas). En production, la
seule notification Radar automatique passe donc par le **digest du matin** (via la cloche), jamais par
l'alerte dédiée template 13. Le template 13 est aujourd'hui **de fait dormant** en exploitation.

### 🟠 KO-D — Dédup « bien physique » absente : sur-comptage
Clé = `list_id` seul. **5 paires / 10 biens** identiques (commune, prix, surface) sous des `list_id`
distincts (re-publication ou 2ᵉ portail) → biens et stats **sur-comptés**. Le twin-matching `_bien_jumeau`
existe mais n'est branché que sur l'ancien chemin vision. Un client peut recevoir **deux fois** le même
bien physique s'il est republié avec un nouvel identifiant.

### 🟡 KO-E — La veille ne sait pas filtrer par type d'événement
Un client peut créer une veille « seulement les baisses de prix » : la clé `evenements` est **acceptée à la
saisie mais jamais évaluée**, et une migration la **supprime** de `criteria` (`veilles.py:65`). Toute annonce
du jour qui matche les critères de fond notifie, `nouvelle` comme `baisse` comme `retour` — le tri par
événement promis à l'écran n'existe pas dans le moteur.

### 🟡 KO-F — La carte n'a pas de légende pour ses deux marqueurs Radar
Rond **plein** (rattaché à une parcelle) vs rond **creux** (position de quartier) sont peints
(`MapView.tsx:712-720`) mais **aucune légende** ne l'explique sur la carte ; le sens n'est donné que par la
puce « Quartier » du listing et le panneau fiche. Un utilisateur voit deux symboles sans clé.

---

## Ce qu'il faudrait corriger (sans corriger ici)

1. **KO-A (le plus urgent)** — élargir `_biens_du_jour` à **« depuis le dernier digest / la dernière
   capture »** (ou « hier + aujourd'hui »), ou dater les biens sur `last_seen_at` du dépôt plutôt que sur le
   calendrier civil. Sinon aligner l'heure de capture de l'extension **avant** le digest le même jour Réunion.
   C'est la correction qui rend la notification fiable.
2. **KO-B** — **installer et vérifier** le crontab généré sur l'environnement servant (déjà au registre) ;
   ajouter une sonde « `radar-cloche`/`digest` a-t-il tourné cette nuit ? » à la Tour de contrôle, et rendre
   le verrou `run-job.sh` tolérant à l'absence de `/run/lock` (repli `TMPDIR`).
3. **KO-C** — décider : soit **planifier** `radar-digests` (template 13) si l'alerte par veille est voulue en
   plus du digest, soit **retirer** le template 13 du registre pour ne pas laisser un canal mort qui prétend
   exister (le dashboard `etat_configuration` le liste comme « branché »).
4. **KO-D** — rebrancher `_bien_jumeau` sur le chemin HTML **en proposition** (`fusion_proposee`), jamais en
   fusion automatique (instruction admin), pour cesser de sur-compter.
5. **KO-E** — soit implémenter l'évaluation de `criteria.evenements` dans `veille.matche`, soit retirer la
   case de l'UI (ne pas promettre un filtre inopérant).
6. **KO-F** — ajouter à la légende de la carte l'entrée « ● rattaché à une parcelle / ○ position de quartier ».

---

## Inventaire de purge des objets `[RC-TEST]`

Objets créés pour ce diagnostic — **purgés en fin d'audit** (les 5 `DELETE` ci-dessous ont été exécutés,
base rendue à son état initial ; table ci-dessous conservée pour traçabilité) :

| Objet | Table | Clé | Repère |
|---|---|---|---|
| Compte de test | `comptes` | **id 80** | `nom = '[RC-TEST] RADAR-CHAINE-1'` |
| Titulaire | `utilisateurs` | **id 79** | `email = 'kampusreunion+rctest@gmail.com'` |
| Veille Radar | `veilles` | **id 19** | `criteria->>'nom' = '[RC-TEST] maison Saint-Denis 390-400k'` |
| Événement cloche | `event_log` | **id 9756** | `compte_id = 80 AND kind = 'radar'` |
| Ligne mail | `mail_queue` | **id 16** | `compte_id = 80` (dedup `rc-test:alerte:80:19:2026-09-27`) |

⚠️ **Un mail template 13 a réellement été envoyé** via Brevo à `kampusreunion+rctest@gmail.com` (preuve de
départ) — il ne peut pas être « dé-envoyé » ; il arrive dans la boîte `kampusreunion@gmail.com`.

Purge SQL (dans l'ordre des dépendances) :
```sql
DELETE FROM mail_queue      WHERE compte_id = 80;
DELETE FROM event_log       WHERE compte_id = 80;
DELETE FROM veilles         WHERE compte_id = 80;
DELETE FROM utilisateurs    WHERE compte_id = 80;
DELETE FROM comptes         WHERE id = 80;
```

*Fin — RADAR-CHAINE-1. Lecture seule sur `src/` ; seuls les objets `[RC-TEST]` ci-dessus ont touché la base.*
