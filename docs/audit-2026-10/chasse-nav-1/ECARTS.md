# CHASSE-NAV-1 — ÉCARTS

Audit navigation (lecture seule). Une ligne par écart : passage · gravité · départ · clic · attendu · obtenu · cause · fichier:ligne · capture.
Gravités : 🔴 bloquant · 🟠 majeur · 🟡 mineur · ⚪ cosmétique/artefact.

---

## N-1 🟡 LIEN — le lien du digest mail (`#parcelle=`) n'ouvre pas la fiche

- **Passage** : lien cliquable d'un mail de digest / notification « voir la parcelle ».
- **Départ** : mail de digest reçu par le client (hors app).
- **Clic** : URL `https://app.labuse.immo/socle/#parcelle={idu}`.
- **Attendu** : l'app s'ouvre sur la fiche de la parcelle `{idu}`.
- **Obtenu** : l'app s'ouvre sur l'écran d'accueil générique (carte de l'île) ; la fiche NE s'ouvre PAS. Reproduit en local : rechargement réel de `/socle/#parcelle=97411000BZ1065` → URL réécrite en `/socle/` nu, aucune fiche. Le MÊME idu en `/socle/#idu=97411000BZ1065` ouvre correctement la fiche (URL réécrite `#f=1&idu=…`, panneau fiche présent).
- **Cause** : le front ne lit QUE le paramètre de hash `idu` (`App.tsx:375` `p.get('idu')`), jamais `parcelle`. Or le mail construit le lien avec la clé `parcelle` : `emails.py:61` `f"{base_url}/socle/#parcelle={idu}"`. Les événements stockent aussi `lien=/socle/#parcelle={idu}` (`events.py:447,457,470,484`) — sans impact IN-APP car la cloche utilise le champ structuré `e.idu` et non `e.lien` (`Header.tsx:392`), donc le clic dans la cloche fonctionne ; seul le lien EMAIL est cassé.
- **Portée (raffinée en Lot E)** : seul le digest **TEXTE** (repli multipart) porte ce lien `#parcelle=` cassé — matérialisé : `digest_notifications(...)` produit `https://app.labuse.immo/socle/#parcelle=97411000BZ1065`. Le digest **HTML** (version primaire affichée par la plupart des clients mail, `digest_html_email`) n'a **AUCUN lien cliquable par parcelle** (texte « détail dans l'application »). Net : il n'existe **aucun deep-link parcelle fonctionnel depuis un digest e-mail**. La cloche in-app n'est PAS touchée (elle utilise `e.idu`). Gravité 🟡 (périmètre e-mail digest, in-app sain).
- **fichier:ligne** : `src/labuse/emails.py:61` (construit `#parcelle=`) vs `frontend/src/App.tsx:375` (lit `#idu=`). Aussi `src/labuse/api/events.py:447,457,470,484`.
- **Capture** : `captures/N1-parcelle-hash-accueil.png` (après reload `#parcelle=` → accueil), `captures/N1-idu-hash-fiche.png` (reload `#idu=` → fiche).
- **Correctif pressenti (hors périmètre)** : aligner `emails.py:61` sur `#idu={idu}` (ou faire lire `parcelle` par `App.tsx`). À porter dans CHASSE-NAV-FIX-1.

---

## N-2 🔴 CASSÉ — ouvrir la fiche d'une parcelle DISPARUE plante toute l'app

- **Passage** : ouvrir la fiche d'une parcelle disparue du cadastre (témoin du mandat : « une disparue ouverte depuis un projet »). Vaut pour TOUT chemin d'entrée vers la fiche : projet, veille, recherche omnibox, CRM, deep-link `#idu=`.
- **Départ** : n'importe quel écran qui sélectionne une parcelle disparue (ex. Projets 237/241 contiennent `97411000AE0013`).
- **Clic** : ouverture de la fiche (`select(idu)`), reproduit ici via `/socle/#idu=97411000AE0013` (reload réel).
- **Attendu** : la fiche affiche l'encart « Parcelle disparue du cadastre » (le back renvoie justement `cadastre_disparue` = message + `remplacee_par`), sans casser l'app.
- **Obtenu** : **écran d'erreur plein écran** (ErrorBoundary) « Une erreur est survenue · Cannot read properties of undefined (reading 'filter') » — toute l'app est remplacée, le contexte (projet, veille…) est perdu. 5 erreurs console, stack `Fiche.tsx`.
- **Cause** : le payload d'une disparue est `{idu, commune, cadastre_disparue}` SANS `lines` (la parcelle n'est pas au run servi). La fiche calcule des dérivés INCONDITIONNELS en tête de composant : `const hardLines = f?.lines.filter(...) ?? []` (`Fiche.tsx:561`) — l'optional chaining protège `f` mais PAS `f.lines` ; `f.lines` est `undefined` → `.filter` lève AVANT le `?? []`. Idem `ongletLines`/`proprioLines` (`:582,:595`) et `:917`. Le **garde disparue existe** (`Fiche.tsx:688` `if (f?.cadastre_disparue) return <encart>`), mais il est placé APRÈS ces dérivés → **inatteignable**. Le type `Fiche` déclare `lines` non-optionnel (mensonge de type vs payload réel).
- **fichier:ligne** : `frontend/src/components/fiche/Fiche.tsx:561` (crash), garde mort `:688` ; back honnête `src/labuse/api/...` renvoie `cadastre_disparue`.
- **Capture** : `captures/N2-disparue-crash.png`.
- **Correctif pressenti (hors périmètre)** : remonter le retour anticipé `cadastre_disparue` AVANT les dérivés `hardLines/proprioLines`, et/ou `(f?.lines ?? []).filter(...)`. À porter dans CHASSE-NAV-FIX-1.

