# Remettre le Radar en route — dans l'ordre (≤10 gestes)

1. **Décider « Phase 8 » : on rallume ?** Le gel des 5 tâches est volontaire (motif « Phase 8 Stéphanie »).
   Rien ne repart sans cette décision.
2. **Dégeler** les 5 tâches dans le registre (`jobs.py` : retirer `gel=` de radar-cloche, radar-cycle,
   radar-cycle-dvf, radar-cycle-mensuel, digest), puis **redéployer le crontab** sur le VPS.
3. **Créer au moins une vraie veille Radar de client** (commune/type/prix) — sans ça, radar-cloche
   n'aura rien à matcher.
4. **Choisir la machine qui capture** : un poste **toujours allumé le soir** (Mac mini conseillé, sinon
   le Mac actuel laissé ouvert et non endormi à 21 h).
5. **Sur ce poste, régler l'extension pour la PROD** : URL LABUSE = `https://app.labuse.immo` (au lieu de
   `localhost:8205`), coller le jeton `LABUSE_RADAR_TOKEN` de prod, et ajouter l'origine prod aux
   permissions du `manifest.json`.
6. **Vérifier que l'extension part seule** : utiliser « test-alarm » (déclenche dans 2 min), confirmer une
   capture arrivée en prod, puis laisser l'alarme de 21 h faire son travail.
7. **Régler le trou « annonces du soir »** (écart 7) : élargir la fenêtre du digest à « depuis le dernier
   passage » (ou J-1), sinon la capture du soir sera invisible le lendemain matin.
8. **Surveiller une nuit complète** : le lendemain, vérifier dans `job_runs` que radar-cloche + digest ont
   tourné, et dans `mail_queue` qu'un mail est bien parti (SMTP vide → les mails bruts du digest ne
   partent pas : passer par Brevo ou poser un SMTP).
