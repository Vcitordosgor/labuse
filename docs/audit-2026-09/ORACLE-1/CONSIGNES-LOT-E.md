# ORACLE-1 Lot E — consignes sous-agent « fiche écran + données servies vs Dossier PDF »

Demande de Vic : pour chaque parcelle, comparer **ligne à ligne** trois représentations du MÊME bien et lister les écarts de CONTENU (pas de mise en forme). Lecture seule, aucune écriture hors `docs/audit-2026-09/ORACLE-1/lot_e_parts/`.

## Les trois sources (déjà sur le disque, cwd = /Users/openclaw/Desktop/labuse-oracle)
Pour chaque SLOT/IDU de ta liste, dans `docs/audit-2026-09/ORACLE-1/dossiers/` :
1. **Données servies** = `{SLOT}_{IDU}.json` (la fiche API : 72 clés ; les 42 `lines` tracées ; le_bien, aleas, sols, dispositifs, dvf_parcelle, reglement_plu, viabilisation, territoire_fiscal, taxe_amenagement, proximites, etablissements, proprietaire_moral, iris_quartier…). `{SLOT}_{IDU}_enrichment.json` et `_zone.json` complètent.
2. **Écran** = `{SLOT}_{IDU}_ecran.txt` : le texte RÉELLEMENT affiché dans le panneau fiche du front (tiroir par tiroir, marqueurs `### tiroir ouvert : …`). C'est ce que l'utilisateur voit.
3. **Dossier PDF** = `{SLOT}_{IDU}.txt` : le texte du PDF exporté (pdftotext -layout).

## Ce qu'on veut
Un tableau par parcelle qui répond à deux questions :
- **Présent à l'écran, ABSENT du PDF** : une information/ligne que l'utilisateur voit dans la fiche mais qui ne figure pas dans le Dossier qu'il transmet (banque, comité, vendeur).
- **Présent dans le PDF, ABSENT de l'écran** : une information imprimée dans le Dossier mais que l'utilisateur ne voit pas dans la fiche interactive (y compris chiffres recalculés pour le PDF, mentions légales propres au PDF).

Compare le CONTENU, pas l'habillage. Ignore : logos, pagination, puces, ordre, reformulations identiques en sens, et le chrome de l'app (menus « Carte / Outils / Copilote / Radar / Projets / CRM / Admin / Sources », « COUCHES / FILTRES », bandeau d'accueil) qui n'est pas la fiche. Concentre-toi sur les BLOCS MÉTIER : identité/propriétaire, terrain, bâti, urbanisme/PLU, risques/environnement, réseaux, fiscalité/dispositifs, marché/DVF, quartier, potentiel/faisabilité.

Quand une donnée est servie dans le JSON mais n'apparaît NI à l'écran NI dans le PDF, note-le aussi (colonne « servi mais nulle part ») — c'est le cas le plus intéressant pour Vic.

## Sortie
Un fichier Markdown par parcelle : `docs/audit-2026-09/ORACLE-1/lot_e_parts/{SLOT}.md`, avec CE format exact :

```
## {SLOT} — {IDU} ({commune})

**Présent à l'écran, absent du PDF**

| bloc | ligne / donnée (écran) | servie dans le JSON ? |
|---|---|---|
| Risques | « Parcelle au contact de la bande des 50 pas… » | oui (lines.cinquante_pas) |
| … | … | … |

**Présent dans le PDF, absent de l'écran**

| bloc | ligne / donnée (PDF) | servie dans le JSON ? |
|---|---|---|
| Marché | « 10 ventes à moins de 500 m » (recalcul propre au PDF) | dérivé (prix_ancien) |
| … | … | … |

**Servi dans le JSON mais ni à l'écran ni dans le PDF** (si pertinent)

| bloc | donnée (clé JSON) | valeur |
|---|---|---|
| … | … | … |

**Synthèse (2-3 phrases)** : ce qu'un promoteur perd en ne lisant que le PDF, ou l'inverse.
```

Si une section est vide, écris « *(aucun écart constaté)* ». Garde les tableaux courts et significatifs (regroupe les lignes de même nature ; ne recopie pas les 400 lignes de l'écran). Vise l'exhaustivité sur les BLOCS, pas sur chaque micro-ligne.

## Rendu final (dernier message)
JSON compact : `{"slot":"SXX","ecran_sans_pdf":N,"pdf_sans_ecran":N,"servi_nulle_part":N,"faits_saillants":["…1 ligne…"]}`
