# M26-B — Plan d'implémentation (Point d'arrêt A)

Front seul, branché sur l'API M26-A mergée. Référence design : `copilote_maquette_B4_reference_M26B.html` (tokens repris tels quels, bandeaux ambre exclus).

## 1 · Composants (tous nouveaux, sous `frontend/src/components/copilote/`)

| Composant | Rôle |
|---|---|
| `CopiloteView` | Écran complet (topbar/eyebrow/console + dispatch des 5 états). Vue de premier niveau, **pas** un module du ModulePanel : la maquette est une page pleine largeur (wrap 1000 px), incompatible avec le panneau 320 px. |
| `useCopiloteRun` (hook) | Toute l'intégration : création du run, EventSource sur `/api/copilote/runs/{id}/events?after_seq=N`, journal d'événements en mémoire, reconnexion auto (`after_seq` = dernier seq reçu, y compris à l'expiration des 180 s côté serveur), indicateur « flux interrompu », `answer`, `cancel`. |
| `reduireEvenements` (pur) | Event log → view-model. Aucune donnée dérivée : entonnoir, compteurs, étiquettes, calibrage, exhaustif, requalification lus tels quels dans les payloads (`step_completed.resultat`, recap d'`assemblage`, `run_completed`). Testable à sec sur fixtures. |
| `Console` | Brief + bouton Instruire/Annuler + sélecteur des 5 missions (`instruire`, `shortlist`, `verifier_adresse` actives ; `aide_dossier`, `brief_matin` désactivées « bientôt »). |
| `Entonnoir` | 6 étages, rail, badges `exh/trunc` + `calib/gener`, étages non atteints en `pending`. |
| `FilInstruction` | Lignes générées depuis `run_started.plan` ; ✓ / ! / pulse / attente ; étiquette du payload ; compteurs `avant → après`. |
| `Resultats` | Carte lead #01 + lignes #02…#20 + `restnote` « N autres retenues » (toujours visible si retenues > restituées). Encart ambre `au_dessus_charge_supportable` par parcelle (charge supportable vs prix probable). |
| `PanneauClarification` | Question + options + champ libre → `POST answer`, le fil reprend (SSE ré-ouvert, même run). |
| `PanneauZero`, `PanneauQuota`, `BlocLivrable`, `Etiquette`, `Badge` | Selon maquette. Quota : payload du 429 (`detail`, `quota`, `gel_jusqua`). |

Accroches existantes : entrée dans la nav d'`App.tsx` (nouvelle vue `copilote` — IAStub intact), appels API ajoutés à `lib/api.ts` (réutilise `ApiError`/`is429`), libellés dans `CLIENT.copilote` de `lib/strings.ts`, tokens maquette scopés (extension Tailwind `cp-*` ou CSS vars sur la vue — la palette maquette diffère légèrement des tokens app : mint `#63F2B8` vs `#5CE6A1`, fond `#070A09` vs `#060A08` ; je suis la maquette, validée par Vic).

## 2 · Correspondance état ↔ événements

| État | Projection |
|---|---|
| 2 · En cours | `run_started` (plan gelé) puis `step_started`/`step_completed` ; étage d'entonnoir rempli à chaque `compteur` ; **aucun résultat** avant `run_completed`. |
| 3 · Précision | `clarification_requested` + `fin(awaiting_user)` → panneau ; réponse → `POST answer` → SSE ré-ouvert `after_seq`, le fil continue. |
| 1 · Terminée | `run_completed` avec `n_restituees > 0` ; recap : entonnoir, top-20, `exhaustif`/`requalification`, `calibrage`/`mention_sdp`, « N autres retenues ». |
| 4 · Zéro | `run_completed` avec `n_restituees = 0` — même projection, panneau honnête, entonnoir complet, relances sans assouplissement. |
| 5 · Quota | `POST /runs` → 429 : aucun run, panneau quota depuis le corps du 429. |
| (annulation) | `run_cancelled` → fil figé + mention ; `run_failed` → message honnête du payload. |

## 3 · Tests (infra à créer : **aucun test front n'existe** — ajout Vitest + Testing Library + jsdom, devDeps uniquement)

- 5 fixtures figées (un jeu d'événements par état) + rendu de chaque état.
- Verrous : non calibré → zéro occurrence « tracée par article » · retenues > 20 → « N autres retenues » dans le DOM · `exhaustif: false` → requalification visible non repliée.
- `reduireEvenements` : reconnexion `after_seq` sans doublon ni trou (rejeu partiel + suite).
- Back intouché ; golden 116/116, tiers au bit près et suite Python re-exécutés en fin de mandat pour preuve.

## 4 · Questions ouvertes (arbitrage Vic avant GO)

1. **Compteur quota en topbar** (« 2/10 » permanent sur la maquette) : aucun endpoint ne l'expose (`/moi` ne porte pas le quota Copilote ; le 429 ne parle qu'à l'échec). Options : (a) le retirer au M26-B, quota visible seulement à l'état 5 — *ma reco* ; (b) mini-mandat back pour l'exposer. Je ne le calculerai pas côté front.
2. **Progression intra-étape** (état 2 : « 1 862 examinées sur 4 250 », « 44 % ») : pas d'événement `step_progress` dans la taxonomie M26-A. Reco : étape active en pulse sans pourcentage ; à enrichir par mandat si voulu.
3. **Carte lead #01** : la maquette montre article PLU (« UB10 · R+2 »), façade voirie, nb comparables DVF, checks PPR/ABF/DPE et vignette — absents du payload `restituees`. Options : (a) carte lead réduite aux champs du payload (zone, SDP, surface, tier, prix, charge) — *ma reco M26-B* ; (b) enrichir via `GET /parcels/{idu}` existant (affichage de données back, pas de recalcul — mais l'écran n'est plus une pure projection du log) ; (c) mandat back.
4. **« Voir la liste complète »** (restnote) : le back ne restitue que le top-20. Bouton omis au M26-B ?
5. **Relances de l'état 4** : « Relancer avec un budget de 630 k€ » suppose un chiffre calculé, absent du payload. Reco : relances génériques pré-remplissant la console (l'utilisateur relance lui-même), aucun chiffre inventé.
6. **Bloc livrable** : le PDF est M26-C. Reco : bloc affiché, « Télécharger le PDF » désactivé « bientôt », « Voir le journal » actif (le log est disponible).
7. **Les 5 missions** : je lis `instruire`, `shortlist`, `verifier_adresse` (actives) + `aide_dossier`, `brief_matin` (« bientôt ») — la note d'opportunité étant le livrable d'`instruire`, pas une mission. À confirmer.
8. **Écrans `shortlist`/`verifier_adresse`** : la maquette ne couvre qu'`instruire`. Reco : même gabarit (fil + recap), sans entonnoir 6 étages pour `verifier_adresse` (plan à 2 étapes).
