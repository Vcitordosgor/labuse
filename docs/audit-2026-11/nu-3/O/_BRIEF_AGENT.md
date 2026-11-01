# BRIEF — vérification indépendante de faits (AUDIT-NU-3 lot O)

Tu es un sous-auditeur. LECTURE SEULE : aucune écriture base, aucun correctif code, aucun accès prod.
Ton rôle : vérifier INDÉPENDAMMENT une liste de « faits » que l'application affirme au client.

## Ce que tu as à disposition
- **Base PostgreSQL** `labuse` (image proche prod, run 17 q_v20) : `psql -d labuse -c "..."`
  (rôle OS, pas de mot de passe). 285 tables. C'est la SOURCE DE VÉRITÉ pour recalculer.
- **API** bootée sur `http://127.0.0.1:9360` (routes SANS préfixe /api — ex. `/parcels/{idu}`,
  `/communes/{insee}/contexte`, `/outils/taxe-amenagement`, `/moteurs/assemblage`, `/outils/gabarit/{idu}`…).
  `curl -s http://127.0.0.1:9360/openapi.json` liste les 401 routes. C'est la valeur SERVIE.
- **Code source** dans ce worktree `/Users/openclaw/Desktop/labuse-nu3-o/src/labuse/…` : les colonnes
  `source` et `formule` du fait pointent fichier:ligne. Lis le code pour comprendre le calcul réel.
- WebSearch/WebFetch pour confronter une formule réglementaire/fiscale au texte officiel cité
  (Légifrance, BOFiP, barème taxe aménagement 2026, service-public.fr).

Tu ne peux PAS piloter le navigateur (Playwright est partagé, réservé au chef). Pour chaque fait,
dis si une vérification écran reste nécessaire (libellé ambigu, rendu conditionnel) → `ecran_a_verifier: true`.

## Méthode par fait (fichier JSON fourni : liste d'objets à 13 colonnes)
Pour CHAQUE fait de ta liste :
1. **Comprends** le fait : libelle (ce qui est affiché), source (fichier:ligne/table.colonne), formule, type.
2. **Recalcule INDÉPENDAMMENT** depuis les tables sources, par TES propres requêtes SQL (ne te
   contente pas de relire le code — refais le calcul). Choisis **≥5 cas variés** : parcelles /
   communes / projets DIFFÉRENTS ; pour un outil « à zone » prends au moins **une commune du
   littoral** (ex. Saint-Paul 97415, Saint-Pierre 97410, Saint-Denis 97400) **et une des Hauts**
   (ex. Cilaos 97414, Salazie 97413, La Plaine-des-Palmistes 97412, Le Tampon 97418 hauts).
3. **Appelle l'API** sur les mêmes cas et extrais la valeur servie (jq/python sur le JSON, chemin
   exact). Compare au recalcul. **Toute différence est un écart, même d'une unité.**
4. Si le fait est **réglementaire/fiscal** : confronte la formule du code au TEXTE officiel cité
   (cite la source). Barème taxe aménagement 2026, R.111-*, L.562-1, loi 2025-1129, etc.
5. **Libellé** : le libellé affirme-t-il EXACTEMENT ce que le chiffre est ? (ex. « médian » alors
   que c'est une moyenne ; « maison » alors que le €/m² vient d'appartements ; unité fausse).
6. Note tout écart avec **preuve chiffrée** (cas, valeur recalc vs valeur API) et **cause
   fichier:ligne**.

## Cas introuvables / impossibles
Si un fait ne peut pas être recalculé (table vide, route absente, donnée non déterministe,
dépend d'un état live externe), dis-le explicitement avec la raison. Ne bluffe pas.

## Format de sortie (OBLIGATOIRE)
Retourne UNIQUEMENT un JSON (une ligne par fait) : liste d'objets
```
{"id":"OUT-X-001","verdict":"juste|ecart|impossible","n_cas":5,
 "cas":["97415000AB0001", "..."],
 "preuve":"recalc=X API=X sur 5 cas ... (ou: recalc=9366 API=9500 cas 97410... ÉCART 134)",
 "cause":"fichier:ligne + explication (si écart)",
 "reglementaire":"formule vs texte officiel + verdict (si applicable, sinon '')",
 "libelle_ok":true|false, "libelle_note":"...",
 "ecran_a_verifier":true|false,
 "col12":"vérifié nu-3-O, 5 cas, juste  (OU)  écart nu-3-O : <résumé 1 ligne>"}
```
Écris aussi ce JSON dans un fichier `docs/audit-2026-11/nu-3/O/resultats/<GROUPE>.json` avant de finir.
Sois rigoureux et honnête : un « juste » doit être prouvé par le recalcul, pas supposé.
