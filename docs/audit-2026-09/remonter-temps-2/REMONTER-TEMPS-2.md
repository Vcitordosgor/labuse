# REMONTER-TEMPS-2 — Frise lisible et cliquable · cadastre d'époque · 3 écarts

Exécution de la suite de [REMONTER-TEMPS-1](../REMONTER-TEMPS-1.md). Branche
`feat/remonter-temps-2` (worktree `labuse-temps2`, base main `f457b319`, ports 8355/5555). Non mergé.
DA : composants partagés `ui/` (Chip). 3 lots, un commit chacun.

Outil : `frontend/src/components/outils/TimeMachine.tsx` (comparateur) + `HistoireFrise.tsx` (frise) ·
backend `src/labuse/api/moteurs.py` (`/moteurs/histoire/{idu}`, `/moteurs/parcellaire-epoque/{idu}`).
Témoins : **BZ1065** `97411000BZ1065` · **CH1970** `97414000CH1970` · **CM1086** `97422000CM1086` ·
**AB0001** `97401000AB0001` (+ **DK0386** `97422000DK0386` pour le cadastre, voir Lot B).

---

## Lot A — Frise : échelle non linéaire + points cliquables (commit `8a6f0c83`)

**Échelle non linéaire, FIXE pour tout le monde** (prévisible, pas de zoom auto par parcelle). L'axe
linéaire 1950→aujourd'hui écrasait tous les faits récents (le cas courant) sur les derniers pixels.
Trois segments : **1950-2000 = 20 %** · **2000-2015 = 30 %** · **2015-aujourd'hui = 50 %** de la
largeur ; bornes de segment (2000, 2015) matérialisées par un trait vertical léger sur le rail ; les
repères d'orthos et les faits se replacent via un `pct()` segmenté.

**Empilement par MOIS** (avant : par année) : deux faits du même mois se décalent verticalement (aucun
masqué) ; des faits de mois différents partagent la rangée 0 et s'étalent — avec l'échelle non linéaire
le récent a enfin la place.

**Encart cliquable SOUS la frise** : un seul ouvert à la fois (état unique), **fermeture au clic
ailleurs** (mousedown hors frise+encart via `ref`), survol = rien (règle DA). Le détail (prix/surface
pour une vente, pétitionnaire pour un permis, ancienne/nouvelle PM, mères/filles pour une découpe) et
les ponts (Permis / fiche-ventes / Scan patrimoine) existaient déjà — l'encart passe côté→dessous.

Captures : `avant-ch1970-frise.png` (linéaire — 4 faits 2025 écrasés à droite, 1950-2018 vide) vs
`apres-ch1970-frise.png` (segments + bornes 2000/2015, faits datés lisibles) · `apres-ch1970-encart.png`
(encart ouvert sous la frise).

---

## Lot B — Cadastre d'époque : version MINIMALE retenue (commit `64aeb592`)

**Découverte data (bloquante pour la version « pleine ») :** `cadastre_historique` (ingestion
RETOURS-14) n'est **pas** un parcellaire d'époque complet. Elle ne stocke que **~6 398 parcelles
d'origine DISPARUES** du cadastre actuel (les **mères** de divisions, `WHERE NOT EXISTS in parcels`),
**une seule géométrie par idu**, aucune au millésime courant. Les 4 témoins de l'audit (et leurs mères)
n'y sont **pas** → la surimpression « cadastre du millésime » plein écran et la capture « CH1970 découpe
2025 visible » sont **impossibles** avec cette table.

**Décision (validée) : version MINIMALE** — pas de couche cadastre plein écran ; on montre l'**ancien
contour de la parcelle courante** quand sa **mère est captée**, sinon un message honnête.

- **Backend** `GET /moteurs/parcellaire-epoque/{idu}` → FeatureCollection du/des contour(s) de la/les
  parcelle(s) MÈRE (`cadastre_historique ⋈ dfi_filiation` sur `idu_mere`), avec millésime. Vide quand
  la mère n'est pas captée — **jamais un contour inventé**.
