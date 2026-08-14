# AUDIT M73-G — Direction artistique des 5 documents (Phase 1, mesure)

**Branche `feat/m73g-da-documents`. Aucune écriture. Mesuré le 14/08/2026.**
Maquettes de référence : `docs/DA-LABUSE.html`, `DA-PDF-v2.html`, `DA-DOSSIER-v1.html`, `DA-BANQUIER-v1.html`.

## Verdict global
Alignement de fond **correct** (palette d'impression, cartouches, `.lg`, `.e.*`, en-têtes). Le vrai
trou du Volet A est UNIQUE et partagé : **les blocs ANC + réhabilitation (M73-C/D) sont posés en HTML
mais NON STYLÉS** dans les 4 documents WeasyPrint. Le reste = 3 écarts ciblés.

## ÉCART CENTRAL — les blocs `.bloc-*` sont nus (C1)
`blocs_documents.py` produit `<div class="bloc bloc-anc"><div class="bloc-tete"><span class="bloc-titre">…
</span><span class="bloc-etat">…</span></div><p class="bloc-libelle/maille/phrase">…</p></div>`.
**Aucun CSS** ne stylise `.bloc / .bloc-tete / .bloc-titre / .bloc-etat / .bloc-libelle / .bloc-maille /
.bloc-phrase` :
- `flash/templates/rapport.css` : 0 règle `.bloc*` (grep vide).
- `api/briques_pdf.py` PAGE_CSS (banquier + argumentaire) : 0 règle `.bloc*`.
- `api/export.py` one-pager `<style>` : le one-pager rend l'ANC en `kv` (pas `.bloc`), réhab idem — pas
  d'habillage `.bloc` non plus.
→ Les blocs Assainissement/Réhabilitation s'affichent en **texte brut** (pas de fond `--carte-fond`,
pas de filet, pas de pastille d'état). **C'est l'objet principal du Volet A.** L'habillage cible
(maquette `.carte`/`.chef`/`.past`/`.lg`/`.e.*`) : fond `#F3F6F4`, rayon 9px, titre 13.5px, état mono
avec couleur sémantique (`.e.ok`=`#1B5E3C`, `.e.att`=`#8A6414`, `.e.abs` italique gris).
Le premium (fpdf) dessine déjà ces blocs en primitives (M73-D) mais **sans le cartouche** (pas de fond
`--carte-fond` ni de pastille) — habillage fpdf à ajouter aussi.

## ÉCART 2 — vert print du premium hors canon (C2)
`pdf_premium.py:25` `MINT = (11, 138, 95)` = **#0B8A5F**. Le canon print (mandat + les 4 weasyprint via
`rapport.css`/`briques_pdf`) = **#1E9E58** (30, 158, 88). Le premium doit s'aligner sur `#1E9E58`.

## ÉCART 3 — badges de tier du one-pager hors palette (C3)
`export.py:657-658` : `.v-chaude` = **#c2913f** (vs ambre DA `#8A6414`), `.v-reserve_fonciere` = `#4a7ba6`
(bleu hors palette print), `.v-ecartee` = `#697079`, `.v-brulante` = `#b8574a` (vs rouge `#A33A2A`). Trait
en-tête `#c9a86a` + `.action` `#faf6ec`/`#c9a86a` (beige hors palette). À réaligner sur la palette DA.

## ÉCART 4 — texte sous 8 pt (C4) — Phase 3 l'interdit
- `rapport.css` footer `@bottom-center` : **6.5 pt**.
- `briques_pdf` PAGE_CSS footer : **6 pt** ; `th` : 6.8 pt.
- `pdf_premium.py` labels/sources : **6.3–6.6 pt** (lignes ~234, 259, 275, 330) ; **le rappel de méthode
  des comparables + l'attribution du plan que j'ai posés en M73-E/F sont à ~6.5 pt** → Phase 2.4 : « une
  réserve qu'on doit deviner est une réserve absente » → à remonter (≥ 8 pt pour les réserves/méthode ;
  les sources techniques secondaires peuvent rester plus petites mais ≥ 7 pt de préférence).

## ÉCART 5 — mise en page (connu M73-F)
Titre « Plan de situation » (premium) s'orpheline en bas de page (image page suivante). Généraliser la
gestion veuves/orphelines des titres de bloc (premium fpdf : test `get_y()` avant titre ; weasyprint :
`break-inside: avoid` / `break-after: avoid` sur titres+blocs).

## Ce que l'audit N'a PAS trouvé (bon)
- Aucun **mauve/iris** hors IA dans les documents.
- Aucun **#F5C518** (Pages Jaunes) dans les documents.
- En-têtes noir `#0A0C0B` + filet mint 2px, cartouches 4 chiffres, `.lg`/`.e.*` : conformes.

## Récapitulatif par document
| Doc | Blocs `.bloc-*` | Vert print | Palette | <8pt | Verdict |
|---|---|---|---|---|---|
| **Premium (fpdf)** | dessinés sans cartouche | **#0B8A5F ≠ #1E9E58** | OK | 6.3-6.6pt | habillage cartouche + MINT + tailles + orphelin plan |
| **Dossier** | **NUS** | #1E9E58 ✓ | OK | footer 6.5pt | habillage `.bloc` + footer |
| **Banquier** | **NUS** | #1E9E58 ✓ | OK (+rouge-voile) | footer 6pt, th 6.8pt | habillage `.bloc` + tailles |
| **Argumentaire** | **NUS** | #1E9E58 ✓ | OK | footer 6pt | habillage `.bloc` |
| **One-pager** | ANC/réhab en `kv` | n/a (web) | **badges hors palette** | web OK | badges palette + `.bloc` si migré |

## Décision demandée à Vic (STOP — ordre de traitement)
Le gros du Volet A (C1) est **partagé** : un même habillage `.bloc-*` sert dossier + banquier +
argumentaire (via un snippet CSS commun injecté dans les 2 points CSS : `rapport.css` et
`briques_pdf.PAGE_CSS`), + le pendant fpdf pour le premium. Deux façons de séquencer :
1. **Transversal d'abord** (reco) : (a) habillage `.bloc-*` partagé sur les 4 weasyprint + premium fpdf ;
   (b) premium MINT→#1E9E58 + tailles <8pt + orphelin plan ; (c) one-pager badges palette. Un commit par
   étape, chacun recettable. Efficace car C1 est mutualisé.
2. **Un document à fond** : si tu juges qu'un seul document mérite l'effort complet (le premium = le
   document vendu ? le banquier = celui tendu au financeur ?), je le traite intégralement d'abord.
