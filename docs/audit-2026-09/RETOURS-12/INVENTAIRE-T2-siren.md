# INVENTAIRE T2 — surfaces affichant SIREN/SIRET (RETOURS-12)

Aucun composant `<Siren/>` ni lien Pappers n'existe aujourd'hui. Convention de lien
externe du projet : `target="_blank" rel="noreferrer"`. Un seul lien externe SIREN
existant : Fiche.tsx:1431 (vers annuaire-entreprises.data.gouv.fr).

| Fichier:Ligne | Écran | Valeur | Rendu actuel | Clé |
|---|---|---|---|---|
| outils/ScanPatrimoine.tsx:167 | Scan patrimoine | SIREN {owner} | texte brut mono | owner |
| outils/VeillePromoteurs.tsx:226 | Veille (frise) | SIREN {o.siren} | texte brut | o.siren |
| outils/moteurs.tsx:301 | Assemblage (ligne parcelle) | · SIREN {pr.siren} | texte brut | pr.siren |
| outils/moteurs.tsx:757-758 | Promoteurs (bloc) | SIREN {p.siren} | title + texte | p.siren |
| outils/ModulePanel.tsx:233 | M02 Patrimoine (popup) | ['SIREN', d['siren']] | texte brut mono | d['siren'] |
| outils/ModulePanel.tsx:308 | M10 Permis (drawer) | SIREN {d['porteur_siren']} | texte brut mono | d['porteur_siren'] |
| fiche/Fiche.tsx:1413 | Fiche parcelle propriétaire PM | SIREN {…siren} | texte brut mono | f.proprietaire_moral.siren |
| fiche/Fiche.tsx:1431 | Fiche parcelle propriétaire PM | Annuaire entreprises ↗ | **lien externe** | idem |
| fiche/ProprietaireHistorique.tsx:47 | Histo propriétaire | SIREN {avant}→{apres} | texte brut mono | c.siren_avant/apres |
| fiche/ProprietaireHistorique.tsx:78 | Histo timeline | · {m.siren} | texte brut discret | m.siren |
| outils/EtudeZone.tsx:427,505 | Étude de zone concurrents/étab. | SIRET en clé (non affiché) | — | x.siret / e.siret |
| admin/Programmes.tsx:66,69 | Admin Programmes | SIREN {sirenFixe} + input | badge + input éditable | sirenFixe / siren |

**À NE PAS toucher** : boutons-actions déjà cliquables (VeillePromoteurs:240 « voir patrimoine », Communes:110-121 « Scan patrimoine → »), clés non affichées (EtudeZone), input éditable (Programmes:69).

**Décision** : composant unique `shared/Siren.tsx` — SIREN (9 chiffres) → lien `https://www.pappers.fr/entreprise/{siren}` (nouvelle fenêtre, rel="noopener"), SIRET (14) affiche le SIRET mais lie sur les 9 premiers ; pas de lien si != 9/14 chiffres valides. Survol conforme (souligné).
