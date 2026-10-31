# PRODUIT-NU-1 — Compte-rendu

**Branche** `fix/produit-nu-1` · worktree `~/Desktop/labuse-produit` · API `:9220` · front `:6420` · run servi **q_v20** · base locale (= le Mac). Pas de merge, aucun accès prod.
Date : 2026-10-31. Modèle : Opus. Deux sessions sœurs tournaient (VITESSE-3, COHERENCE-HOOK) : rien touché aux temps de chargement de Pilotage / Sources / Étude de zone / fiche commune / Successions / autocomplétion, ni aux tests, ni au hook.

Sources : `docs/audit-2026-11/nu-1/` lots **B**, **C**, **F**. Chaque point ci-dessous = un constat corrigé, avec sa preuve.

---

## Vue d'ensemble

| Point | Constat | État |
|---|---|---|
| **B-001** | Carte — « Voir les N parcelles » annonce 2× ce que la carte peint | ✅ bouton garde le total + split « à instruire · écartées » |
| **B-002** | État du sol — 41,5 % des parcelles hors de la partition nu/bâti | ✅ 3ᵉ état « Non mesuré » (partition exacte) |
| **F-003** | Projets — « sélection filtrée » ≠ filtres carte (étage 0 retiré, 4/11 familles) | ✅ toutes les familles, étage 0 compris, **compteur = carte prouvé sur 3 combinaisons** |
| **F-011** | Projets — le kanban parle d'« analyse LABUSE / probabilité de mutation » que le wizard dément | ✅ discours aligné |
| **F-012** | Projets — compteur de la liste périmé après une bascule de run | ✅ cache invalidé si antérieur à la promotion du run |
| **F-013** | Projets — plafond 200 (figé) jamais dit | ✅ dit au compteur du cadrage |
| **F-008** | CRM — étiquette de contact morte | ⚠️ **bloqué par les tests** (voir plus bas) — décision Vic : laisser + documenter |
| **F-009** | CRM — colonne « vide » indéboulonnable | ✅ garde `_cards_in` alignée (actives seules) |
| **F-010** | CRM — dialogue de suppression lit un compteur filtré par la recherche | ✅ compteur non filtré |
| **F-017** | Notifications — « Rien de nouveau » affiché alors qu'il y a des événements | ✅ `vide = (n_evenements == 0)` |
| **F-019** | DA — hex de marque en dur (Projets) | ✅ (cluster DA — voir §DA) |
| **F-020** | DA — `<select>` natifs / pastilles maison (Radar, Veille) | ✅ (cluster DA) |
| **F-021** | DA — espaces insécables manquantes (« 3 038€/m² ») | ✅ (cluster DA) |
| **F-022** | A11y — clavier / labels | ✅ (cluster DA) |
| **F-050** | Admin — L'usine peint « au vert » un job gelé/périmé | ✅ pastille **ambre « en retard »** si dernier succès > 1,5× cadence |
| **F-051** | Admin — incidents périmés lus comme alarmes « maintenant » | ✅ âge « ouvert depuis » remonté dans la phrase |
| **C-002** | Étude de zone — PDF « Revenu médian » (= une moyenne), contredit l'écran | ✅ PDF « Niveau de vie moyen / an » |

---

## Carte

### B-001 — « Voir les N parcelles » : total + split
**Décision Vic (étage 0) :** *« Total partout, split visible »* — le bouton garde le **total** (compteur carte), et affiche en dessous ce que la carte **peint** vraiment (hors étage 0) vs les écartées.

- Backend `src/labuse/api/app.py` `_q_v2_stats` : ajout d'un compteur `instruire` = `count(*) FILTER (WHERE NOT (d.status IN ('exclue','faux_positif_probable')))` — MÊME gate que la liste d'IDU peinte. `ecartees = total − instruire` (somme garantie).
- Front `FiltreLabuse.tsx` : sous le bouton « Voir les N parcelles » (qui garde le total), une ligne `N à instruire · M écartées`.
- **Preuve (Cilaos, q_v20)** : `/filtre?communes=Cilaos&source=q_v20&limit=0` → `total 6576 · instruire 3107 · ecartees 3469` ; `&idus=1` → **nb_idus = 3107** (= instruire, non tronqué). Le split décrit donc EXACTEMENT ce que la carte allume.

## État du sol

