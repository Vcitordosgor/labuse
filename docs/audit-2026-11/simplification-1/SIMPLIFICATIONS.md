# SIMPLIFICATIONS — SIMPLIFICATION-AUDIT-1

*12 novembre 2026 — lecture seule. Synthèse de `SOUS-LE-CAPOT.md`. Tu décides ; rien n'est changé.*

L'idée confirmée : **on recalcule et on surveille comme si les données bougeaient chaque nuit, alors qu'elles bougent rarement.** Le gros du gain est là (calcul + disque + bruit de mails), **sans toucher** aux sauvegardes ni à la surveillance qui, elles, attrapent les vrais problèmes.

---

## 1. Tous les rythmes : aujourd'hui / proposé

| Élément | Aujourd'hui | Proposé | Pourquoi |
|---|---|---|---|
| **Calcul du classement** | chaque nuit (abstient si rien ne change, sinon ~3 h) | **1×/mois max, ou à l'injection d'une source du classement** | Cadastre/PLU/PPR changent rarement ; DVF semestriel |
| **Candidats gardés** | 5+ runs (21 Go), jamais purgés | **1 à la fois**, l'ancien supprimé à la promotion | `purge-runs` est gelé |
| Table `cascade_results` | 1,4 Go morts, lue à 1 endroit | **supprimée** | obsolète (EXP-007) |
| `coherence-banc` | quotidien (12 min) | **2-3×/semaine** | a attrapé 2 écarts/30 j |
| `coherence-robinets` | quotidien (16 min) | **2-3×/semaine** | ~0 prise |
| `verite-permanente` | quotidien (4 min) | **hebdo** | 0 vraie prise, 6 flakes |
| `estimer-banc-precision` | quotidien | **hebdo** | régression lente OK |
| `fiche-commune-cache` | ~2×/jour (13 min) | **1×/jour** ou après injection | 24 communes stables |
| `john-veille` | quotidien | **2-3×/semaine** | peu consulté, coût |
| `mail-queue-consommer` | toutes les 5 min | **toutes les 15 min** | ≈0 mail client |
| **Incidents par mail** | 1 mail par incident (108/30 j) | **repliés dans le résumé du matin** (URGENT seul reste immédiat) | ta boîte = ~116 mails/mois de bruit |
| `recap-matin` (mort) | encore au registre | **supprimé** | remplacé par `resume-matin` |
| Sauvegardes, `healthcheck`, `sante-endpoints`, `fraicheur-nuit`, `sonde-sources`, alertes URGENT | — | **INCHANGÉS** | voir §4 |

---

## 2. Gains estimés

- **Calcul par nuit** : de « jusqu'à ~3 h + ~15 candidats/mois » à **~1 calcul/mois** → **~40 h de calcul économisées/mois** (et le serveur respire la nuit).
- **Croissance du disque** : chaque candidat pèse ~4-6 Go et aucun n'est purgé → aujourd'hui **~60-90 Go/mois** de croissance potentielle. Avec « 1 candidat à la fois » + purge : **croissance ~0**, et **~16 Go récupérés tout de suite** (runs morts) + **1,4 Go** (`cascade_results`). *C'est ce qui débloque la sauvegarde (disque à 92 % aujourd'hui).*
- **IA** : ~10,2 €/mois aujourd'hui, très loin du plafond 50 €. Ralentir `john-veille` ≈ **0,3 €/mois** — **gain négligeable en euros** (le vrai gain est le bruit, pas le coût). Ne pas sur-optimiser.
- **Mails** : de **~116 mails d'exploitation/mois** (dont 43 retards, 28 échecs, 12 escalades) à **~30/mois** (un résumé par jour) + les rares URGENT → **~3 mails de bruit/jour supprimés**.

---

## 3. Les dix simplifications, classées par gain et risque

| # | Simplification | Gain | Risque | Décision requise |
|---|---|---|---|---|
| 1 | **Calcul mensuel / à-l'injection** au lieu de chaque nuit | ⭑⭑⭑ ~40 h calc + ~60 Go/mois | **faible** (promotion déjà manuelle ; recalc déclenché par PLU/Cadastre/PPR) | doctrine (D10 audit préc.) |
| 2 | **Dégeler `purge-runs` + 1 candidat à la fois** | ⭑⭑⭑ +16 Go now, stoppe la croissance, **sauve la sauvegarde** | **faible** (garde servi + précédent) | **oui** (dégel = ton accord) |
| 3 | **Replier les incidents dans le résumé du matin** (URGENT seul immédiat) | ⭑⭑ −86 mails/mois | faible (garder le canal URGENT) | non (réglage) |
| 4 | **Supprimer `cascade_results`** (obsolète) | ⭑⭑ 1,4 Go + corrige EXP-007 | faible (corriger `builder.py:413` d'abord) | non |
| 5 | **Ralentir les bancs quotidiens** (coherence-banc, robinets, verite-permanente) à 2-3×/sem ou hebdo | ⭑⭑ ~14 h calc/mois | moyen (régression vue en 2-3 j au lieu d'1) | non |
| 6 | **`mail-queue` /5 min → /15 min** | ⭑ CPU + moins de collision backup 13:35 | faible (mail transactionnel un peu plus lent) | non |
| 7 | **`fiche-commune-cache` 2/j → 1/j** | ⭑ ~6 h/mois | faible | non |
| 8 | **Supprimer `recap-matin`** du registre (mort) | ⭑ propreté | nul | non |
| 9 | **`john-veille` 2-3×/sem + évaluer `agents-sources`** | ⭑ bruit + 0,3 € | faible (vérifier que la sortie est lue) | non |
| 10 | **`estimer-banc-precision` quotidien → hebdo** | ⭑ léger | faible | non |

**Priorité** : faire **#2 puis #1** d'abord (ils règlent le disque et la sauvegarde, cf. EXPLOITATION-AUDIT-1 EXP-013/EXP-003). Les autres sont du confort/propreté.

---

## 4. Ce qu'il ne faut SURTOUT PAS ralentir

| À garder tel quel | Pourquoi (preuve 30 j) |
|---|---|
| **Sauvegarde quotidienne + hebdo + rapatriement + copie externe + test mensuel** | la reprise prouvée date déjà du 04/11 ; ralentir = risquer une perte de données irrattrapable. Au contraire, il faut la **réparer** (EXP-003). |
| **`healthcheck` (/15 min) + `sante-endpoints` (/30 min)** | ce sont eux qui ont attrapé les **vrais** problèmes : disque (6), readyz (3), job bloqué (2). |
| **`fraicheur-nuit` + `sonde-sources` (quotidiens)** | détectent les retards de sources (DVF, SITADEL) — légers (3 s / 2,6 min). |
| **Alertes `[URGENT]` immédiates** | un disque plein, une sauvegarde absente, un readyz rouge doivent sonner tout de suite, pas le lendemain matin. |
| **Injection classe A de nuit + garde 974 + injection sûre (retour arrière)** | triviales en coût (<1 s) et ce sont les garde-fous qui protègent les données servies. |

**Règle simple** : on ralentit ce qui **recalcule** (classement, bancs de cohérence) et ce qui **notifie** (mails d'incidents) ; on ne touche jamais à ce qui **protège** (sauvegardes) ni à ce qui **détecte une panne en direct** (santé, fraîcheur, alertes urgentes).

---

*Détail chiffré et sources dans `SOUS-LE-CAPOT.md` (T1→T8). Toutes les corrections restent à décider par toi — rien n'a été changé.*
