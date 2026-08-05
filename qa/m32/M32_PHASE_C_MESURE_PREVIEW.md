# M32 — PHASE C : intégration + mesure à blanc (PREVIEW) — vers le point d'arrêt

GO Vic reçu. Périmètre gravé. Phase C est gatée : intégration + mesure → **point d'arrêt (deck)** →
bascule **seulement après GO sur la mesure**. Ce document = l'intégration + la mesure PREVIEW.

## 1. Intégration au moteur (fait) — `config/calibrage/au_ouverture_planchers.yaml`

**21 communes** (4 existantes + 17 intégrées M32). Validé : toutes ouvertures ∈ {fermee,
conditionnelle_operation, conditionnelle_etat_tiers} ; planchers (min_log+densité) sur les **3**
communes à min_log uniforme : Saint-Leu (10/30-15), Les Trois-Bassins (5/35-20), **L'Étang-Salé
(10/50-30-15, nouveau)**. Toutes les autres = densité seule / per-site / scan négatif → **pas de
plancher** (jamais approximé). HORS intégration : Saint-André (opposabilité en attente), Saint-Benoît
(19 fiches graphiques → v2), Saint-Philippe (RNU).

**Sûreté** : le servi lit le CACHE `parcel_au_statut`, pas le YAML en direct → **golden 117/117, 0
incohérence** avec le nouveau YAML. Rien de servi ne bouge tant que le cache n'est pas reconstruit
(= la bascule). L'intégration est donc mesurable avant tout serve.

## 2. Mesure à blanc — PREVIEW du déclassement direct (sans re-scoring)

Classification `classify()` du nouveau YAML appliquée aux **190 parcelles en TÊTE servie** (brûlante/
chaude) des zones AU des communes intégrées :

| Effet | n | Détail |
|---|---|---|
| **declasse_au_fermee** | **0** | aucune tête en zone fermée (les fermées ne portaient pas de tête) |
| **declasse_au_statut_inconnu** (phasage 2AU) | **10** | Saint-Louis 9 (2AUst), Sainte-Suzanne 1 (2AU) — QUITTENT la tête |
| **au_sous_plancher** (SERVIE + mention) | 21 | L'Étang-Salé 14 (nouveau), Saint-Leu 6 + Trois-Bassins 1 (déjà servis) |
| inchangé (conditionnelle, servie) | 159 | — |

**Mouvement net direct** : **10 parcelles déclassées** (phasage 2AU), **14 nouvelles au_sous_plancher**
servies avec mention « terrain sous le plancher » (L'Étang-Salé). Impact **modeste et localisé** — le
gros des communes intégrées est en densité-seule (conditionnelle, servie inchangée).

## 3. Ce que la PREVIEW ne couvre PAS (→ mesure complète, étape suivante)

La preview = déclassement DIRECT. La **mesure complète** (re-scoring dans les tables `dryrun_*`,
label de mesure) est nécessaire pour :
- le **départage** recalculé et le **backfill** (les 10 têtes déclassées libèrent des places → des
  chaudes remontent) ;
- le **recalcul SDP des 5 132 bâties révélées** (la mention « terrain nu théorique » tombe) ;
- les **3 Salazie hors-PLU** → outillées par la calibration Salazie ;
- les **compteurs globaux avant/après** (brûlantes/chaudes/tiers), le **top 100**, le **deck des 20**.

## 4. Statut & prochaine étape

- **FAIT (sûr, servi inchangé)** : intégration 21 communes validée + golden 117/117 + preview mesure.
- **À FAIRE (mesure complète, compute lourd)** : re-scoring `dryrun_*` (label mesure) + SDP bâties
  révélées + Salazie + compteurs/top100/deck → **POINT D'ARRÊT (revue Vic du deck)**.
- **PUIS (sur GO mesure)** : bascule gardée (6 gardes + check_fraicheur), golden régénéré, archive
  `_pre_m32`, recompte vs mesure (écart non listé = rollback).

L'intégration est posée et sûre ; la mesure complète est le compute lourd qui produit le deck de
revue. Aucune bascule sans GO sur la mesure.