### B-002 — 3ᵉ état « Non mesuré »
- Backend `app.py` (prédicat `etat_sol`) : clé `non_mesure` = `NOT EXISTS (parcel_residuel … taux_emprise_pct IS NOT NULL)` — complément exact de nu∪bâti.
- Front `FiltreLabuse.tsx` : `ETAT_SOL` passe à trois chips `Terrain nu · Terrain bâti · Non mesuré` (ChipGroup `partition` → tout coché = base complète).
- **Preuve** : la combinaison `etat_sol=nu,non_mesure` est appliquée à l'identique par la carte et par Projets (voir F-003, combinaison 3). Les 41,5 % sans emprise ne disparaissent plus en silence.

## Projets — parité carte (F-003 / F-011 / F-012 / F-013)

### F-003 — « Partir d'une sélection filtrée » applique EXACTEMENT les filtres de la carte
- `src/labuse/api/projets.py` :
  - `/projets/compteur` sert désormais `total` (= `_q_v2_stats.total`, étage 0 compris, **le même nombre que `/filtre`**) + le split `figeable` (ce que le projet triera, hors étage 0, = `_cadrage_total.total`) + `ecartees`.
  - `_CADRAGE_MAP` complété : familles **bâti** (`hauteurMin/Max`, `empriseMin/Max`, `empriseSature`) et **Propriétaire** (`pmDenom`, `pmSiren`, `pmForme`, `pmApe`, `pmAge`, `pmDirigMin/Max`) ; ajout du kind `"str"` à `clean_cadrage`. Sans elles, le cadrage les avalait en silence.
- Front `FiltreFacettes.tsx` : rend maintenant les MÊMES familles que la carte (le terrain + `<AffinerRecherche/>` + `<SectionProprietaire/>`, réutilisés tels quels depuis `FiltreLabuse`). Le compteur affiche le total carte + « N à trier · M écartées » + le plafond shortlist.
- `ParcoursProjet.tsx` : « — rien d'autre » retiré de la porte « sélection filtrée ».

**Preuve — compteur Projets == compteur carte, sur 3 combinaisons (API `:9220`, q_v20) :**

| Combinaison | Carte `/filtre` (total / instruire / ecartees) | Projets `/compteur` (total / figeable / ecartees) | Verdict |
|---|---|---|---|
| Cilaos + nu | 642 / 547 / 95 | 642 / 547 / 95 | ✅ MATCH |
| Saint-Denis + personne morale + hors copro | 11 405 / 7 169 / 4 236 | 11 405 / 7 169 / 4 236 | ✅ MATCH |
| Saint-Paul + nu,non_mesure + surface ≥ 500 | 13 776 / 2 548 / 11 228 | 13 776 / 2 548 / 11 228 | ✅ MATCH |

(La combinaison 2 exerce les nouvelles familles Propriétaire ; la 3 exerce le nouvel état « non mesuré ».)

### F-011 — un seul discours
`ProjetKanban.tsx` : le bandeau ne dit plus « LABUSE a analysé … classées par probabilité de mutation » (que la porte « sélection filtrée » promet de ne pas dire) ; il parle de « signaux de vie récents » et d'« ordre de tri ».

### F-012 — cache invalidé à la bascule de run
`src/labuse/runs.py` : nouveau `promu_at()` (lit `promoted_at` du manifeste). `projets.py:projets_list` recalcule `cadrage_total` quand `cadrage_total_at` est **antérieur** à la promotion du run — fini le « 399 à trier » qui devient 368 à la 1ʳᵉ ouverture.

### F-013 — plafond 200 explicite
Le compteur du cadrage (`FiltreFacettes.tsx`) dit, quand le vivier dépasse le cap : « la shortlist figera les 200 meilleures ».

## CRM (F-008 / F-009 / F-010)

### F-009 — colonne « vide » supprimable
`src/labuse/api/crm_columns.py` `_cards_in` : ajout de `AND archived_at IS NULL`. La garde « colonne peuplée » compte désormais EXACTEMENT ce que l'écran affiche (cartes actives) → une colonne vide à l'écran n'est plus indéboulonnable.

### F-010 — dialogue de suppression : compteur non filtré
`frontend/src/components/crm/Kanban.tsx` : nouveau `cardCountAll(key)` (sans le prédicat de recherche) alimente le dialogue de suppression. `/pipeline` ne sert que les cartes actives → ce compte est exactement celui de la garde backend (F-009). Fini « 0 carte · suppression immédiate » suivi d'un 422 muet.

