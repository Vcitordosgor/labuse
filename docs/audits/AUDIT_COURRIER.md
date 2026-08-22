# Audit — outil « Courrier propriétaire » (M09). CONSTAT SEUL, aucune correction.

Générateur `POST /modules/courriers` (`src/labuse/api/modules.py:692`) · PDF `POST /courrier/pdf`
(`src/labuse/api/courrier.py:70`) · logique envoi `src/labuse/courrier.py` · front M09
`frontend/src/components/outils/ModulePanel.tsx:663`.

## VERDICT EN UNE LIGNE
Outil PROPRE côté données (gabarit, aucun propriétaire nommé, aucun chiffre inventé, aucun
vestige, ne touche NI `_q_v2_fiche` NI `_build_fiche`) — **MAIS le bouton PDF est CASSÉ** : il
lève une `FPDFException` sur TOUT courrier (les lignes vides entre paragraphes), et le front
**avale l'erreur en silence** → « Télécharger le PDF » ne fait rien. 3ᵉ PDF cassé de la semaine
(après M136 q_score et la page /p).

---

## 1. Branchement et données

- **Tables lues** : `parcels` SEULEMENT (`modules.py:698` : `idu, commune, section, numero,
  round(surface_m2)`). Rien d'autre. **Pas de scoping run** — et pour cause : le courrier n'utilise
  NI tier, NI score, NI cascade. La question « scopé q_v10_m129 ? » est **sans objet** (aucune
  donnée de run lue). Pas de fiche, donc **ni `_q_v2_fiche` ni `_build_fiche`** — le défaut du
  comparateur ne s'applique pas ici (rien à dégrader, aucun tier n'est servi).
