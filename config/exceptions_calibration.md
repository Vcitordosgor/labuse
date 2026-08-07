# Registre des exceptions de calibration PLU (famille AK1442)

Corrections de calibration **CONSTATÉES et MESURÉES mais DIFFÉRÉES** (impact marginal ne justifiant
pas une bascule immédiate), à reprendre à la prochaine recalibration de la commune concernée. Chaque
entrée porte : la règle du document, ce que le servi applique, l'écart mesuré, les IDU concernés, et
la raison du report. **Rien ici n'est servi** — c'est une mémoire de dette calibratoire.

---

## AK1442-01 · Saint-Benoît (97410) · AUb2 « Bourbier les Hauts » — recul voirie 10 m
- **Document (opposable 2020)** : fiche annexe du règlement **N°02**, zone AUb Bourbier les Hauts —
  « Recul minimum obligatoire des constructions : **10 mètres** à compter de l'emprise de la voie »
  (`97410_reglement_20200206.pdf`, p.PDF 55).
- **Servi aujourd'hui** : recul voirie **5 m** (défaut moteur `engine.recul_voirie_defaut_m`, zone non
  calibrée — `plu_saint_benoit.yaml` `zones:{}`, dé-calibration hauteurs arbitrage Vic 28/07/2026).
- **Écart** : sous-recul de **5 m** sur la seule zone AUb2 (les 17 autres fiches AU sont à 3 m < 5 m,
  donc conservatrices). Impact mesuré (inset géométrique 5 m→10 m) : **perte d'emprise 27–57 %** →
  SDP réduite >10 % **si** appliqué.
- **Parcelles concernées : 4, TOUTES `reserve_fonciere`** (potentiel long terme, tier le plus froid) :

  | IDU | perte d'emprise 5→10 m | tier servi |
  |---|---|---|
  | `97410000AE0025` | 32 % | reserve_fonciere |
  | `97410000AE0027` | 28 % | reserve_fonciere |
  | `97410000AE0250` | 27 % | reserve_fonciere |
  | `97410000AE0251` | 57 % | reserve_fonciere |

- **Décision (Vic, clôture M51)** : **AUCUNE entrée `zones:{AUb2}`** — une zone calibrée repasserait
  `resolve_zone(AUb2)` en `calibree=True` et changerait le chemin `au_statut` (effet de bord
  disproportionné pour 4 parcelles réserve). **Correction DIFFÉRÉE** à la prochaine calibration
  Saint-Benoît — qui sera de toute façon rouverte par les **modifications n°2/n°3** (à confirmer en
  mairie, hors GPU, cf. incertitude M40). À ce moment : porter le recul voirie 10 m sur AUb2.
- **Origine** : M51-P2 (mesures), `qa/m51/M51_P2_SAINT_BENOIT.md`.
