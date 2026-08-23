# M139 — Projets : la fin de vie, les deux dates, le plafond (`feat/m139-projets`)

Branché sur `origin/main` @ `81daf718` (avance depuis M137 = un `.gitignore` ; branches M138
`fix/projets-plafond` et `audit/projets` poussées mais non mergées, aucune n'apporte de code
dont M139 dépend — signalé). CC ne merge jamais.

**Résumé : Lot 1 (le filet) et Lot 2 (les deux dates) livrés et vérifiés. Lot 3 (figer TOUTES
les retenues) : STOP chiffré — l'insertion du figeage complet explose (28,6 s / 87 s pour un
cadrage « toute l'île », 286 k lignes). Options pour Vic ci-dessous. Bricoles dead-code faites.**

---

## Lot 1 — F1, le filet (miroir M137)

**Plus aucun chemin ne détruit le travail de tri ni les cartes CRM.**

- **API** — `DELETE /projets/{pid}` (`projets.py`) **ne fait plus `db.delete(p)`** : il **archive**
  (`statut="archive"`, réversible) et **synchronise les cartes CRM**. Le hard-delete qui cascadait
  sur `projet_parcelles` (perte des tris) et orphelinait les cartes est **fermé**.
- **Nouveau helper** `_sync_crm_projet_statut(db, pid, statut, now)` : `archive` ⇒ archive les
  entrées pipeline liées à CE projet (`archived_at`, réversible) ; `actif` ⇒ les restaure. Ciblé
  `projet_id` — une carte manuelle/d'un autre projet n'est jamais touchée. Miroir exact de
  `_sync_crm_retenue` (M137).
- **`PATCH /projets/{pid}` statut** : sur transition `actif↔archive`, les cartes CRM **suivent**
  (elles étaient inertes avant — audit F1). La restauration = `PATCH statut=actif` (déjà le geste
  du front).
- **Front** — `deleteProjet` (`api.ts:859`) était **du code mort jamais appelé** : l'archivage
  passe déjà partout par `patchProjet({statut})` (ProjetsPanel « Archiver/Réactiver », ProjetKanban),
  avec un onglet « Archivés » existant. Le wrapper mort est **retiré**. Aucune UI à ajouter.

**Contrôle (testé API, non destructif, rollback)** : projet P13 (12 cartes CRM liées) →
`DELETE` ⇒ projet **archivé** (existe toujours) + **12 cartes → 0 active** (archivées) →
`PATCH actif` ⇒ **12 cartes actives** de nouveau. **SEC-IDOR** : autre compte → **404** sur
DELETE. **Aucune perte du tri** : `projet_parcelles` intact (plus de cascade). ✓

---

## Lot 2 — F2, les deux dates

**L'avertissement en prose devient une donnée, sourcée du run servi (M135), pas d'un texte.**

- **Nouveau helper** `_residuel_run_servi(db)` : lit le run résiduel SERVI par le flag `is_served`
  (`residuel_runs`, M135 — **aucun `MAX`/tri**, lecture directe du flag) → `{label, seq, date}`
  (`date` = `created_at` du run). `None` si indisponible → repli sur la seule date de cadrage,
  jamais un mensonge.
- **PDF** (`pdf_projet.py`) — l'en-tête affiche désormais **trois dates nommées** :
  `Cadrage figé le JJ/MM · Valeurs au JJ/MM (run N) · Document généré le JJ/MM`. La date des
  valeurs vient du run résiduel servi (la source des SDP/zone que le dossier **relit live** —
  c'était le cœur de F2).
- **Écran** (`projet_parcelles` → ProjetKanban) — même donnée : `figee_le` + `valeurs_run`
  exposés par l'endpoint, rendus en en-tête (`· valeurs au JJ/MM (run N)`, avec infobulle
  expliquant la relecture live). Type front `ParcoursEtat` étendu.
- **Aucun gel de valeurs** : on ne fige toujours que la liste d'IDU ; on **date** ce qu'on relit.

**Contrôle** : projet QA figé le **2026-07-20** → PDF/écran affichent
**« Valeurs au 2026-08-22 (run m135-run2-ile) »** — un cadrage de juillet qui sert des valeurs
d'août, désormais **explicitement daté**. PDF rend en 8 pages / 71 Ko (non-régression). ✓

---

## Lot 3 — le plafond : **STOP chiffré (les deux mesures demandées)**

Lot 3 a été redéfini par Vic : **supprimer `shortlist_defaut` et figer TOUTES les retenues**
(la sélection par proba de mutation disparaît — gain doctrine), pagination serveur à l'écran,
PDF = extrait des 200, export CSV complet, non rétroactif. Avec **STOP si une mesure explose**.

### Mesure 1 — coût du figeage complet (pire cas « toute l'île »)
Population = **285 781** parcelles (cadrage vide, hors étage 0, plancher sliver). Insertion
ensembliste dans `projet_parcelles`, mesurée puis **rollback** (non destructif) :

