# OUTIL-COMMUNES-FIX-7 — réponse au recontrôle `03-COMMUNES-ASTRA-5.md`

Les 4 points « C'est faux » sont le périmètre. `main` fusionné (déjà à jour). Ce que le rapport déclare
clos (8 médianes communales, 24 compteurs CatNat, 24 baromètres, traitement des indisponibilités) est
INCHANGÉ. SEULE la table `dvf_secteur_medianes` est écrite (rebuild autorisé par Vic, mêmes règles que
FIX-5/6) + sa sauvegarde datée. Chiffres par script committé, sortie brute dans
`docs/audit-2026-11/outil-communes-fix-7/`.

PRINCIPE tenu : le seuil de diffusion d'un prix de section vit maintenant à UN SEUL endroit
(`labuse/dvf_secteur.py`) — plus « corrigé lecteur par lecteur ».

---

## LOT 0 — filet (commit séparé `01034a1a7`)
`tests/test_communes_fix7.py` (pytest) + `frontend/src/lib/plu.test.ts` (vitest). AVANT correction :
pytest **8 failed** (Carnet CD terrain = 133 ; Carnet AT/AB maison = 3905/2624 sur 8 ; `prix_section`
absent ; révisions Saint-Leu/Saint-André/Trois-Bassins au 31/12/2024 ; Plaine sur le domaine mort) ;
vitest **1 failed** (bandeau sans date). tsc vert. (`LOT0-*.txt`)

---

## LOT 1 — une seule fonction rend « le prix d'une section pour un type de bien »

Nouveau module `src/labuse/dvf_secteur.py` :
- `prix_section(db, secteur, type_bien, *, seuil=None)` — bornes (appliquées au build), effectif = ventes
  UTILISÉES, SEUIL de diffusion (`seuil_section()` = `dvf_mediane.SEUIL_N` = 8), renvoie
  `{prix_m2 (None si < seuil), n, assez, …}` (« pas assez de ventes »).
- `prix_sections(db, secteur)` — tous les types (Carnet / fiche parcelle / Comparer).
- `medianes_sections_commune(db, insee, types, *, seuil)` — repli commune (Bilan mode B).

**Builder** `dvf_marche.py` : l'effectif des MAISONS / APPARTEMENTS compte désormais les ventes DANS les
bornes (comme le terrain au FIX-6 et la VEFA), plus le total des actes (AT/AB : 7 utilisées sur 8).

