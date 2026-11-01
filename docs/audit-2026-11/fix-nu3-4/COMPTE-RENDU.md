# FIX-NU3-4 — extension Radar (correctifs K-RAD + L-EXT + M-T)

**Branche** `fix/nu3-4` · worktree `~/Desktop/labuse-fix4` · ports 9430/6630 · **Opus**
Périmètre : l'extension Chrome (`outils/radar-extension/`) et le point d'entrée serveur qui reçoit ses
captures (`src/labuse/pige/api.py`). Aucun accès prod, aucun merge. K-RAD-04 « lisible dans l'admin » a
nécessité un ajout **lecture seule** minimal côté admin (décision validée : `Radar.tsx` + type `api.ts`).

Entrées : `docs/audit-2026-11/nu-3/K/RAPPORT.md` (K-RAD), `L/RAPPORT.md` (L-EXT), `M/RAPPORT.md` (M-T).

---

## Ce qui est corrigé

| # | Constat | Correctif |
|---|---------|-----------|
| **K-RAD-02** | Verrou `running` sans garde-fou → une passe tuée (sommeil Mac / fermeture Chrome / éviction MV3) bloque **toutes** les passes auto suivantes. | Verrou **horodaté** (`runningSince`). Un verrou plus vieux que **45 min** (`RUN_STALE_MIN`, une passe dure 10-30 min) est considéré **libre** : la passe repart seule. Relâché aussi au (re)chargement du worker (`relacherVerrouPerime`). `verrouActif(opts, now)` pure. |
| **K-RAD-03** | `autoRunDate` posé **avant** le run → un hoquet réseau en début de soirée « brûle la nuit » (plus de reprise auto). | `autoRunDate` posé **après le succès** seulement (source `auto`). Un échec ne pose rien → le battement suivant (toutes les 5 min, dans la fenêtre) **retente** la nuit même. |
| **K-RAD-01** | Le Mac dort pendant la fenêtre → passe ratée **en silence**. | Détection de **veille** : un écart entre deux battements ≥ **15 min** (`SEUIL_VEILLE_MIN`, cadence normale = 5 min) = sommeil système. C'est **dit** dans le compte-rendu de passe (« ⚠ Mac en veille détectée ce soir, réveil après ~N min ») et envoyé au serveur. `veilleDetectee(last, now)` pure. |
| **K-RAD-04** | Le journal de passe ne vivait que dans `chrome.storage` → une nuit **ratée** ne laissait aucune trace active côté serveur. | L'extension POSTe un **compte-rendu de fin de soirée** (succès / échec / veille) à `POST /admin/radar/journal` → `event_log` (EV_CAPTURE, dedup `pige:soiree:<jour>`, rafraîchi). `GET /admin/radar/check` renvoie `dernier_journal` ; l'écran admin Radar l'affiche (bloc lecture seule). |
| **L-EXT-01 / L-EXT-08** | La capture Leboncoin postait `document.documentElement.outerHTML` — le DOM **complet d'une session connectée** (identité de Vic, messagerie, parfois jetons) — archivé verbatim côté serveur. | `inspectPage` n'extrait plus l'`outerHTML`. On n'envoie **que les annonces** : `searchData.ads` (variante A) reconstruites dans la forme attendue par le parseur serveur, ou — pages A/B sans searchData — les seules cartes `<article>` (variante B). `payloadDeCapture(info)` pure ; `<` échappé (pas d'injection `</script>`). Plus aucune donnée personnelle dans le POST **ni dans l'archive** serveur. |
| **L-EXT-02** | Un JSON Bien'ici **HTTP 200 au schéma changé** (`realEstateAds` renommée / absente / `null`) était traité `|| []` = « fin d'inventaire » silencieuse, run affiché « OK ». | `biCapturePage` distingue trois cas : JSON illisible (tronqué) → erreur ; clé absente/non-tableau → **erreur « structure changée »** ; tableau vide → fin propre en page > 1, **erreur** en page 1 (aucune annonce du tout). Plus jamais « OK » silencieux. |
| **M-T18** | Recette « Tester l'alarme (+2 min) » livrée dans le **popup de prod** (visible/cliquable par un client). | Retirée du popup ; déplacée dans **Options → Recette (vérification technique)**, repliée (`<details>`). Le message `test-alarm` du worker est inchangé. |
| **M-T19 / M-T17** | Jargon en surface client : « Jeton (X-Radar-Token) », « Jitter max », « LBC nouv 3, relec 12, conf 1 ». | « **Jeton de connexion Radar** » (+ `type="password"`, cf. L-EXT-06), « **Décalage aléatoire maximum (minutes)** », compte-rendu humain « **Leboncoin : 3 nouvelle(s), 12 revue(s), 1 vérifiée(s)** » / « Bien'ici : … ». |
| **M-T11** | Tutoiement/vouvoiement mélangés pour la même consigne (« Déposez » vs « dépose à la main »). | Vouvoiement uniforme : notification « Radar bloqué — **déposez** à la main ». |
| **L-EXT-06** | Jeton admin stocké/affiché en clair. | Champ `type="password"`, `autocomplete="off"`, mention de portée. |

> **Non traités (hors périmètre de ce lot, documentés)** : L-EXT-03 (horloge Mac fausse — défense de temps serveur),
> L-EXT-04/05/07/09, L-CHN-\*, L-MIL-\*, L-JOB-\* (chaîne des données, millésimes, jobs — code serveur hors
> point d'entrée des captures). K-SAV-\* / K-CHG-\* / K-NAV-\* (sauvegardes, charge, navigateurs — autres domaines).

---

## Recette (hors navigateur, `node`)

Les 6 recettes existantes restent vertes (fakeInspect réaligné sur le nouveau contrat `inspectPage` :
`searchAds`/`vignettes` au lieu de `outerHTML`/`nextData`). Deux recettes ajoutées :

- **`recette_verrou.mjs`** — `verrouActif` (frais = bloque, > 45 min = libéré) ; `veilleDetectee`
  (écart ≥ 15 min = sommeil, minutes rapportées) ; **passe tuée** (verrou périmé) → la soirée **repart**
  seule et relâche le verrou ; **K-RAD-03** : échec → `autoRunDate` vide (reprise possible) → succès →
  `autoRunDate` posé + compte-rendu serveur.
- **`recette_contenu.mjs`** — **L-EXT-01** : `payloadDeCapture` n'émet que les annonces (0 fuite
  identité/messagerie/jeton de la session connectée), reste parseable par le serveur, `</script>`
  neutralisé ; variante B = stub `__NEXT_DATA__` + cartes `<article>` seules. **L-EXT-02** : JSON tronqué
  → « illisible », clé renommée / `null` → « structure changée » (jamais « OK »).

```
recette_alarme · bascule · bienici · confirmation · fenetre · pagination · verrou · contenu → 8/8 OK
```

## Banc complet (filet du hook, local)

- Front **`tsc -b` 0 erreur** · **vitest 301 passed / 63 fichiers**.
- Python **unitaires (`not db/local/reel/network`) 2813 passed**, 48 skipped, 0 échec.
- **Cohérence 6/6** (base locale, run 17 servi) — aucun écart (les correctifs n'altèrent aucune valeur servie).
- Scan de secrets : rien trouvé.

## Fichiers touchés

Extension : `background.js` (verrou horodaté, veille, autoRunDate-après-succès, payload épuré, schéma
Bien'ici, journal, libellés), `popup.html`/`popup.js` (recette retirée du popup), `options.html`/`options.js`
(recette déplacée, libellés, jeton masqué), `README.md`, recettes (`alarme`/`bascule`/`pagination` réalignées,
`verrou`/`contenu` neuves). Serveur : `pige/api.py` (`JournalIn`, `POST /admin/radar/journal`,
`dernier_journal` dans `/admin/radar/check`). Admin (lecture seule) : `Radar.tsx`, `lib/api.ts`.

## Rappel déploiement (pour Vic)

Après le merge, **recharger l'extension dans Chrome** (`chrome://extensions` → recharger « LABUSE Radar »)
pour que le nouveau `background.js` prenne effet.
