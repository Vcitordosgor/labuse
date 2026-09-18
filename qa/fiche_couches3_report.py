"""Génère FICHE-COUCHES-3.md depuis /tmp/fc3_final.json (audit par la preuve)."""
import json

NOM = {
    'zfang': 'ZFANG (zone franche)', 'frr': 'FRR (revitalisation rurale)', 'tva_primo': 'TVA primo-accédant',
    'qpv': 'Quartiers prioritaires (QPV)', 'anru': 'Rénovation urbaine (ANRU)', 'parc_national': 'Parc national',
    'bassin_versant': 'Bassins versants', 'znieff': 'ZNIEFF (I & II)', 'enp': 'Espaces naturels protégés',
    'zone_humide': 'Zones humides', 'foret_publique': 'Forêts publiques', 'amenite_bpe': 'Équipements INSEE (BPE)',
    'amenite': 'Équipements OSM', 'sar': 'SAR — vocations', 'safer': 'Foncier agricole (RPG/SAFER)',
    'zone_activite': "Zones d'activité", 'friche': 'Friches', 'piscine_cosia': 'Piscines (CoSIA)',
    'vefa_neuf': 'Prix logement neuf (VEFA)', 'cimetiere': 'Cimetières', 'abf': 'Périmètres ABF',
    'ligne_mt': 'Lignes moyenne tension (HTA)', 'ligne_ht': 'Lignes haute tension (HTB)',
    'tri_zone': 'TRI — zones inondables', 'alea_inondation': 'Aléa inondation', 'alea_mvt': 'Aléa mouvement de terrain',
    'construction_surfacique': 'Barrages, ponts, dalles', 'casias': 'CASIAS', 'bruit_carte': 'Cartes de bruit',
    'bruit_route': 'Classement sonore', 'peb': "Plan d'exposition au bruit", 'endiguement': "Systèmes d'endiguement",
    'construction_lineaire': 'Murs de soutènement', 'trait_de_cote': 'Érosion côtière', 'dpf': 'Ravines et reculs (DPF)',
    'ppr': 'PPR multirisque', 'icpe': 'ICPE', 'sis': 'SIS', 'cavite': 'Cavités', 'tcsp': 'TCSP',
    'axe_structurant': 'Axes structurants', 'transport_ligne': 'Transport — lignes', 'telepherique': 'Téléphérique',
    'pole_echange': "Pôles d'échange", 'transport_arret': 'Transport — arrêts', 'zonage_parcelle': 'Zonage PLU parcelle',
    'plu_gpu_zone': 'Limites PLU (GPU)', 'cinquante_pas': '50 pas géométriques', 'artificialisation': 'Artificialisation (OCS GE)',
    'dpu': 'DPU', 'sup': 'SUP', 'er': 'Emplacements réservés', 'ebc': 'Espaces boisés classés',
}

d = json.load(open('/tmp/fc3_final.json'))
V = [r for r in d if r['verdict'] == 'VISIBLE']
M = [r for r in V if r['pdf']]
inv = [r for r in d if 'INVISIBLE' in r['verdict']]
absente = [r for r in d if r['verdict'] == 'ABSENTE']

out = []
out.append('# FICHE-COUCHES-3 — Audit du branchement couche → fiche, par la preuve\n')
out.append(f'## {len(V)} couches VISIBLE sur 53, dont {len(M)} dans le PDF Dossier expert.\n')
out.append(f'Répartition : **{len(V)} VISIBLE**, **{len(inv)} INTERROGÉE MAIS INVISIBLE**, '
           f'**{len(absente)} ABSENTE** (= 53).\n')
out.append('Branche `feat/couches-tuyau`, départ `854ad0bf`. **Lecture seule, aucune tuile touchée, '
           'aucune correction** — le rapport sert à décider si on débranche tout et on rebranche.\n')
