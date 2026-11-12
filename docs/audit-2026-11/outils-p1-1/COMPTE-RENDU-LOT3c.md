# OUTILS-P1-1 — Lot 3, recette des preuves

Étape 0 : `pwd`=labuse-outils, branche `fix/outils-p1-1`. L'arbre n'était pas « propre » — mais à cause de
l'extraction (toutes les captures committées supprimées dans l'arbre + `PREUVES/` ajouté). Les fichiers
suivis ont été restaurés (`git checkout HEAD -- docs/…`) ; `PREUVES/` (untracked) laissé tel quel.

Captures cropées sur l'élément : `lot3c-<NN>-<outil>-<quoi>.png`.

## À CORRIGER

| # | Point | État |
|---|-------|------|
| 1 | Scan : « 0 nus » pour CBO (0/833/1000) comme pour la SIDR (0/3366/822) | **Fait + rapport.** Sur toute la base, **`p_model_bati.emprise_bati_m2 = 0` n'arrive JAMAIS** (0 ligne sur 329 965 ; la table ne stocke que les parcelles bâties, emprise > 0). Le champ ne sait donc PAS dire « nu » → le « 0 nus » était un artefact. **Fix** : l'état bâti est lu comme la fiche (BD TOPO/CoSIA) via `p_model_frame` (l'ensemble évalué, 99,7 % des parcelles) : **bâti** = ligne `p_model_bati` · **nu** = dans la frame SANS bâti cartographié · **non renseigné** = hors frame. Résultat réel : **CBO = 994 nus · 833 bâtis · 6 non renseigné** ; SIDR = 745 · 3 366 · 77. (île : ~103 000 parcelles nues.) Plus aucun « 0 nus » faux. |
| 2 | Permis : « Permis dormants · sans achèvement déclaré (DAACT) » a perdu l'ancienneté | **Fait.** Seuil réel du code (`permis_point_mort` : `date < now() − 36 mois` + sans DAACT + parcelle non bâtie) écrit dans la définition : **« autorisés depuis plus de 3 ans, sans achèvement déclaré (DAACT) »**. |
| 3 | Permis : la définition passe sous le libellé, sur toute la largeur | **Fait.** Le bouton d'état est en deux lignes : pastille · nom · compte (1ʳᵉ ligne), définition pleine largeur (2ᵉ). Fini « sans / achèvement / déclaré / (DAACT) » coincé sur 4 lignes. |
| 4 | Successions : « du plus grand au plus petit » → « de la plus grande à la plus petite » | **Fait** (accord avec « SDP restante »). |
| 5 | Courrier : « au siège social déclaré » écrit deux fois ; « Saint-Denis » coupé au trait d'union | **Fait.** La mention n'est plus affichée quand elle est déjà dans le libellé du destinataire → « au siège social déclaré » une SEULE fois. Trait d'union INSÉCABLE (U+2011) sur les communes/adresses → « Saint‑Denis » ne se coupe jamais. |
| 6 | Scan : le nom du propriétaire coupé par « … » | **Fait.** `break-words` (plus de `truncate`) → « SOCIETE IMMOBILIERE DEPARTEMENT REUNION » passe sur plusieurs lignes, jamais tronqué. |
| 7 | Scan : « 12 / 210 affichées » → « affichés » (blocs) | **Fait** (`ListPaginationFooter` reçoit `uniteAccord="affichés"` ; défaut « affichées » ailleurs, inchangé). |

## PREUVES MANQUANTES

| # | Point | État |
|---|-------|------|
| 8 | Scan CBO : capture de la liste des blocs (ha + pied) avant / après un clic | **Fait.** `lot3c-08-scan-blocs-avant.png` (12 / 210 affichés · surfaces en ha · « Voir 198 de plus ») et `lot3c-08-scan-blocs-apres.png` (après clic : 210 blocs, pied disparu). Fichiers DISTINCTS (md5 différents) — le doublon de lot3b est corrigé. |
| 9 | Successions : capture de 97409000AY1281 avec « A 75 % · UE 25 % » | **Fait.** `lot3c-09-successions-ay1281.png` : la carte montre « 12 031 m² · Estimé · SDP restante · Saint‑André · 34 107 m² · A 75 % · UE 25 % · … · 76 ans ». |
| 10 | Assemblage et Taxe : captures + compte-rendu des retouches | **Fait ci-dessous.** |

### Point 10 — Assemblage / Taxe
- **Assemblage « ligne tronquée »** — **était cassé, corrigé** : la ligne par parcelle (`surface · bâti conservé X · reconstruction Y`) était coupée à droite (span unique sans retour). `items-baseline` + `min-w-0 break-words` → elle passe à la ligne. Capture `lot3c-10-assemblage-parcelles.png`.
- **Assemblage « 17 % hors zone »** — **déjà fait (lot 1)** : « dont N m² en zone constructible · X % hors zone » (ici 31 %). Capture `lot3c-10-assemblage-horszone.png` (avec les trois lectures Existant / Si conservé / Après démolition).
- **Assemblage « vocabulaire par parcelle »** — **déjà fait (lot 1)** : « bâti conservé non estimé » quand la SDP conservée manque (plus de recopie de la reconstruction). Même capture `…-parcelles.png`.
- **Taxe « i »** — **corrigé** : la DÉFINITION de la surface taxable (close + couverte > 1,80 m, garages inclus) vit en clair sous le champ (label + exemple garage) ; elle n'est plus RÉPÉTÉE dans le « i », qui garde la méthode + les sources (valeur forfaitaire, base légale, administration). Capture `lot3c-10-taxe-i.png`.

## Vérification
- tsc 0 · vitest **326** · secrets · DB patrimoine/permis/successions · pytest unitaires · cohérence 12 témoins.
- Backend : `patrimoine` lit `p_model_frame` (garde `to_regclass` : sur base partielle sans la frame, l'absence
  de bâti retombe en « non renseigné » — aucun 500). Prod : CBO 994/833/6, SIDR 745/3366/77.
