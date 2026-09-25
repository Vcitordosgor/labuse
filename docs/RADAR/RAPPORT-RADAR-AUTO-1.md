# RAPPORT — RADAR-AUTO-1 · Le Radar sans Vic

Branche `feat/radar-auto-1` (depuis `audit/radar-1`) · worktree `~/Desktop/labuse-radar` · ports 8205/5405.
Livrables : `outils/radar-extension/` · `docs/RADAR/RADAR-AUTO-1-MESURES.md` · ce rapport · `docs/RADAR/captures/auto-1/`.
Doctrine tenue : le navigateur de **Vic** capture (jamais le VPS), **zéro LLM** dans la chaîne, aucune parcelle rattachée sans preuve (le niveau s'affiche), prix Radar = **prix demandés** (jamais confondus DVF).

---

## 1. Les 5 mesures et leurs décisions (Lot 0)

Détail chiffré + preuves dans **`RADAR-AUTO-1-MESURES.md`**. Résumé et décisions :

| # | Mesure | Résultat | Décision |
|---|---|---|---|
| 0.1 | Page 1 riche | `searchData.ads` = **35/35** avec position + `first_publication_date`/`index_date` ; `searchData` porte **`total:5116`, `max_pages:100`, `pivot.page_number`** | Régime cible de la passe « nouvelles » ; le total/pagination servent les garde-fous |
| 0.2 | Pages suivantes | Page 1 ouverte normalement = riche ; page 2 **par URL** = dégradée (DOM seul) | L'extension avance par le **« page suivante » DU SITE** (nav Next.js), jamais par URL froide ; confirmation live reportée à la recette (doctrine : pas de hit VPS) |
| 0.3 | Terrains | 20 annonces à surface de terrain → à **±1 %** : 3 uniques ; à ±3 % l'ambiguïté explose (jusqu'à 9) | **Lot D auto = ±1 % unique** ; sinon bouton manuel. ⚠️ affiné : les 3 uniques sont des **maisons** (cascade bâtie) ; 0 **pur terrain** unique sur l'échantillon → l'auto-terrain fire rarement, le manuel est la voie principale |
| 0.4 | Lecteurs `pige_*` | demandé/DVF **déjà séparés** partout ; `marche.stats` **inclut déjà** les apparts | Lot E = **consolidation** (`radar_stats`), pas correction de fond ; ne pas régresser les libellés |
| 0.5 | Jobs cycle | `radar-cycle`/`-dvf`/`-mensuel` codés+idempotents mais **non planifiés** | Lot C = wrappers manquants + **3 entrées au registre CRON** |

---

## 2. Ce que l'extension fait, soir par soir (Lot B)

`outils/radar-extension/` — Chrome MV3, permissions **`alarms` / `storage` / `notifications` / `scripting` / `tabs`** + hôtes `*.leboncoin.fr` (+ URL LABUSE). Une alarme quotidienne à l'heure choisie **+ aléa 0–180 min**. Un onglet de fond, **rythme humain**, **plafond dur 40 pages/soir**. Chaque appel porte `X-Radar-Token`.

1. **Nouvelles** — ouvre la recherche **page 1** normalement (rendu riche), lit `#__NEXT_DATA__` de la page **vivante**, `POST /admin/radar/capture` (`passe:"nouvelles"`, un seul `captured_at` pour tout le run). Avance par le **« page suivante » du site** (garde `searchData`), 4–8 s entre pages. S'arrête quand la `index_date` max de la page ≤ `derniere_capture_at − 1 h`. **Plafond 15 pages.**
2. **Relecture** — ~20 pages de l'inventaire **par commune**, en **rotation persistante** (`relectureCursor` avancé chaque soir → inventaire complet relu en **≤ 7 jours**). Chaque page → `/capture` (`passe:"relecture"`) ; LABUSE compare les prix. **Plafond 20 pages.**
3. **Confirmation** — `GET /admin/radar/etat` → `a_confirmer` (actives non vues depuis 8 j). Ouvre chaque lien (8–15 s), verdict **`presente`** (annonce affichée, HTTP 200) / **`supprimee`** (404/redirection/page absente) / **`inconnue`** → `POST /admin/radar/confirmation`. **Plafond 60 liens.**

