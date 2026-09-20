# Contrat — retrouver les citations NON RETROUVÉES (famille C) d'UNE commune

Ces règles sont `propose` parce que leur citation n'a pas été localisée dans le PDF. Tu relis le
PDF autour de la page indiquée (±5 pages) pour TROUVER la règle. Travaille SÉQUENTIELLEMENT. Pas de
sous-agent/fork/Task. ZÉRO invention.

## Entrée
Lis `/Users/openclaw/Desktop/labuse/captures/plu-calibrage5/c_input/<INSEE>.json` : `pdf`,
`rules[]` avec zone, chemin (rubrique.feuille), valeur_actuelle, article, page_pdf,
citation_actuelle, raison.

## Clé de valeur : emprise_sol.ces→pct · hauteur.faitage/egout→m · hauteur.niveaux→r_plus ·
## retraits.voie/limites_separatives→min_m · pleine_terre.pct→pct · stationnement.par_logement→places

## Lire le PDF (±5 pages autour de page_pdf ; base 1)
```
cd /Users/openclaw/Desktop/labuse && PYTHONPATH=src .venv/bin/python -c "import pypdf; r=pypdf.PdfReader('data/plu_reglements/<PDF>'); [print('==p',i+1,'==', r.pages[i].extract_text()) for i in range(<PAGE-6>, <PAGE+5>) if 0<=i<len(r.pages)]"
```

## Décision par règle
- **valider** : la règle est retrouvée et sa valeur = valeur_actuelle. `valeur` = {clé: <nombre>}.
- **corriger** : la règle est retrouvée mais la valeur diffère (ou valeur_actuelle vide). `valeur` = {clé: <nombre trouvé>}.
- **absent** : le texte de la zone/rubrique existe et dit « non réglementé » / « il n'est pas fixé de règle » → silence prouvé.
- **propose** : introuvable même après ±5 pages, ou ambigu → reste propose ; raison courte.

## Règles dures
- Pour valider/corriger, le NOMBRE décidé DOIT apparaître LITTÉRALEMENT dans `preuve` (sous-chaîne
  exacte du PDF). Pour absent, `preuve` = la phrase de SILENCE. Jamais d'invention.
- Rattache la valeur à la ZONE et à la FEUILLE (égout ≠ faîtage).

## Sortie
Écris `/Users/openclaw/Desktop/labuse/captures/plu-calibrage5/c_decisions/<INSEE>.json` (crée le
dossier c_decisions) :
```
{ "insee":"<INSEE>", "decisions":[
  { "zone":"...", "chemin":"...", "geste":"valider|corriger|absent|propose",
    "valeur":{"<clé>":<nombre>}, "preuve":"sous-chaîne exacte du PDF", "note":"court, + p.N lue" } ] }
```
Traite TOUTES les règles. Termine par UNE ligne : comptes par geste + non résolues.