| Variante | Durée insertion | Taille |
|---|---:|---:|
| Avec tri (`row_number` sur le rang) | **87,0 s** | 81 o/ligne |
| Sans tri (rang NULL — la sélection disparaît) | **28,6 s** | **~22 Mo / projet** |

→ Même dépouillé de tout tri, **figer un cadrage large = 28,6 s en synchrone** : au-delà du
budget d'une requête HTTP (timeout), et **~22 Mo par projet** (≈ 221 Mo pour 10 projets île).

### Mesure 2 — routes qui listent sans pagination
`GET /projets/{pid}/parcelles` (`projets.py:833`) charge **toutes** les lignes **sans LIMIT**,
puis enrichit **par parcelle** (adresse BAN, centroïde, événement, marché, carence, proprio des
retenues). Sur 285 781 lignes, le **seul scan SQL nu = 9,2 s** — l'enrichissement Python le
ferait exploser (286 k lookups BAN + transforms). `carte/{idu}` et `export.pdf` sont bornés.

### Verdict : **je n'implémente pas Lot 3.** Les deux mesures confirment que « figer toutes les
retenues » n'est pas viable en synchrone pour un cadrage large. Options pour Vic :

1. **Cadrage paginé en LIVE (ne rien figer de plus).** L'écran et le CSV paginent la **requête de
   cadrage** en direct (LIMIT/OFFSET) ; seules les **décidées** (retenue/écartée/à analyser)
   restent stockées. Évite le figeage 286 k. Cohérent avec F2 (les valeurs sont **déjà** relues
   live). Casse le mot « figé » pour les proposées — mais c'est déjà la réalité. **Meilleur
   rapport valeur/coût.**
2. **CSV complet STREAMÉ (non stocké) + shortlist bornée.** Le CSV « liste complète » se calcule
   à la volée depuis le cadrage (streaming, zéro ligne figée en plus, zéro rang/score) ; l'écran
   et le PDF gardent une shortlist figée **bornée** (plafond relevé mais fini). Donne « la liste
   complète en export » sans les 286 k lignes ni les 28 s.
3. **Figeage asynchrone.** Un job d'arrière-plan fige tout hors requête HTTP. Permet le design
   littéral, mais **aucune infrastructure de job n'existe** (FastAPI synchrone) — gros chantier.
4. **Seuil conditionnel.** Figer tout si le vivier ≤ N (petits cadrages, instantané), sinon
   plafond + en-tête honnête « extrait de X sur N ».

Ma recommandation : **option 1 ou 2** (le CSV complet est ce qui porte réellement « la liste
entière » ; ni l'une ni l'autre ne stocke 286 k lignes). Vic tranche.

---

## Bricoles

- **`capacite_estimee` mort-lu** : retiré du `SELECT` de `_shortlist_pdf` (était sélectionné,
  jamais consommé). ✓
- **`q_score` = None dans `/apercu`** : clé retirée du payload **et** du type front `ApercuTop`
  (toujours `None`, jamais rendue — grep front confirmé). ✓
- **Tag Sourcé/Estimé d'en-tête** : **examiné, pas de changement — la FICHE DE CADRAGE ne porte
  que les ENTRÉES du promoteur** (Périmètre, SDP min « facette du cadrage », Budget « indicatif »,
  Programme « indicatif »), qui ne sont ni sourcées ni estimées mais **déjà étiquetées par leur
  nature** (indicatif/facette). Le tag Sourcé/Estimé s'applique à la **donnée par parcelle**, où
  il est déjà tenu partout (surface, SDP, hauteur, zone). Un tag Sourcé/Estimé sur des saisies
  utilisateur serait trompeur. **Consigné, pas un manque.**
- **Verrou de concurrence** (audit C.3) : `_figer_shortlist`/`chercher-plus` n'ont pas de lock
  applicatif (sûreté par la contrainte d'unicité `uq_projet_parcelle` + `ON CONFLICT`). Risque
  faible. **Dette nommée** (à traiter si le multi-utilisateur sur un même projet monte).

---

## Contrôles d'acceptation

1. **Aucun chemin de perte du tri** : `DELETE` archive (plus de `db.delete`/cascade), `PATCH`
   idem ; grep : plus aucun hard-delete de projet côté API ni front. ✓
2. **Cartes CRM suivent** l'archivage/restauration (12→0→12, ciblé `projet_id`). ✓
3. **SEC-IDOR** : DELETE/PATCH/écran/PDF bornés au compte (404 autre compte). ✓
4. **Deux dates** à l'écran ET au PDF, sourcées du run servi (M135), pas d'un texte statique. ✓
5. **`tsc` vert**, **ruff sans nouveau warning** (3 I001 pré-existants, identiques à origin/main). ✓
6. **Lot 3** : mesuré, STOP chiffré, non implémenté, options posées. ✓
7. Ce rapport. ✓

*Fin. Commits sur `feat/m139-projets`. Vic tranche l'option Lot 3 (M140 ?). CC ne merge jamais.*