**Blocage** (page sans `searchData` ni `aditem_container`, ou captcha/DataDome) → notification Chrome « **Radar bloqué, dépose à la main** », **arrêt net**, rien envoyé, badge ✗. Succès → badge ✓ + heure.

---

## 3. Installation (README, 4 lignes)

1. `chrome://extensions` → activer le **mode développeur** → **Charger l'extension non empaquetée** → choisir `outils/radar-extension/`.
2. Ouvrir les **Options** de l'extension.
3. Coller : l'**URL de la recherche île entière**, l'**URL de LABUSE**, le **jeton** (`LABUSE_RADAR_TOKEN`), l'**heure** (défaut 21:00).
4. (Si LABUSE est distant : ajuster l'hôte dans `manifest.json`.) Bouton **« Capturer maintenant »** pour la recette.

Côté serveur : poser `LABUSE_RADAR_TOKEN=<secret>` dans `.env` (jamais le mot de passe admin ; secret révocable).

---

## 4. La chaîne prix / suppression, avec un exemple réel (Lots A + C)

- **`last_seen_at`** est posé à chaque vue (capture ou dépôt), à l'insert comme à la re-vue.
- **Prix** : à chaque re-vue, comparaison au dernier prix connu. Au-delà de **±1 %** (`SEUIL_VARIATION_PRIX`), un événement daté : **`pige.baisse_prix`** (le plus actionnable) ou **`pige.hausse_prix`** (nouveau). Sous 1 % : historisé (traçabilité) mais **pas** d'événement (anti-bruit). Le badge « Baisse de prix » du portail (jusqu'ici **jeté**) devient un événement.
- **Suppression** : une active non vue depuis **8 jours** entre dans `a_confirmer` ; l'extension ouvre son lien ; verdict **`supprimee`** → `statut = retiree` + `retiree_le`. **Jamais** `retiree_sans_vente` ici — ça reste au cycle mensuel, sur **preuve DVF** (absence de vente). Un lien mort ne retire jamais tout seul : c'est un verdict humain/extension par le lien.
- **Temps sur le marché** = `first_publication_date → retiree_le`, qui alimente l'entonnoir `vendue` (DVF) → Courrier et le digest.

**Exemple réel (recette locale, base dev)** — dépôt des 2 pages de Vic sur l'API 8205 :
- `POST /capture nouvelles` (page riche) → **35 annonces, 34 nouvelles, 1 remontée, 4 à qualifier, `json_riche`** ; re-dépôt identique → **0 nouvelle / 35 maj** (idempotent).
- `POST /capture relecture` (page dégradée) → **40 annonces, `dom_degrade`** ; **11 badges « Baisse de prix » stockés** en événement (vérifié : `select count(*) … dedup like 'pige:baisse-badge:%'` = 11).
- `GET /etat` → `derniere_capture_at` posé, `actives`/`a_confirmer` servis.
- `POST /confirmation {verdict:"supprimee", http_status:404}` → le bien passe `retiree`.
- **Journal** : une ligne par passe (`pige.capture`) — « Radar — nouvelles · 2 page(s) », « relecture · 1 page(s) », « confirmation · 1 lien(s) vérifié(s) ».

---

## 5. Taux de rattachement des terrains (Lot D)

Règle : un **`type==terrain`** dont la surface matche **une seule** parcelle à **±1 %** dans 150 m → `rattachee` niveau `estime`, **preuve « probable »**, confiance 0,70. Deux candidates ou plus → **rien** d'automatique. Bouton **« C'est cette parcelle »** (endpoint `rattacher-humain` existant) → **`certain`**. Niveau **`certain` / `probable` / `quartier`** dérivé (`niveau_preuve`) et servi au client (`rattachement.preuve`).