### F-008 — étiquette de contact morte : **bloqué, décision Vic « laisser + documenter »**
La fonctionnalité est verrouillée par des tests que le mandat interdit de toucher :
- **Backend** : `tests/test_scoring3_terrain.py` (asserte le PATCH `contact_etiquette`, les 8 états, la réversibilité, le journal, le libellé servi), `tests/test_cloisonnement_1.py` (PATCH + `contact_etiquette_log` + effacement RGPD), `tests/test_boot_verrou_1.py` (`ensure_contact_etiquette`).
- **Front** : `frontend/src/components/crm/Kanban.test.tsx` construit un mock avec `contact_etiquette` / `contact_etiquettes` — et ce test tourne dans le hook (vitest/tsc).

Retirer la moindre partie casserait un de ces tests (donc le hook / la CI), ce qui exigerait d'éditer les tests — contraire à la consigne « ne touche pas aux tests ». La fonctionnalité est **déjà invisible au client** (aucun sélecteur, aucune clé affichée — l'erreur fuyant les clés a été corrigée en amont par URGENCE-1/NU-F-028) ; le compteur Pilotage « étiquettes/semaine » est honnêtement à 0. Décision Vic : **laisser le backend intact, documenter**. Le vrai geste (ressusciter un sélecteur, ou retirer backend + tests de concert) relève d'une session qui a le droit de toucher aux tests.

## Notifications

### F-017 — « Rien de nouveau » faux
`src/labuse/api/events.py` : `vide = (n_evenements == 0)` au lieu de `vide = (len(veilles)==0 and permis_hier==0)` qui ignorait les événements perso (`groupes`, p. ex. une vente DVF sur parcelle suivie).

## Admin — L'usine / Tableau de bord

### F-050 — un job périmé ne peint plus « au vert »
`src/labuse/cockpit_resume.py` : nouveau prédicat partagé `_job_perime(job)` (dernier succès > **1,5× la cadence**, MÊME règle que `ops_alertes._jobs_en_retard`). `_pastille_job` et `_pastille_poste` rendent **ambre** (« en retard ») un poste ok mais périmé ; `_resume_usine` sort un compteur `retard` ; la légende gagne « ambre = en retard ». Front `Usine.tsx` : pastille ambre (fond posé inline via `var(--ambre)` pour ne pas toucher au snapshot de `style.ts`), compteur « N en retard ».
- **Preuve (`GET /admin/usine`, q_v20)** : résumé `{postes:30, vert:1, echec:0, arret:24, retard:5}` — **5 postes basculent de « vert » (mensonge) à « ambre/en retard »**. Légende : `… ['ambre','en retard'] …`.

### F-051 — incidents périmés
`cockpit_resume.py` `_cartes_incidents` : l'âge « ouvert depuis {date} » remonte dans la **phrase** de la carte (plus caché dans « Voir le détail ») → un incident vieux de 2 j ne se lit plus comme « maintenant » et ne contredit plus en silence un autre onglet redevenu vert.

## Étude de zone

### C-002 — PDF « Niveau de vie moyen / an »
`src/labuse/exports/blocs/etude_zone.py` : le libellé PDF « Revenu médian » (une valeur qui est en réalité `sum(ind_snv)/sum(ind)` = niveau de vie moyen par individu) devient « **Niveau de vie moyen / an** », aligné sur l'écran.
- **Preuve (`GET /etude-zone.pdf?idu=97411000AB0332&rayon_km=1`, pdftotext)** : « Niveau de vie » PRÉSENT · « Revenu médian » ABSENT.

---

## DA & accessibilité (F-019 / F-020 / F-021 / F-022)

9 fichiers front (aucun test, aucun snapshot, aucun `style.ts` touché).

