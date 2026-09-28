# PLU-EXCEPTIONS-1 — protocole d'extraction VERBATIM des exceptions

Pour UNE commune, tu extrais le **texte exact** (verbatim, jamais reformulé) de chaque
exception que PLU-VERIF-1 a repérée (verdict « JUSTE + exception »), depuis le PDF du
règlement servi, et tu la classes.

## Étapes
1. Tes cas :
   ```
   ~/Desktop/labuse/.venv/bin/python -c "import json;d=json.load(open('/Users/openclaw/Desktop/labuse-pluverif/docs/audit-2026-09/PLU-EXCEPTIONS-1/verbatim_worklist.json'));print(json.dumps(d['<INSEE>'],ensure_ascii=False,indent=1))"
   ```
   (`exception_resume` = le résumé écrit en Lot B ; il t'indique QUELLE exception chercher,
   mais il ne doit PAS être recopié — on veut le texte exact du PDF.)
2. Lis la page citée (±2) :
   ```
   ~/Desktop/labuse/.venv/bin/python /Users/openclaw/Desktop/labuse-pluverif/scripts/plu_verif/page_text.py <INSEE> <page> 2
   ```
3. Localise la phrase / clause du règlement qui PORTE l'exception (celle qui déroge à la
   valeur de la règle pour cette zone) et copie-la **mot pour mot** (accents, ponctuation,
   guillemets d'origine). Recolle proprement les coupures de ligne (retire les retours à la
   ligne parasites du PDF, sans changer les mots). Si l'exception tient en plusieurs phrases,
   garde la (les) phrase(s) porteuse(s) — ≤ 400 caractères. **AUCUNE paraphrase, AUCUN [...]
   au milieu d'une phrase** (une coupure entre deux clauses distinctes est tolérée avec « … »).

## Classer `porte` (à quoi l'exception s'applique) — un seul mot-clé :
- `sous_secteur` — un secteur/indice de la zone a une autre valeur (ex. Uc3 40 % vs Uc 60 %).
- `bande_limite` — règle dans une bande depuis une limite/voie (ex. 6 m dans les 3 m).
- `hauteur_alternative` — hauteur différente selon un cas (surélévation, mitoyenneté…).
- `majoration_conditionnelle` — la valeur peut augmenter sous condition (opération ≥ N m², RPA, commerce RDC).
- `voie_specifique` — recul particulier le long d'une RN/RD nommée.
- `destination` — dépend de la destination (habitat/activités/équipements).
- `operation_ensemble` — s'applique en opération d'aménagement d'ensemble.
- `exclusion_generique` — carve-out standard (ouvrages techniques, extensions de bâti non
  conforme, éléments protégés L.151-19, équipements d'intérêt collectif, saillies, piscines).
- `autre` — sinon (précise en clair dans `note`).

## Drapeau `modifie_calcul` (booléen)
`true` si l'exception CHANGERAIT l'enveloppe chiffrée d'une parcelle ORDINAIRE de la zone
(bande depuis limite, sous-secteur à valeur différente, majoration/minoration conditionnelle
de hauteur/emprise). `false` pour les carve-outs génériques (`exclusion_generique`) et les
cas qui ne touchent pas la capacité de base. Ces `true` seront listés « à part pour calibrage ».

## Sortie
Écris `docs/audit-2026-09/PLU-EXCEPTIONS-1/verbatim/<INSEE>.json` : une liste d'objets
```
{"zone","regle","valeur_regle","article","page_pdf","texte","porte","modifie_calcul","note"}
```
- `texte` = le VERBATIM (guillemets d'origine conservés s'il y en a).
- `article`/`page_pdf` = l'article et la page PDF où se lit l'exception (souvent = ceux de la
  règle ; corrige si l'exception est à un autre article/page).
- `note` = null sauf `porte:autre` (préciser) ou remarque utile.
Renvoie un résumé court : N cas, répartition `porte`, combien `modifie_calcul=true`, et
signale tout cas où tu n'as PAS trouvé de verbatim clair (→ `texte:null`, on le traitera à part).
