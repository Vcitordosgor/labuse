# Micro-mandat — grille EXPORTS : « 1950 » sort, « Argumentaire » entre (`fix/fiche-argumentaire`)

Branché sur `origin/main` @ `96cb3731` (HEAD courant). Front seul. CC ne merge jamais.

## 1. Ce qu'était « 1950 » (pour la remettre ailleurs un jour)

La tuile « 1950 » de la grille EXPORTS (`Fiche.tsx`) était un **simple lanceur de navigation** — pas
une couche ortho ni un lien externe, **aucun état actif à démonter** :

```js
onClick={() => { setParcelPrefill(idu); setFlyTo({ center: f.coords, zoom: 18 }); setModule('temps') }}
```

Elle ouvrait le module **`temps`** (comparateur temporel in-app — « Ce terrain de 1950 à aujourd'hui,
curseur avant/après », ortho historique IGN), en pré-remplissant la parcelle et en recentrant la
carte. C'était un **DOUBLON** de la porte « **Remonter le temps** » du tiroir **Marché**
(`Fiche.tsx`, action identique `setModule('temps')`), **conservée**. Donc le module temporel reste
pleinement atteignable — rien n'est perdu. Pour remettre « 1950 » ailleurs un jour : l'action est
`setParcelPrefill(idu) → setFlyTo(coords) → setModule('temps')`.

## 2. À sa place : tuile « Argumentaire »

Même comportement que le bouton retiré en **M143 lot 2** — `<a>` vers
`/argumentaire/{idu}.pdf` avec les hypothèses de la calculette, `data-argumentaire`, nouvel onglet,
icône (bulle de dialogue) cohérente avec la grille. URL :

```
/argumentaire/{idu}.pdf?cout_construction_m2=…&marge_frais_pct=…[&vrd_m2=…][&prix_demande_eur=…]
```

- Hypothèses lues de l'état partagé `calculette` (`useApp`), déjà en scope de la grille (le PDF s'en
  sert). Nullable : parcelle non chiffrable → URL nue `/argumentaire/{idu}.pdf` (défauts serveur ;
  la route rend honnêtement « non chiffrable », régime M143).
- Tuile **inconditionnelle** (comme PDF) : la grille reste à **8 tuiles** même sans calculette.

## 3. VRD (M144) threadé

La calculette expose bien une VRD depuis M144 (`deb.vrd`, défaut serveur). Threadée jusqu'à
l'argumentaire : `vrd_m2` ajouté à l'objet `calculette` du store (`useApp.ts`, optionnel — le PDF
fiche l'ignore par typage structurel) ; `setCalculette` le pose ; l'URL le porte quand présent,
sinon **défaut serveur, rien d'inventé**.

## Capture avant / après (structure de la grille 4×2)

```
AVANT :  PDF · Dossier · Finance · Cadastre
         1950 · Maps · Courrier · Pré-dossier
APRÈS :  PDF · Dossier · Finance · Cadastre
         Argumentaire · Maps · Courrier · Pré-dossier
```

## Contrôles

1. **Grille à 8 tuiles (4×2)** intacte (PDF · Dossier · Banquier · Cadastre / Argumentaire · Maps ·
   Courrier · Pré-dossier). ✓
2. **« 1950 » absent** de la grille EXPORTS (seule mention restante = le commentaire-tombstone qui
   explique le remplacement) ; la porte « Remonter le temps » (Marché) conservée. ✓
3. **L'argumentaire s'ouvre** : `/argumentaire/{idu}.pdf` + hypothèses calculette (cout/marge/vrd/prix). ✓
4. `setFlyTo`/`setParcelPrefill` **non orphelins** (encore utilisés par la porte Marché + le zoom
   section) ; commentaire de `setFlyTo` corrigé (ne cite plus la tuile retirée). ✓
5. **`tsc` vert.** Seuls `Fiche.tsx` + `useApp.ts` touchés (le second, nécessaire pour threader vrd). ✓

*Fin. Commit sur `fix/fiche-argumentaire`. CC ne merge jamais.*