out.append('## Méthode\n')
out.append('On ne lit pas le code : on prouve par l\'artefact. Pour chacune des 53 couches thématiques '
           '(56 − 3 fonds/repères), une parcelle témoin RÉELLEMENT concernée est choisie par requête SQL '
           '(intersection pour une surface, KNN sous le seuil pour une proximité). Sa fiche est ouverte '
           'dans le navigateur (accordéon `.fiche-v6`, tiroirs ouverts un à un) et l\'information cherchée ; '
           'le dry-run de cascade du run servi a été recalculé pour chaque témoin (les couches lues depuis '
           '`dryrun_cascade_results`). Verdict en un mot :\n')
out.append('- **VISIBLE** — l\'information apparaît dans la fiche (onglet + libellé + capture).\n'
           '- **INTERROGÉE MAIS INVISIBLE** — le back la calcule, la fiche ne l\'affiche pas.\n'
           '- **ABSENTE** — aucun croisement.\n')
out.append('Pour chaque VISIBLE, on vérifie aussi si la ligne est dans le **PDF Dossier expert** '
           '(`/dossier/{idu}.pdf`, `pdftotext` + recherche de termes). Le PDF est un sous-ensemble '
           'CURÉ (zonage, DPU, servitudes, dispositifs, propriétaire, pente) : la cascade « risques » '
           'et les proximités transport n\'y figurent pas, d\'où les 13 VISIBLE hors PDF.\n')
out.append('Preuve : 53 captures `<kind>_<parcelle>.png` dans `captures/fiche-couches3/`. '
           'Scripts rejouables : `qa/fiche_couches3_audit.py` (témoins + dry-run + back + PDF) et '
           '`frontend/qa/fiche_couches3_dom.mjs` (visibilité DOM + captures).\n')
out.append('## Le tableau des 53 couches\n')
out.append('| # | couche (kind) | parcelle témoin | verdict | onglet | libellé | dans le PDF | capture |')
out.append('|---|---------------|-----------------|---------|--------|---------|:-----------:|---------|')
for i, r in enumerate(d, 1):
    lib = (r['libelle'] or '').replace('|', '/').strip()[:88] or '—'
    pdf = 'oui' if r['pdf'] else ('—' if r['verdict'] != 'VISIBLE' else 'non')
    cap = f"{r['kind']}_{r['idu']}.png" if r['idu'] else '—'
    out.append(f"| {i} | {NOM.get(r['kind'], r['kind'])} (`{r['kind']}`) | {r['idu'] or '—'} | "
               f"{r['verdict']} | {r['onglet'] or '—'} | {lib} | {pdf} | {cap} |")
out.append('')
out.append('## Les cas particuliers\n')
out.append('- **INTERROGÉE MAIS INVISIBLE (1)** : `foret_publique` — le back calcule un HARD_EXCLUDE '
           '« Exclue : forêt domaniale (domaine public — terrain inacquérable) » (parcelle 97415000AH0019), '
           'mais aucun tiroir de la fiche ne l\'affiche (vérifié : ni Urbanisme, ni entête/verdict). '
           'La donnée atteint le moteur, pas l\'écran.\n')
out.append('- **ABSENTE (5)** : `piscine_cosia`, `vefa_neuf`, `cimetiere`, `construction_surfacique`, '
           '`construction_lineaire` — aucun croisement fiche (hors périmètre de FICHE-COUCHES-2). '
           'NB : la recherche naïve de « piscine » et « cimeti » tombe sur du texte SANS RAPPORT '
           '(détection de bâti CoSIA ; nom d\'arrêt « Cimetière de la Chaloupe ») — faux positifs écartés '
           'à la lecture du libellé, verdict ABSENTE confirmé.\n')
out.append('- **VISIBLE mais HORS PDF (13)** : ' + ', '.join(f"`{r['kind']}`" for r in V if not r['pdf'])
           + " — visibles à l'écran, absents du Dossier expert (curé).\n")

open('/Users/openclaw/Desktop/labuse-couches-tuyau/FICHE-COUCHES-3.md', 'w').write('\n'.join(out))
print(f'FICHE-COUCHES-3.md écrit — VISIBLE={len(V)}/53 dont PDF={len(M)} ; INVISIBLE={len(inv)} ; ABSENTE={len(absente)}')
