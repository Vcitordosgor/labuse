# MANDAT — SANS ENGAGEMENT, PLANCHE D'ÉCRANS, LISIBILITÉ DES PAGES LÉGALES
Régime AUTONOME. Commits par lot (S1→S3). RÈGLES COMMUNES. Findings SE-001→. Court mandat, trois objets.

## DÉCISION COMMERCIALE (Vic, 27/08/2026 — remplace la précédente)
INTÉGRAL passe en **mensuel SANS ENGAGEMENT**. Plus de durée ferme de 12 mois, plus de reconduction annuelle.
- Abonnement mensuel reconduit tacitement chaque mois, prélèvement automatique (le client saisit sa carte une fois).
- **Résiliation : le client ÉCRIT à LABUSE** (e-mail), Vic résilie depuis l'admin. PAS de bouton de résiliation en self-service, et les CGV ne doivent PAS promettre « depuis son espace ».
- Le mois entamé est dû ; l'accès reste ouvert jusqu'à la fin de la période payée.
- FLASH est inchangé : 79 €, paiement unique.
Prix inchangés : Intégral 349 €/mois, Flash 79 €.

## S1 — « ENGAGEMENT 12 MOIS » DISPARAÎT PARTOUT
Balaye TOUT le dépôt (front, back, offres.py, CGV, mentions légales, templates Brevo référencés, PDF, docs, tests, seeds, config Stripe) et liste chaque occurrence d'un engagement, d'une durée ferme, d'une reconduction annuelle, d'un préavis d'un mois, de la loi Chatel / L. 215-1, d'un avis d'échéance. Tableau au rapport : fichier · ligne · nature · action.
Puis corrige :
- La source de vérité (offres.py) ne porte plus d'engagement ; les écrans affichent « 349 €/mois · sans engagement ».
- **CGV article 5 réécrit intégralement** : abonnement mensuel sans durée d'engagement, reconduit tacitement chaque mois, résiliable à tout moment par demande écrite adressée à LABUSE, effet à la fin de la période mensuelle en cours, mois entamé dû, accès maintenu jusqu'au terme payé. LABUSE conserve sa faculté de résilier avec préavis de 30 jours et remboursement de la période non servie.
- **Loi Chatel : sans objet** (elle encadre les contrats à durée déterminée reconductibles). Retirer la mention de l'article 5 ET de l'article 8 (où l'avis d'échéance est cité comme mail transactionnel). La mécanique avis-echeance : neutraliser la commande et RETIRER son cron (cf. EXPLOITATION-CRON.md), en le disant au rapport.
- Vérifier qu'aucun écran client ne propose une résiliation en self-service, et que le portail client Stripe (s'il est exposé) ne permet pas l'annulation directe — sinon le fermer et le dire.
- L'article 9 (plafond de responsabilité sur 12 mois glissants) reste inchangé — c'est une notion différente.
Test anti-régression : échoue si « engagement », « 12 mois » (hors art. 9) ou « L. 215-1 » réapparaît dans les écrans ou les CGV.

## S2 — PLANCHE D'ÉCRANS (livrable de vérification pour Vic)
Capture TOUS les écrans du parcours, desktop (1440) ET mobile (390), après les corrections S1. La liste part des routes réelles — ne l'invente pas ; l'inventaire E4 du mandat précédent en donne 9, vérifie s'il en manque. Au minimum : connexion · invitation client (souscription Intégral) · activation admin · Flash (saisie IDU, confirmation, attente, lien de téléchargement) · mot de passe oublié (demande + réinitialisation) · essai 48 h · abonnement à régulariser · session expirée / déconnexion · CGV · mentions légales · confidentialité.
Livre une **planche HTML unique** (docs/audit-2026-08/ONBOARDING/PLANCHE-ECRANS.html) : chaque écran en grand, titré, avec sa route, desktop et mobile côte à côte. Vic doit pouvoir la parcourir d'une traite et juger.
Pour chaque écran, indique au rapport s'il applique la **DA actuelle** (DA-LABUSE.html, vert #4ADE80, mauve réservé à l'IA, typographie d'identité) ou une DA ancienne/incohérente — et liste les écarts constatés. NE CORRIGE PAS la DA dans ce mandat : tu constates et tu documentes ; Vic arbitrera.

## S3 — LISIBILITÉ DES PAGES LÉGALES
Constat Vic : les CGV forment « un gros bloc amassé au centre », illisible. Refonds la mise en page des trois pages légales (CGV, mentions légales, confidentialité) — le fond et le texte juridique ne changent pas (hors S1), seule la présentation :
- Largeur de lecture confortable (~70 caractères par ligne), pas un bloc centré étroit ni pleine largeur.
- Hiérarchie claire : titres d'articles numérotés lisibles, espacement entre articles, interligne aéré.
- Sommaire cliquable en tête pour les CGV (les 10 articles), retour en haut.
- Lisible sur mobile (390) sans zoom.
- DA LABUSE respectée, sobre.

## FIN
Critères : zéro occurrence d'engagement/Chatel hors art. 9 (test qui le garantit) · CGV art. 5 réécrit · cron avis-echeance retiré · planche d'écrans livrée (desktop + mobile, tous les écrans, avec verdict DA par écran) · pages légales lisibles · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree). Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff fix/sans-engagement). Tu ne merges pas.
