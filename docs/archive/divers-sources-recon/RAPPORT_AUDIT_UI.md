# RAPPORT — AUDIT UI/UX EXHAUSTIF & CHASSE AUX BUGS (12/07/2026)

**Branche `feat/audit-ui-bugs`** (depuis main 7699909, post pile 9/9) · 8 commits · **jamais de merge** (Vic, `--no-ff`).
App auditée : socle React (`/socle/`) servi par `labuse api`, base réelle 431 663 parcelles, `LABUSE_DEV_MODE=1` (fix Phase A1).
Livrables liés : **`BUGS.md`** (triage + preuves) · **`AMELIORATIONS-UX.md`** (suggestions, rien d'implémenté) ·
`audit_shots/ui2026/` (174 captures en local, ~42 Mo — les preuves citées sont committées) ·
`qa/audit/` (harnais réutilisable + findings.jsonl + resultats/*.json).

## 1. Table de couverture (vue × viewport × statut)

| Vue / flux | 1440 | 768 | 375 | Statut |
|---|---|---|---|---|
| Cartes (couches ×9, verdict, liseré brûlantes, clic parcelle→fiche, zoom/flyTo) | ✔ | ✔ | ✔ | exercé |
| Fiche ×6 parcelles contrastées (brûlante, V=0, public, copro, sans bâti, littoral bruit+50 pas) × 7 onglets | ✔ | ✔ | ✔ | exercé (126 combinaisons) |
| Fiche : « Pourquoi ce score » (somme=total), liens BODACC (cible exacte), PDF, Escape | ✔ | — | — | exercé |
| Header : omnibox (commune, IDU, limites : vide/espaces/script/inexistant/0), sélecteur commune, contexte | ✔ | — | — | exercé |
| Segments : galerie (5 presets), ouverture ×5, compteurs vs réel, export CSV ×5 (RGPD) | ✔ | capture | capture | exercé |
| Segments builder : **37 filtres UN PAR UN** (37/37, 0 grisé), valeurs limites, combo ×3, 11 tris | ✔ | — | — | exercé (desktop = outil pro ; mobile → AMELIORATIONS n°6) |
| Segments admin : duplication TEST_AUDIT_, `?inclure_inactifs=true` (21 dont 15 inactifs), PUT désact./réact., DELETE | ✔ | — | — | exercé (API+UI) |
| Publipostage (ZIP : CSV « À l'occupant » 472 lignes, étiquettes PDF, gabarit) | ✔ | — | — | exercé |
| Recherche NL : 10 requêtes (pièges : filtre inexistant, flou, absurdes, injection, destruction) | ✔ | — | — | exercé |
| NL segments : 3 requêtes dont piège + demande nominative (refusée) | ✔ | — | — | exercé |
| Dossier parcelle PDF (quota compté 5→6, plan Intégral illimité) + pré-dossier PC (« Document préparatoire » ×3) | ✔ | — | — | exercé |
| Flash : 4 parcelles contrastées (sections conditionnelles, watermark EXEMPLE, carte image) | n/a (PDF) | — | — | exercé |
| Solaire : M23 parkings APER (24 échéances dépassées + badges), M24 toitures, onglet Solaire fiche | ✔ | — | — | exercé |
| Piscinistes ×2 : compteurs (5 541 / 497), fiabilité 90,7 % sur exports | ✔ | — | — | exercé → P1-2 fixé |
| Outil validation ortho : page, tirage, contrat verdict | ✔ | — | — | partiel (écritures réelles exclues, cf. BUGS §Non testé) |
| CRM Kanban : ajout → déplacement → retrait (objet TEST) | ✔ | capture | capture | exercé (API ; DnD souris au backlog) |
| Projets : création TEST_AUDIT_ → rejouer → archive → suppression | ✔ | — | — | exercé |
| Events/watch : toggle aller-retour (état restauré), liste | ✔ | — | — | exercé |
| Sources / IA / TimeMachine / ContextePanel / SourceDrawer | ✔ | capture | capture | exercé (SourceDrawer : ouverture partielle) |
| États limites : commune sans résultats, réponse lente 4 s (loader ✓), offline (abort) | ✔ | — | — | exercé |
| UI Vue historique `/app/` | — | — | — | **exclu** : en transition, remplacée par le socle (qa/e2e.mjs la couvre déjà) |
| Courrier réel / paiement Stripe | — | — | — | **exclu** : providers stub sans clé, aucun bouton front (conforme) |

## 2. Stats

- **≈ 420 interactions** exercées (37 filtres, 11 tris, 9 couches ×2, 126 fiche×onglet, 10+3 NL, 5 exports, limites…)
- **38 anomalies auto collectées → 14 uniques** (console/pageerror/réseau, horodatées vue+action : `qa/audit/findings.jsonl`)
- **Bugs : 1 P0 · 5 P1 · 7 P2 · 4 P3** — **fixés en session : P0-1, P1-1, P1-2, P1-3, P1-4** (5 fixes, un commit + un test chacun) ; P1-5 + P2/P3 = backlog motivé
- Tests ajoutés : **13 unitaires** (protection ×5, PDF ×2, segments/ortho ×4, +2 A2) + **8 asserts E2E** (`qa/e2e_429.mjs`, `qa/e2e_audit_fixes.mjs`)

## 3. Top 10 (preuves dans BUGS.md)

1. **P0-1** Export PDF fiche : 500 partout (`NameError RUN`) — **fixé**, re-crawl 200.
2. **P1-1** « **-9 parcelles** correspondent » (compteur négatif figé, serveur disait 167) — **fixé** + E2E.
3. **P1-2** Fiabilité 90,7 % absente des presets/exports piscines (décision Option B non appliquée) — **fixé** (badge + pied CSV).
4. **P1-5** NL dégradé silencieux : « DPE F ou G au Tampon » → 2 080 parcelles (critère DPE ignoré sans le dire) — backlog produit.
5. **P1-3** Omnibox : IDU hors commune = no-op muet (+ 422 avalé) — **fixé** (île entière + toast).
6. **P1-4** Verdict ortho écrasable sans profil (dataset ML) — **fixé** (garde systématique).
7. **P2-5** Mobile 375 : la carte est inaccessible derrière le panneau (`375_boot.png`).
8. **P2-1** Offline : loader muet ~5 s avant l'erreur (fiche), toast carte sans fin (`1440_etat_offline.png`).
9. **P2-2** Liste vide sans message (Cilaos, `1440_carte_cilaos_vide.png`).
10. **P2-4** NL stub : « supprime toutes les parcelles » → filtre appliqué au lieu d'un refus.

## 4. Passe experte UX

→ **`AMELIORATIONS-UX.md`** : 15 suggestions priorisées impact×effort. Top 5 : (1) mobile
Cartes en tiroir, (2) repli NL affiché dans la restitution, (3) wording erreur « serveur
périmé » → humain, (4) état vide de liste avec CTA, (5) garde négatifs des ranges. Rien
d'implémenté — décision Vic.

## 5. Nettoyage TEST_AUDIT_ — confirmé

- Presets `test-audit-*` : DELETE 200, `inclure_inactifs=true` → **0 résiduel** ✔
- Pipeline : entrées 14/15 supprimées → **0 résiduel** ✔ · Projet #23 supprimé → **0** ✔
- Watch 97411000KE0316 : retour à `false` ✔ · Flash `flash_TEST_AUDIT_*.pdf` : supprimés ✔
- Ortho : **aucun verdict réel écrit** (ids 990001/990002 en base de TEST uniquement, purgés par le test) ✔
- Traces résiduelles ASSUMÉES (lecture seule) : `consultation_log`/`usage_compteurs` portent le trafic de l'audit
  (sujet IP local) — le scan `abuse-scan` de demain scorera ce sujet, ne pas s'en étonner.

## 6. État prêt-à-valider

- 8 commits atomiques sur `feat/audit-ui-bugs` : A1 protection (1ee0901), A2 429 (b072f44),
  P0 PDF (ef9611e), compteur négatif (3a1482c), omnibox (433c8fb), mentions+ortho (dae612e),
  + docs. **Aucun merge effectué.**
- Suites : `pytest tests/test_protection.py tests/test_pdf_premium.py tests/test_audit_ui_fixes.py tests/test_dpe.py tests/test_rnic.py` → **26 passed** ·
  `node qa/e2e_429.mjs` 5/5 · `node qa/e2e_audit_fixes.mjs` 3/3.
- Re-crawl des vues fixées : PDF 200, mention piscines en galerie+CSV, restitution ≥ 0, toast omnibox.
- Dette de suite proposée (hors mandat) : DnD Kanban souris sur objet TEST, PATCH partiel presets, bandeau offline.
