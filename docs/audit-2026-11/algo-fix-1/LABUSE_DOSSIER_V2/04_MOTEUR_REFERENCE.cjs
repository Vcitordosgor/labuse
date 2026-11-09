/* ALGO-LABUSE-2 — reference pedagogique, donnees fictives uniquement.
 * Aucun SIG, reglement PLU ou modele statistique n'est reconstitue ici.
 * Contrat : evaluate(record, options), order(records, options).
 * order renvoie les evaluations, avec les faits d'origine dans .record.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.LabuseV2 = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = 'ALGO-LABUSE-2-reference-demo-1.0';
  const LABELS = Object.freeze({
    ESTIMATED: 'Capacité théorique estimée',
    PRESTUDY: 'Préétude à mener',
    TO_VERIFY: 'Analyse à compléter',
    DEFERRED: 'À différer',
    NO_MARGIN: 'Aucun ajout identifié',
    OUTSIDE_OBJECTIVE: 'Hors de ce projet',
    SIGNAL_AVAILABLE: 'Signal de mutation disponible',
    SIGNAL_TO_VERIFY: 'Signal à vérifier',
    SIGNAL_NOT_AVAILABLE: 'Signal non évalué',
    SIGNAL_OUT_OF_SCOPE: 'Hors du domaine du modèle'
  });
  const GROUPS = Object.freeze({ESTIMATED:0, PRESTUDY:0, TO_VERIFY:1,
    DEFERRED:2, NO_MARGIN:3, OUTSIDE_OBJECTIVE:4,
    SIGNAL_AVAILABLE:0, SIGNAL_TO_VERIFY:1, SIGNAL_NOT_AVAILABLE:2,
    SIGNAL_OUT_OF_SCOPE:3});
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const nonnegative = value => finite(value) && value >= 0;
  const present = value => value !== null && value !== undefined;
  const normalizeId = value => typeof value === 'string' ? value.trim().toUpperCase() : '';
  const statusLabel = status => LABELS[status] || String(status);
  const formatQuantity = value => !finite(value) ? 'Non calculé'
    : value > 0 && value < 1 ? '<1 m²'
    : value < 0 && value > -1 ? '−<1 m²'
    : new Intl.NumberFormat('fr-FR', {maximumFractionDigits:2}).format(value) + ' m²';

  function optionsFor(input) {
    const supplied = input || {};
    const mode = supplied.mode || 'potential';
    const scenario = supplied.scenario || 'keep';
    const defaultSort = mode === 'sale' ? 'signal' : scenario === 'divide' ? 'area' : 'capacity';
    const opts = Object.assign({mode, scenario, sort:defaultSort, policy:'DEMO'}, supplied);
    if (!['sale','potential'].includes(opts.mode)) throw new RangeError('mode invalide');
    if (!['keep','rebuild','divide'].includes(opts.scenario)) throw new RangeError('scenario invalide');
    if (!['signal','capacity','gain','area','id'].includes(opts.sort)) throw new RangeError('sort invalide');
    if (opts.sort === 'signal' && opts.mode !== 'sale') throw new RangeError('tri Signal réservé à la prospection');
    if (opts.sort === 'gain' && (opts.mode !== 'potential' || opts.scenario !== 'rebuild'))
      throw new RangeError('tri gain net réservé à la reconstruction');
    if (opts.sort === 'capacity' && (opts.mode === 'sale' || opts.scenario === 'divide'))
      throw new RangeError('tri capacité réservé aux scénarios de capacité');
    return opts;
  }

  function evaluateSignal(record, opts) {
    const declared = String(record.signal_status || 'NOT_AVAILABLE').toUpperCase();
    const empty = (status, reason) => ({status, p:null, level:null,
      label:status === 'OUT_OF_SCOPE' ? 'Hors du domaine du modèle'
        : status === 'TO_VERIFY' ? 'Signal à vérifier' : 'Signal non évalué', reason});
    if (declared === 'OUT_OF_SCOPE') return empty('OUT_OF_SCOPE','SIGNAL_DOMAIN_OUT_OF_SCOPE');
    if (declared === 'NOT_AVAILABLE') return empty('NOT_AVAILABLE','SIGNAL_NOT_COMPUTED');
    if (declared === 'TO_VERIFY') return empty('TO_VERIFY','SIGNAL_DECLARED_UNVERIFIED');
    if (declared !== 'AVAILABLE') return empty('TO_VERIFY','SIGNAL_STATUS_INVALID');
    if (!present(record.p)) return empty('NOT_AVAILABLE','SERVED_PROBABILITY_MISSING');
    if (!finite(record.p) || record.p < 0 || record.p > 1)
      return empty('TO_VERIFY','SERVED_PROBABILITY_INVALID');
    // p est le champ declare comme probabilite servie dans les fixtures.
    // p_raw, logits et score historique sont volontairement ignores.
    if (record.signal_domain_verified !== true)
      return empty('TO_VERIFY','SIGNAL_DOMAIN_UNVERIFIED');
    const demoPermitted = opts.policy === 'DEMO' && record.demo === true;
    // La référence ne possède aucune politique de service de production.
    // Un booléen dans une fixture ne vaut pas validation d'un manifest réel.
    if (!demoPermitted)
      return empty('TO_VERIFY','SIGNAL_POLICY_UNVERIFIED');
    if (present(record.signal_value_kind) && record.signal_value_kind !== 'served_probability')
      return empty('TO_VERIFY','SIGNAL_VALUE_KIND_UNVERIFIED');
    const level = record.p >= 0.20 ? 'strong' : record.p >= 0.10 ? 'medium' : 'weak';
    return {status:'AVAILABLE', p:record.p, level,
      label:level === 'strong' ? 'Signal fort' : level === 'medium' ? 'Signal moyen' : 'Signal faible',
      reason:'SERVED_PROBABILITY', demo:demoPermitted};
  }

  function inspectBound(bound, central) {
    if (!present(bound)) return {present:false};
    const min = Array.isArray(bound) ? bound[0] : bound.min;
    const max = Array.isArray(bound) ? bound[1] : bound.max;
    if (!nonnegative(min) || !nonnegative(max) || min > max)
      return {present:true,error:'BOUNDS_INVALID'};
    if (finite(central) && (central < min || central > max))
      return {present:true,error:'CENTRAL_ESTIMATE_OUTSIDE_BOUNDS'};
    if (!bound.source || bound.documented !== true)
      return {present:true,error:'BOUNDS_NOT_DOCUMENTED'};
    return {present:true,min,max,source:bound.source};
  }

  function evaluate(input, inputOptions) {
    const opts = optionsFor(inputOptions);
    const record = input && typeof input === 'object' && !Array.isArray(input) ? input : {};
    const signal = evaluateSignal(record, opts);
    const result = {id:normalizeId(record.id), record, mode:opts.mode, scenario:opts.scenario,
      horizon:record.horizon || 'unknown', status:'TO_VERIFY', label:LABELS.TO_VERIFY, tone:'amber',
      quantities:{additional:null,project_total:null,existing:null,net_signed:null,conditional_future:null},
      bounds:null, cause_codes:[], warnings:[], signal, rank_value:null,
      analysis_version:VERSION};
    const cause = code => {if (!result.cause_codes.includes(code)) result.cause_codes.push(code);};
    const warning = message => {if (!result.warnings.includes(message)) result.warnings.push(message);};
    const finish = (status, code, label) => {
      result.status = status;
      result.label = label || LABELS[status];
      result.tone = status === 'ESTIMATED' ? 'green' : status === 'PRESTUDY' ? 'blue'
        : ['TO_VERIFY','DEFERRED','SIGNAL_TO_VERIFY'].includes(status) ? 'amber' : 'neutral';
      if (code) cause(code);
      if (opts.sort === 'id') result.rank_value = null;
      else if (opts.sort === 'area') result.rank_value = nonnegative(record.area) ? record.area : null;
      else if (opts.mode === 'sale') result.rank_value = signal.status === 'AVAILABLE' ? signal.p : null;
      else if (opts.scenario === 'divide') result.rank_value = nonnegative(record.area) ? record.area : null;
      // Une capacité future conditionnelle n'est pas le résiduel courant,
      // ni le gain net. Aucun tri de quantité non calculée n'est simulé.
      else if (status === 'DEFERRED') result.rank_value = null;
      else if (opts.scenario === 'rebuild') result.rank_value = opts.sort === 'gain'
        ? result.quantities.net_signed : result.quantities.project_total;
      else result.rank_value = result.quantities.additional;
      return result;
    };

    if (!result.id) return finish(opts.mode === 'sale' ? 'SIGNAL_TO_VERIFY' : 'TO_VERIFY','ID_MISSING');
    if (opts.mode === 'sale') {
      // Aucun zonage, SDP ou facteur physique ne change le Signal de cette vue.
      const map = {AVAILABLE:'SIGNAL_AVAILABLE',TO_VERIFY:'SIGNAL_TO_VERIFY',
        NOT_AVAILABLE:'SIGNAL_NOT_AVAILABLE',OUT_OF_SCOPE:'SIGNAL_OUT_OF_SCOPE'};
      const answer = finish(map[signal.status], signal.reason, signal.label);
      if (signal.status === 'AVAILABLE') answer.tone = signal.level === 'strong' ? 'green'
        : signal.level === 'medium' ? 'blue' : 'neutral';
      if (signal.demo) warning('Probabilité fictive de démonstration ; aucun modèle ML n’est exécuté.');
      return answer;
    }

    // Les avertissements n'ajoutent aucun coefficient au calcul.
    if (!present(record.slope)) warning('Pente non renseignée ; aucune pente favorable ou défavorable imputée.');
    else if (!nonnegative(record.slope)) warning('Valeur de pente à vérifier ; aucun coefficient appliqué.');
    else if (record.slope > 30) warning('Pente supérieure à 30 % : difficulté physique à étudier, sans malus numérique.');
    if (record.complexity) warning(String(record.complexity));
    if (Array.isArray(record.checks)) record.checks.forEach(item => warning(String(item)));
    if (!nonnegative(record.area) || record.area === 0) return finish('TO_VERIFY','PARCEL_AREA_INVALID');
    if (record.geometry_status !== 'valid') return finish('TO_VERIFY',
      record.geometry_status === 'suspect' ? 'GEOMETRY_SUSPECT' : 'GEOMETRY_NOT_AVAILABLE');
    if (record.eligibility === 'incompatible') {
      if (record.proof_verified === true) return finish('OUTSIDE_OBJECTIVE','HOUSING_INCOMPATIBILITY_PROVED');
      return finish('TO_VERIFY','INCOMPATIBILITY_PROOF_UNVERIFIED');
    }
    if (record.eligibility !== 'allowed') return finish('TO_VERIFY','HOUSING_ELIGIBILITY_UNKNOWN');
    if (record.horizon === 'deferred') {
      if (present(record.future_capacity) && !nonnegative(record.future_capacity)) {
        cause('FUTURE_CAPACITY_INVALID');
        warning('Hypothèse future invalide : quantité non servie ; le caractère différé reste établi.');
      }
      result.quantities.conditional_future = nonnegative(record.future_capacity) ? record.future_capacity : null;
      if (nonnegative(record.existing)) result.quantities.existing = record.existing;
      warning('Capacité conditionnelle ; aucune date d’ouverture ni disponibilité actuelle n’est inventée.');
      return finish('DEFERRED','AVAILABILITY_DEFERRED');
    }
    if (record.horizon !== 'now') return finish('TO_VERIFY','AVAILABILITY_HORIZON_UNKNOWN');
    if (opts.scenario === 'divide') {
      warning('Préétude documentaire : divisibilité, nombre de lots, accès individuels et viabilisation non calculés.');
      return finish('PRESTUDY','DIVISION_DOCUMENTARY_PRESTUDY');
    }

    if (record.height_status === 'missing' && record.height_required !== false)
      return finish('TO_VERIFY','HEIGHT_CRITICAL_MISSING');
    if (!present(record.capacity)) return finish('TO_VERIFY','CAPACITY_MISSING');
    if (!nonnegative(record.capacity)) return finish('TO_VERIFY','CAPACITY_INVALID');
    if (!present(record.existing)) return finish('TO_VERIFY','EXISTING_SDP_MISSING');
    if (!nonnegative(record.existing)) return finish('TO_VERIFY','EXISTING_SDP_INVALID');

    const C = record.capacity, E = record.existing;
    result.quantities.project_total = C;
    result.quantities.existing = E;
    result.quantities.net_signed = C - E;
    result.quantities.additional = Math.max(0, C - E);
    const capacityBound = inspectBound(record.capacity_bounds,C);
    const existingBound = inspectBound(record.existing_bounds,E);
    if (capacityBound.error || existingBound.error)
      return finish('TO_VERIFY',capacityBound.error || existingBound.error);
    if (capacityBound.present && existingBound.present) {
      const gain = {min:capacityBound.min-existingBound.max,max:capacityBound.max-existingBound.min};
      const additional = {min:Math.max(0,gain.min),max:Math.max(0,gain.max)};
      result.bounds = {
        additional_interval:[additional.min,additional.max],
        gain_interval:[gain.min,gain.max],
        capacity_interval:[capacityBound.min,capacityBound.max],
        existing_interval:[existingBound.min,existingBound.max],
        sources:[capacityBound.source,existingBound.source],
        kind:'documented_assumption_envelope'
      };
      warning('Enveloppes d’hypothèses documentées ; pas un intervalle de confiance statistique.');
      if (opts.scenario === 'keep' && gain.min <= 0 && gain.max > 0)
        return finish('TO_VERIFY','ADDITIONAL_CAPACITY_ENVELOPE_CROSSES_ZERO');
    } else {
      warning('Estimation ponctuelle ; incertitude non quantifiée.');
      if (capacityBound.present || existingBound.present)
        warning('Une seule entrée bornée : aucune enveloppe de résultat n’est inventée.');
    }

    if (opts.scenario === 'keep') {
      warning('Marge par différence : insertion avec le bâti conservé non vérifiée par ce moteur pédagogique.');
      return result.quantities.additional === 0
        ? finish('NO_MARGIN','NO_ADDITIONAL_BUDGET','Aucun ajout identifié selon les hypothèses')
        : finish('ESTIMATED','ADDITIONAL_BUDGET_ESTIMATED');
    }
    if (E === 0) warning('Terrain déjà nu : aucune démolition nécessaire.');
    else warning('Occupation, démolition, protections, relogement et coûts restent à vérifier.');
    if (C - E < 0) warning('La reconstruction présente une perte théorique de SDP ; ce n’est pas une conclusion économique.');
    return C === 0 ? finish('NO_MARGIN','NO_REBUILD_CAPACITY','Aucune capacité identifiée selon les hypothèses')
      : finish('ESTIMATED','REBUILD_CAPACITY_ESTIMATED');
  }

  function order(records, inputOptions) {
    if (!Array.isArray(records)) throw new TypeError('records doit être un tableau');
    const opts = optionsFor(inputOptions);
    return records.map(record => evaluate(record,opts)).sort((a,b) => {
      const group = GROUPS[a.status] - GROUPS[b.status];
      if (group) return group;
      if (opts.sort !== 'id') {
        const aKnown = finite(a.rank_value), bKnown = finite(b.rank_value);
        if (aKnown !== bKnown) return aKnown ? -1 : 1;
        if (aKnown && a.rank_value !== b.rank_value) return b.rank_value - a.rank_value;
      }
      return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    });
  }

  return Object.freeze({VERSION,DEMO_ONLY:true,STATUS_LABELS:LABELS,
    evaluate,order,formatQuantity,normalizeId,statusLabel});
});