- **Frontend** : chip `ui/Chip` **« Parcellaire de l'époque »** (ambre, off par défaut), **grisé quand
  la période « avant » < 2017** (mention « parcellaire d'époque disponible à partir de 2017 »). ON +
  période ≥ 2017 : superpose sur le **volet AVANT** le contour **ambre fin en tirets** de la mère (sous
  le contour blanc de la parcelle courante), **millésime affiché** ; mère non captée → « pas de
  parcellaire d'époque pour cette parcelle ». Tuiles : GeoJSON du seul contour de la mère (version
  minimale ; l'infra MVT `couches_tuyau` reste disponible pour une version pleine ultérieure).

Captures : `apres-dk0386-cadastre.png` (témoin **couvert** : mère `DK0029` millésime **2017-07-06**,
contour ambre sur le volet 2016-2020, chip ON) · `apres-ch1970-cadastre-vide.png` (témoin non couvert :
message « pas de parcellaire d'époque »).

---

## Lot C — Les 3 écarts de l'audit (commit `914e2bc7`)

| Écart | Avant | Après | Preuve |
|---|---|---|---|
| **E1** ligne millésime PM | « Fichiers fonciers PM : millésimes 2019→**2024** » (max de la table timeline) | « millésimes 2019→**2025** » — lit le snapshot COURANT servi (`parcelle_personne_morale`, = Scan patrimoine / dashboard), max des deux tables | visible sur toutes les captures « après » |
| **E2** vente ré-attribuée | vente CM1086 24/03/2025 affichée AVANT la découpe 09/06/2025, sans le dire | la vente porte la mention **« sur la parcelle mère (avant la découpe de cette parcelle) »** quand sa date précède la naissance DFI de la parcelle ; date vraie conservée | `apres-cm1086-e2-encart.png` |
| **E3** changement PM pseudo-siren | « Changement de propriétaire » affirmé même entre deux pseudo-sirens « U… » (ex. AB0001 ONF→DIE) | quand l'un des SIREN est un pseudo-siren : **aucun changement affirmé**, tiret neutre **« Propriétaire PM non identifiable (DGFiP) »** | `apres-ab0001-e3-encart.png` |

Détail des corrections (`moteurs.py`) :
- **E1** — `mil_ff = max(int)` sur `pm_proprietaires_millesimes` (2024) **et** `parcelle_personne_morale`
  (snapshot 2025) → 2025. Lu en base, jamais une constante.
- **E2** — `naissance_dfi = min(date_validation) WHERE idu_fille = idu` ; chaque vente porte
  `sur_parcelle_mere = (date_mutation < naissance_dfi)`. Rendu au front (point + encart).
- **E3** — si `siren_avant` OU `siren_apres` commence par `U` (pseudo-siren, ~13 % des lignes DGFiP) :
  on n'émet plus le changement (avec avant/après) mais un tiret `non_identifiable`.

Vérifié end-to-end (backend + rendu front) :
- E1 : ligne = « … Fichiers fonciers PM (DGFiP) : millésimes 2019→2025 … » (4 témoins).
- E2 encart CM1086 : « Vente | 24/03/2025 | **sur la parcelle mère (avant la découpe de cette
  parcelle)** | 900 000 € | 2 110 m² terrain ». CH1970 (vente 31/12/2025, après sa découpe) : pas de mention.
- E3 encart AB0001 : « **Propriétaire PM non identifiable (DGFiP)** | entre le 1ᵉʳ janv. 2020 et le
  1ᵉʳ janv. 2021 » — aucun « Changement » ni avant/après.

---

## Vérification / tests

- **Backend** : `tests/test_outils_muscler2.py` **8/8** — dont 3 nouveaux :
  `test_histoire_e3_pseudo_siren_aucun_changement` (pseudo → aucun changement affirmé, tiret non
  identifiable), `test_histoire_e3_vrais_sirens_changement_conserve` (contrôle : vrais sirens →
  changement conservé), `test_histoire_e2_vente_avant_decoupe_porte_mention_mere`.
- **Frontend** : `tsc --noEmit` vert · `npm run build` vert · `vitest` **178/178** (dont
  `HistoireFrise.test` inchangé).

## Ce qui est explicitement reporté / hors mandat
- **Cadastre plein écran par millésime** : non faisable avec `cadastre_historique` (mères disparues
  seulement) — à revoir avec une ingestion cadastre complète (mandat ultérieur). Version minimale livrée.
- Hors mandat non touchés : ajout d'une période IGN, bâti BD TOPO à la date, PLU à la date, autres outils.

## Recette navigateur (environnement)
Back `:8355`, front `:5555`, DB libre (pas de run résiduel → boot propre). Captures via **node
playwright** (chromium-1217) : frise = retrait des cartes WebGL puis screenshot de `[data-histoire-frise]`
(DOM stable) ; cadastre = plein écran cartes gardées. **Piège** : l'input de l'outil temps a le
placeholder « Adresse, IDU ou référence » (≠ la recherche d'en-tête « IDU, SIREN… ») — cibler
`input[placeholder*="ou référence"]`, sinon Entrée déclenche une sélection globale. avant/après frise =
`cp` de côté + `git checkout <main> -- HistoireFrise.tsx` + HMR + restauration (jamais `git stash`).
