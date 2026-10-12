# CHASSE-DONNEES-1 — RAPPORT

Chasse du 12/10/2026, local q_v18 (scoring) / q_v18_sources (cascade) / run_seq 15 (résiduel), API worktree :8740, base en lecture seule stricte. Lots A→E exécutés ; **lot F (local vs prod) non joué** — à faire après le déploiement q_v18, les 40 témoins et le banc sont prêts pour ça.

## Verdict (5 lignes)

1. **La donnée amont est juste** : cadastre 16/16 au m² près (le 1 m² de DV0285 est dans l'acte), BAN 7/7, GPU exact (dépublications confirmées au jour), PPR = GASPAR, DVF 5/5 au centime, DPE = ADEME, INSEE 3/3, BODACC en table au byte près, 44/50 règles PLU exactes au règlement — et les grands invariants tiennent sur 24/24 communes (compteur filtre = liste = stats = entonnoir = Σ bandes ; carte = run = fiche ; accueil = Σ communes).
2. **C'est entre les tables et les lecteurs que ça casse : 83 écarts** (17 FAUX-CLIENT · 20 DIVERGENT · 13 LATENT · 18 ÉTIQUETTE · 6 ABSENCE · 9 FRAÎCHEUR), presque tous dans les lecteurs secondaires : export md/html, Courrier, Comparatif, Copilote, API partenaire, cloche Radar — la fiche, la carte et le Dossier, eux, se tiennent.
3. **Trois familles font la moitié des dégâts** : (a) le **dessin vs la contenance** (CONTENANCE-1 non propagé à 8 lecteurs : tuiles, export, CSV projets, repère Bilan, Courrier, Copilote, digest, partage) ; (b) les **lecteurs à moteur parallèle** qui relisent des tables figées (Courrier sur `cascade_results` du 29/06 → « zone rouge inconstructible » sur une parcelle servie bande A ; export sur le mauvais run → cascade vide ; cloche Radar figée au 21/08 ; fiche BODACC gelée au 09/07 ; SIRENE « active » sur société cessée) ; (c) les **étiquettes statistiques** (« médian » qui est une moyenne, « 12 mois » horloge sur source arrêtée, « ventes » avec échanges, « Rayon 10 km » imprimé pour une isochrone 10 min).
4. **Le pire zéro menteur** : `taux_emprise_pct NULL` (174 840 parcelles) rendu 0 → badge « Nu » et filtre « Terrain nu » servent des parcelles bâties à 66-132 %.
5. **Tout est reproductible** : 83 écarts avec témoin + fichier:ligne des deux chemins dans `ECARTS.md`, et un banc d'une commande (`scripts/coherence/chasse_donnees.py`) qui mord sur les écarts ouverts — corrections dans CHASSE-DONNEES-FIX-1, rien n'a été corrigé ici.

## Chiffres de la chasse

| Lot | Contenu | Volume | Écarts |
|-----|---------|--------|--------|
| A | Lignée + sources→lecteurs | 1 141 lignes / 929 notions ; 1 481 lecteurs / 81 tables | 324 divergences latentes repérées (dont 13 actées LATENT) |
| B | Témoins | 40 parcelles / 28 cas prouvés SQL + 24 communes | — |
| C | Même valeur partout | ~3 100 relevés (41×7 lecteurs, 24/24 communes, 17 PDF, 2 builders Copilote) | 45 |
| D | Vérité face à la source | 40 confrontations officielles + 50 règles PLU + 99 millésimes | 20 |
| E | Étiquettes et absences | 237 étiquettes + 18 rendus d'absence + front post-FC2 | 18 |

## Les FAUX-CLIENT (17)

Priorité de CHASSE-DONNEES-FIX-1 — le détail (valeurs, cause, fichier:ligne, reproduction) est dans `ECARTS.md` :

1. Export md/html : cascade/risques **vides** (« Ont répondu : — ») — `_build_fiche` lit `dryrun_cascade_results` au run scoring au lieu du run cascade (app.py:7349).
2. Export md/html : « Surface » = dessin (30/41 témoins faux depuis CONTENANCE-1) ; « Propriétaire inconnu » quand la fiche connaît la SCI.
3. Export d'une parcelle **disparue** sans la mention (la fiche l'affiche, l'export non).
4. Dossier 6 pages + Courrier d'une disparue : « parcelle stable », « Votre parcelle AV 2114… » — aucun document ne lit `cadastre_disparue_le`.
5. Courrier AK0804 : « PPR zone rouge (inconstructible) » envoyé au propriétaire d'une parcelle servie bande A / SDP 34 223 m² — `courrier_compose` lit `cascade_results` legacy figée au 29/06.
6. Courrier : « Surface cadastrale » = dessin (DV0285 : 117 505 m² au courrier, 1 m² partout ailleurs).
7. Comparatif bizone BZ0005 : « Usdu, constructible » (2,4 % de la parcelle) et « zone A inconstructible » dans le même PDF.
8. SIRENE : SCI servie « active » alors que cessée depuis le 08/07/2026 (état d'unité légale jamais raccordé au stock géolocalisé).
9. Fiche BODACC : « dernière annonce 2024-10-08 » — lit `bodacc_annonces_owner` gelée au 09/07, rate l'annonce du 21/08 présente localement et officiellement.
10. Règles PLU ×3 : hauteur graduée Saint-Joseph servie au palier max ; palier ≥2 500 m² Sainte-Rose absent ; formule H/2 réduite à son plancher.
11. Étude de zone : « ventes / 12 mois » = fenêtre horloge sur DVF arrêté 2025-12 → 13 servies, 57 réelles.
12. Badge « Nu » / filtre « Terrain nu » sur parcelles bâties (taux_emprise NULL → 0, 174 840 parcelles concernées).
13. PDF Étude de zone : « Rayon 10.0 km » imprimé quand le back bascule silencieusement en isochrone 10 min.
14. (+ les déclinaisons listées dans ECARTS.md : CSV projets/repère Bilan au dessin, Copilote SDP double moteur.)

## Ce qui tient (prouvé, pas déclaré)

- Compteur `/filtre` = len(idus) = `/stats` = entonnoir = Σ bandes = Σ tiers, 24/24 communes (slivers réconciliés).
- Carte (mvt bakée) = cascade q_v18_sources = run q_v18 = « évaluées » fiche ; accueil 433 229 = Σ 24 communes.
- Bizones : zone dominante identique sur tous les lecteurs (la fiche seule détaille les parts — c'est le Comparatif et le Copilote-outil qui dévient).
- PPR partiel post-q_v18 : AK0804/AY0786 bande A + SDP identiques partout ; le badge a disparu **partout de façon cohérente** (reste AC0157 : servie 0 `portion_reduite` sans badge, le badge n'existe que pour `ppr_rouge` — à arbitrer).
- Nouvelles parcelles d'octobre servies partout ; disparues correctement traitées **sur la fiche** (pas dans les documents).
- Prix des offres, dashboard sources (99=99=99), DVF/DPE/INSEE/BAN/cadastre/GPU face à l'officiel.

## À verser au dossier (hors écarts client)

- **Payload mort** : 49 champs fiche sans lecteur front (bloc `renouvellement` = 4 count(*) par fiche pour rien), endpoints accueil orphelins, `/partners/match/compatibilite` orphelin, outil ZAN dormant depuis le 21/08, `pdf_premium.py` 1 182 lignes sans route, partage vivant sans porte UI (0 token valide en base).
- **Angle mort** : des permis annulés (etat=4) pointent des IDU absents de `parcels` — invisibles de partout.
- ScoreV2Block re-fetch `/v2/score` au lieu de lire le payload fiche (doublon de chemin structurel, pas de divergence observée aujourd'hui).
- Flash = Dossier byte-identique (numéro `DP-…`) ; le commentaire « sans la section 9 » est périmé.
- apicarto PCI retarde sur le cadastre d'octobre (sert encore AV2114, ignore AB0993) — écart de la source externe, pas de LABUSE.

## Livrables

- `LIGNEE.csv` (1 141 lignes ; `lignee-parts/` par surface) · `SOURCES-LECTEURS.csv` (1 481 lecteurs) · `BANC-EXISTANT.md`
- `TEMOINS.md` (40 + 24, requêtes rejouables)
- `ECARTS.md` (83 écarts, régénérable par `assembler_ecarts.py` depuis `ecarts-parts/*.csv`) ; matrices `lotC/`, confrontations `lotD/` (dont `fraicheur-sources.csv` 99 sources, `regles-plu.csv` 50 règles)
- Banc : `PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_donnees --api http://127.0.0.1:8740` — 14 gardes, une par écart reproductible, exit 1 tant que les écarts sont ouverts. Sortie du 12/10 (`BANC-SORTIE.txt`) : **12 ECART · 2 OK · 0 SKIP** — il mord. Les 2 OK sont les invariants sains (compteurs commune) et la zone courrier dont le témoin ne diverge pas aujourd'hui (chemin LATENT acté dans ECARTS.md).

## Suites

1. **CHASSE-DONNEES-FIX-1** : corriger dans l'ordre FAUX-CLIENT → DIVERGENT → zéros menteurs → étiquettes ; le banc doit passer au vert garde par garde.
2. **Lot F** après déploiement q_v18 en prod : rejouer les 40 témoins + le banc contre app.labuse.immo, tout écart local/prod = écart de déploiement.
3. Arbitrages Vic : badge PPR pour `portion_reduite` ; sort des payloads morts ; millésimes volontairement masqués (doctrine PAGE-SOURCES-1) face aux 17 vitrines muettes.
