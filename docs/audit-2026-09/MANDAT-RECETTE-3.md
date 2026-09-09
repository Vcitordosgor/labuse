# MANDAT RECETTE-3 — les décisions de Vic, et les sources qui ne servent pas

**Branche** : `feat/recette-3` depuis `feat/recette-2`. **Worktree** : `~/Desktop/labuse-recette3`.
**Modèle CC** : Fable. **Rapport** : `docs/audit-2026-09/RECETTE-3.md`.

**Garde-fous** : étape 0 (pwd, branche, arbre propre, `.env`) · aucun merge · aucune bascule · aucun rescoring · DA existante · périmètre fermé aux points T1–T14.
**Règle de preuve** : rien n'est déclaré fait sans avoir été **constaté dans un vrai navigateur** (Playwright). Pour chaque point : la manipulation, ce qui est vu, la capture.
**Un commit par lot.**

---

## LOT 1 — Les six décisions de Vic

- **T1** — **Brief apporteur, version validée.** Maquette de référence : `docs/audit-2026-09/maquette-apporteur-v3.html`. Page 1 : un seul bandeau (confidentiel + pas de mandat fusionnés), **plan de situation** de la parcelle et de ses voisines, **parcelles voisines du même propriétaire** (Blocs fonciers le sait déjà), **dernière vente datée et chiffrée** — et si elle est inconnue, **la ligne ne s'imprime pas** (règle S8). Retirer « document à jour du GPU » et toute mention de plomberie. Pages 2 à 4 : le questionnaire garde son fond, avec trois changements — **nom et coordonnées du contact en première question**, trois questions marquées « l'essentiel », les photos envoyées par message en citant la référence au lieu d'être collées. Une phrase courte sous chaque section dit pourquoi on la pose.
- **T2** — **Supprimer le document Résumé** (décision Vic). Route, builder, bouton, tests, proxy : tout part. Vérifier qu'aucun autre document n'en dépend.
- **T3** — **Tri par défaut du listing factuel** : la surface décroissante remonte des emprises géantes sans adresse et sans intérêt. Proposer le meilleur critère de remplacement (commune ? potentiel ? mixte ?), **le justifier par ce que les 30 premières lignes donnent dans chaque cas**, puis appliquer celui qui sert le mieux un promoteur ou un agent.
- **T4** — **Segmentation du listing d'analyse** (décision Vic). Quatre segments, chacun gardant son palier :
  1. **Un professionnel a déposé un permis** (le signal de q_v14, ~88 parcelles)
  2. **Terrain nu constructible** (SDP résiduelle, rien de bâti)
  3. **Bâti à densifier** (occupé, résiduel restant)
  4. **Le reste**
  Les segments sont repliables, l'ordre est celui-ci, et le compte de chacun est affiché.
- **T5** — **Servitudes de Pièges et risques** : ajouter au dictionnaire `_KINDS` les kinds manquants — droit de préemption (DPU), ravines et reculs (DPF), zones humides, espaces naturels protégés, emplacements réservés et espaces boisés classés (`plu_gpu_prescription`), et remettre le PEB qui avait été retiré.
- **T6** — **Message IA** : vérifier que le texte servi quand le compte Anthropic n'a plus de crédits dit bien quoi faire, et qu'il ne dit plus « réessayez dans un instant ».

## LOT 2 — Les 22 sources, où elles servent et où elles devraient servir

**Ce lot commence en lecture seule.** Il rend compte avant d'appliquer quoi que ce soit — Vic tranche source par source.

- **T7** — **Le tableau.** Une ligne par source ingérée par SOURCES-1. Cinq colonnes : la source · où elle sert **aujourd'hui** (fiche, outil, export, cascade, carte — avec `fichier:ligne`) · où elle **devrait** servir · ce que ça apporterait au client, en une phrase · le coût (petit / moyen / gros).
- **T8** — **Les orphelines.** Les sources qui ne servent nulle part ou seulement sur la carte : DPF, zones humides, espaces naturels, RPG, et toutes les autres que le tableau révélera. Pour chacune : est-ce un oubli ou un choix ?
- **T9** — **Les trois surfaces à couvrir**, dans cet ordre de valeur : la **fiche parcelle** (ce que le client regarde le plus), les **outils** (Pièges et risques, Étude de zone, Faisabilité, Commune), les **exports** (Dossier, Financier, Apporteur, pré-dossier PC).
- **T10** — **Rendre compte et s'arrêter.** Livrer le tableau et la liste des branchements proposés, classés par valeur. **Ne rien appliquer sans l'accord de Vic**, sauf ceux du lot 1 (T5) déjà décidés.

## LOT 3 — Ce que RECETTE-2 a laissé ouvert

- **T11** — Vérifier que le **Financier** produit bien son document de bout en bout après les correctifs S2/S3, et que les 20 questions restantes apparaissent toutes dans le bilan. Toute question dont la réponse n'apparaît nulle part sort.
- **T12** — Vérifier que le **courrier propriétaire** n'imprime plus jamais un champ vide, sur trois parcelles différentes dont une sans adresse connue.
- **T13** — Reprendre les points de RECETTE-2 marqués « à recetter à l'œil » et les constater au navigateur.
- **T14** — La **maquette apporteur validée** est archivée dans le dépôt à côté du rapport, pour servir de référence aux prochains tours.

---

## Rapport
Un tableau des 14 points : numéro · état · ce qui a été constaté au navigateur · preuve. Le lot 2 rend son tableau des sources en français, avec la liste des branchements proposés classés par valeur, et rien d'appliqué au-delà de T5. Rien n'est mergé.
