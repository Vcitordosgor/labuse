# CRON-1 · Lot 2 — le verrou G8

**Branche** `feat/cron-1` · un commit. Aucun job posé en prod.

## La règle

> **G8** — « Aucune source vitrine sans contrôle depuis plus de 7 jours ; Radar sans dépôt depuis plus que son échéance. »

Un **contrôle** = un passage de sonde amont (`source_veille.dernier_passage_at`, méthode `api`/`page`/`entete`/`temoin`) de moins de 7 jours, OU l'agent (`agents-sources`) qui a écrit un passage. Une **source hors sonde** (méthode `rappel` ou aucune) n'a comme contrôleur possible que l'agent — **et l'agent est plafonné à 0 € (défaut)**, donc il ne tourne pas. **Personne ne les contrôle.** Une sonde configurée qui n'a pas encore eu son 1er passage est « surveillée » (grâce) ; une sonde configurée **muette depuis > 7 j** est en panne → sans contrôle.

Un G8 qui passerait **vert** dans cet état serait **faux**.

## Preuve — ROUGE sur l'état réel (aujourd'hui)

`verrou_g8(db)` sur la vraie base : **CASSÉ**, `15 source(s) vitrine sur 94 sans contrôle récent (agent à 0 €) · Radar à jour`. Les 15, **nommément** (dans le verrou ET dans le Résumé) :

1. Communes La Réunion — contours (IGN ADMIN EXPRESS, seed) — *aucune sonde*
2. Coût de construction (EPTB SDES + choix LABUSE) — *rappel manuel*
3. DEAL — cartes de bruit stratégiques (CBS) — *aucune sonde*
4. FRR ex-ZRR (Légifrance) — *aucune sonde*
5. INPI RNE (dirigeants) — *aucune sonde*
6. INPN / patrinat — espaces protégés — *aucune sonde*
7. INSEE RP Logement 2023 — *rappel manuel*
8. NPNRU (DEAL / ANCT) — *rappel manuel*
9. OpenStreetMap / Overpass — *aucune sonde*
10. PLH des 5 EPCI — *rappel manuel*
11. PVGIS (Commission européenne) — *rappel manuel*
12. RTAA DOM (Légifrance) — *rappel manuel*
13. Radar (pige d'annonces) — *rappel manuel*
14. VRD / assainissement (SPANC) — *rappel manuel*
15. ZFANG (Légifrance) — *aucune sonde*

**Inventaire SRU (DHUP)** (ajouté à la sonde au lot 1) est **exclu** à juste titre : sonde `api` configurée, 1er passage en attente → « surveillée », pas « sans contrôle ». Radar : dernier dépôt il y a 9 j < échéance 14 j (`LABUSE_RADAR_DEPOT_ECHEANCE_JOURS`) → à jour.

### Le Résumé du Circuit les nomme
Ligne dédiée, **rouge** : `15 · sources sans contrôle (agent à 0 €)` — phrase : *« Personne ne vérifie : Communes La Réunion — contours…, Coût de construction…, DEAL — cartes de bruit… [les 15] . Fixer LABUSE_AGENT_PLAFOND_EUR (l'agent du dimanche les reprend) ou leur poser une sonde amont. »* (composée par `circuit_resume.composer`, partagée avec le verrou via `circuit_garanties.sources_sans_controle`).

## Preuve — VERT sur un cas construit

Démo sur la vraie base, en transaction **annulée** (rien persisté) : quand les 94 sources reçoivent une sonde `api` + un passage récent (l'agent a repris les hors-sonde) —
```
AVANT (réel)              : G8 = casse · 15 sans contrôle
APRÈS (construit, 94 OK)  : G8 = ok    · 0 sans contrôle
rollback                  : G8 = casse (état réel restauré)
```
Et en test unitaire pur (`tests/test_cron1_g8.py`, sans DB) : `test_g8_vert_quand_les_94_ont_un_controle_recent` (94 passages récents → aucune sans contrôle).

## Câblage
- `circuit_garanties.py` : `classer_sans_controle` (logique pure, testable) ; `sources_sans_controle(db)` ; `radar_sans_depot(db)` ; **`verrou_g8(db)`** ; ajouté à `jouer_garanties` → **`labuse circuit verrous` joue G8** (8 garanties).
- `circuit_resume.py` : ligne rouge dédiée qui **nomme** les sources (paramètre `sources_sans_controle`).
- `api/dashboard.py` : calcule les sources et les passe au Résumé.
- `tests/test_cron1_g8.py` : rouge (hors-sonde + sonde en panne), vert (94 contrôlées).

## État de `labuse circuit verrous`
**G8 est ROUGE aujourd'hui — c'est voulu et correct** : 24 verts + **G8 cassé** (15 sources). Le vert complet (« G8 compris ») s'obtient dès que Vic **fixe le plafond agent** (`LABUSE_AGENT_PLAFOND_EUR > 0` → l'agent du dimanche reprend les 15) ou qu'on pose une sonde amont à ces sources. Faire passer G8 vert dans l'état actuel serait mentir.

`tsc -b` : lot 2 ne touche pas le front (Horloge = lot 3). Tests pytest verts (43 passed).
