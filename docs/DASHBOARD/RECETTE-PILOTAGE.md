# Recette DASHBOARD-2 — Pilotage (5 points)

Recette jouée sur la base réelle `labuse` (uvicorn + Vite, `#admin=1`, 1440 px). Preuve par extraction
DOM (les captures PNG butent sur la limite 5 s du pont Playwright-MCP — cf. VERIFICATION-LIVE.md).
Contrainte respectée : **le rail et la CSS partagée n'ont pas été touchés** (feat/compte-2 y travaille).

## 1. La jauge Système mentait (0) → nombre d'alertes réelles (2), rouge

**Changé** : Système ne lit plus la santé serveur ; elle affiche le **nombre de lignes rouges de « À
faire »** (les alertes ouvertes) — **un seul calcul** (`rouges.length`), la même source que les lignes.
Rouge dès qu'il y en a une.

**Preuve** : avant `0 · Système · alertes` ; après `2 · Système · alertes ouvertes` (23 horloges + 1
sauvegarde = 2 lignes rouges).

## 2. Licences actives : 12 vs page → une seule fonction, test + admin exclus

**Changé** : `plateforme.comptes_actifs` (la fonction unique lue par la jauge, le rail et — à brancher
côté COMPTE-2 — la page) exclut désormais les comptes **admin** (`plan='interne'`) **et de test**
(e-mail en domaine placeholder : `labuse.local`, `ex.test`, `example.com`… — mandat §14).

**Preuve** : avant jauge `12` / nav Comptes `12` ; après **`5` / nav Comptes `5`** (base réelle : 12
actifs − 6 admin `interne` − 1 `@labuse.local`). Le nombre exact (la recette citait 9) dépend des
données : l'app a accumulé des comptes admin depuis ; ce qui compte est qu'**une seule fonction**
excluant test+admin est désormais lue par la jauge ET le rail (mêmes 5).

⚠ **À SIGNALER** : la **page Comptes** (livrée par COMPTE-2, non mergée) doit lire **cette même
fonction** `comptes_actifs` pour fermer le compteur unique côté page. Non touché ici (territoire
COMPTE-2 — la consigne dit de signaler, pas de reconstruire la page Comptes).

## 3. Jauges triées par urgence

**Changé** : les jauges sont triées **rouge → ambre → vert** ; à état égal, l'ordre de la maquette
(tri stable).

**Preuve** : après → `Système(r) · Circuit(a) · Courrier(a) · Produit(a) · Argent · Clients · Radar ·
IA`. Avant : ordre figé (Argent en tête).

## 4. Argent : le MRR en grand, l'encaissé en légende

**Changé** : la jauge Argent montre le **MRR** (récurrent = licences × prix intégral, lu de `/api/offres`)
au lieu de l'encaissé bloqué à 0. L'encaissé du mois passe en légende, le mois est nommé.

**Preuve** : avant `0 € · Argent · encaissé ce mois` ; après **`1 745 € · Argent · par mois · 0 €
encaissé en septembre`** (= 5 licences × 349 €). Cohérent avec la jauge Clients (même 5).

## 5. Trois détails

- **Clients** : libellé « licences actives » (redondant avec Argent) → **« licences · N à toucher »**.
  Preuve : après `5 · Clients · licences · 0 à toucher`.
- **Lignes à zéro** retirées de « À faire ». Preuve : après, la liste ne contient que les lignes > 0
  (Poser les horloges, Configurer la sauvegarde, Regarder le circuit 8, Déposer les courriers 24,
  Traiter les retours 2) — plus de « 0 clients à toucher » ni « 0 à re-vérifier » ; note explicite.
- **Bandeau Stripe** : « cache … » → **« chiffres à l'instant · Stripe daté du JJ/MM HH:MM »** en heure
  Réunion (`fmtReu`, la vraie date du cache = dernier `apercu()`), teinte ambre si > 1 h.

## Vérification & qualité

- `tsc -b` 0 · `vitest` 191 · `vite build` OK.
- Backend : `test_comptes_actifs` (témoin) mis à jour au « client actif compte, ni interne ni suspendu » ;
  `test_dashboard2_cloture::test_clients_le_meme_9` mis à jour (actif NON interne) — **6 verts**.
- Rail et CSS partagée : **inchangés**. Le compteur du rail (Comptes) suit `comptes_actifs` sans édition
  du rail (il lit `d.licences_actives`).
