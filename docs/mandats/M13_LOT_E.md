# M13 — LOT E · Projet

Branche `fix/m13-e-projet` (worktree isolé, base M12 `884daf0`). Zéro touche scoring.
Chaque point est prouvé par une capture de l'app en fonctionnement (`qa/m13/E/`).

Golden : **116/116 PASS** (API 8034, run servi). Tests projet back : `test_projet_m2.py` 4/4
(backend `projets.py` inchangé). `npm run build` : 0 erreur TS.

---

## E1 — La recherche projet est déclenchée AU LANCEMENT (QA-51) — **FAIT, prouvé**

**Symptôme** : après « Lancer la recherche », les 3 colonnes restaient vides (« Rien à trier ») ;
seul « + Chercher plus » peuplait. La recherche marchait mais n'était pas déclenchée à l'arrivée.

**Correctif** (`components/projets/ProjetEntretien.tsx`) : le handler de « Lancer la recherche »
(mutation `lancer`) déclenche désormais la proposition **avant** d'ouvrir le kanban :
`createProjet` puis `proposerProjet(projet.id)` (idempotent, `ON CONFLICT DO NOTHING`), puis
`setOpenProjet`. À l'arrivée dans la vue 3 colonnes, « À trier » est déjà PEUPLÉE. L'échec de
proposition n'empêche pas l'ouverture (le kanban conserve son filet `useEffect` idempotent).

**Preuve** : `qa/m13/E/e1_a_trier_peuplee.png` — vue 3 colonnes, « À trier **24** » peuplée
(24 rangs affichés), Retenues/Écartées vides, juste après le lancement.

## E2 — « + Chercher plus » retiré, remplacé par une phrase (QA-52) — **FAIT, prouvé**

**Correctif** (`components/projets/ProjetKanban.tsx` + `lib/strings.ts`) : bouton `+ Chercher plus`
et sa mutation `elargir` supprimés (rendus inutiles par E1). Remplacés par une phrase orientée
client, placée dans le fichier de chaînes centralisé (`CLIENT.projet.enrichir`). Le placeholder de
colonne vide « Rien à trier — « Chercher plus » » devient « Rien à trier ».

**Texte E2** (`lib/strings.ts` → `CLIENT.projet.enrichir`) :

> Une parcelle en tête ailleurs ? Ajoutez-la à ce projet à tout moment depuis sa fiche, avec le
> bouton « Projet ».

**Preuve** : `qa/m13/E/e2_phrase.png` — l'en-tête du kanban montre la phrase à la place du bouton
(ne restent que Exporter / Renommer / Archiver).

## E3 — Bouton « Projet » : ajout fiable + anti-doublon + projets grisés (QA-53) — **FAIT, prouvé**

- **Ajout fiable** : depuis la fiche, la parcelle atterrit bien en « À trier » (`proposee`).
  Vérifié en UI (ajout à E3-ALPHA) et back (`/ajouter` → `added=true`).
- **Anti-doublon** :
  - **Backend** (déjà en place, `projets.py::projet_ajouter` / `_upsert_proposee`) : `INSERT …
    ON CONFLICT (projet_id, parcel_id) DO NOTHING` → un 2e ajout renvoie `added=false, already=true`.
    Prouvé au runtime (add ×2 sur la même parcelle : `already=true` au 2e).
  - **UI** (`components/fiche/Fiche.tsx`) : un projet contenant déjà la parcelle est **grisé et
    non cliquable** (`data-deja=1`, `disabled`, `opacity-50 cursor-not-allowed`, « ✓ dedans »).
    Source de vérité : `GET /projets/pour-parcelle/{idu}` (M12) → `dejaIds`.
- **Décision de conception (accès au menu)** : le bouton « Projet » ouvre désormais **toujours** le
  menu (avant : `attaches.length===1` ouvrait directement le projet, rendant le menu — et donc
  l'ajout à un autre projet — inatteignable, ce qui contredisait le titre du bouton « ouvrir /
  rattacher à un autre »). Le menu liste en tête une section « Ouvrir » (liens vers les projets déjà
  rattachés) puis « Rattacher à un projet » (les rattachés grisés, les autres cliquables). Ainsi une
  parcelle déjà dans un projet reste rattachable à un second, et l'anti-doublon est visible.

**Preuve** : `qa/m13/E/e3_projets_grises.png` — menu Projet après ajout à E3-ALPHA : **E3-ALPHA
grisé « ✓ dedans » (non cliquable)**, E3-BETA et les autres projets actifs (« + »).

---

## Fichiers touchés

- `frontend/src/components/projets/ProjetEntretien.tsx` — E1 (proposition au lancement)
- `frontend/src/components/projets/ProjetKanban.tsx` — E2 (retrait bouton, phrase, placeholder)
- `frontend/src/lib/strings.ts` — E2 (texte client `CLIENT.projet.enrichir`)
- `frontend/src/components/fiche/Fiche.tsx` — E3 (menu toujours ouvert, section « Ouvrir »,
  grisé renforcé, `data-deja`)

Backend `src/labuse/api/projets.py` : **inchangé** (l'anti-doublon back existait déjà).

## Vérifications

- `npm run build` → 0 erreur TS.
- `pytest tests/test_projet_m2.py` → 4/4.
- Golden (`qa/golden_check.py`, API 8034) → **116/116 PASS, 0 FAIL**.