**Taux mesuré sur la page de Vic** : parmi les **5 purs terrains**, **0** a une parcelle unique à ±1 % (2 en ont 0, un 3, un 2, un 0). → **l'auto-terrain ne rattache rien ici** ; le bouton manuel est la voie principale, exactement ce que le garde 0.3 prévoyait. ⚠️ Les « 3 uniques » de 0.3 sont des **maisons** (surface_hab + terrain) : elles passent par la **cascade bâtie** (surface + emprise), pas par la règle terrain — c'est correct (une maison doit avoir un bâti sur sa parcelle). La règle terrain existe pour le jour où un pur terrain sera unique.

---

## 6. Lecteurs corrigés / consolidés (Lot E)

- **Nouveau cœur `radar_stats(commune, type)`** (`pige/marche.py`) : annonces actives, **médiane €/m² demandé**, **part de baisses / 30 j** (nouvelle), délai médian de retrait. **Appartements INCLUS** (la règle copro ne vaut que pour carte/digests/veilles). Chaque chiffre porte son **`registre_id`** ; libellé **« prix demandés (Radar) »**. Exposé par `GET /radar/stats?commune=&type_bien=`.
- **Aucun lecteur ne mélangeait demandé/DVF** (constat 0.4) : fiche §annonces, Mon secteur, étude de zone étiquettent déjà « prix demandés — jamais un prix LABUSE » / « annonces suivies, jamais un compteur de marché ». Rien à corriger, tout à **ne pas régresser** — préservé.
- `marche.stats` (onglet Marché) inchangé (déjà apparts-inclus) ; `radar_stats` est le cœur réutilisable pour Communes/fiche.

---

## 7. Limites (dites franchement)

- **Mac éteint** : pas de capture ce soir-là ; la source passe « en retard » et la tâche « Déposer Radar » réapparaît (aucune capture depuis 26 h). Rien ne se perd, la collecte reprend.
- **Captcha / DataDome** : l'extension s'arrête net et notifie ; le repli reste le dépôt manuel (`/deposer-html`). On n'insiste jamais (doctrine).
- **Plafond leboncoin ~3 500 / recherche** (`max_pages:100 × 35`) alors que l'île entière = **5 116** : l'inventaire complet **exige des recherches par commune** — d'où la passe « relecture » par commune en rotation. L'encodage exact du paramètre `locations` par commune est **à valider en recette** (0.2) ; défaut = recherche île entière.
- **Confirmation live du clic « page suivante » = riche** : reportée à la recette sur le Mac de Vic (hitter leboncoin depuis le worktree déclencherait DataDome et violerait « pas de capture VPS »). La conception repose sur l'asymétrie déjà prouvée par les deux fichiers.
- **Variante dégradée** : si une page arrive en `dom_degrade`, elle est **acceptée et dite** (provenance), mais sans position → non rattachée ni datée (cf. RADAR-AUDIT-1).

---

## 8. Recette avec Vic (Lot F — à faire ensemble, sur son Mac)

Non automatisable ici (nécessite Chrome + le vrai site + le Mac de Vic) :
1. Installer l'extension, renseigner les Options (searchUrl, LABUSE `http://localhost:8205`, jeton).
2. **« Capturer maintenant »** → vérifier : pages riches, 35 annonces avec position, Radar à jour, « Déposer » absent de À faire, journal 1 ligne/passe.
3. Relancer 5 min après → **0 nouvelle**.
4. Une **relecture** de 3 pages ; une **confirmation** sur 2 liens (une annonce vivante = `presente`, une supprimée = `supprimee`).
5. Captures avant/après → `docs/RADAR/captures/auto-1/`.
6. Valider l'encodage `locations` par commune (0.2) et le clic « page suivante » = riche.

---

## 9. Tests (Lot F)

`tests/test_radar_auto1.py` (9 tests) : registre des 3 jobs cycle ; parseur riche 35 / dégradé 40 ; seuil de prix baisse/hausse 1 % ; confirmation `supprimee` → retiree (jamais retiree_sans_vente) ; `niveau_preuve` ; règle terrain unique/multiple (déterministe) + biconditionnel réel ; `radar_stats` apparts inclus. Plus les tests de registre CRON mis à jour (`radar-cycle` planifié, 23 jobs). Détail des exécutions et de l'unique régression corrigée (`_crit_surface` monkeypatchable) en fin de section.
