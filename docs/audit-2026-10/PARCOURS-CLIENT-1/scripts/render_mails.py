"""SECTION A — rend les 16 templates Brevo en LECTURE SEULE (GET /v3/smtp/templates/{id}),
substitue des valeurs de test, écrit le HTML + un résumé JSON. N'ENVOIE RIEN."""
import os, sys, json, re
os.environ.setdefault('LABUSE_DATABASE_URL', 'postgresql+psycopg://openclaw@localhost:5432/labuse')
sys.path.insert(0, 'src')
import httpx
from labuse import brevo

OUT = 'docs/audit-2026-10/PARCOURS-CLIENT-1/mails'
os.makedirs(OUT + '/html', exist_ok=True)

PROD = 'https://app.labuse.immo'
# valeurs de test couvrant TOUS les params + flags du registre
BASE_PARAMS = {
    'PRENOM': 'Rémi',
    'EMAIL': 'remi.teoule@cabinet-foncier.re',
    'LIEN_INVITATION': PROD + '/invitation?token=TESTTOKEN',
    'LIEN_SOUSCRIPTION': PROD + '/souscrire',
    'LIEN_PAIEMENT': PROD + '/facturation',
    'LIEN_RESET': PROD + '/reset?token=TESTRESET',
    'LIEN_PDF': PROD + '/flash/telecharger/XYZ.pdf',
    'FIN_ESSAI': 'mardi 7 octobre 2026 à 18 h 00 (heure Réunion)',
    'DATE_FIN_ACCES': 'le 12 octobre 2026',
    'DATE_HEURE': '5 octobre 2026 à 21 h 30 (heure Réunion)',
    'DATE': '5 octobre 2026',
    'VALIDITE': '1 heure',
    'NB_BIENS': '7',
    'CARTES': '<div style="padding:8px;border:1px solid #ddd">7 biens — aperçu</div>',
    'VEILLE': 'Saint-Denis — terrains < 400 m²',
    'CRITERES': 'Saint-Denis · terrain · < 400 m²',
    'IDU': '974110000AB0123',
    'COMMUNE': 'Saint-Denis',
    'ANCIEN_EMAIL': 'ancien@cabinet-foncier.re',
    'NOUVEL_EMAIL': 'nouveau@cabinet-foncier.re',
    'SON_MESSAGE': 'La surface affichée me paraît fausse sur la parcelle AB0123.',
    'REPONSE': 'Merci — la surface a été corrigée après vérification cadastrale.',
    # flags conditionnels → True pour exercer les blocs {% if %}
    'RENVOI': True, 'JAMAIS_CONNECTE': True,
}

api = brevo._api_key()
rows = []
for key, t in brevo.REGISTRE.items():
    tid = brevo.template_id(key)
    row = {'key': key, 'id': tid, 'nom': t.nom, 'libelle': t.libelle,
           'params_attendus': list(t.params), 'flags': list(t.flags)}
    # métadonnées brutes (sender, replyTo, isActive)
    try:
        r = httpx.get(f'https://api.brevo.com/v3/smtp/templates/{tid}',
                      headers={'api-key': api}, timeout=20.0)
        data = r.json() if r.status_code // 100 == 2 else {}
        row['http'] = r.status_code
        row['isActive'] = data.get('isActive')
        row['sender'] = (data.get('sender') or {}).get('email')
        row['sender_name'] = (data.get('sender') or {}).get('name')
        row['replyTo'] = data.get('replyTo')
        row['subject_brut'] = data.get('subject')
    except Exception as e:
        row['http'] = 'ERR ' + type(e).__name__
    # rendu substitué (apercu)
    params = {k: BASE_PARAMS[k] for k in (list(t.params) + list(t.flags)) if k in BASE_PARAMS}
    params.setdefault('PRENOM', 'Rémi')
    ap = brevo.apercu_template(key, params=params)
    subject = ap.get('subject') or ''
    html = ap.get('html') or ''
    row['subject'] = subject
    row['configure'] = ap.get('configure')
    # vérifications
    reste = re.findall(r'\{\{[^}]+\}\}', subject + ' ' + html)
    row['variables_non_remplies'] = reste[:8]
    row['contient_127'] = ('127.0.0.1' in html) or ('127.0.0.1' in subject)
    row['contient_localhost'] = ('localhost' in html.lower())
    row['a_desabonnement'] = bool(re.search(r'désabonn|desabonn|désinscri|desinscri', html, re.I))
    row['a_mentions'] = bool(re.search(r'mentions légales|LABUSE|SIREN|SAS|contact@labuse', html, re.I))
    row['a_signature'] = bool(re.search(r'LABUSE', html))
    row['html_len'] = len(html)
    # écrire le html pour capture
    open(f'{OUT}/html/{row["id"]:02d}-{key}.html', 'w', encoding='utf-8').write(
        f'<!doctype html><meta charset=utf-8><title>{key} — {subject}</title>'
        f'<div style="background:#eee;padding:10px;font:13px system-ui;border-bottom:2px solid #333">'
        f'<b>Template {row["id"]} · {key}</b> — <b>Objet :</b> {subject}<br>'
        f'<b>Expéditeur :</b> {row.get("sender_name") or "?"} &lt;{row.get("sender") or "?"}&gt; · '
        f'<b>Reply-To :</b> {row.get("replyTo") or "—"}</div>' + html)
    rows.append(row)

json.dump(rows, open(f'{OUT}/MAILS_render.json', 'w'), ensure_ascii=False, indent=1)
# résumé compact
for r in rows:
    print(f"#{r['id']:>2} {r['key']:<14} act={r.get('isActive')} send={r.get('sender')} "
          f"reply={r.get('replyTo')} 127={r['contient_127']} vars={r['variables_non_remplies']} "
          f"desabo={r['a_desabonnement']} len={r['html_len']}  OBJET={r['subject'][:48]}")
