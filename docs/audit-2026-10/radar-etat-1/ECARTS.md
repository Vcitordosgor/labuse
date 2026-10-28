# Radar & Veille — écarts, du plus grave au moins grave (28/10/2026)

1. **Les cinq tâches de nuit du Radar sont gelées** (`radar-cloche`, `radar-cycle`, `radar-cycle-dvf`,
   `radar-cycle-mensuel`, `digest` — commentées « Phase 8 Stéphanie » dans le crontab prod) : aucune
   annonce ne devient alerte, aucun mail du matin ne part, le cycle de vie ne bouge plus.

2. **Aucun client n'a de veille Radar** (0 veille `radar` avec un compte sur 27 comptes) : même tout
   rallumé, `radar-cloche` ne matcherait rien et ne notifierait personne.

3. **La prod ne reçoit plus de captures depuis le 6 octobre** (22 jours) : le Radar de prod est figé sur
   des annonces d'il y a trois semaines, la plus récente datant du 5 octobre.

4. **L'extension est configurée pour le dev, pas la prod** : elle pointe sur `localhost:8205` et ne nourrit
   que la base du Mac (captures des 10, 23, 27 octobre restées locales, jamais arrivées en prod).

5. **L'extension ne se lance pas toute seule le soir** : toutes les captures réelles sont des lancements
   manuels après minuit ; l'alarme de 21 h n'a jamais sa signature dans les données.

6. **Zéro notification client depuis le 1er octobre** : cloche Radar 0, digest 0, mail Radar 0 ; les seuls
   mails partis sont des mails de cycle de vie (essai/souscription/mot de passe) à 4 comptes.

7. **Le digest du soir rate les annonces du soir** (défaut de septembre non corrigé) : sa fenêtre « du
   jour » exclut les captures faites la veille au soir — à surveiller le jour où tout sera rallumé.

8. **Le réglage de fréquence du digest est stocké mais jamais lu** (`digest_freq`) : un client ne peut
   choisir ni « immédiat » ni « hebdo » ; sans effet tant que le digest est gelé, mais toujours là.
