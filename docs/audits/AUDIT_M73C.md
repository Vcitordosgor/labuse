# AUDIT M73-C — Réhabilitation & Assainissement dans les 5 documents (Phase 1, mesure)

**Branche `feat/m73c-contenu`. Aucune écriture. Mesuré le 14/08/2026.**

## TL;DR
- **ANC : rendu NULLE PART.** La donnée est disponible dans 3 documents (premium, dossier, one-pager
  via `fiche["anc"]` / `out["anc"]`) mais aucun ne l'affiche ; absente des données du banquier et de
  l'argumentaire. Le dossier flash **collecte** `out["anc"]` (data.py:489) mais son template Jinja
  **ne le rend pas**.
- **Réhabilitation : rendue seulement dans le one-pager** (+ exports md/html). Absente des 4 PDF
  (premium, dossier, banquier, argumentaire).
- **Aucun recalcul local d'ANC** (`zone_anc`/`proba_anc`) dans un générateur — le bug M59 est propre,
  personne ne le réintroduit.
- **Les deux helpers exposent ce qu'il faut** → pas de STOP forcé. Restent 2 arbitrages Vic (réhab
  one-pager/premium ; ANC premium ; média fpdf vs HTML pour le « rendu écrit une fois »).

## Les helpers (source unique confirmée)
- **ANC** : `anc_service.statut_anc(db, idu)` → via `_anc_block` (app.py:2607, dans `_build_fiche`) et
  `flash/data.py:489`. États M88 : Sourcé / Sourcé secteur (taux INSEE, maille+millésime) / Absent.
- **Réhabilitation** : `faisabilite.bilan.compute_mode_b(session, idu, run)` → via `_mode_b_block`
  (app.py:2519, dans `_build_fiche` → `fiche["mode_b"]`). Rendu de référence : `export.py` (md 75-99,
  html 210-234, one-pager 44-75).

## Matrice — ANC (assainissement)
| Document | Générateur | Rendu ? | Donnée dispo ? |
|---|---|---|---|
| Premium (fpdf) | `pdf_premium.render_fiche_pdf(fiche)` | ❌ non | ✅ `fiche["anc"]` |
| Dossier (weasyprint Jinja) | `flash/report.py` + `templates/rapport.html.j2` | ❌ non (template ignore `out["anc"]`) | ✅ `out["anc"]` collecté (data.py:489) |
| Banquier (weasyprint) | `banquier.py` + `briques_pdf.py` | ❌ non | ❌ absent de `briques_pdf.collect` |
| Argumentaire (weasyprint) | `argumentaire.py` + `briques_pdf.py` | ❌ non | ❌ absent |
| One-pager (weasyprint) | `export.py:fiche_onepager(fiche)` | ❌ non | ✅ `fiche["anc"]` |

→ **ANC rendu nulle part.** Data présente premium/dossier/one-pager, absente banquier/argumentaire.

## Matrice — Réhabilitation (`mode_b`)
| Document | Rendu ? | Donnée dispo ? |
|---|---|---|
| Premium (fpdf) | ❌ non | ✅ `fiche["mode_b"]` |
| Dossier (weasyprint Jinja) | ❌ non | ❌ `flash/data.py` ne collecte PAS `mode_b` |
| Banquier (weasyprint) | ❌ non | ❌ (briques_pdf lit `shab_vendable_m2` = capacité NEUVE, ≠ réhab) |
| Argumentaire (weasyprint) | ❌ non | ❌ (idem, shab neuf) |
| One-pager (weasyprint) | ✅ **oui** (export.py 44-75) | ✅ `fiche["mode_b"]` |
| (export md / html) | ✅ oui | ✅ |

→ **Réhab rendue au one-pager seul** (parmi les documents). Absente des 4 PDF.

## Fautes constatées (à corriger en Phase 2)
1. **Aucune faute de recalcul** : ni ANC ni réhab ne sont recalculés dans un générateur (bon).
2. La faute est d'**omission** : deux critères servis à l'écran, sortis d'un helper unique, mais non
   rendus dans les documents qui devraient les porter. Pas de divergence de calcul — un trou d'affichage.
