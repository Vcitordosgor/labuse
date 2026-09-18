# SOURCES-CORRECTION-2 — Les trois restes

**Branche** `feat/sources-audit-1` — étape 0 : `c478d2e2` (HEAD après SOURCES-CORRECTION-1). Un commit par
lot, branche poussée, aucun merge. Gates : `tsc -b` vert, `labuse circuit verrous -w G8` vert.

---

## Lot 1 — les deux statuts, tranchés

### `cadastre_epoque` → **`interne`** (nouveau statut) : hors vitrine CLIENT, visible au Circuit ADMIN

Décision : cadastre_epoque ne sert qu'à **recaler la géométrie des permis Sitadel** (aucune surface
client) → elle **sort de la vitrine**, mais reste **inspectable dans le Circuit admin avec son rôle
déclaré** — pas masquée comme les retirées. Aucun statut existant ne disait « référentiel interne » :
j'en ai **ajouté un** (`DataSourceStatus.INTERNE = "interne"`), première classe comme `hub`/`partenariat_requis`.

- **`enums.py`** — `INTERNE = "interne"` (ingéré et LU par la pompe, rien au client ; la note DOIT nommer le rôle).
- **`circuit_verrous.py`** (V2b `analyse_catalogue`) — branche `elif statut == "interne"` : accepté hors
  vitrine **à condition que la note nomme le rôle** (sinon violation) — même discipline que `partenariat_requis`.
- **`api/dashboard.py`** (`_assembler_reservoirs`, ce que sert le Circuit admin) — filtre passé de
  `WHERE_AFFICHEES` à **`(WHERE_AFFICHEES) OR status='interne'`** : le Circuit montre désormais **vitrine ∪
  référentiels internes**. Les compteurs CLIENT (`WHERE_AFFICHEES` : `/sources`, accueil, `flux.construire_flux`,
  V2a) sont **inchangés** — le split des deux audiences est là.
- **`seed_sources.py`** — entrée cadastre_epoque : `status=S.INTERNE` + note refaite qui **nomme le rôle**
  (`cadastre_historique` lue par `ingestion/cadastre_historique.py:rattacher_par_geometrie` pour recaler
  Sitadel). **DB** : `UPDATE status='interne'` + même note.

### `sudocuh` → **reste en vitrine** (inchangé)

Elle alimente le modèle candidat `q_v14` (`anciennete_plu`), **visible dès la bascule** du run servi. On la
garde `connecte` : la sortir puis la rentrer à la promotion de `q_v14` serait du yo-yo. Aucune modification.

### Preuve

- **Vitrine 93 → 92** (client). **`V2a` OK — 92 = 92 = 92** (vitrine SQL = prédicat Python `est_affichee` =
  page `flux.construire_flux`) ; **`V2b` OK** (interne accepté, rôle nommé) ; catalogue validé.
- **cadastre_epoque dans le Circuit ADMIN** : `_assembler_reservoirs` = **93 réservoirs, cadastre_epoque
  présent** (carte réservoir rendue, mode one_shot) ; **`flux.construire_flux` (client) = 92, cadastre_epoque
  ABSENT**. Le référentiel interne est visible à l'admin, invisible au client — exactement le partage demandé.
- **`verrous -w G8` exit 0, tout va bien** : ajouter un statut a demandé **4 listes fermées** cohérentes —
  `enums.py` (l'enum), V2b `analyse_catalogue` (accepte + exige le rôle), **`STATUTS_ADMIS` de G1** (la
  garantie « liste fermée » — G1 a cassé au premier essai, réparé ici), et `_assembler_reservoirs`
  (le Circuit). `test_g1_statut_hors_liste_fermee_casse` (qui fige la liste) mis à jour avec `interne` → **passe**.
- `tsc -b` : le front Circuit est data-driven (rend la carte réservoir telle quelle) → aucun fichier front touché.
- *Les autres tests rouges (les 4 « morts » d'avant CRON-1 + `test_g2_signature_dpe`, périmé par la
  ré-ingestion DPE du mandat précédent qui asserte encore `dpe_ademe quasi_vide` + la composition
  25 verrous/garanties) sont réconciliés au **lot 3** (« pytest sans échec »).*