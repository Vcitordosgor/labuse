# M130-4 — PDF projet : rapports + vérifications

Branche `feat/m130-pdf-projet`. Ne pas merger. PDF joints : `M130-4-projet-{P1..P4}.pdf`.

---

## A — Ligne d'état de la liste : `total` exact et état retenu

`total` = le **vivier figeable à ce jour** (`_vivier_figeable`, count, jamais la
liste). Trois états, **inconditionnels** :

| Projet | `total` (vivier) | n figé | État retenu |
|---|---|---|---|
| **P1** (toute l'île) | **285 781** | 60 | **État 1 — Liste plafonnée** (285 781 > 60) |
| **P2** (Le Tampon ≥ 3 000 m²) | **839** | 60 | **État 1 — Liste plafonnée** (839 > 60) |
| **P3** (Saint-Pierre, `tiers:[ecartee]`) | **0** | 60 | **État 3 — INDISPONIBLE** (total = 0) |

### Pourquoi P3 tombe pile sur 60

Le cadrage test P3 sélectionne `tiers:[ecartee]` = **uniquement l'étage 0**
(parcelles non constructibles / faux positifs). Deux chemins divergent :

- **La liste** : `_figer_shortlist` → `_search_items` → `_run_cadrage` **inclut**
  l'étage 0 quand un filtre `tiers` est posé → le run a matché les **10 846**
  parcelles étage 0 de Saint-Pierre, **plafonnées à `shortlist_defaut = 60`** au
  figeage. D'où « pile 60 ».
- **Le dénominateur** : `_vivier_figeable` compte `NOT étage 0` → **0** pour ce
  cadrage (il n'y a aucune parcelle *figeable hors étage 0*). Le total honnête est
  donc **indisponible** pour ce cadrage pathologique → **État 3** (jamais l'omission
  du M130-3, qui laissait la ligne absente parce que `tronquee` était faux).

En M130-3, P3 (vivier 0 → `tronquee=False`) **n'affichait aucune ligne** : un rang
caché servi muet sur un projet sur trois. Corrigé : la ligne est désormais
**inconditionnelle** (None/0 → État 3, jamais l'absence).

---

## Vérifications exigées (une par une)

- **P3 — ligne d'état présente + lequel** : ✅ présente, **État 3**
  (« Nombre total … : INDISPONIBLE. Cette liste peut être tronquée ; si elle
  l'est, … sélectionnées par probabilité de mutation — un rang non visible. »).
- **P1 / P2 — ligne d'état inchangée sur le fond, phrase B corrigée** : ✅ État 1
  (« Liste plafonnée : 60 … sur ~ 285 781 / ~ 839 … »), suivie de la **phrase B** :
  « Élargir la shortlist ne supprime pas ce rang : seule une liste complète ou un
  tri explicite (surface) est neutre. » (la fausse issue « chercher plus » est
  retirée).
- **`BV2471`, `CL1113`, `CX1483` — ligne « Parcelle multi-zones »** : ✅
  - `BV2471` : « Nco (naturelle) ~ 50 % · Ua (urbaine) ~ 48 % — la SDP n'est pas
    chiffrée ; une partie constructible peut exister et reste à instruire. »
  - `CL1113` : « Nco ~ 51 % · Uc ~ 49 % — … peut exister … »
  - `CX1483` (P3) : « A (agricole) ~ 58 % · Uf (urbaine) ~ 42 % — … peut exister … »
- **Multi-zone à dominante constructible (P1/P2)** : ✅ **`97422000BS0941`** (P2) —
  « Ub (urbaine) ~ 74 % · Nco (naturelle) ~ 26 % — **SDP calculée sur la partie
  constructible** ; les autres parts restent à instruire. » (la ligne s'affiche
  dans les DEUX sens ; aucune SDP partielle chiffrée).
- **P4 — plus aucune occurrence de « figé le »** : ✅ en-tête « **Cadrage non
  figé** · Document généré le 2026-08-22 » ; section limites adaptée.
- **Bloc parcelle non coupé en bas de page** : ✅ keep-together (mesure de la
  hauteur du bloc IDU + adresse + lignes, saut de page avant si débordement) —
  contrôle : aucune page ne se termine sur une ligne IDU.

Source des parts (§C) : **même chemin que le tableau ZONE/PART du dossier
banquier** — `spatial_layers plu_gpu_zone`, `pct = surface d'intersection /
surface parcelle` (décompte spatial direct, agrégé par libellé pour ne pas
répéter une zone multipolygone).

---

## E — Finitions vérifiées

- **E.1** Surface cadrage : « 3 000 m² et plus » (plus d'« ∞ », milliers espacés).
- **E.2** Causes sur vocabulaire fermé : *zone fermée à l'urbanisation* /
  *logement non admis au règlement de la zone* / *résiduel nul après reculs et
  emprises* / *capacité annulée par les modulations (risque / pente / servitude)*.
  « résiduel nul » seul supprimé.
- **E.3** Point final des citations retiré (« p.84. » → « p.84 »).
- **E.4** Keep-together (cf. ci-dessus).
- **E.5** Mention finale : « la SDP résiduelle est une surface de plancher cumulée
  sur plusieurs niveaux : elle peut dépasser la surface de la parcelle. »

---

## F — Hors périmètre, consigné (non traité)

- **F.1** → `qa/m130/DETTE_CADRAGE_ETAGE_0.md` (mandat app, pas PDF).
- **F.2** — `97416000EP1044`, zone **Us** (Saint-Pierre), cause
  `zone_non_constructible`, citation `resolve_zone.sources.hauteur` =
  « **Préambule Us p.129 + Art. Us1 (tableau) p.130 ; Art. AU01, p.200.** » — une
  zone Us qui **cite un article AU01**. Incohérence de la chaîne `*_src` du YAML
  PLU Saint-Pierre → **à verser au mandat data `*_src`** (comme la réserve F.4 de
  M130-3).
