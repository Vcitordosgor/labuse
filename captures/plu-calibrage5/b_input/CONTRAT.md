# Contrat — relire et trancher les règles PLU « propose » (famille B) d'UNE commune

Tu relis les règles d'urbanisme d'une commune pour trancher des règles laissées `propose` (un
pas automatique était incertain). Travaille SÉQUENTIELLEMENT. N'invoque PAS de sous-agent, de fork,
ni l'outil Task/Agent. Tâche de précision, ZÉRO invention.

## Entrée
Lis `/Users/openclaw/Desktop/labuse/captures/plu-calibrage5/b_input/<INSEE>.json` : `commune`,
`pdf` (fichier sous `data/plu_reglements/`), `rules[]` avec zone, chemin (rubrique.feuille),
valeur_actuelle, article, page_pdf, citation, raison.

## Clé de valeur par rubrique
- emprise_sol.ces → `pct` (CES, % emprise au sol)
- hauteur.faitage / hauteur.egout → `m` (mètres) ; hauteur.niveaux → `r_plus`
- retraits.voie / retraits.limites_separatives → `min_m` (mètres) OU une formule
- pleine_terre.pct → `pct` (%) ; stationnement.par_logement → `places`

## Décision par règle (une seule)
- **valider** : la citation soutient EXPLICITEMENT `valeur_actuelle` pour CETTE zone (ex. citation
  « 70% en zone AUa » et la règle est AUa pct=70). On garde.
- **corriger** : la citation donne pour cette zone une valeur DIFFÉRENTE de valeur_actuelle → on
  pose la bonne. L'ancienne valeur était fausse.
- **absent** : le texte prouve qu'il n'y a PAS de règle pour cette zone (« non réglementé », « il
  n'est pas fixé de règle ») → on marque absent.
- **formule** : la règle est une FORMULE, pas un nombre unique (recul « H/2 min 3 m », « sur limite
  OU recul ≥ … ») → on laisse pour un traitement séparé.
- **propose** : même après la citation ET la page PDF, la valeur reste indéterminable → reste
  propose ; donne la raison.

## Lire le PDF (seulement si la citation est insuffisante pour une règle)
```
cd /Users/openclaw/Desktop/labuse && PYTHONPATH=src .venv/bin/python -c "import pypdf; r=pypdf.PdfReader('data/plu_reglements/<PDF>'); print(r.pages[<PAGE-1>].extract_text())"
```
Essaie page_pdf puis ±3 pages autour. page_pdf est en base 1.

## Règles dures
- JAMAIS inventer une valeur. Chaque `valider`/`corriger` DOIT citer dans `preuve` la sous-chaîne
  EXACTE (de la citation ou de la page PDF) qui contient la valeur pour CETTE zone. Le nombre
  décidé DOIT apparaître littéralement dans `preuve`.
- Rattache la valeur à la ZONE et à la FEUILLE (égout ≠ faîtage ; chaque zone peut avoir son %).
- Une citation qui liste plusieurs zones → prends la valeur de la zone de CETTE règle.
- Si tu ouvres le PDF, indique dans `note` « lu PDF p.N ».

## Sortie
Écris `/Users/openclaw/Desktop/labuse/captures/plu-calibrage5/b_decisions/<INSEE>.json` (crée le
dossier b_decisions si besoin) :
```
{ "insee": "<INSEE>",
  "decisions": [
    { "zone": "...", "chemin": "...", "geste": "valider|corriger|absent|formule|propose",
      "valeur": { "<clé>": <nombre> },   // valeur CONFIRMÉE (valider = valeur_actuelle ; corriger = corrigée ; omets pour absent/formule/propose)
      "preuve": "sous-chaîne exacte prouvant la valeur pour cette zone",
      "note": "courte justification (+ « lu PDF p.N » si PDF)" }
  ] }
```
Traite TOUTES les règles du fichier (une décision par règle). Termine par UNE ligne : comptes par
geste + toute règle non résolue. Rien d'autre.
