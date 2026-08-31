# OUTILS-5 — Refonte de la catégorie Projets

Branche `feat/outils-1`. Référence visuelle et conceptuelle : `docs/maquettes/projets-v3.html`.

**Principe directeur** — *« Rien n'est caché, tout est ordonné. »* Un promoteur refuse une sélection secrète. La
shortlist plafonnée disparaît (écrans **et** textes). Un projet **contient le vivier entier** de son cadrage,
**ordonné par probabilité de mutation** (score LABUSE), mieux classées en tête, **servi par pages** de 50.

**Un moteur, une donnée** — le vivier d'un projet est la MÊME requête vivante que la carte / le filtre
(`_cadrage_to_filtre → FiltreCriteres → _q_v2_where/_q_v2_list`), servie par `_cadrage_page_idus`
(`ORDER BY s2.rang ASC` — `projets.py:290`). Aucune donnée figée, aucun texte codé en dur dans le front.

---

## P0 — Table rase

~70 projets de test supprimés (données `projets` + `projet_parcelles` — retenues/écartées/à-trier).
**`courrier_demandes` n'a PAS été touché** (les demandes de courrier ne sont pas des projets). Pas de
migration d'ancien format.

```
$ psql -tAc "select count(*) from projets"
0
```

## P1 — « À trier » = le vivier entier, classé, paginé

- Servi par `_cadrage_page_idus` → `ORDER BY s2.rang ASC NULLS LAST, p.idu ASC LIMIT :lim OFFSET :off`
  (`src/labuse/api/projets.py:290`). **Preuve** : le rang 1 du run servi est `brulante` (Priorité) —
  la page 1 remonte donc bien les mieux classées d'abord.
  ```
  $ psql -tAc "select parcelle_id, rang, tier from parcel_p_score_v2 order by rang asc limit 3"
  97423000AB1908|1|brulante
  97408000AP1647|1|brulante
  ```
- Compteur en toutes lettres : **« N · les mieux classées d'abord »** ; l'affichage de pagination dit
  honnêtement « Charger plus · les X premières sur M » (jamais un plafond, jamais un compteur muet).
- **Filtres de navigation** (chips `data-kanban-nav-tier`) : Tous / Priorité (`brulante`) / À suivre (`chaude`),
  appliqués par la MÊME facette `tiers` que la carte : `cadrage = {**filtres, **({"tiers":[tier]} if tier else {})}`
  (`projets.py:1001`) — jamais un moteur parallèle.
- **Signal de classement par carte** : `s2.top5_contributions` (`projets.py:1030`) → `raison_dominante(top5)`
  (`projets.py:1083`, `data-card-signal`) : « permis récent », « succession probable »…
- **Instantané daté** : chaque projet affiche « valeurs au JJ/MM (run X) » — un instantané des valeurs du
  vivier, pas le figeage d'une sélection.

## P2 — « pourquoi ? » = l'explication UNIQUE de LABUSE

Interdit d'écrire une prose parallèle. Les modales existantes de l'analyse LABUSE (`AlgoExplainer` /
`ScoringExplainer`) sont **exportées** depuis `panel/LeftPanel.tsx` et **réutilisées telles quelles** dans
le kanban ET le wizard — une seule explication, servie partout. Le lien `data-kanban-pourquoi` (récap vivier)
et `data-recap-pourquoi` (wizard) ouvrent la même modale via le store (`setAlgoModale('scoring')`).

## P3 — Écran 0 (deux portes) + wizard 5 étapes

- **Écran 0** : deux portes (`data-projet-porte`) — « Partir du vivier LABUSE » / « Projet de zéro ».
- **Projet de zéro** : `createProjet({ de_zero: true })` → sentinelle `__de_zero__` → vivier vide (gardes
  `_cadrage_page_idus`/`_cadrage_total`). Les parcelles s'ajoutent depuis les fiches (bouton « Projet »),
  `projet_ajouter` insère `statut='retenue'` (+ `_sync_crm_retenue`) → **elles alimentent la colonne Retenues**
  (vérifié : BZ1065 ajoutée à un projet vide apparaît en Retenues).
- **Wizard** : 5 étapes (était 6) — `NOM · PÉRIMÈTRE · CONTEXTE · CADRAGE · RÉCAPITULATIF`. « CONTEXTE » fusionne
  budget + type. « CADRAGE » ne mentionne plus aucune shortlist. Le **RÉCAP affiche le vrai nombre du vivier**
  (`getCadrageCompteur` → `data-recap-vivier`), plus jamais « 2 facettes ».

## P4 — Projet ouvert

