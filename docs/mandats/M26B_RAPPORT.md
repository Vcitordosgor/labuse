# M26-B — Rapport de mandat : Copilote · Écran (Point d'arrêt C)

> **⚠ CONSIGNE (Vic, 28/07/2026) — tant que le mandat `MANDAT_HYPOTHESES_BILAN` n'est
> pas passé, le Copilote ne doit être montré à PERSONNE.** Sa charge supportable est
> ×2,37 trop généreuse et un verdict de viabilité sur deux est faux (hypothèses YAML
> périmées, cf. `M26B_CONSTAT_CHARGES.md`). Ce n'est pas un défaut du M26-B — mais
> c'est cet écran qui donne ces chiffres à voir, et c'est ce qui compte.

**Branche** : `feat/m26b-copilote-ecran` (base `origin/main` post-M26-A + dette-tests).
**Périmètre tenu** : front seul — `git diff` vide sous `src/` (back intouché).
**Référence design** : `docs/mandats/copilote_maquette_B4_reference_M26B.html`, tokens repris (`cp-*`).

## 1 · Architecture livrée

- **`lib/copilote.ts`** — types du contrat M26-A (vérifiés sur le code back, pas sur la
  doc) + appels HTTP (`CopiloteQuotaError` conserve le corps du 429 intégral).
- **`reduireEvenements.ts`** — réducteur PUR, miroir de `events.reduce_run` : event log →
  modèle de vue, idempotent au rejeu (tri par seq, dédoublonnage, terminal absorbant).
  Aucune donnée dérivée : entonnoir, compteurs, étiquettes, calibrage, exhaustivité,
  requalification lus tels quels dans les payloads. + `entonnoirEnCours` (projection des
  `step_completed` pendant le run — étages sans compteur : en attente, jamais inventés).
- **`useCopiloteRun.ts`** — LE hook SSE : reprise `after_seq` (dernier seq reçu), filet
  serveur 180 s (`fin: flux_expire` → réouverture), coupure réseau (reprise + indicateur
  discret), reprise post-clarification, annulation, run épinglé (localStorage) pour que
  le **rafraîchissement en plein run retombe sur le même fil** (critère du mandat).
- **Composants** : `CopiloteView` (dispatch des 5 états), `Entonnoir` (final/en cours),
  `FilInstruction` (+ ligne Interprétation), `Resultats` (lead + lignes + « N autres
  retenues »), `BlocLivrable`, `ui.tsx`. Libellés intégralement dans `CLIENT.copilote`
  (`strings.ts`) — zéro texte en dur.
- Câblage : vue de premier niveau (`View 'copilote'`, Rail, App), proxy Vite `/api`.

## 2 · Les 5 états (captures `frontend/qa/captures/m26c-*.png` — runs réels via SSE)

| État | Capture | Run |
|---|---|---|
| 1 · Terminée | `m26c-etat1-integral.png` — entonnoir 6 étages, fil 8 moteurs étiquetés, lead #01 (prix probable **et** charge supportable côte à côte, pastille budget), 20 restituées, « 2 927 autres retenues », journal actif, PDF « bientôt » | Saint-Paul 6 logements 480 k€ |
| 2 · En cours | `m26c-etat2-en-cours.png` — fil qui pulse, entonnoir partiel (étages à venir « — »), calibrage déjà badgé, AUCUN résultat partiel | même run, en vol |
| 3 · Précision | `m26c-etat3-precision.png` + `-reprise.png` — vraie question de l'interpréteur, 24 communes en options, champ libre ; la reprise continue LE MÊME run (`after_seq`) | brief volontairement vague |
| 4 · Zéro | `m26c-etat4-zero.png` — run `done`, entonnoir complet (820 → 0), panneau honnête, relances NON chiffrées (pré-remplissage du brief), livrable 0 restituée | 300 logements à Cilaos 100 k€ |
| 5 · Quota | `m26c-etat5-quota.png` — 429 RÉEL avant création (quota 10 consommé), corps du 429 verbatim, aucun flux ouvert | aucun run créé |

## 3 · Règles de la boussole — verrouillées par tests (26/26 verts, Vitest)

- règle 1 : chaque chiffre porte l'étiquette du payload (fil, entonnoir par étage, stats) ;
- règle 2 : non calibré → zéro « tracé(e) par article » dans le DOM (fixture générique) ;
- règle 3 : `exhaustif: false` → requalification intégrale, visible, hors repli ;
- règle 4 : « N autres retenues » toujours au DOM quand retenues > restituées ;
- règle 5 : aucun résultat partiel pendant l'instruction (étages non atteints « — ») ;
- règle 6 : zéro = `done`, panneau sans ton d'erreur, relances sans chiffre ;
- règle 7 : indicateur charge supportable = information (parcelle restituée) ; **cas
  dédié charge ≤ 0** : « Opération non viable — … (valeur brute), même à foncier
  gratuit » (décision revue B), lead + lignes, testé ;
- SSE : reconnexion `after_seq` sans doublon ni trou (réducteur + hook + refresh testés).

## 4 · Preuves

- Suite front : **26/26 PASS** (`npm test` — Vitest, devDeps seulement, build prod intact).
- `tsc -b` et `npm run build` propres.
- Golden : **116/116 PASS, 0 incohérence** (28/07, `LABUSE_API_BASE=127.0.0.1:8000` —
  la cible par défaut :8010 du script ne pointe sur rien sur ce poste, cf. constat).
- Back intouché : aucun fichier modifié sous `src/`.

## 5 · Constats et suites (hors périmètre M26-B, documentés)

- **`M26B_CONSTAT_CHARGES.md`** — divergence d'hypothèses `compute_bilan` (YAML
  périmé d'avant audit O2 vs défauts audités) : ×2,37 médian, 11/20 verdicts de
  viabilité inversés, inventaire des 7 consommateurs. **Mandat back prioritaire.**
- **`M26ABIS_SPEC.md`** — enrichissement du payload `restituees` (article invoqué,
  façade, comparables, checks risques) pour la carte lead complète.
- Écarts maquette assumés (arbitrages GO) : pas de compteur quota en topbar (aucun
  endpoint), pas de progression intra-étape (pas de `step_progress` — étages
  « examinées »/« restituées » en attente jusqu'au recap), relances de l'état 4 non
  chiffrées, « Voir la liste complète » retiré, mission `verifier_adresse` en
  « bientôt », PDF « bientôt » (M26-C).

## 6 · Notes d'exploitation (incidents de la nuit, consignés)

- Le heal de schéma au démarrage (lifespan) contient des DDL sur `parcels` : il ne PASSE
  PAS pendant un batch à transactions longues (type `division_or_candidates`) et une
  session orpheline en file gèle toutes les lectures (rejouer O12). Purge : voir pids
  dans `pg_stat_activity` (`query ILIKE 'ALTER TABLE parcels%' OR 'CREATE INDEX%'`).
- Deux runs réels ont échoué en `timeout_global` honnête pendant ces blocages — l'écran
  les a affichés tels quels (comportement voulu).
