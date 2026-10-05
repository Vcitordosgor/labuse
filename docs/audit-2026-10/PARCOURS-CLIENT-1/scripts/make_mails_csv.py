import json, csv, os
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
rows = json.load(open('mails/MAILS_render.json'))
TRIG = {
 'essai': "Creation essai (B1) + bouton Renvoyer l'invitation (B3)",
 'souscription': "Creer un client (lien d'abonnement, manuel)",
 'onboarding1': "Mail de bienvenue (fiche) / post-activation",
 'onboarding2': "Job onboarding - relance J+3",
 'onboarding3': "Job onboarding - dernier rappel J+10",
 'relance_carte': "Echec paiement Stripe (facturation.py)",
 'suspension': "AUCUN geste auto (le bouton Suspendre ne l'envoie pas)",
 'retablissement': "AUCUN geste auto (le bouton Retablir ne l'envoie pas)",
 'radar_digest': "Job Radar - digest quotidien",
 'radar_alerte': "Job Radar - alerte de veille",
 'mdp_oublie': "Mot de passe oublie (client) + reset admin (fiche)",
 'mdp_modifie': "Changement de mot de passe (client)",
 'resiliation': "Fin d'abonnement (facturation)",
 'flash_pret': "Rapport Flash pret au telechargement",
 'email_change': "Changement d'adresse e-mail",
 'retour_traite': "Reponse a un signalement (dashboard retours)",
}
w = csv.writer(open('MAILS.csv', 'w', newline=''))
w.writerow(['id', 'key', 'libelle', 'objet', 'expediteur', 'reply_to', 'actif', 'declencheur',
            'variables_non_remplies', 'lien_localhost', 'desabonnement', 'verdict', 'capture_desktop', 'capture_mobile'])
for r in rows:
    vars_ = ';'.join(r['variables_non_remplies']) or '-'
    loc = 'oui' if (r['contient_127'] or r['contient_localhost']) else 'non'
    notes = []
    verdict = 'OK'
    if r['variables_non_remplies']:
        verdict = 'GENANT'; notes.append('variables brutes')
    if r['contient_127'] or r['contient_localhost']:
        verdict = 'GENANT'; notes.append('lien localhost')
    if not r['a_desabonnement'] and r['key'] in ('radar_digest', 'radar_alerte'):
        verdict = 'GENANT'; notes.append('pas de desabo (mail recurrent)')
    if r['key'] == 'resiliation':
        notes.append('objet prefixe "le" dans le template (double "le" si le caller passe une date avec "le")')
    if r['key'] in ('suspension', 'retablissement'):
        verdict = 'GENANT'; notes.append('aucun geste ne le declenche automatiquement')
    verdict = verdict + (' - ' + '; '.join(notes) if notes else '')
    cap = 'mails/%02d-%s-desktop.png' % (r['id'], r['key'])
    capm = 'mails/%02d-%s-mobile.png' % (r['id'], r['key'])
    w.writerow([r['id'], r['key'], r['libelle'], r['subject'], r.get('sender'), r.get('replyTo'),
                r.get('isActive'), TRIG.get(r['key'], '?'), vars_, loc,
                'oui' if r['a_desabonnement'] else 'non', verdict, cap, capm])
print('MAILS.csv written', len(rows), 'rows')