- **En-tête** : « vivier N classées · valeurs au JJ/MM · contexte ».
- **RETIRÉS** : « Rejouer » (le projet est un instantané daté assumé), « CSV complet », le bouton « Trier »
  (parcours carte), le geste « ◑ Peut-être », le bandeau « cadrage modifié / rejeu ».
- **Deux gestes seulement** : ✓ Retenir · ✕ Écarter. Écartées **réversible**.
- **Retenues** : « → CRM » + **« ✉ Courrier (N) »** (`data-kanban-courrier`) qui ouvre l'outil Courrier
  propriétaire **pré-rempli des parcelles retenues** (`setCourrierPrefillIdus(retenues.idus)` → outil courriers).
- « Ouvrir la fiche → » par carte.

## P5 — Accueil

- **Menu ⋯ retiré** (`<details data-projet-menu>` supprimé).
- Carte : nom / périmètre / **« vivier N classé »** / valeurs au JJ/MM / contexte + **jauge de progression**
  (« N retenues · M écartées · K à explorer, classées ») ; **compteur RETENUES** à droite (`data-projet-retenues`).
- Onglets Actifs / Archivés / Mes courriers inchangés.

---

## Vérif finale

| Contrôle | Résultat |
|---|---|
| `tsc` (noUnusedLocals) | **0 erreur** |
| `vitest` | **vert** |
| `build` | **vert** |
| `pytest tests/` | **2000 passed, 42 skipped, 0 failed** (5 min 36) |
| Golden | **intact** — aucun fichier `scoring/` / `qa/` / golden modifié |
| Périmètre d'écriture | 6 fichiers, domaine projets + P0 uniquement |

**Fichiers modifiés**
```
 M frontend/src/components/panel/LeftPanel.tsx        (export AlgoExplainer/ScoringExplainer — P2)
 M frontend/src/components/projets/ParcoursProjet.tsx (écran 0 + wizard 5 étapes + récap réel — P3)
 M frontend/src/components/projets/ProjetKanban.tsx   (vivier classé, nav, signal, 2 gestes, Courrier — P1/P2/P4)
 M frontend/src/components/projets/ProjetsPanel.tsx   (accueil ⋯ retiré, vivier classé, RETENUES — P5)
 M frontend/src/lib/api.ts                            (de_zero, tier, raison)
 M src/labuse/api/projets.py                          (tier, top5→raison, de_zero, ajouter→retenue)
```

**Grep résidus — domaine front `frontend/src/components/projets/`** : aucune occurrence *vivante* de
« shortlist » / « Rejouer » / « Peut-être » / export CSV. Les seules correspondances restantes sont des
**commentaires documentant les retraits**, plus l'affichage de pagination légitime « les X premières sur M »
(P1, pages de 50 — honnête, jamais un plafond).

### Résidus signalés (hors périmètre d'écriture)

1. **`ParcoursTinder.tsx`** (ancien parcours swipe) est devenu **inatteignable** : son unique point d'entrée
   était le bouton « Trier », retiré en P4. `openParcours(` n'est plus appelé nulle part → l'état `parcours`
   reste toujours `null`, donc `{parcours && <ParcoursTinder/>}` (`App.tsx:380`) ne rend jamais rien. Vestige
   inerte laissé en place : le retirer toucherait `App.tsx` (conditionnel de layout du `LeftPanel`) et le store,
   hors du périmètre d'écriture chirurgical de ce mandat. **Nettoyage recommandé en suivi.**
2. **Backend `_figer_shortlist` / `projet_rejouer`** subsistent (legacy M120, couverts par
   `tests/test_projet_m120.py`). Le figeage daté d'une sélection n'est plus **servi nulle part** dans l'UI
   (le vivier vient de la requête vivante paginée) ; la route `/projets/{id}/rejouer` renvoie déjà **404**
   (`test_audit_secu.py:91`). Laissé pour ne pas casser une suite verte hors périmètre.

### Captures (`docs/OUTILS-5/captures/`)
- `01-accueil-P5.png` — accueil sans ⋯, vivier classé, compteur RETENUES.
- `02-kanban-P1-P4.png` — vivier 33 910 classées, « pourquoi ? », 3 filtres de nav, signal « permis récent »,
  2 gestes, Courrier (N).
- `03-pourquoi-modale-P2.png` — l'explication LABUSE unique, ouverte depuis le kanban.
- `04-wizard-ecran0-P3.png` — écran 0, deux portes.
- `05-wizard-step1-P3.png` — « 1 / 5 · NOM ».
- `06-wizard-recap-P3.png` — récap avec vrai nombre du vivier + « pourquoi ? ».

---

**Provenance** — API (uvicorn :8000) et front (vite) redémarrés avant recette ; captures Playwright prises
sur l'app servie. Lectures Postgres partout ; écritures limitées au domaine projets (suppressions P0). Golden
non touché.
