# Contrat — encoder les FORMULES de recul (famille A) d'UNE commune

Tu traites des règles de RECUL laissées `propose` parce que la valeur est une FORMULE, pas un
nombre fixe. But : encoder la formule proprement quand le texte la porte, sinon laisser `propose`.
Travaille SÉQUENTIELLEMENT. N'invoque PAS de sous-agent/fork/Task. ZÉRO invention.

## Entrée
Lis `/Users/openclaw/Desktop/labuse/captures/plu-calibrage5/a_input/<INSEE>.json` : `pdf`,
`rules[]` avec zone, chemin (retraits.voie ou retraits.limites_separatives), citation, article,
page_pdf, note_lot2 (indice éventuel).

## Décision par règle
- **valider** : la citation décrit un recul RELATIF À LA HAUTEUR avec un MINIMUM chiffré — p.ex.
  « distance au moins égale à la moitié de la hauteur (H/2), sans être inférieure à 3 m », ou
  « L ≥ H/2 avec un minimum de 4 m », OU une implantation conditionnelle « sur limite OU en retrait
  d'au moins N m ». Tu poses :
    `valeur`: { "min_m": <N>, "formule": "<relation VERBATIM courte, ex. 'H/2, minimum 3 m'>" }
  où **N (le minimum) apparaît LITTÉRALEMENT dans la citation**. `preuve` = la sous-chaîne exacte
  contenant N.
- **propose** : pas de minimum chiffré dans le texte, ou ce n'est pas une formule de hauteur
  (renvoi, « à l'alignement » seul, texte absent) → reste propose ; donne la raison courte.

## Lire le PDF (si la citation ne suffit pas) — page_pdf est en base 1
```
cd /Users/openclaw/Desktop/labuse && PYTHONPATH=src .venv/bin/python -c "import pypdf; r=pypdf.PdfReader('data/plu_reglements/<PDF>'); print(r.pages[<PAGE-1>].extract_text())"
```

## Règles dures
- Le `min_m` DOIT figurer LITTÉRALEMENT dans `preuve` (sinon la décision sera refusée).
- N'invente jamais un minimum. Si le texte ne chiffre pas de plancher, c'est `propose`.
- `formule` = la relation telle qu'écrite (courte), pour la trace ; c'est `min_m` qui borne le calcul.

## Sortie
Écris `/Users/openclaw/Desktop/labuse/captures/plu-calibrage5/a_decisions/<INSEE>.json` (crée le
dossier a_decisions) :
```
{ "insee": "<INSEE>",
  "decisions": [
    { "zone":"...", "chemin":"...", "geste":"valider|propose",
      "valeur": { "min_m": <N>, "formule": "..." },   // pour valider ; omets pour propose
      "preuve":"sous-chaîne exacte contenant N", "note":"court (+ « lu PDF p.N » si PDF)" } ] }
```
Traite TOUTES les règles. Termine par UNE ligne : comptes par geste + non résolues. Rien d'autre.
