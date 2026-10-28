# LABUSE Radar — extension Chrome (pige Leboncoin)

1. Ouvrir `chrome://extensions`, activer le **mode développeur**, cliquer **Charger l'extension non empaquetée** et choisir ce dossier.
2. Cliquer sur l'icône de l'extension → **Ouvrir les options**.
3. Coller l'**URL de recherche Leboncoin** (île entière, ouverte normalement), vérifier l'**URL LABUSE** (prod `https://app.labuse.immo` par défaut), coller le **jeton** `X-Radar-Token` de prod, régler l'**heure** et le **jitter**, puis **Enregistrer**.
4. C'est prêt : **capture automatique chaque soir** (entre l'heure de base et +jitter, sans clic, Mac allumé + Chrome ouvert) ; le bouton **Capturer maintenant** (popup) lance un run immédiat « manuel ».

> **Prod par défaut** (RADAR-FIX-2) : l'extension nourrit `https://app.labuse.immo` (déjà dans `host_permissions`). `localhost` ne sert qu'en recette, en le tapant explicitement dans les Options (origine `localhost` déjà autorisée). Première capture après une bascule (hôte LABUSE changé) : **rattrapage** depuis la dernière annonce connue (arrêt par `index_date`, plafond dur 40 pages).

> **Déclenchement automatique** : une alarme PÉRIODIQUE (battement toutes les 5 min) vérifie si on est dans la fenêtre du soir et capture une seule fois par soir, source `auto` (le journal LABUSE porte la signature « déclenchée auto »). Recette : lien popup **Tester l'alarme (+2 min)** → une capture `auto` part seule dans 2 minutes.
