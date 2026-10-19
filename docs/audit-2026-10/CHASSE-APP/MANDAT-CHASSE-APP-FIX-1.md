# MANDAT CHASSE-APP-FIX-1 — corriger ce que la chasse du 19/10 a trouvé en prod

Branche `fix/chasse-app-1` · worktree `~/Desktop/labuse-chasse-app` · ports 8820 / 6020 · Opus.

## Étape 0

Vérifie `pwd`, la branche (`fix/chasse-app-1`) et que l'arbre est propre. Si l'un des trois ne va pas, arrête-toi et signale-le sans rien écrire.

## Dans cet ordre, un commit par point

1. **La date DVF affichée au client.** « DVF — jusqu'à déc. 2025 » n'est **pas** un retard : c'est la dernière publication du producteur (7 avril 2026), et la suivante est attendue fin octobre. Le vrai défaut, c'est que le client voie cette date. Vic a décidé le 18/09 qu'aucune date ni aucun millésime de source n'est montré au client, ces informations restant réservées à l'admin. Retire-la, et toute autre mention du même genre que tu croises sur la fiche. Ne touche ni à l'ingestion DVF ni au crontab : c'est le rôle de FRAICHEUR-PROD-1.
2. **La surface sur l'écran `/flash`.** Il annonce 27 156 m² là où le cadastre dit 25 633 m², juste avant le paiement. Reprends exactement le traitement de la fiche : la contenance cadastrale en valeur principale, « Dessin du plan » en mention secondaire.
3. **Les lenteurs.** Vérifie d'abord si les écrans d'outil, le PLU et la fiche attendent une réponse complète avant d'afficher quoi que ce soit. Si c'est le cas, affiche un squelette immédiat dans la DA existante. Sors aussi `/usage/event` du chemin critique : une mesure d'usage ne doit jamais bloquer l'interface. N'optimise pas le serveur dans ce mandat.
4. **Les petits points.** Le halo de focus sur les huit entrées du rail. Le message « Aucune correspondance » qui ne doit plus être un `role="option"`.

Stripe en paiement réel ne fait pas partie de ce mandat : il fera l'objet d'une session séparée.

## Comment travailler

- Vérifie avant de corriger : si tu ne retrouves pas un constat dans le code, dis-le au lieu de corriger au hasard.
- Pour chaque point, fais une capture avant et une capture après, et indique ce que Vic doit regarder pour constater que c'est réglé.
- Arrête-toi et demande si un point suppose une décision de Vic ou dépasse ce qui est décrit.
- Reste dans ce périmètre : pas d'audit collatéral, pas d'extraction de composant partagé, pas de liste d'autres endroits qui auraient le même problème.

## Interdits

- Jamais `deploy.sh`, et pas de `deploy_app.sh` non plus : le déploiement est un geste de Vic.
- Aucune donnée de démonstration en prod, aucun compte client touché.
- Aucune clé ni aucun mot de passe dans un fichier ou un commit.
- Pas de merge.

## Avant de rendre la main

Arrête ton API et ton navigateur, puis vérifie avec `lsof -ti :8820` et `lsof -ti :6020` que plus rien n'écoute.
