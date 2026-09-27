# VEILLE-FIX-2 — La grille de veille tient toute seule, et le mail dit vrai

**Branche** `fix/veille-fix-2` · **base main** `d6f17fb9` · **worktree** `~/Desktop/labuse-veillefix` ·
**un commit par lot** · **date** 27/09/2026 · **modèle** Opus · transport neutralisé (dry-run, SMTP absent) ·
objets `[VF2-*]` purgés en fin. Exécute les recos de [[VEILLE-AUDIT-2]].

Commits : `020dc0a6` (Lot A) · `2012c46a` (Lot B) · `0a9978b0` (Lot C) · `0f3aa11f` (Lot D) ·
Lot E ci-dessous.

| Lot | Trou de l'audit | Correctif |
|---|---|---|
| A | Le Radar rate le dépôt du soir (`_biens_du_jour` = date ≥ aujourd'hui) + grille des kinds floue | Fenêtre du Radar élargie à la capture du soir ; grille des kinds (`veille_grille`) : ce qui va à la cloche, au digest, au mail immédiat |
| B | Événements manquants | `radar_baisse`, `radar_retrait`, `parcelle_en_vente` (mise en vente d'une parcelle SUIVIE → mail immédiat) |
| C | `digest_freq` stocké, jamais lu | La fréquence est lue et réglable (préférences) |
| D | Worker mails programmés non branché, pas de rejeu d'échec | La file `mail_queue` tient toute seule (rejeu, dédup) |
| **E** | **Aucun rendu réel des mails de la grille** | **Rendu dry-run de la grille + du mail immédiat, sur base réelle → un bug de corps trouvé et corrigé** |

---

## Lot E — Le rendu réel : ce que le client reçoit vraiment

`captures/render.py` joue la grille complète sur la **base réelle** en dry-run (compte de test `[VF2-E]`,
adresse de Vic, transport neutralisé, tout purgé en fin — **aucun client réel touché**) : parcelle suivie
vendue (DVF réelle CY0018), veille de commune, trois biens Radar (nouvelle / baisse / retrait), une mise
en vente rattachée à la parcelle suivie. Sorties dans `captures/` : `digest.txt/.html`,
`mise-en-vente.txt/.html`, `rendu.json`.

### 1. Bug trouvé — le mail de mise en vente affichait son SUJET à la place de son corps

`emails.mise_en_vente_email` faisait `txt, _ = annonce_email(...)`. Or `annonce_email` retourne
`(sujet, corps)` : `txt` récupérait donc le **sujet recopié**, et le corps était jeté. Le vrai envoi
(`digests.py:416` lit ce `txt`) partait donc avec un corps réduit à une ligne. Le HTML, lui, était bon —
c'est le rendu texte (repli `multipart/alternative`) qui était cassé, invisible sans le jouer pour de vrai.

Correctif (une ligne) : `_, txt = annonce_email(...)`. La capture `mise-en-vente.txt` porte désormais le
corps complet (« Bonjour, … Une annonce vient de paraître sur une parcelle que vous suivez : CY0018 —
Maison à Saint-Paul, 350 000 €. » + lien).

### 2. Ordre de la grille dans le digest (`_digest_data`, `events.py`)

`ORDER BY` explicite : **parcelle suivie d'abord** (la mutation en tête), puis Radar dans l'ordre
**nouvelle → baisse → retrait**. Un ordre stable et lisible, plutôt qu'un tri par timestamp qui mélangeait
les lignes. Vérifié : `rendu.json → digest_ordre = [parcelle_suivie, radar, radar, radar_baisse, radar_retrait]`.

### 3. Le digest ne parle plus de « secteurs »

Les secteurs sont archivés depuis VEILLE-2 (Lot 4). L'intro (« vos parcelles suivies **et vos critères** »)
et le pied (« vous suivez des parcelles ou surveillez des **critères Radar** ») ne les mentionnent plus.

### Garde-fous (`tests/test_veille_fix2_lot_e.py`)

- `test_mise_en_vente_mail_porte_son_corps_pas_son_sujet` — le corps ≠ le sujet, contient la phrase
  d'annonce, le lieu, le prix, le lien ; commence par « Bonjour » (garde de régression du bug ci-dessus).
- `test_digest_ne_parle_plus_de_secteurs` — « secteur » absent du corps.
- `test_grille_digest_ordre_stable` — parcelle suivie en tête, Radar nouvelle < baisse < retrait
  (base de test ; la parcelle suivie est posée directement car `labuse_test` n'a pas les mutations DVF).

### Vérifications

```
pytest tests/test_veille_fix2_lot_{a,b,c,d,e}.py tests/test_pige_digests.py → 24 passed
```

Compte `[VF2-E]` restant en base app : 0 · `mail_queue` orphelins : 0.
