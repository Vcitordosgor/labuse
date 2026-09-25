# LABUSE Radar — extension Chrome (pige Leboncoin)

1. Ouvrir `chrome://extensions`, activer le **mode développeur**, cliquer **Charger l'extension non empaquetée** et choisir ce dossier.
2. Cliquer sur l'icône de l'extension → **Ouvrir les options**.
3. Coller l'**URL de recherche Leboncoin** (île entière, ouverte normalement), l'**URL LABUSE** (ex. `http://localhost:8205`), le **jeton** `X-Radar-Token`, régler l'**heure** et le **jitter**, puis **Enregistrer**.
4. C'est prêt : capture automatique chaque soir ; le bouton **Capturer maintenant** (popup) lance un run immédiat.

> Si l'URL LABUSE n'est pas sur `localhost`, éditer `host_permissions` dans `manifest.json` pour y ajouter son origine.
