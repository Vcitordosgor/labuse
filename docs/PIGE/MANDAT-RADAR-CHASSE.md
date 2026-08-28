# MANDAT — RADAR : CHASSE AUX BUGS
Régime AUTONOME. Findings RD-501→. RÈGLES COMMUNES.
Le Radar a été construit en quatre mandats successifs (P0/P2, P1, P3, P4-P5-P6), chacun vert sur SA branche. Personne n'a encore éprouvé l'ensemble d'un bout à l'autre, sous stress, avec des entrées hostiles. C'est l'objet de cette passe.

## ESPRIT DE LA PASSE
Tu ne construis rien. Tu **cherches à casser**. Un mandat qui revient avec « tout va bien » après avoir gentiment rejoué le chemin nominal n'a rien vérifié : le chemin nominal est déjà couvert par les tests de chaque lot. Ce qui t'intéresse, c'est ce que personne n'a essayé.
Corrige au fil de l'eau ce que tu casses, sauf si la correction change le comportement voulu — dans ce cas, note le finding et laisse la décision à Vic.
Le Radar doit être PARFAIT : c'est un outil que Vic va utiliser tous les jours et montrer à des clients à 349 €/mois.

## C1 — LE PARCOURS COMPLET, EN VRAI
Déroule la chaîne entière avec de vraies données, plusieurs fois, dans des ordres différents :
dépôt de capture → extraction → correction → validation → rattachement → apparition côté client → clic sortant → veille → digest → cycle de vie → statistiques Marché.
Vérifie que ce qui sort à chaque étape est bien ce qui entre à la suivante. Les bugs d'intégration vivent aux jointures entre les lots, pas au milieu.

## C2 — ENTRÉES HOSTILES ET CAS TORDUS
Attaque l'intake et l'extraction avec ce qu'un usage réel produira tôt ou tard :
capture illisible, floue, tronquée · capture qui n'est pas une annonce (une photo au hasard, une capture d'écran d'autre chose) · image énorme, image de 1 pixel, fichier corrompu, extension mensongère (un .png qui est un .pdf) · lien vide, lien malformé, lien qui n'est pas une URL, lien vers un portail inconnu, lien avec des paramètres de suivi · même capture déposée deux fois, dix fois · dépôt simultané de vingt captures · caractères spéciaux, accents, emoji dans les champs corrigés à la main · prix à zéro, prix négatif, prix absurde (1 € ou 99 millions) · surface à zéro, surface plus grande que la parcelle · date de publication dans le futur · commune limitrophe hors des 24 · annonce sans aucun champ lisible.
Pour chacun : le système refuse-t-il proprement, avec un message honnête, sans rien écrire de faux en base ? Ou avale-t-il l'erreur en silence ?

## C3 — LES INVARIANTS DE LA DOCTRINE, ÉPROUVÉS
Ce sont les promesses que le Radar ne doit jamais rompre. Cherche activement à les faire tomber :
- **Aucun contenu d'annonce** nulle part — base, API, mails, exports, logs, réponses d'erreur, page admin. Fouille les payloads réels, pas seulement le code.
- **Aucune capture servie par le web** : essaie d'y accéder par une URL construite à la main, teste la traversée de chemin, vérifie les permissions du répertoire.
- **Carte = rattachés seulement.** Essaie de faire apparaître un non-rattaché sur la carte par un filtre tordu, un tri, une pagination, un état d'URL bricolé.
- **`retiree_sans_vente` jamais déduit d'un lien mort.** Fabrique le scénario piège : bien retiré, aucune mutation DVF, moins de 12 mois → il doit rester `retiree`.
- **Écart de prix seulement sur Sourcé.** Tente de le faire afficher sur un Estimé.
- **n < 5 = pas de chiffre** dans l'onglet Marché. Fabrique une commune à 4 biens et vérifie qu'aucune médiane ne fuit.
- **Anti-invention** : un champ absent de la capture reste-t-il null jusqu'au bout de la chaîne, ou quelqu'un le remplit-il en route ?
- **Aucun appel réseau vers un portail** : au-delà du grep de P0, surveille le trafic réel pendant un parcours complet.

## C4 — CLOISONNEMENT ET DROITS
- Un client peut-il voir les biens **non validés** (brouillons de l'intake) ? Essaie par l'API directement, pas par l'écran.
- Un client peut-il voir les **captures**, les métadonnées internes, les confiances d'extraction ?
- Un compte non-admin peut-il atteindre les endpoints admin du Radar ? Un compte non connecté ?
- **Deux comptes clients différents** : l'un voit-il les veilles, les clics ou les signalements de l'autre ? (Rappel : une dette IDOR à deux comptes est déjà notée dans le projet — vérifie qu'elle ne s'applique pas au Radar.)
- Les clics et signalements sont-ils bien attribués au bon compte ?

## C5 — VOLUME ET DURÉE
- Charge le Radar avec un volume réaliste à six mois (plusieurs milliers de biens, historiques de prix, clics) et mesure : liste filtrée, carte, fiche, onglet Marché, file de re-vérification. Ce qui est fluide à 20 biens ne l'est pas forcément à 5 000.
- Les jobs de cycle de vie sur ce volume : combien de temps, quelles requêtes lourdes, y a-t-il des index qui manquent ?
- Les deux digests avec plusieurs dizaines de clients et de veilles : combien d'appels, combien de temps, que se passe-t-il si Brevo est lent ou indisponible en plein envoi ?
- L'extraction vision sur vingt captures d'affilée : coût réel constaté, comportement en cas de limite de débit de l'API.

## C6 — L'ÉTAT DE DÉMARRAGE ET LES ÉTATS VIDES
C'est l'état dans lequel Vic verra le Radar demain matin : rien dedans.
Chaque écran, chaque compteur, chaque agrégat, chaque mail doit être digne et honnête à zéro donnée. Pas d'écran blanc, pas de « NaN », pas de « 0 %', pas de division par zéro, pas de médiane sur rien, pas de mail vide. Parcours-les tous.
Puis l'état à une seule donnée, et l'état à quatre (le seuil du n<5).

## FIN
Rapport docs/PIGE/RAPPORT-CHASSE.md : ce que tu as tenté (la liste complète des attaques, y compris celles qui n'ont rien donné — c'est ça qui prouve la couverture), ce qui a cassé, ce que tu as corrigé, ce que tu laisses à Vic et pourquoi. Findings RD-5xx numérotés avec leur gravité.
Un mandat honnête peut conclure « voici les 40 attaques tentées, 6 ont cassé, 5 corrigées, 1 laissée à l'arbitrage ». Un mandat qui conclut « tout va bien » sans liste d'attaques n'a pas fait le travail.
Critères : gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · [CHASSE-TEST] purgés (vérifié SQL) · le test anti-requêtes-portails reste vert.
Compte-rendu « Demandé → traité » + commande de merge en dernier élément isolé (git merge --no-ff fix/radar-chasse). Tu ne merges pas.