**Tous les lecteurs appellent la fonction** (plus aucune lecture directe de `dvf_secteur_medianes` pour un
prix — `LOT1-aucune-lecture-directe.txt`) : Comparer (via la liste gatée), fiche parcelle
(`flash/data.py` + `api/app.py`), Carnet (`api/carnet.py`), `api/mon_secteur.py`, cascade de scoring
(`cascade/context.py`, `seuil=0` : brut, son propre plancher 3/5), Bilan mode B (`faisabilite/bilan.py`,
son seuil `mode_b_prix_local`=3 conservé), score_e (via la constante `TERRAIN_PAR_SECTEUR_SQL` du module).
Grep : `FROM dvf_secteur_medianes` n'apparaît plus que dans `dvf_secteur.py` (la fonction), `dvf_marche.py`
(le builder, écriture + count de contrôle), et `app.py:2321` (EXISTS d'existence, aucun prix lu).

Le GRAPHE du registre (`registre/lectures.py`) est mis à jour « dans les deux sens » : la table est
déclarée lue par `dvf_secteur.py` (lecteur UNIQUE) ; les 4 déclarations périmées (carnet, mon_secteur,
cascade, flash — qui délèguent désormais) sont retirées. Les garanties du dépôt le PROUVENT :
`test_graphe_exact_dans_les_deux_sens` et `test_g6_vert_apres_raccords` passent (toute arête du code est
déclarée, aucune déclaration périmée).

### Reconstruction du cache (autorisée, cette table seule)
- **a.** Sauvegarde `dvf_secteur_medianes_bak__20261124_fix7` · AVANT = 2354 l · checksum -19351249823.
- **b.** `compute_medianes_secteur` lancé à **23 h 18 (Indian/Reunion)**, hors 13 h 30–14 h → {2354 l,
  848 secteurs, 36463 ventes}. APRÈS = 2354 l · -18091543399.
- **c.** (`scripts/communes_fix7_cache_after.py`, `LOT1-cache-apres.txt`) :
  - AT (Les Avirons) et AB (La Possession) maison : **n=7 → prix None** (via `prix_section`, sous le seuil) ;
  - CD terrain : n=1, pas de prix (inchangé FIX-6) ;
  - `n_ventes` du cache maison/appartement == ventes dans les bornes : **0 divergence** sur 1229 lignes ;
  - sections maison/appart dont l'effectif change : 92 ; dont **PERDENT leur prix servi (n≥8→<8) : 2**
    (= AT + AB, exactement les deux témoins du rapport).
- **d.** Cohérence (`LOT1-coherence.txt`) : **87 passed · aucun écart (1 €/1 m²)** — AUCUN témoin du Bilan
  ne bouge (le Bilan mode B garde son seuil 3 ; le seuil grand public 8 ne s'applique qu'aux affichages).
  Rien à arrêter, aucun témoin modifié.
- **e.** RETOUR ARRIÈRE (testé sur copie TEMP → revient à 2354 · -19351249823) :

```sql
BEGIN;
TRUNCATE dvf_secteur_medianes;
INSERT INTO dvf_secteur_medianes
       (secteur, type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre, computed_at, millesime_dvf)
SELECT  secteur, type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre, computed_at, millesime_dvf
FROM    dvf_secteur_medianes_bak__20261124_fix7;
COMMIT;  -- contrôle : lignes=2354, checksum=-19351249823
```
Aucune autre table de `labuse` écrite.

---

## LOT 2 — révisions : date d'une pièce IDENTIFIÉE de la bonne procédure
`config/veille_plu.yaml` — chaque commune en révision porte un `piece_objet` (objet de la pièce) et un
lien qui s'ouvre (GPU / MRAe). Libellé servi : **« dernière pièce connue de LABUSE le … — vérifié le … »**.

| Commune | Date servie | Objet de la pièce |
|---|---|---|
| Saint-Leu | 18/11/2026 | avis (défavorable) de la commission d'enquête sur la **révision générale** |
| Saint-André | 09/09/2025 | avis de la **MRAe** sur le projet de révision générale (n° 2025AREU7) |
| Les Trois-Bassins | mai 2025 | présentation du **PADD** de la révision générale (concertation) |
| L'Étang-Salé | 17/09/2025 | **révision allégée n°1** approuvée — ≠ révision générale (encore en cours) |
| Saint-Louis | 18/12/2025 | **modification simplifiée n°5** — ≠ révision générale (encore en cours) |
| Saint-Denis | 23/04/2026 | document opposable au GPU — **rattachement à la révision générale non certifié** |
| Saint-Paul | 17/12/2025 | document opposable au GPU — **rattachement non certifié** |
| La Plaine-des-Palmistes | 27/11/2025 | pièce municipale confirmant la révision générale en cours |

Les 3 pièces du rapport sont intégrées (collectivité, objet, date, lien). Pour les 4 non certifiables,
l'objet RÉEL de la pièce est écrit (allégée / modification / opposable), au lieu de la présenter comme la
dernière pièce de la révision générale.

---

## LOT 3 — grand bandeau + liens des 24 fiches
- La case **« État du PLU »** du bandeau à neuf chiffres porte désormais la DATE de la dernière pièce
  (`bandeauEtatPluSous(etat_au)`, vitest vert). La Plaine : « en révision · au 27/11/2025 ».
- **Liens des 24 fiches testés** par `scripts/communes_fix7_liens.py` (`LOT3-liens.txt`) : les 24
  répondent HTTP 200 (ou RNU sans lien). Le domaine mort `www.plaine-des-palmistes.re` (et les autres
  domaines communaux non résolus) sont remplacés par la source canonique qui s'ouvre (GPU / MRAe /
  data.gouv Sudocuh). Aucun lien cassé.

---

## Vérifications finales
- Filets `tests/test_communes_fix7.py` + fix6 + cas_externes + `test_veille_plu.py` : **32 passed** ;
  vitest **351 passed** (71 fichiers) ; tsc vert.
- Cohérence (base reconstruite) : **87 passed, aucun écart** (aucun témoin du Bilan ne bouge).
- Cache reconstruit ; sauvegarde conservée ; rollback testé sur copie TEMP. Aucune autre table écrite.
- Clos par le rapport (8 médianes communales, 24 CatNat, 24 baromètres) : inchangé.
- Pas de fusion dans `main`.
