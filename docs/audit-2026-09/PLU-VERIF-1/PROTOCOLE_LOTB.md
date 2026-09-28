# PLU-VERIF-1 — Protocole Lot B (relecture PDF des cas AMBIGU / ABSENT)

Tu relis, pour UNE commune, les règles chiffrées du PLU que le vérificateur
automatique (Lot A) a classées AMBIGU ou ABSENT. But : trancher chaque cas en
lisant le PDF du règlement servi.

## Étapes
1. Récupère tes cas (remplace `<INSEE>`) :
   ```
   ~/Desktop/labuse/.venv/bin/python -c "import json;d=json.load(open('/Users/openclaw/Desktop/labuse-pluverif/docs/audit-2026-09/PLU-VERIF-1/lotB_worklist.json'));print(json.dumps(d['<INSEE>'],ensure_ascii=False,indent=1))"
   ```
2. Pour chaque cas, lis la page citée (±1, élargis si besoin) :
   ```
   ~/Desktop/labuse/.venv/bin/python /Users/openclaw/Desktop/labuse-pluverif/scripts/plu_verif/page_text.py <INSEE> <page> 1
   ```
   Si la page semble être un TABLEAU illisible en texte ou un scan, ouvre le PDF
   avec l'outil Read (chemin dans `lotB_pdfs.json`, dossier
   `~/Desktop/labuse/data/plu_reglements/`) sur la page voulue (Read `pages:"N-M"`).
3. Pour chaque cas, cherche l'ARTICLE cité et la VALEUR LABUSE dans le paragraphe
   de cet article, pour CETTE (sous-)zone. Attention aux formes : « 9 m »,
   « neuf mètres », « 60 % », « 0,6 », « R+2 », « 1,90 mètre », « à l'alignement ».

## Verdicts finaux (un par cas)
- **JUSTE** — la valeur LABUSE s'applique bien à cette zone, sans exception ignorée.
- **JUSTE+exception** — la valeur est juste MAIS il existe sur la page une exception
  / sous-secteur / dérogation que la fiche ne dit pas ; donne le texte de l'exception.
- **FAUSSE** — la valeur (ou la zone visée) est fausse au regard du PDF. Donne la
  valeur LUE dans le PDF.
- **MAUVAISE_REFERENCE** — valeur juste mais page ou article faux. Donne la bonne page/article.
- **INDECIDABLE** — impossible de trancher ; dis précisément pourquoi (annexe absente,
  page scannée illisible, renvoi non résolu, table non extraite…).

## Cas fréquents attendus
- Zones AU qui renvoient aux zones U (« se reporter au règlement des zones urbaines
  correspondantes ») : la valeur vient de la zone U ; si `page_pdf` pointe la page
  d'intro AU et non l'article U réel → MAUVAISE_REFERENCE (donne la page de l'article U).
  Si la valeur U est bien reprise et le renvoi assumé → JUSTE (dis-le).
- « cf. annexe du règlement » pour le stationnement : la valeur n'est pas sur la page
  d'article → INDECIDABLE si l'annexe n'est pas dans le PDF, sinon vérifie l'annexe.
- Valeurs « harmonisées ≠ texte » (voir champ `raison`) : si le PDF porte une AUTRE
  valeur que LABUSE → FAUSSE (valeur lue), même si `raison` l'explique.
- Emprise en « m²/ha » convertie en % : si la conversion est exacte → JUSTE (note la conversion).

## Sortie
Écris `docs/audit-2026-09/PLU-VERIF-1/lotB/<INSEE>.json` : liste d'objets
```
{"zone","regle","valeur_labuse","page","article","verdict_final","valeur_lue","page_correcte","article_correct","exception","preuve"}
```
`preuve` = ≤200 car cités du PDF. Champs non pertinents = null. Renvoie un résumé
court : N cas, combien JUSTE / JUSTE+exception / FAUSSE / MAUVAISE_REFERENCE / INDECIDABLE,
et la LISTE des FAUSSE + MAUVAISE_REFERENCE en tête.
```
