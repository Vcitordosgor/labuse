# GPU-PILOTE — extension 23 communes : ÉTAT DES ARCHIVES (garde-fou avant extraction)

> Garde-fou appliqué AVANT toute extraction (arbitrage Vic) : comparaison de la version LOCALE à la
> version EN VIGUEUR via l'API grid GPU (`?grid=<insee>` → `effectiveStatus=EN_VIGUEUR`). Méthode
> légère (métadonnées, pas de téléchargement) ; sur L'Étang-Salé, le nom d'archive concordant a été
> confirmé byte-identique par sha256 — le nom fait donc foi pour détecter un décalage.
> **Rien extrait, rien écrit en base, aucun YAML modifié.**

## Blocage : la moitié des archives ne sont pas exploitables

Sur les 24 communes (dossier `~/Downloads/GPU:PLU/`) :

| statut | n | communes |
|---|---|---|
| **OK — à jour** | 10 | 97404 L'Étang-Salé (fait) · 97401 Les Avirons · 97402 Bras-Panon · 97403 Entre-Deux · 97406 La Plaine-des-Palmistes · 97415 Saint-Paul · 97416 Saint-Pierre · 97419 Sainte-Rose · 97423 Les Trois-Bassins · 97424 Cilaos |
| **OK mais PÉRIMÉ** (local < en vigueur) | 2 | **97411 Saint-Denis** (local 2024-02-20 → en vigueur 2026-04-23) · **97412 Saint-Philippe** (local 2019 → en vigueur 2025-12-10) |
| **VIDE (0 octet)** | 7 | 97405 Petite-Île · 97407 Le Port · **97408 La Possession** · 97414 Saint-Louis · 97420 Sainte-Suzanne · 97421 Salazie · 97422 Le Tampon |
| **ABSENTE** | 5 | 97409 Saint-André · **97410 Saint-Benoît** (seul un `saint benoit.pdf` = règlement, pas d'archive) · 97413 Saint-Leu · 97417 Saint-Joseph · 97418 Sainte-Marie (seul un `Sainte marie .pdf`) |

→ **9 communes extractibles immédiatement** (hors L'Étang-Salé) ; **14 bloquées** (2 périmées + 7 vides + 5 absentes).

## Le premier paquet (tes 12 brûlantes) est bloqué à 3/4

| commune | INSEE | archive | garde-fou | action |
|---|---|---|---|---|
| Bras-Panon | 97402 | OK 145 Mo | **à jour** (= en vigueur `20260428`) | extractible |
| Saint-Denis | 97411 | OK 214 Mo | **PÉRIMÉ** (local 2024, en vigueur 2026) | à retélécharger |
| La Possession | 97408 | **0 octet** | — | à télécharger |
| Saint-Benoît | 97410 | **absente** (PDF seul) | — | à télécharger |

Seul Bras-Panon est à la fois présent ET à jour. Je n'extrais pas Saint-Denis (périmé, ta règle dit
« ne pas extraire, signaler ») ni La Possession / Saint-Benoît (pas d'archive).

## Saint-Philippe : le GPU dit PLU, pas RNU

Tu m'as demandé de graver Saint-Philippe (97412) comme RNU. **La source GPU dit l'inverse** :
`grid.rnu = false`, et un **PLU EN VIGUEUR** `97412_PLU_20251210` (approuvé 10/12/2025). Aucune des
24 communes n'a `rnu = true` côté GPU. Je ne grave PAS « RNU » sur une affirmation que la source
contredit (boussole) — dis-moi si tu vises un autre statut (PLU annulé ? procédure en cours ?), sinon
je la traite comme PLU (archive à retélécharger, la locale de 2019 est périmée).

## Ce dont j'ai besoin pour avancer
1. **Retélécharger** les 2 périmées (Saint-Denis 97411, Saint-Philippe 97412) et les 7 vides.
2. **Fournir** les 5 absentes (dont Saint-Benoît 97410 — brûlantes).
3. **Trancher Saint-Philippe** (RNU vs PLU en vigueur).

Dès que le premier paquet (97410 + 97411 + 97408 + 97402) est complet et à jour, je l'extrais et
rends le rapport court. Je peux aussi, si tu préfères, avancer sur les **9 déjà à jour** dans un ordre
révisé — mais tes 4 prioritaires portent les brûlantes, d'où le signalement d'abord.
