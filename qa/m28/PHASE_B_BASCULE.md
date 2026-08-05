# M28 — PHASE B : BASCULE SERVIE — POINT D'ARRÊT 2 (05/08/2026)

## Séquence exécutée (GO ferme Vic, arbitrages V1/V2/V3 inclus)
1. **6 gardes** passées (disque, péremption, sauvegardes, anti-écrasement post-rename,
   complétude, golden régénéré dans le geste). Archive : `q_v8_calibre_pre_m28`
   (RENOMMAGE — rien détruit ; le journal antérieur, CY0104 incluse, suit l'archive).
2. **Bascule** : re-score sous label (264 s), rebuild=False (features inchangées),
   ordre A7 (filtre AVANT départage). **Conformité STRICTE q_v12_m28 : 0 écart** avant registre.
3. **Registre** (served_run_exceptions du run servi — 4 entrées) :
   - **AK1442 (V1)** : brûlante → **a_creuser** — piscine centrale (FLAIR, 88 m², PVA 2025) ;
     seul OVERRIDE.
   - AP0323 (V2), HE0234 (V3-c, dette #12 ouverte), AT0870 (A9) : **documentaires**
     (tier inchangé, motifs tracés avec millésimes).
4. **Recompte post-bascule vs mesure phase A : écart unique = AK1442** (vérifié requête,
   collé ci-dessous). Tout autre écart aurait déclenché le rollback.

## Tiers servis
**119 brûlantes · 1 033 chaudes** · 29 872 declasse_bati_sature (motivées) · 4 010
declasse_bati_revele · 29 767 a_creuser · réserve 2 917 · le reste inchangé.

## Golden — incident corrigé dans le geste (transparence)
La 1ʳᵉ régénération a gelé des fiches en erreur : `import os` MANQUAIT dans app.py → le
gate des badges (`LABUSE_M28_BADGES`) faisait des HTTP 500 (33 incohérences détectées par
le golden — il a fait son travail). Fix (1 ligne), re-régénération :
**117/117 PASS (CY0104 réintégrée via la règle), 0 incohérence base↔API.**

## Exploitation
MVT rebuildées (tier_v2 embarqué, `declasse_bati_sature` inclus). **L'API de prod doit être
servie avec `LABUSE_M28_BADGES=1`** (badges filtre bâti + géométrie sur les fiches). CY0104 :
l'ancienne exception suit l'archive ; la règle la classe.

## Dette ouverte
**#12 — couche voirie surfacique absente** (nature « délaissé » non mesurable, cas HE0234) —
au BACKLOG.
écarts vs q_v12 : 97422000AK1442 (brulante→a_creuser)
