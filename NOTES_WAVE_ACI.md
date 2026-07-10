# Notes de travail — mandat Wave Adresses, Courrier, Protection & Recherche IA

Notes intermédiaires (matière du rapport de fin). Branche `feat/wave-adresses-courrier-ia`.

## Phase 0 — comptes/sièges/plans (10/07/2026)

Vérifié en base : AUCUNE table comptes/sièges/plans (seule `api_keys` — quotas des clés
partenaires, pas des comptes utilisateurs ; l'auth app = mot de passe pilote unique).
Décision conforme au mandat : quotas + rate limiting au niveau **session/IP**, gating par
plan **stubbé** (constantes + branchements prêts), et **« mandat Auth & Plans » = prérequis
à la commercialisation** (à reprendre au rapport de fin).

## Lot 5 — CERFA vérifié (recherche 10/07/2026)

- **CERFA n° 13406\*17**, en vigueur depuis le **01/07/2026** (les guichets SVE rejettent
  les \*15/\*16 depuis la généralisation du dépôt dématérialisé au 01/01/2026).
- PDF officiel vendorisé : `data/cerfa/cerfa_13406-17.pdf` (source :
  https://www.formulaires.service-public.gouv.fr/gf/cerfa_13406.do — sert toujours la
  version courante). AcroForm remplissable, 20 pages, 376 champs (vérifié pypdf).
- Champs TERRAIN (page 5 du PDF = « 3/18 », cadre 3.1) :
  adresse `T2Q_numero`, `T2V_voie`, `T2W_lieudit`, `T2L_localite`, `T2C_code` ;
  parcelles 1-3 : `T2{F,S,N,T}_…`, `T2{F,S,N,T}P2_…`, `T2{F,S,N,T}P3_…`
  (préfixe/section/numéro/superficie) ; superficie totale `D5T_total`.
  Au-delà de 3 parcelles → annexe « références cadastrales complémentaires ».
- Identité demandeur (page 2/18) : `H1N_nom`, `H1P_prenom`, … — champs PROJET laissés
  vides par le pack (mandat).

## Lot 1 — BAN 974

- Export officiel : https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-974.csv.gz
  (Licence Ouverte). Téléchargé 10/07/2026 : **340 771 adresses**, 0 sans voie ni lieu-dit.
- `cad_parcelles` (rattachement cadastral BAN natif) rempli à **35,3 %** seulement →
  jointure spatiale point-dans-parcelle = méthode principale (mandat), `cad_parcelles`
  en complément, plus proche parcelle < 20 m en dernier recours.
- `type_position` : entrée 155k, bâtiment 57k, parcelle 50k, segment 40k, logement 27k.
- RNIC : 287/2220 copropriétés sans `parcelle_idu` (12,9 %) — colonnes `adresse`,
  `insee`, `commune` disponibles pour le rattachement via la table `adresses`.