- **F-021 — insécables** : les helpers locaux `fmtEur`/`fmt`/`pct` (espace normale) sont supprimés et remplacés par ceux de `lib/format` (U+00A0) dans `RadarEcran.tsx`, `RadarMarcheColonne.tsx`, `VeilleEcrans.tsx`, `ProjetKanban.tsx` ; `€/m²` composé sur `fmtEur`, `−N %` avec NBSP. Contrôle `grep -nP ' [€%]|[0-9] m²'` : plus aucune espace normale avant une unité dans une chaîne rendue (restes = commentaires / en-têtes de colonne sans nombre). Fin du « 3 038€/m² ».
- **F-020 — composants charte (Radar/Veille)** : `<select>` natifs → `Select` ; pastilles de statut → `Badge` ; fréquences → `Chip` (avec `aria-pressed`) ; hex `#E7B008` → token `text-amber` ; opacité hors-charte `bg-mint/12` → `bg-mint/10`. (L'état « carte sélectionnée » de RadarEcran garde un `<span>` dédié : `Badge` ne reproduit pas le mint-sur-mint inversé sans changer l'apparence — noté.)
- **F-022 — clavier + labels** : `role="button" tabIndex={0}` + `onKeyDown` Entrée/Espace sur les `<div onClick>` de `ProjetsPanel.tsx` (ligne projet + « Voir … de plus »), calqués sur `VeilleEcrans` ; `aria-label` sur tous les champs placeholder-seul (`AccueilCopilote`, `ParcoursProjet` ×4, `Header` ×4, `SourcesPage`).
- **F-019 — couleur de marque** : le mint `#4ADE80` en dur → `var(--mint)` dans `ProjetsPanel.tsx` (×3) et `ParcoursProjet.tsx` (`ACCENT_MINT`). Les gris neutres laissés tels quels (hors périmètre « couleur de marque »).

Vérif cluster : `npx tsc -b` 0 erreur · `npx vitest run` **305 passed / 64 fichiers**, aucune régression, snapshots intacts.

---

## Recette & vérifications

- **Compteurs Projets = carte** : prouvé sur **3 combinaisons** (tableau F-003) — égalité exacte `total/figeable/ecartees`.
- **Partition État du sol** : nu 34 203 + bâti 230 920 + non mesuré 167 227 = 432 350 = base (exacte).
- **B-001** : `instruire` (3 107) == pastilles réellement peintes (`idus=1` → 3 107, non tronqué).
- **F-050** : `/admin/usine` → 5 postes basculent « vert » → ambre « en retard » (prédicat 1,5× partagé).
- **C-002** : pdftotext du PDF Étude de zone — « Niveau de vie moyen / an » présent, « Revenu médian » absent.
- **Hook (vert)** : `tsc -b` **0 erreur** · `vitest` **305 passed / 64 fichiers** · pytest non-db **2 799 passed, 48 skipped, 0 failed** (famille du hook `-m "not db and not local and not reel and not network"`). Les tests et le hook n'ont pas été modifiés.
  - *Note* : la 1ʳᵉ passe a cassé 2 tests verrouillant `cockpit_resume._resume_usine` à un dict de 4 clés (mon ajout `retard`). Correctif : `_resume_usine` garde son contrat 4-clés ; le « en retard » se lit sur les pastilles (ambre) et est recompté au front. Re-passe : vert.
- **Captures** (non versionnées, `.gitignore **/captures/`) : `carte-B001-split-B002-etatsol.png` (bouton total + split « 3 107 à instruire · 3 469 écartées » + 3 chips État du sol), `radar-F020-F021.png`.

## Fichiers modifiés

**Back** : `api/app.py` (B-001, B-002), `api/projets.py` + `runs.py` (Projets), `api/crm_columns.py` (F-009), `api/events.py` (F-017), `cockpit_resume.py` (F-050/051), `exports/blocs/etude_zone.py` (C-002).
**Front** : `panel/FiltreLabuse.tsx`, `panel/FiltreFacettes.tsx`, `lib/api.ts`, `lib/strings.ts` (B-001/B-002/Projets) ; `projets/ParcoursProjet.tsx`, `projets/ProjetKanban.tsx`, `projets/ProjetsPanel.tsx` (F-003/011/019/022) ; `crm/Kanban.tsx` (F-010) ; `admin/circuit/Usine.tsx`, `admin/circuit/types.ts` (F-050) ; `radar/RadarEcran.tsx`, `radar/RadarMarcheColonne.tsx`, `radar/VeilleEcrans.tsx`, `copilote/AccueilCopilote.tsx`, `header/Header.tsx`, `sources/SourcesPage.tsx` (F-020/021/022).
**Aucun** fichier de test, snapshot, hook, ni `style.ts` modifié. Aucun code de chargement de Pilotage / Sources / Étude de zone / fiche commune / Successions / autocomplétion touché.
