# COMPTE-RENDU FICHE-1 — Les trous de la fiche parcelle

Branche `feat/fiche-1`, worktree `~/Desktop/labuse-audit`, depuis `origin/main` (`aa4b520c OUTILS-FIX-4`). Rien mergé. Un commit + un push par lot.

## Environnement & pièges

- Editable install `labuse` pointe sur un AUTRE worktree (`~/Desktop/labuse`) → toujours `PYTHONPATH=src` pour tester CE worktree (piège CIRCUIT-5b).
- WeasyPrint : `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` sinon `OSError libgobject` casse la collecte pytest (FZ-002).

## Suites de départ (avant tout changement)

- **vitest** : 187 passed (43 fichiers).
- **pytest** : `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python -m pytest -q` → **2689 passed, 4 failed, 50 skipped** en 88 s.
- Les **4 échecs sont PRÉ-EXISTANTS** (base fraîche, avant toute modification FICHE-1), tous liés à l'état DB de test local (`sqlalchemy` / dashboard) :
  - `tests/test_courrier_boucle.py::test_boucle_piste_courrier_reponse`
  - `tests/test_courrier_boucle.py::test_backfill_rattache_par_idu_compte_univoque`
  - `tests/test_dashboard.py::test_ia_log_attribue_au_compte`
  - `tests/test_front_reliquats.py::test_r5_etudier_deux_marges_chacune_dit_son_referentiel`
  - Cible de non-régression : rester à ≤ 4 échecs, ces mêmes 4.

---

## Journal des lots

### Lot 1 — Le bâti (nouveau tiroir « Le bien ») ✅

Nouveau tiroir « Le bien », placé après « Constructibilité » (front + registre).

- **Producteur unique** `bati.le_bien_block(session, idu)` (aucun calcul au front) : emprise bâtie au sol, nombre de bâtiments, hauteur du bâti, surface au sol libre, nature/pente du toit.
- **Emprise bâtie** = empreinte **vecteur BD TOPO** (somme des intersections), COHÉRENTE avec le nombre de bâtiments. **Décision tranchée** : CoSIA sur-détecte à la maille parcelle (ex. 97419000AI0999 : CoSIA 29 010 m² alors que BD TOPO voit 0 bâtiment → « vacant »). Mélanger CoSIA à l'emprise donnait un bloc incohérent. CoSIA est donc servi **à part** (`cosia_detecte_m2`, « détecté non cartographié — à vérifier »), jamais confondu avec l'emprise.
- **Hauteur** = `potentiel._hauteur_bati_m` (BD TOPO, max des bâtiments). **Nb bâtiments** = `bati.fiche_block` (BD TOPO, ≥ 10 m²). **Surface libre** = max(0, surface − emprise).
- **Toit** (LiDAR HD) : nature + pente lues sur le **cache `toiture_lidar` SEUL** via `solaire_toiture.toiture_depuis_cache` — **jamais de requête WMS dans la fiche** (un fetch LiDAR de 60 s à chaque ouverture est exclu ; le cache est chauffé par la fiche soleil / le builder de nuit). Les trois états RETOURS-15 U5 (servie · « non déterminée — pans non nets » · « non calculée — LiDAR indisponible ») voyagent dans `toit.verdict/libelle`. Cache froid → ligne toit muette « non encore relevée », pas un faux.
- **Tiroir omis** si couche bâtiments non ingérée (`le_bien=null`) — jamais un bloc creux.
- **Registre** : `emprise_batie_m2`, `hauteur_bati_m`, `n_batiments` sortis d'`en_attente` (« maquettes d'exports ») et servis ; 3 nouvelles données `surface_libre_sol_m2`, `nature_toit`, `pente_toit_deg`. Robinet `fiche_parcelle_le_bien` ajouté. Les 6 sont **mono-robinet** → auto-pass V5c.
- **Vérifs** : `circuit verrous` 16/16 vert (174 données) · tsc 0 · vitest 187 · `test_fiche1_le_bien.py` 4/4 · doc registre régénéré (+19 lignes, tiroir « Le bien »).

### Lot 2 — Le DPE, rétabli ✅

`dpe_connu` était `en_attente` (« bloc payload construit mais plus affiché », Fiche.tsx:1492) : la fiche premium (`_q_v2_fiche`) ne le servait pas. Rétabli dans le tiroir « Le bien ».

- **Producteur** `_dpe_connu_block(db, idu)` (passe-plat de `dpe_records`, table déjà dans la carte) : sert le **plus récent** (étiquette énergie + GES, date, type de bâtiment) et le **nombre** de DPE connus. Rattachement adresse/BAN → parcelle, donc c'est le DPE du **bâtiment**, pas de la parcelle — le libellé le dit (« DPE du bâtiment »).
- **Plusieurs DPE** → le plus récent servi + « N DPE connus, le plus récent » en source.
- **Aucun DPE** → `null` → le front dit **« non déterminée — aucun DPE rattaché »** (affiché seulement quand il y a du bâti ; jamais sur un terrain nu).
- **Registre** : `dpe_connu` sorti d'`en_attente`, fonction repointée `_dpe_connu_block`, ajouté au robinet `fiche_parcelle_le_bien` (mono-robinet → auto-pass V5c). Test guard `test_eau_dpe_attribuable_au_registre` mis à jour (rétabli, plus en_attente, dpe_ademe non muet). Commentaire mort Fiche.tsx (F2) remplacé.
- **Vérifs** : `circuit verrous` 16/16 vert · tsc 0 · vitest 187 · tests registre/verrous 41/41 · doc régénéré. Vérifié en base : 97411000AC0079 → D/GES B (2026), 97408000AO1568 → E/E (2022), 97411000BD0080 → aucun.
