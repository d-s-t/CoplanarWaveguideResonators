async function fetchOptions() {
  const res = await fetch('/api/options');
  if (!res.ok) throw new Error('Failed to load options');
  return res.json();
}

// debounce helper
function debounce(fn, wait) {
  let t = null;
  return (...args) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

function _computeRange(defn) {
  let d = (defn && defn.default !== undefined) ? Number(defn.default) : 0;
  let min = defn && defn.min !== undefined && defn.min !== null ? Number(defn.min) : null;
  let max = defn && defn.max !== undefined && defn.max !== null ? Number(defn.max) : null;
  let step = defn && defn.step !== undefined && defn.step !== null ? Number(defn.step) : null;

  if (min === null || max === null) {
    if (d === 0) {
      min = -1;
      max = 1;
    } else if (d > 0) {
      min = Math.max(d * 0.01, d * 0.5);
      max = d * 1.5;
    } else {
      min = d * 1.5;
      max = d * 0.5;
      if (min > max) [min, max] = [max, min];
    }
  }

  if (!step || step === 0) {
    const span = Math.abs(max - min);
    if (span === 0) step = Math.abs(d) / 100 || 1e-6;
    else {
      step = span / 100;
      if (Number.isInteger(min) && Number.isInteger(max) && Math.abs(step) >= 1) step = Math.max(1, Math.round(step));
    }
  }

  return {min, max, step, default: d};
}

// stored parameters per category/option
const storedParams = {
  transition_lines: {},
  capacitor_couplings: {},
  substrates: {}
};

function createParamControl(name, defn, container, paramsStore, onChange) {
  const wrapper = document.createElement('div');
  wrapper.className = 'param';

  const label = document.createElement('label');
  label.textContent = name;
  wrapper.appendChild(label);

  const controls = document.createElement('div');
  controls.className = 'param-controls';

  const r = _computeRange(defn);

  const inputNumber = document.createElement('input');
  inputNumber.type = 'number';
  inputNumber.className = 'param-number';
  inputNumber.min = r.min;
  inputNumber.max = r.max;
  inputNumber.step = r.step;
  inputNumber.value = (paramsStore && paramsStore[name] !== undefined) ? paramsStore[name] : r.default;

  // initialize store value
  paramsStore[name] = Number(inputNumber.value);

  inputNumber.addEventListener('input', () => {
    paramsStore[name] = Number(inputNumber.value);
    const range = wrapper.querySelector('.param-range');
    if (range) range.value = inputNumber.value;
    if (onChange) onChange();
  });

  controls.appendChild(inputNumber);

  const inputRange = document.createElement('input');
  inputRange.type = 'range';
  inputRange.className = 'param-range';
  inputRange.min = r.min;
  inputRange.max = r.max;
  inputRange.step = r.step;
  inputRange.value = inputNumber.value;

  inputRange.addEventListener('input', () => {
    inputNumber.value = inputRange.value;
    paramsStore[name] = Number(inputRange.value);
    if (onChange) onChange();
  });

  controls.appendChild(inputRange);

  // Special case: substrate permittivity/permeability sliders should be narrower
  if (container && container.id === 'substrate_params' && (name.includes('permitt') || name.includes('permeab'))) {
    inputRange.classList.add('narrow-range');
    inputNumber.classList.add('narrow-number');
  }

  wrapper.appendChild(controls);
  container.appendChild(wrapper);
}

function clearChildren(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function renderParamsFor(category, selectEl, paramsContainerEl, optionsMap, onChange) {
  clearChildren(paramsContainerEl);
  const key = selectEl.value;
  const entry = optionsMap[key];
  const params = (entry && entry.parameters) ? entry.parameters : {};

  // ensure we have a stored params object for this selection
  if (!storedParams[category][key]) {
    storedParams[category][key] = {};
    // prefill with defaults
    Object.keys(params).forEach(pn => {
      const d = params[pn] && params[pn].default !== undefined ? params[pn].default : 0;
      storedParams[category][key][pn] = d;
    });
  }

  const paramsStore = storedParams[category][key];

  Object.keys(params).forEach(pname => {
    createParamControl(pname, params[pname], paramsContainerEl, paramsStore, onChange);
  });
}

function buildSelector(map, selectEl) {
  Object.keys(map).forEach(k => {
    const opt = document.createElement('option');
    opt.value = k;
    opt.textContent = k; // remove class name from label
    selectEl.appendChild(opt);
  });
}

// helper: deep clone simple object (numbers)
function cloneParams(obj) {
  const out = {};
  for (const k in obj) out[k] = obj[k];
  return out;
}

async function main() {
  let opts;
  try {
    opts = await fetchOptions();
  } catch (e) {
    alert('Could not load options: ' + e.message);
    return;
  }

  const tSelect = document.getElementById('transition_line_select');
  const inSelect = document.getElementById('input_coupling_select');
  const outSelect = document.getElementById('output_coupling_select');
  const sSelect = document.getElementById('substrate_select');
  const symmetricCheckbox = document.getElementById('symmetric_checkbox');

  // containers and symmetric controls
  const inputContainer = document.getElementById('input_container');
  const outputContainer = document.getElementById('output_container');
  const symmetricContainer = document.getElementById('symmetric_container');
  const symmetricSelect = document.getElementById('symmetric_coupling_select');
  const symmetricParamsContainer = document.getElementById('symmetric_coupling_params');

  buildSelector(opts.transition_lines, tSelect);
  buildSelector(opts.capacitor_couplings, inSelect);
  buildSelector(opts.capacitor_couplings, outSelect);
  buildSelector(opts.capacitor_couplings, symmetricSelect);
  buildSelector(opts.substrates, sSelect);

  // set defaults without resetting other selections
  if (opts.defaults) {
    if (!tSelect.value) tSelect.value = opts.defaults.transition_line;
    if (!inSelect.value) inSelect.value = opts.defaults.input_coupling;
    if (!outSelect.value) outSelect.value = opts.defaults.output_coupling;
    if (!sSelect.value) sSelect.value = opts.defaults.substrate;
    if (!symmetricSelect.value) symmetricSelect.value = opts.defaults.input_coupling;
  }

  const tParamsContainer = document.getElementById('transition_line_params');
  const inParamsContainer = document.getElementById('input_coupling_params');
  const outParamsContainer = document.getElementById('output_coupling_params');
  const sParamsContainer = document.getElementById('substrate_params');

  const modeNumber = document.getElementById('mode_n_number');
  const modeRange = document.getElementById('mode_n_range');

  // schedule simulation with debounce
  const doSimulate = debounce(async () => {
    const n = parseInt(modeNumber.value) || 1;

    // determine whether symmetric mode is active
    const symmetric = !!symmetricCheckbox.checked;
    let inputName = inSelect.value;
    let outputName = outSelect.value;
    let inputParams = storedParams.capacitor_couplings[inputName] || {};
    let outputParams = storedParams.capacitor_couplings[outputName] || {};

    if (symmetric) {
      // authoritative control is symmetricSelect
      const symName = symmetricSelect.value;
      inputName = symName;
      outputName = symName;
      const symParams = storedParams.capacitor_couplings[symName] || {};
      inputParams = symParams;
      outputParams = symParams;
      // ensure the hidden input/output storedParams are present
      storedParams.capacitor_couplings[inputName] = cloneParams(symParams);
      storedParams.capacitor_couplings[outputName] = cloneParams(symParams);
      // keep the hidden selects in sync
      inSelect.value = symName;
      outSelect.value = symName;
    }

    const payload = {
      transition_line: tSelect.value,
      input_coupling: inputName,
      output_coupling: outputName,
      substrate: sSelect.value,
      transition_line_params: storedParams.transition_lines[tSelect.value] || {},
      input_coupling_params: inputParams,
      output_coupling_params: outputParams,
      substrate_params: storedParams.substrates[sSelect.value] || {},
      n: n,
      symmetric: symmetric
    };

    try {
      const res = await fetch('/api/simulate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.error) {
        console.error('Simulation error', data.error);
        return;
      }

      document.getElementById('w1').textContent = (data.w1 !== null && data.w1 !== undefined) ? Number(data.w1).toExponential(3) : '-';
      document.getElementById('f1').textContent = (data.f1 !== null && data.f1 !== undefined) ? Number(data.f1).toExponential(3) : '-';
      document.getElementById('q_i').textContent = (data.q_internal !== null && data.q_internal !== undefined) ? Number(data.q_internal).toExponential(3) : '-';
      document.getElementById('q_e').textContent = (data.q_external !== null && data.q_external !== undefined) ? Number(data.q_external).toExponential(3) : '-';
      document.getElementById('q_tot').textContent = (data.q_total !== null && data.q_total !== undefined) ? Number(data.q_total).toExponential(3) : '-';

      const plotDiv = document.getElementById('plot');
      const qNames = ['Q_internal', 'Q_external', 'Q_total'];
      const qVals = [data.q_internal || 0, data.q_external || 0, data.q_total || 0];

      const trace = { x: qNames, y: qVals, type: 'bar' };
      const layout = { title: 'Quality Factors', yaxis: {title: 'Q'} };
      if (window.Plotly) Plotly.newPlot(plotDiv, [trace], layout, {responsive: true});

      // render getters under each component
      if (data.getters) {
        const ig = document.getElementById('input_coupling_getters');
        const og = document.getElementById('output_coupling_getters');
        const tg = document.getElementById('transition_line_getters');
        const sg = document.getElementById('substrate_getters');
        const sg_sym = document.getElementById('symmetric_coupling_getters');

        ig.innerHTML = '';
        og.innerHTML = '';
        tg.innerHTML = '';
        sg.innerHTML = '';
        if (sg_sym) sg_sym.innerHTML = '';

        if (data.getters.input_coupling && data.getters.input_coupling.capacitance !== undefined) {
          const d = document.createElement('div');
          d.textContent = 'capacitance: ' + Number(data.getters.input_coupling.capacitance).toExponential(3);
          ig.appendChild(d);
        }
        if (data.getters.output_coupling && data.getters.output_coupling.capacitance !== undefined) {
          const d = document.createElement('div');
          d.textContent = 'capacitance: ' + Number(data.getters.output_coupling.capacitance).toExponential(3);
          og.appendChild(d);
        }
        if (data.getters.transition_line) {
          const tvals = data.getters.transition_line;
          Object.keys(tvals).forEach(k => {
            const v = tvals[k];
            const d = document.createElement('div');
            d.textContent = k + ': ' + (v === null || v === undefined ? '-' : (typeof v === 'number' ? Number(v).toExponential(3) : String(v)));
            tg.appendChild(d);
          });
        }
        if (data.getters.substrate) {
          const svals = data.getters.substrate;
          Object.keys(svals).forEach(k => {
            const v = svals[k];
            const d = document.createElement('div');
            d.textContent = k + ': ' + (v === null || v === undefined ? '-' : (typeof v === 'number' ? Number(v).toExponential(3) : String(v)));
            sg.appendChild(d);
          });
        }
        // if symmetric, render symmetric getter too
        if (symmetric && data.getters.input_coupling) {
          const d = document.createElement('div');
          d.textContent = 'capacitance: ' + Number(data.getters.input_coupling.capacitance).toExponential(3);
          if (sg_sym) sg_sym.appendChild(d);
        }
      }

    } catch (err) {
      console.error('Simulator request failed', err);
    }
  }, 250);

  // helper to re-render param panels and attach onChange to trigger simulate
  const renderAll = () => {
    renderParamsFor('transition_lines', tSelect, tParamsContainer, opts.transition_lines, doSimulate);
    renderParamsFor('capacitor_couplings', inSelect, inParamsContainer, opts.capacitor_couplings, doSimulate);
    renderParamsFor('capacitor_couplings', outSelect, outParamsContainer, opts.capacitor_couplings, doSimulate);
    renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
    renderParamsFor('substrates', sSelect, sParamsContainer, opts.substrates, doSimulate);

    // if symmetric initially, show/hide containers accordingly
    if (symmetricCheckbox.checked) {
      inputContainer.style.display = 'none';
      outputContainer.style.display = 'none';
      symmetricContainer.style.display = 'block';
      // ensure symmetricSelect value synced
      symmetricSelect.value = inSelect.value;
      storedParams.capacitor_couplings[symmetricSelect.value] = cloneParams(storedParams.capacitor_couplings[inSelect.value] || {});
    } else {
      inputContainer.style.display = 'block';
      outputContainer.style.display = 'block';
      symmetricContainer.style.display = 'none';
    }

    // trigger simulate after re-render
    doSimulate();
  };

  tSelect.addEventListener('change', () => { renderParamsFor('transition_lines', tSelect, tParamsContainer, opts.transition_lines, doSimulate); doSimulate(); });

  inSelect.addEventListener('change', () => {
    renderParamsFor('capacitor_couplings', inSelect, inParamsContainer, opts.capacitor_couplings, doSimulate);
    if (symmetricCheckbox.checked) {
      // when symmetric is on, update symmetric select to match input
      symmetricSelect.value = inSelect.value;
      storedParams.capacitor_couplings[symmetricSelect.value] = cloneParams(storedParams.capacitor_couplings[inSelect.value] || {});
      renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
    }
    doSimulate();
  });

  outSelect.addEventListener('change', () => {
    renderParamsFor('capacitor_couplings', outSelect, outParamsContainer, opts.capacitor_couplings, doSimulate);
    if (symmetricCheckbox.checked) {
      // if user changes output while symmetric is on, keep symmetric in sync
      symmetricSelect.value = outSelect.value;
      storedParams.capacitor_couplings[symmetricSelect.value] = cloneParams(storedParams.capacitor_couplings[outSelect.value] || {});
      renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
    }
    doSimulate();
  });

  symmetricSelect.addEventListener('change', () => {
    // when symmetric_select changes, copy its stored params to input and output and re-render hidden panels
    const sym = symmetricSelect.value;
    storedParams.capacitor_couplings[sym] = storedParams.capacitor_couplings[sym] || {};
    inSelect.value = sym;
    outSelect.value = sym;
    storedParams.capacitor_couplings[inSelect.value] = cloneParams(storedParams.capacitor_couplings[sym] || {});
    storedParams.capacitor_couplings[outSelect.value] = cloneParams(storedParams.capacitor_couplings[sym] || {});
    renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
    doSimulate();
  });

  sSelect.addEventListener('change', () => { renderParamsFor('substrates', sSelect, sParamsContainer, opts.substrates, doSimulate); doSimulate(); });

  symmetricCheckbox.addEventListener('change', () => {
    if (symmetricCheckbox.checked) {
      inputContainer.style.display = 'none';
      outputContainer.style.display = 'none';
      symmetricContainer.style.display = 'block';
      symmetricSelect.value = inSelect.value;
      storedParams.capacitor_couplings[symmetricSelect.value] = cloneParams(storedParams.capacitor_couplings[inSelect.value] || {});
      renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
    } else {
      inputContainer.style.display = 'block';
      outputContainer.style.display = 'block';
      symmetricContainer.style.display = 'none';
      renderParamsFor('capacitor_couplings', inSelect, inParamsContainer, opts.capacitor_couplings, doSimulate);
      renderParamsFor('capacitor_couplings', outSelect, outParamsContainer, opts.capacitor_couplings, doSimulate);
    }
    doSimulate();
  });

  // mode controls sync
  modeNumber.addEventListener('input', () => {
    let v = parseInt(modeNumber.value) || 1;
    if (v < 1) v = 1; if (v > 10) v = 10;
    modeNumber.value = v; modeRange.value = v; doSimulate();
  });
  modeRange.addEventListener('input', () => {
    modeNumber.value = modeRange.value; doSimulate();
  });

  renderAll();
}

window.addEventListener('DOMContentLoaded', main);
