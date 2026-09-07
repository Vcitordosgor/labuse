# DASHBOARD-2 — vérification LIVE (app réelle, base `labuse`)

App lancée localement (uvicorn `:8000` sur la base `labuse` réelle + Vite `:5173`, `#admin=1`,
viewport 1440 px). Les **captures PNG** échouent sur la limite dure de 5 s du pont Playwright-MCP
(les polices se chargent puis l'encodage dépasse 5 s — limite de l'environnement, pas de l'app). À la
place, le **contenu rendu** a été extrait du DOM — c'est la preuve la plus directe du contrat
« un chiffre = une fonction » : les chiffres, pas les pixels.

## Pilotage — 8 jauges + rail + compteurs de nav (données réelles)

| Jauge | Valeur | Compteur de nav | Concordance |
|---|---|---|---|
| Argent · encaissé ce mois | 0 € | — | (Stripe local vide) |
| Clients · licences actives | **12** | Comptes **12** | ✓ |
| Circuit · à regarder | **8** | Données **8** | ✓ |
| Courrier · à déposer | **24** | Courrier **24** | ✓ |
| Radar · annonces en vie | **109** | — (page Radar : 109) | ✓ |
| Produit · retours ouverts | **2** | Produit **2** | ✓ |
| IA · conso du mois | (1,05 €) | — | ✓ (= page IA) |
| Système · alertes | 0 | — | santé serveur (Lot 2) |

Rail : **Serveur OK · Run servi q_v11_m137 · Backup non configuré · Horloge 0 / 23 · Verrous 16 / 16**.
(Backup « non configuré » car `LABUSE_BACKUP_DIR` absent en local ; Horloge 0/23 = aucun job n'a
tourné ici = le « ce qui cloche » rouge, honnête ; Verrous 16/16 = dernier passage sans casse.)

Les compteurs de nav **égalent** les jauges en direct → le contrat compteur unique est vérifié à
l'écran (et endpoint-contre-endpoint par `tests/test_dashboard2_cloture.py`).

## Courrier

- h1 « Courrier ».
- Colonnes = maquette : **Client · Parcelle · Propriétaire · Demandé le · Piste CRM · Statut · Gestes**.
- Chips : **Tous 26 · À déposer 24 · Déposé 0 · Envoyé 2 · Répondu 0 · Sans réponse 0** (vocabulaire
  unifié — plus « à traiter » / « imprimé » / « posté »).
- Bouton bloc : **« Marquer les 24 déposés »**.
- 1re ligne : `interne · 97411000BZ1065 · Saint-Denis · Propriétaire "—" · piste #12 ↗ · À déposer ·
  aperçu / Déposé`.

Le « 24 à déposer » = jauge Pilotage = compteur de nav (compteur unique, en direct).

## Radar

- h1 « Radar » · **109 annonces en vie** (= jauge Pilotage).
- Mention **« Le chemin par captures d'écran est retiré »** présente (chemin capture supprimé).

## Produit

- h1 « Produit » · **une file « Retours »** avec type chips unifiés : **donnée · bug · idée · question**
  (+ « Tous types »).

## IA — cinq repères, fenêtre nommée, formule unique

- h1 « IA ».
- Repères : **« septembre » 1,05 € · 133 questions servies** · **Projection fin de mois ≈ 5 €** ·
  **Coût moyen 0,008 € par question (septembre, ledger ia_log)** · Plafond défaut · Crédit Anthropic.
- Table plafond : filtres **Clients 26 · Avec conso 0 · Tous, tests compris 32**.
- Modèle par surface **replié** : « **23 surfaces · claude-sonnet-4-6 ×16 · claude-haiku-4-5-20251001
  ×7 · source unique ai_models.py** ».

Le coût moyen affiché (0,008 €) est la MÊME valeur qui donne le « ≈ N questions » de la table
(2,00 € ÷ 0,008 = 250) — l'incohérence « ≈ 335 » est éliminée à la source.

## Contacts

- h1 « Contacts » · **24 cartes de communes** (grille) · 1re carte « **Bras-Panon · 02 62 51 50 50 ·
  standard seul** » (format standard · N contacts) · EPCI présents en dessous.

## Données / Destinations

- Lien **« Calibration des destinations — le détail du réservoir plu_destinations → »** présent au-dessus
  du Circuit ; Destinations a quitté le rail (nav : Pilotage · Comptes · Données · Courrier · Radar ·
  Produit · IA · Contacts).
