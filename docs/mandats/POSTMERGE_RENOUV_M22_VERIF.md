# VÉRIFICATION POST-MERGE — RENOUV A/B/C + M22 0/A/B/C/D/F · RAPPORT

Main locale `7976d54` (10 merges `--no-ff`, séquence RENOUV A→B→C puis M22 0→A→B→C→D→F,
arbre propre — **non poussée**, Vic pousse). Vérification lecture seule + générations de
preuve : aucun code, aucune branche, rien de commité. Instance :8025 (dev_mode, IA
neutralisée), parcelle M22 = 97415000AC0197, parcelle golden RENOUV = 97413000DM0210.

## LOT D — Renouvellement : TOUT VÉRIFIÉ ✅

| Point | Constat |
|---|---|
| **Effectifs 5 tiers servis** | `servi_q_v7_defisc` : brûlante **120** · chaude **1 031** · réserve **3 587** · à creuser **72 980** · écartée **353 945** — **au bit près** (challengers identiques ; historiques m5 distincts, attendu) |
| **Badge fiche** | DM0210 : « Renouvellement — rang 18 222/68 445 » + libellé « Parcelle occupée — potentiel de renouvellement urbain » + « pourquoi ? » (4 composantes 40/25/20/15) — verdict Écartée inchangé |
| **Toggle carte** | OFF par défaut (légende absente) → activation dans le panneau couches → légende « Renouvellement » teinte cuivre visible. Prouvé par bascule live |
| **Outil liste** | module `renouvellement` : 300 lignes rendues, tri par score |
| **CLI bout-en-bout** | `labuse renouv` : rebuild **68 445** parcelles, entonnoir tracé 195 209 → 182 330 (zone U/AU) → 73 078 (capacité) → 71 313 (hors copro) → **68 445** (hors foncier public), run q_v7_defisc as-of 2026, top-20 affiché, **idempotent** (68 445 avant/après) |
| **3 cas golden** | (1) DM0210 porte le bloc `renouvellement` (score 53, rang 18 222) ✓ ; (2) parcelle riche hors segment (AT2317) → `null` ✓ ; (3) `meta.tiers_effectifs` gelés dans la référence = comptes DB exacts ✓ — et le run golden les compare (PASS) |

## LOT E — M22 : TOUT VÉRIFIÉ ✅

| Point | Constat |
|---|---|
| **8 PDF régénérés sur main** | flash 7 p. · dossier 7 · banquier 7 · argumentaire 8 · potentiel 6 · lettre 3 · fiche 2 · projet 1 — tous 200, template Flash **1.2** |
| **Identité unifiée (C2)** | wordmark + DA Flash sur les 4 briques, carte plan clair |
| **Bandeaux (C7)** | « LABUSE — produit · IDU — commune » présent dans les 4 briques (toutes pages intérieures) |
| **Chiffres-héros (C6)** | argumentaire PRIX D'ACHAT MAX · potentiel SURFACE CONSTRUCTIBLE RESTANTE · banquier CHARGE FONCIÈRE |
| **C1 même chiffre** | **160 k€** dans le Banquier ET l'Argumentaire sur AC0197 (défauts) ✓ |
| **Titres (C3)** | « Rapport Flash » / « Dossier parcelle » différenciés |
| **Attestation (C8)** | registre en base **incrémente** : LZ-2026-0001 → LZ-2026-0002 (2 lignes tracées) |
| **Dataviz (C9)** | bande de points + cascade rendues dans l'argumentaire |
| **Non-régression tiroir Faisabilité** | fiche écran DM0210 : calculette rend en mode « Charge supportable » (−742 €, honnête sur mini-parcelle), bascule « Prix d'achat max » → même chiffre (identité forward/inverse), lien « Éditer l'argumentaire » avec hypothèses reprises (`?cout=2500&marge=21`) |
| **Fiche** | PDF : 2 pages, carte VERDICT LABUSE en tête, sections cartouches (C4) ; projet #34 : bandeau « en cours de constitution », zéro « — » |

## Filets globaux
- **Golden : 116/116 PASS** (nouvelles ancres renouvellement + tiers stricts incluses).
- **Suite : 1 153 verts**, 10 échecs = les mêmes préexistants qu'avant tout M22/RENOUV
  (9 × test_front_reliquats + test_auth flaky en suite complète) — aucun nouveau.
- tsc 0 · build front OK sur main mergée.

## Notes
- Captures de vérification (non versionnées) : /tmp/verif_badge_renouv.png,
  /tmp/verif_calculette.png, /tmp/verif_outil_renouv.png, /tmp/verif_toggle_carte.png ;
  PDF /tmp/pm_*.pdf.
- Reste connu (hors périmètre de cette vérif) : push de main par Vic · arbitrage C5
  (spécialisation Banquier/Argumentaire) · revue O12 (20 cartes) pour la divisibilité
  chiffrée du Rapport de potentiel · branchement quotas des 3 nouveaux exports.