---

## N-3 ⚪ COSMÉTIQUE — lien Pages Jaunes : commune dupliquée dans la requête

- **Passage** : fiche parcelle → lien « Voir sur Pages Jaunes ».
- **Clic** : ouvre `pagesjaunes.fr/...?ou=3 Chemin de la Citerne, 97417 Saint-Denis Saint-Denis`.
- **Attendu** : `ou=` = adresse (qui contient déjà la commune) OU commune seule.
- **Obtenu** : la commune apparaît DEUX fois (`…97417 Saint-Denis Saint-Denis`) car `pagesJaunes()` concatène `${adresse} ${commune}` alors que l'adresse servie contient déjà la commune. La recherche fonctionne quand même (PJ tolère), mais la requête est redondante.
- **Cause** : `frontend/src/components/fiche/liensExternes.ts:32` `const ou = a ? \`${a} ${c}\`.trim() : c` — l'adresse `a` inclut déjà la commune.
- **fichier:ligne** : `frontend/src/components/fiche/liensExternes.ts:32`.
- **Capture** : href relevé en live (N1-idu-hash-fiche, lien pj). Non bloquant.


---

## N-4 🟡 COHÉRENCE — « Scan patrimoine » depuis Communes n'offre pas le retour

- **Passage** : raccourci « Scan patrimoine » présent dans plusieurs outils.
- **Départ** : outil Communes (ligne acquéreur) → « Scan patrimoine ».
- **Clic** : ouvre l'outil Scan patrimoine préchargé sur le SIREN.
- **Attendu** : même comportement que depuis Blocs/Permis/Remonter le temps, qui posent un fil de retour (`pushOutilRetour`) → l'utilisateur peut revenir « ← Communes ».
- **Obtenu** : depuis Communes, AUCUN fil de retour n'est posé (`Communes.tsx:56-60`) ; l'utilisateur est déposé dans Scan sans retour vers Communes (doit re-naviguer). Blocs (`Blocs.tsx:118`), Permis (`ModulePanel.tsx:433`) et Remonter le temps (`HistoireFrise.tsx:129`) posent bien `pushOutilRetour`.
- **Cause** : `ouvrirScanPatrimoine` de Communes omet `pushOutilRetour` alors que son commentaire revendique « même idiome que Voir le patrimoine ».
- **fichier:ligne** : `frontend/src/components/outils/Communes.tsx:56-60` (vs `Blocs.tsx:118`, `ModulePanel.tsx:433`, `HistoireFrise.tsx:129`).
- **Capture** : analyse de code (comparaison des 4 origines) — cf. LOT-C.md.
- **Correctif pressenti (hors périmètre)** : ajouter `pushOutilRetour({module:'communes', label:'Communes'})` au pont Communes → Scan.

## C-obs1 🟡 COHÉRENCE (à trancher) — « ouvrir la fiche » recentre la carte selon l'origine

- **Passage** : ouvrir la fiche d'une parcelle (action transverse, ~12 occurrences).
- **Obtenu** : les outils-listes (Communes/Successions/Prospection/Veille) utilisent `focusParcelle(idu,{fiche:true})` → vue cartes + zoom + fiche ; CRM/Projets/Copilote/listing utilisent `select(idu)` → fiche seule, SANS recentrer la carte sur la parcelle (contour surligné via `selectedIdu`, mais pas de vol carte).
- **Impact** : depuis CRM/Projets, la fiche s'ouvre mais la carte ne va pas à la parcelle (potentiellement hors écran). Destination correcte dans tous les cas.
- **fichier:ligne** : `store/useApp.ts:764` (`select`) vs `:772` (`focusParcelle`) ; appelants CRM `crm/Kanban.tsx:121,251`, Projets `projets/ProjetKanban.tsx:455`.
- **Statut** : observation (peut-être intentionnel) — à trancher par Vic (unifier sur `focusParcelle` ?).

## N-5 ⚪ CODE MORT — constante PDF Étude de zone pointe une route 404 (non câblée)

- **Passage** : export PDF « Étude de zone » (potentiel).
- **Constat** : `etudeZonePdfUrl = '/outils/etude-zone/export.pdf'` (api.ts:483) → la route renvoie **404** (vérifié live) ; la vraie route servie est `/etude-zone.pdf` (200). La constante n'est importée/utilisée par AUCUN composant (grep hors api.ts = vide) → aucun bouton ne la déclenche aujourd'hui.
- **Impact** : nul en l'état (code mort). Risque dormant : un futur câblage sur cette constante produirait un 404.
- **fichier:ligne** : `frontend/src/lib/api.ts:483`.
- **Correctif pressenti (hors périmètre)** : supprimer la constante morte ou la pointer sur `/etude-zone.pdf`.
