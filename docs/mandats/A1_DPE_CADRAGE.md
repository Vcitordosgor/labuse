# PHASE A cycle 3 — CADRAGE « passoires DPE F/G »

**Branche `phaseA/dpe-passoires` · Étape 1 · LECTURE SEULE.** Aucune écriture DB ; runs servis
`q_v7_defisc`/`q_v6_m8` intouchés. Aucune identité de personne physique (ni propriétaire, ni locataire) —
le signal serait la **parcelle, sa classe DPE datée, et des dates légales**, rien d'autre.

> **Verdict d'instruction : NO-GO pour la composante V.** La couverture DPE est **anecdotique** (914 DPE en
> base = 0,2 % du parc ; **43 F/G ; 7 seulement actionnables** — non-écartés ∩ mono). Les **deux juges sont
> infaisables** : l'event-study repose sur **8 ventes F/G en tout** (4 avant / 4 après le gel), le
> walk-forward sur **2 événements**. Aucun effet dont l'IC pourrait exclure le nul à ces effectifs.
> **Conséquence compteur d'ablation : 2 / 2 → plateau → déclenchement M7.** Le badge reste une option
> (fait réglementaire sourcé) mais aveugle sur 99,8 % du parc — voir §3.6.

> ## ⚖️ CYCLE 3 ACTÉ (clôture Phase A, décision Vic)
> - **Composante V : NO-GO** — deux juges infaisables + couverture anecdotique. Réservée **M4.0**.
> - **Badge DPE : RÉSERVÉ** (pas servi) — avec **critère de réveil chiffré** : réévaluation **à chaque
>   refresh DPE** ; **réveil du badge (et réinstruction) dès que `F/G ∩ mono ∩ non-écarté ≥ 200 parcelles`**
>   (aujourd'hui : **7**). En réserve **M4.0** avec la composante V.
> - **Compteur d'ablation : 2 / 2 → PLATEAU ACTÉ → M7.** (Compteur canonique : `A1_BILAN.md`.)

---

## 1. Calendrier réglementaire (hypothèses du mandat, à re-vérifier avant toute exposition)

- **La Réunion (DROM)** : interdiction de **mise en location** — **G au 1/1/2028**, **F au 1/1/2031**
  (E : 2034). Décalage DOM explicite (loi Climat & Résilience). Métropole : G depuis 2025, F en 2028.
- **Gel des loyers F/G dans les DOM depuis le 1/7/2024** (pas d'augmentation, IRL compris) ; DPE opposable
  dans les DOM depuis 7/2024.
- Frappe les **nouveaux baux et renouvellements**, pas les baux en cours.
- Caveats données : méthode DPE outre-mer en harmonisation ; **réforme des seuils au 1/1/2026** (les
  étiquettes bougent) → **toute exposition doit DATER le DPE source**.

## 2. Nature du signal & choix du juge

Signal **HYBRIDE** : composante **actuelle** (rendement verrouillé par le gel — partiellement dans le label)
+ composante **forward** (échéances 2028/2031, hors label). Deux instruments armés (le ΔRR de l'arène ne juge
pas le forward — règle du bilan Phase 0). L'instruction devait choisir **selon les données** — elles tranchent
en amont : **aucun** des deux n'est exploitable (§3.3-3.4).

## 3.1 Couverture DPE — la fragilité n°1, chiffrée

| Métrique | Valeur |
|---|---|
| DPE en base (974) | **914** (0,2 % de 431 663 parcelles) |
| classes | A 15 · B 22 · C 483 · D 215 · E 136 · **F 25 · G 18** |
| **F/G total** | **43** (42 avec `parcelle_idu`) |
| F/G ∩ **non-écarté** (q_v7_defisc) | **7** |
| F/G ∩ mono | 41 |
| **F/G ∩ non-écarté ∩ mono = ACTIONNABLE** | **7** (6 à creuser + 1 réserve foncière) |
| `date_etablissement` F/G | 2021:6 · 2022:10 · 2023:8 · 2024:9 · 2025:10 |

Géocodage : 903/914 rattachés à une parcelle (`parcelle_idu`). **7 parcelles actionnables** — anecdotique par
tout critère (barème du mandat : « 200 = anecdote »). Le DPE ADEME 974 est un gisement **déjà quasi complet**
(cf. couverture pilote antérieure) : ce n'est pas un trou d'ingestion à combler, c'est le volume réel.

## 3.2 Pas de présomption de bailleur

On ne sait pas qui loue (aucune identité PP, aucun proxy nominatif). Le signal, s'il était servi, serait
« **logement passoire face au calendrier** » — la pression réglementaire vaut surtout locatif, mais la décote
de valeur touche tout propriétaire. **Aucun proxy locatif non-nominatif fiable identifié** dans nos données
(RNIC = copro ; DGFiP PM ≠ statut locatif). Wording neutre imposé.

## 3.3 Event-study J1 — INFAISABLE

Ventes de parcelles **mono** F/G vs D/E (contrôle), avant (2021→30/6/2024) / après (1/7/2024→) le gel :

| groupe | parcelles | ventes AVANT | ventes APRÈS |
|---|---|---|---|
| **F/G** | 29 | **4** | **4** |
| D/E (contrôle) | 140 | 35 | 19 |

**8 ventes F/G au total.** Un diff-in-diff à 4 vs 4 est du bruit pur : l'effet minimal détectable dépasse de
loin tout signal plausible. Un IC bootstrap serait une fausse précision — on ne le fabrique pas. **Infaisable.**

## 3.4 Walk-forward J2 (as-of strict) — INFAISABLE

« Passoire au 1/1/N » = DPE F/G réalisé **avant** le 1/1/N (as-of strict). Mutation dans l'année N :

| fold N | at-risk F/G | mutations |
|---|---|---|
| 2024 | 20 | **0** |
| 2025 | 25 | **2** |

**2 événements en tout.** Le DPE DOM est trop récent et trop rare pour alimenter des folds. **Infaisable.**

## 3.5 Limites honnêtes

- **Étiquettes mouvantes** : réforme seuils 1/1/2026 + harmonisation OM → dater chaque DPE (fait ici :
  `date_etablissement`), mais un F d'aujourd'hui peut ne plus l'être demain.
- **DPE au logement ≠ parcelle** : strate mono d'abord ; copro (« grappe de lots ») = réserve, hors périmètre.
- **Baux en cours non frappés** : l'interdiction ne vaut que nouveaux baux/renouvellements → l'urgence
  vendeur est diffuse.
- **Auto-sélection** : qui fait un DPE ? Souvent à l'occasion d'une vente/location déjà décidée → **le DPE
  est corrélé à la mutation par construction** (biais qui gonflerait artificiellement tout lift observé) —
  raison de plus de ne pas sur-lire les 2 événements du fold 2025.

## 3.6 Recommandation — GO/NO-GO

- **Composante V : NO-GO.** Critère mandat (« ≥ 1 juge avec IC excluant le nul ET couverture non
  anecdotique ») **non atteint sur les deux tableaux**. V en **réserve M4.0**. **Compteur d'ablation → 2/2
  → plateau → M7.** C'est une **issue attendue et bonne** : l'instruction a tué une idée trop mince en une
  heure, sans rien servir de faux ; la Phase A a fait son travail (2 badges livrés, la doctrine
  walk-forward/arène établie, le juge outillé).
- **Badge : OPTION à ta main (léger, sourcé).** Un fait réglementaire sourcé mérite la fiche là où il existe —
  mais il n'existe que sur **~42 parcelles** (aveugle sur 99,8 % du parc). Si tu le veux, wording proposé,
  **factuel, daté, sans jugement ni conseil** :
  > « Classé **F** (DPE 03/2025) · mise en location interdite à partir du **1/1/2031** · **Sourcé** »
  (G → 2028). Classe et échéance **Sourcé** ; aucune inférence, jamais « propriétaire coincé », jamais
  « vendez avant ». Ce n'est **pas un signal de scoring** (couverture trop faible), juste une info de fiche.
  Ma recommandation : **le mettre en réserve avec la V (M4.0)** plutôt que d'exposer un enrichissement présent
  sur 0,01 % des parcelles — mais c'est un fait sourcé, donc légitime si tu le juges utile.

**Décision Vic** : acter le NO-GO V (compteur 2/2, plateau, M7) ; retenir ou réserver le badge.

### Repro
```bash
python scripts/dpe_passoires_cadrage.py    # couverture + faisabilité des deux juges (lecture seule)
```
