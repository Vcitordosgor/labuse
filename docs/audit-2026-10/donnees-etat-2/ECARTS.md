# ECARTS — DONNEES-ETAT-2

Liste numérotée, du plus grave au moins grave. Une phrase chacun. Constaté le 27/10/2026 (VPS déjà au 28/10 01:00, heure Réunion). Lecture seule, aucun correctif.

1. **Disque du serveur à 94 %** (91 Go sur 96, 5,8 Go libres) — incident ouvert depuis le 22/10 avec 6 rappels, et il grimpe (87 → 90 % rien qu'entre 18:17 et 18:47 ce soir) : à ce rythme la prod risque l'arrêt faute de place.

2. **Le crontab posé sur le VPS ne correspond pas au registre du binaire en prod** — la propre vérification de `deploy.sh` (`labuse jobs crontab --verifier`) échoue : **le crontab régénéré par COCKPIT-1 n'a jamais été reposé** après le déploiement d'aujourd'hui (il manque `agents-sources`, et `restore-test` y traîne encore alors qu'il a été retiré du registre).

3. **Surveillance devenue aveugle** (conséquence directe du n° 2) : comme `agents-sources` est attendu par le moniteur mais absent du cron, `/healthz/crons` répond `ok:false` **en permanence**, ce qui fait **alerter la sentinelle du Mac toutes les 10 minutes depuis le déploiement** (storm en cours cette nuit) — le vrai souci serait noyé dans ce faux positif continu.

4. **Les enquêteurs IA (`agents-sources`) n'ont jamais tourné avec succès** : deux tentatives le 13/10 ont planté (`PermissionError: '.local/state/jobs'`), le job est hors crontab, et son plafond de dépense vaut 0 € par défaut — donc les sources que la sonde ne sait pas lire ne sont relues par personne.

5. **Incident « vérité sources » ouvert depuis le 15/10** (13 jours, 0 rappel) : 3 écarts parcelle ↔ source officielle jamais tranchés, et comme le job est mensuel (le 15), la prochaine mesure n'arrivera que le 15/11.

6. **Collision quotidienne `mail-queue-consommer` × `backup-postgres` à 13:30-13:35** : chaque jour (constaté du 14/10 au 27/10) un faux échec « another command is already in progress » ouvre puis referme un incident, et `sante-endpoints` se fait parfois prendre dedans — la même erreur empêche même l'alerte disque de s'écrire en base (repli fichier le 27/10).

7. **Le VACUUM hebdomadaire tourne à vide** : `pg-maintenance` a bien tourné le 25/10, mais sur **0 table** (`"tables": []`, 0,1 s) — le rangement de base ne range rien.

8. **La sauvegarde hors-site est figée depuis le 19/10** : dernière copie réelle sur le disque externe il y a 8 jours (disque actuellement débranché) ; la vigie du VPS déclenchera son alerte « > 10 jours » vers le 29/10.

9. **`recap-matin` est orphelin** : retiré du crontab aujourd'hui à 18:32, il a quand même tourné ce matin à 07:30 ; il n'est plus planifié mais son état et son journal subsistent.

10. **`signal-instantane` n'a jamais tourné** : ajouté au crontab aujourd'hui, mensuel (le 1er), sa première exécution n'aura lieu que le 01/11.

11. **Au dernier passage de la sonde (27/10) : 4 sources injoignables + 3 illisibles** (CatNat GASPAR, OSM transport/parkings/TCSP ; Géorisques SIS, OCS GE, SCOT GPU) — signalées, non bloquantes.

12. **Deux sources de données secondaires en retard** sur le tableau *Sources* : DPE et BAN marquées « en_retard ».

13. **Le dernier rapatriement des sauvegardes s'est fini sur une erreur rsync** (code 255 / SIGUSR1) le 27/10 — probablement transitoire, les dumps attendus sont bien présents en local.