- **Données propriétaire** : **AUCUNE**. Pas de DGFiP PM, pas d'INPI, pas de DINUM. Le courrier
  s'adresse à « **Madame, Monsieur** » (générique). `rappel_identite` (`modules.py:707`) : « aucune
  donnée nominative automatisée » ; l'envoi (`courrier.py:102`) utilise l'adresse BAN, jamais un nom
  de personne physique (« À l'occupant »). **Aucun particulier n'est nommé → anonymisé.**
- **Vestiges de matrice** : **NÉANT** (q_score/a_score/opportunity/completeness/matrice absents — la
  requête ne lit que `parcels`).
- **LIMIT caché** : `body.idus[:100]` (`modules.py:697`) — cap **100 courriers par appel**,
  SILENCIEUX (l'écran ne le dit pas ; en pratique le front n'envoie qu'un IDU à la fois). Côté
  envoi : `max_length=500` destinataires + plafond `courrier_max_jour`. PDF : `texte` ≤ 8000 car.
- **Test « ne lève pas »** : **PARTIEL et à côté du bug**. `tests/test_courrier.py` couvre l'ENVOI
  (`/courrier/statut`, `/courrier/envois`, plafond, responsabilité). **Aucun test** de
  `/modules/courriers` (le générateur) ni de `/courrier/pdf` (le bouton) → le crash PDF est passé
  inaperçu.

## 2. Le contenu du courrier

- **Gabarit, PAS d'IA** (`modules.py:668` `_COURRIER`) : 3 modèles statiques (standard / indivision
  / succession), placeholders `{ref}` `{commune}` `{surface}` `{signature}`. Donc **aucun coût de
  génération, aucun risque d'invention** — texte déterministe.
- **Vocabulaire M135/M137** : **sans objet** — le texte ne cite AUCUN tier, classement, fraction ni
  jargon interne. Rien ne fuit (« un réel potentiel » = qualitatif, jamais « brûlante »/« rang »/etc.).
- **Chiffres LABUSE** : uniquement des **faits cadastraux** — `{surface}` (= `parcels.surface_m2`
  arrondie, exacte), `{ref}` (section+numéro), `{commune}`. **Aucun** score / proba / charge foncière
  / capacité. Sourcés et exacts (cadastre). Rien de calculé par LABUSE dans le texte.
- **RGPD** : le courrier n'est **pas nominatif** (générique + adresse BAN « à l'occupant ») → pas de
  traitement de donnée nominative de particulier par l'outil. L'écran le DIT (bandeau M09) :
  « Adressage générique : aucune identité de propriétaire particulier (workflow SPF/CERFA) ». C'est
  le CLIENT qui envoie (LABUSE n'envoie rien : provider stub). Base légale d'un envoi nominatif : non
  applicable ici puisque rien de nominatif n'est produit — l'écran cadre correctement.

## 3. Ergonomie

- **Ouverture** : (1) **fiche** (tuile « Courrier ») ; (2) **Outils → M09**. Assistant en 4 étapes
  (Parcelle › Motif › Rédaction › Courrier). Parcelle par **3 entrées** : IDU saisi, adresse
  (autocomplétion BAN), clic carte. **Pas** d'entrée « depuis un projet / une liste ».
- **Éditable avant téléchargement** : **OUI** — étape 3 « Rédaction » = `<textarea
  data-courrier-texte>` liée à `texte` (`ModulePanel`), modifiable ; l'étape 4 génère le PDF à
  partir du texte (éventuellement édité).
- **Modèles** : **3** (standard / indivision / succession).

## 4. Le bouton PDF — CASSÉ (testé pour de vrai)

**Le PDF NE se télécharge PAS.** `POST /courrier/pdf` lève :
`fpdf.errors.FPDFException: Not enough horizontal space to render a single character`
(fpdf2 **2.8.7**), reproduit sur un courrier standard réel (parcelle 97415000DK1044).

**Cause racine isolée** (`courrier.py:83-85`) :
```python
for ligne in body.texte.split("\n"):
    pdf.multi_cell(0, 6, safe)     # w=0
```
Un `multi_cell(w=0, "")` sur une **ligne vide** (les `\n\n` entre paragraphes) laisse le curseur x
à la marge DROITE → le `multi_cell(w=0, …)` SUIVANT n'a plus de largeur → exception. Isolé :
- `["Madame, Monsieur,"]` seul, w=0 → **OK**
- `["", "Madame, Monsieur,"]` w=0 → **CRASH** (le motif exact du gabarit : ligne vide puis texte)
- `["", "Madame, Monsieur,"]` avec largeur explicite w=170 → **OK**
Tous les modèles contiennent des lignes vides → **100 % des courriers plantent au PDF.**

**Le front AVALE l'erreur** : `courrierPdf` (`api.ts:643`) `throw` sur 500 ; `telecharger`
(`ModulePanel:682`) `catch { /* ignore */ }` → le bouton « ⬇ Télécharger le courrier (PDF) »
tourne « Génération… » puis **rien** : aucun fichier, aucun message. Défaut **visible client**
(silencieux).

**Contenu du PDF vs affiché** : impossible à comparer — le PDF n'est jamais produit. (Le
générateur de TEXTE, lui, fonctionne : le gabarit se remplit correctement — vérifié.)

---

## Synthèse pour l'arbitrage
| # | point | constat |
|---|-------|---------|
| 1 | données | PROPRE : `parcels` seul, aucun propriétaire nommé, 0 vestige, ni _q_v2_fiche ni _build_fiche |
| 1 | LIMIT | `idus[:100]` silencieux (sans impact pratique : 1 IDU à la fois) |
| 1 | test | envoi testé ; **générateur + PDF non testés** |
| 2 | contenu | gabarit (pas d'IA), 0 chiffre calculé, 0 tier/jargon, RGPD cadré à l'écran |
| 3 | ergonomie | ouverture fiche+Outils (pas projet) · **éditable** · **3 modèles** |
| 4 | **PDF** | **CASSÉ** — `FPDFException` sur ligne vide + `multi_cell(w=0)`, avalé en silence par le front. 3ᵉ PDF cassé de la semaine. |

Le seul défaut réel est le **bouton PDF** (§4), reproductible et client-visible. Correction
probable (à trancher) : largeur explicite dans `multi_cell` (ou `ln()` pour les lignes vides) dans
`courrier.py`, + un test `/courrier/pdf` « ne lève pas » sur un courrier réel.