3. **Piège média** : le premium est en **fpdf** (dessin Python), les 4 autres en **WeasyPrint (HTML)**.
   Le « rendu écrit UNE fois » (règle commune Phase 2) est réalisable comme **un builder HTML partagé**
   pour la famille WeasyPrint (dossier/banquier/argumentaire/one-pager) ; le premium fpdf est un autre
   média → il ne peut pas partager le même snippet HTML. À trancher : le premium porte-t-il ces blocs
   (et alors dans son propre rendu fpdf), ou non ?

## Cibles Phase 2 (mandat) + arbitrages Vic
- **ANC** — mandat : banquier + argumentaire + one-pager. Data à ajouter à `briques_pdf.collect`
  (banquier/argumentaire) via `statut_anc` ; rendu HTML partagé. **Arbitrage** : le premium (data déjà
  là) et le dossier flash (data déjà collectée) doivent-ils aussi le rendre ? (le mandat ne les cite pas
  explicitement pour l'ANC, mais Phase 1 les mesure : ils sont vides).
- **Réhabilitation** — mandat : banquier + argumentaire (fermes). One-pager : déjà rendu. **Arbitrage
  Vic explicite** : one-pager (déjà là — garder tel quel ?) et **premium** (data dispo, rendre ou non ?).
- **Média** : builder HTML partagé pour les 4 weasyprint ; premium fpdf = décision séparée (porte/porte pas).

## Ce que Phase 2 exigera (rappel, pas fait ici)
- Brancher `statut_anc` dans `briques_pdf.collect` (banquier/argumentaire) + `mode_b` idem.
- Un builder de bloc **écrit une fois** (HTML) : ANC (Sourcé/Sourcé secteur avec **maille nommée
  visiblement** + millésime ; jamais un verdict ; testé sur un cas à 16 %) et réhab (absence de
  potentiel affichée, jamais masquée).
- Phase 3 : 5 exports 200 · non-contradiction M73 + **nouveau cas** (un critère écran absent d'un doc
  = échec) · golden 119/119 · recette 4 parcelles (ANC réglementaire L'Étang-Salé, collectif
  Saint-Paul = non-régression M59, Sourcé secteur IRIS Le Tampon, une avec potentiel réhab) · grep
  (aucun `zone_anc`/`proba_anc` en générateur, aucun recalcul réhab).

## ARBITRAGE VIC (14/08/2026) — les deux critères dans les 5 documents
Vic tranche : **ANC ET réhabilitation rendus dans les 5 documents** (couverture uniforme).
- **ANC** : banquier + argumentaire + one-pager (mandat) **+ premium (fpdf) + dossier flash**.
- **Réhab** : banquier + argumentaire (mandat) + one-pager (déjà) **+ premium (fpdf) + dossier flash**.

### Plan Phase 2 arrêté (à exécuter — session suivante)
1. **Builder de bloc partagé (écrit UNE fois)** — HTML, pour la famille WeasyPrint (dossier /
   banquier / argumentaire / one-pager) : `anc_bloc_html(anc)` + `rehab_bloc_html(mode_b)`. Rendu
   ANC : maille **nommée visiblement** (secteur IRIS « nom » ou commune) + millésime ; jamais un
   verdict ; formulation testée sur un cas à 16 %. Réhab : absence de potentiel **affichée**, jamais
   masquée. Nouveau module, ex. `src/labuse/api/blocs_documents.py`.
2. **Premium (fpdf)** — média distinct : rendu fpdf des deux blocs (mêmes libellés/états, dessin
   Python), lisant `fiche["anc"]` / `fiche["mode_b"]` déjà dans le payload.
3. **Câblage data** : ajouter `statut_anc` + `compute_mode_b` à `briques_pdf.collect`
   (banquier/argumentaire) ; ajouter `mode_b` (via `compute_mode_b`, jamais recalcul) à
   `flash/data.py` collect (dossier) ; rendre l'ANC dans `templates/rapport.html.j2` (déjà collecté) ;
   ajouter l'ANC au one-pager (`export.py`). Jamais lire `zone_anc`/`proba_anc` en générateur.
4. **Phase 3** : 5 exports 200 · non-contradiction M73 + **nouveau cas** (critère écran absent d'un
   document = échec) · golden 119/119 · recette 4 parcelles (L'Étang-Salé ANC · Saint-Paul collectif
   = non-régression M59 · Le Tampon Sourcé secteur IRIS · une avec potentiel réhab) · grep de contrôle.
