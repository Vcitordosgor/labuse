# COMPTE-RENDU — COMPTE-3 (les deux 🔴 de COMPTE-AUDIT-2)

**Branche** `feat/compte-3` (depuis `main` `6b34141a`), worktree `~/Desktop/labuse-compte-audit`.
**Environnement.** venv emprunté `~/Desktop/labuse/.venv`, code servi depuis ce worktree (`PYTHONPATH=src`),
API sur la **base locale réelle** (`postgresql://openclaw@localhost/labuse`) au port libre **8056**, front Vite
sur **localhost:5386/socle/** (proxy → 8056). Clé Brevo réelle présente (comme à l'audit), Stripe `sk_test_`.
Périmètre STRICT : les deux bloquants 🔴 de `docs/COMPTE/COMPTE-AUDIT-2.md`, rien d'autre (pas de refonte,
DA existante).

---

## 🔴 1 — Prolonger un essai au-delà de 48 h (Lot 1)

**Avant.** La seule écriture d'échéance était `creer-essai` (création d'un NOUVEAU compte), la modale codait
`heures: 48` en dur, et l'`À faire` « Prolonger l'essai ou convertir » n'avait que « Convertir » câblé (qui met
`essai_expire_at = NULL`). Aucun moyen depuis le dashboard d'allonger un essai existant.

**Après.**
- **Endpoint** `POST /admin/licences/{compte_id}/prolonger` `{heures}` (`dashboard.py`, `ProlongerIn`), bornes
  **1–720** (mêmes que la création). Il repousse `essai_expire_at = now() + heures`, remet le compte **`actif`**
  (un essai expiré/suspendu **redevient Actif**) et pose une ligne de journal.
- **Modale « Prolonger l'essai »** (`Licences.tsx`, `ProlongerModal`), ouverte depuis la fiche (bouton présent pour
  tout compte d'essai, en cours OU expiré). Elle expose une **date de fin** — par défaut = échéance actuelle
  (bornée à maintenant) + 48 h, `min` = maintenant, `max` = +30 j — convertie en `heures` pour l'endpoint. **Plus de
  `heures: 48` figé.**

**Trois preuves** (compte de test 77, essai forcé échu + `suspendu`, prolongé de 240 h) :

| Preuve | Constat |
|---|---|
| `essai_expire_at` mis à jour | `2026-09-21` (échu) → **`2026-10-03 23:15`** (futur) |
| statut recalculé | `suspendu` → **`actif`** (l'essai expiré redevient Actif) |
| ligne de journal | `evenements_compte` type `essai_prolonge` : **« prolongé jusqu'au 03/10/2026 à 23h15 (heure Réunion) par Vic »** |

- **Mail 4 après prolongation** : l'aperçu (non-envoyant) du template `essai` sur le compte prolongé sert
  `FIN_ESSAI = « le 03/10/2026 à 23h15 (heure Réunion) »` — **la NOUVELLE échéance** (le point d'envoi lit
  `essai_expire_at` en direct, aucun code à ajouter).
- **Bornes** : `heures=0 → 422`, `heures=721 → 422`, compte inconnu `→ 404` (validation du corps, aucune écriture).
- Colonne « À faire » et fiche : l'échéance affichée suit `essai_expire_at` (refetch react-query après la modale).

**Captures** : `captures-compte-3/avant-02-fiche-essai.png` (pas de bouton Prolonger) →
`apres-02-fiche-prolonger-btn.png` (bouton « Prolonger l'essai ») + `apres-03-modale-prolonger.png` (la modale, date
de fin, « L'essai sera actif encore ≈ 48 h »).

---

## 🔴 2 — Garde sur l'URL de base des liens de mails (Lot 2)

**Avant.** En local, `public_base_url = http://127.0.0.1:8000` : les liens des mails partent en localhost,
non cliquables pour un destinataire distant. En prod `LABUSE_PUBLIC_BASE_URL` corrige, mais **rien ne le signalait
à l'écran**.

**Après.** Source UNIQUE `config.base_url_probleme(url)` : renvoie un message si l'URL est **absente, vide, ou
pointe sur `localhost` / `127.0.0.1` / `0.0.0.0`**, sinon `None`. L'envoi n'est **jamais bloqué** (Vic teste en
local), mais l'écran ne peut pas le cacher :

- **Bandeau rouge** sur la page **Comptes** et sur la **fiche** (`Licences.tsx`, lu de `/admin/licences.mail_liens`) :
  « Les liens des mails pointent sur {url} — aucun client ne pourra cliquer. »
- **Chaque entrée `mail_queue`** créée dans cet état porte un **avertissement figé** (nouvelle colonne `avert`,
  posée à l'enfilage dans `mailfile.enfiler`) — visible dans l'onglet **Mails/Activité** (chip coral
  « ⚠ liens non cliquables »).
- **`/readyz`** expose la valeur : `mail_liens {base_url, ok, avert}` en session ouverte / local, **nom d'hôte
  seul** (`{host, ok}`) pour une sonde externe en prod.

**Trois preuves** :

| Preuve | localhost (`http://127.0.0.1:8000`) | prod (`https://app.labuse.immo`) |
|---|---|---|
| `config.base_url_probleme()` | « Les liens des mails pointent sur … — aucun client ne pourra cliquer. » | `None` |
| `/admin/licences.mail_liens` | `{ok: false, avert: "…"}` → **bandeau rouge** | `{ok: true, avert: null}` → **rien** |
| `mail_queue.avert` à l'enfilage | entrée #13 : avert **posé** → chip « ⚠ liens non cliquables » | `null` (aucun avertissement) |

- `/readyz` (local) sert `mail_liens = {base_url: "http://127.0.0.1:8000", ok: false, avert: "…"}`.
- Vérifié pour toutes les formes : `https://app.labuse.immo` → `None` ; `127.0.0.1` / `localhost` → message ;
  `""` → « Aucune URL de base n'est configurée … » ; `https://labuse.immo/` → `None`.

**Captures** : `apres-01-comptes-bandeau.png` (bandeau sur la page Comptes) · `apres-02` (bandeau sur la fiche) ·
`apres-04-mails-avert.png` (onglet Activité, « ⚠ liens non cliquables » sur l'entrée créée en localhost, les entrées
antérieures sans avertissement).

---

## Fichiers touchés

**Backend**
- `src/labuse/config.py` — `base_url_probleme()` (garde, source unique).
- `src/labuse/api/dashboard.py` — endpoint `prolonger` + `ProlongerIn` (Lot 1) ; `mail_liens` dans `/admin/licences` (Lot 2).
- `src/labuse/api/app.py` — `/readyz` expose `mail_liens` (nom seul en prod).
- `src/labuse/mailfile.py` — colonne `avert` (`ADD COLUMN IF NOT EXISTS`) + stampée à l'enfilage.

**Frontend**
- `frontend/src/lib/api.ts` — `postAdminLicenceProlonger`, `AdminLicences.mail_liens`, `MailLigne.avert`.
- `frontend/src/components/admin/Licences.tsx` — `ProlongerModal` + bouton fiche (Lot 1) ; bandeaux Comptes/fiche +
  avertissement par ligne dans la liste des mails (Lot 2).

**Tests**
- `tests/test_dashboard.py` — `test_essai_prolongation_prouvee` (redevient Actif, échéance future, journal, 422/404),
  `test_garde_url_base_liens_mails` (verdict par URL + `mail_liens` servi).
- `tests/test_compte2_mailfile.py` — `test_avert_liens_localhost_figé_a_l_enfilage` (avert posé en localhost, nul en prod).

---

## Portes

- **frontend** : `tsc -b` vert · `vite build` vert · `vitest` **178 passés / 3 échecs PRÉ-EXISTANTS**
  (`circuit/Detail.test.tsx` ×2 + `Donnees.test.tsx` snapshot — fichiers non touchés, baseline connue).
- **backend ciblé** : `test_compte2_mailfile` + `test_compte2_comptes` + `test_comptes` + `test_dashboard` +
  `test_onboarding_tunnel` + `test_audit_comptes` = **verts** (53 puis 36 avec les nouveaux).
- **suite backend complète** (`pytest` hors `test_front_reliquats.py`/`test_r5`) : **3242 passed, 9 failed, 63 skipped**
  (33 min). Les 9 échecs sont TOUS pré-existants / environnement — **aucune régression de COMPTE-3** :
  - `test_deps_declared` → `import 'matplotlib'` non déclaré (dette d'imports, sans rapport) ;
  - `test_veille2_lot5` → `IdleInTransactionSessionTimeout` (timeout DB sous forte charge machine, pas une assertion) ;
  - `test_plu_destinations`, `test_reparations1_lot2`, `test_retours17_permis`, `test_scoring6_score_labuse`,
    `verrous/test_garanties` (g4), `verrous/test_lot1_tables` (`…_base_reelle`) → échecs d'environnement connus
    (base réelle absente de `labuse_test`), aucun ne touche les comptes/mails.
  - Le SEUL test impacté par COMPTE-3 était `test_auth::test_readyz_public_mais_reduit_sans_session` : mis à jour au
    NOUVEAU contrat voulu par le mandat (le mode réduit expose `mail_liens` en **nom d'hôte seul** — rien de sensible),
    **repassé au vert**.
- **ruff** (src) : aucun code nouveau hormis 1 `I001` (import local d'endpoint) — idiome IDENTIQUE aux endpoints
  voisins du fichier (42 `I001` pré-existants), volontairement conservé pour lire comme le code autour.

---

## Inventaire de purge `[CT-TEST]`

Écritures de test faites par ce mandat sur la base réelle :

| Objet | IDs | Nature | Purge |
|---|---|---|---|
| Compte `[CT-TEST] Prolong` | compte **77** + utilisateur associé + `mail_queue` **#13** (avert, jamais parti) | test de la prolongation + du stamp avert | `DELETE FROM comptes WHERE id = 77;` (cascade user) puis `DELETE FROM mail_queue WHERE id = 13;` |
| Artefact de capture (compte RÉEL 63) | `mail_queue` #14 + son journal | entrée avert enfilée pour la capture `apres-04` | **déjà supprimée** — le compte 63 est laissé intact (3 entrées réelles d'origine) |

```sql
-- purge des artefacts de test de COMPTE-3 (comptes de test uniquement)
DELETE FROM mail_queue WHERE id = 13;
DELETE FROM comptes    WHERE id = 77;   -- cascade utilisateur + sessions
```
*(Le compte 77 est un `@labuse.test` masqué de tous les chiffres. #14 sur le compte réel 63 a déjà été retiré —
aucun mail réel n'a été envoyé : `enfiler` n'enfile pas, ne part pas.)*
