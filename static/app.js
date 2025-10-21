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
// params are read from the DOM; no storedParams object

function createParamControl(name, defn, container, onChange) {
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
  inputNumber.value = (defn && defn.default !== undefined) ? defn.default : r.default;

  inputNumber.addEventListener('input', () => {
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

  Object.keys(params).forEach(pname => {
    createParamControl(pname, params[pname], paramsContainerEl, onChange);
  });
}

function buildSelector(map, selectEl, defaultValue) {
  Object.keys(map).forEach(k => {
    const opt = document.createElement('option');
    opt.value = k;
    opt.textContent = k; // remove class name from label
    selectEl.appendChild(opt);
  });
  selectEl.value = defaultValue || selectEl.options[0].value;
}

// collect parameter values from a params container (reads .param-number inputs)
function collectParams(container) {
  const out = {};
  if (!container) return out;
  const items = container.querySelectorAll('.param');
  items.forEach(item => {
    const label = item.querySelector('label');
    const input = item.querySelector('.param-number');
    if (label && input) {
      const name = label.textContent;
      const val = input.value;
      out[name] = val === '' ? null : Number(val);
    }
  });
  return out;
}

// copy numeric values from src container into dst container (matching by label text)
function copyParamValues(srcContainer, dstContainer) {
  if (!srcContainer || !dstContainer) return;
  const src = collectParams(srcContainer);
  const dstItems = dstContainer.querySelectorAll('.param');
  dstItems.forEach(item => {
    const label = item.querySelector('label');
    const num = item.querySelector('.param-number');
    const range = item.querySelector('.param-range');
    if (label && num) {
      const name = label.textContent;
      if (Object.prototype.hasOwnProperty.call(src, name) && src[name] !== null) {
        num.value = src[name];
        if (range) range.value = src[name];
      }
    }
  });
}

let currentPlotType = 'lorentzian';
let lorentzianTraces = [];

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
  const ioStack = document.getElementById('input_output_stack');
  const symmetricSelect = document.getElementById('symmetric_coupling_select');
  const symmetricParamsContainer = document.getElementById('symmetric_coupling_params');
  buildSelector(opts.transition_lines, tSelect, opts.defaults.transition_line);
  buildSelector(opts.capacitor_couplings, inSelect, opts.defaults.capacitor_couplings);
  buildSelector(opts.capacitor_couplings, outSelect, opts.defaults.capacitor_couplings);
  buildSelector(opts.capacitor_couplings, symmetricSelect, opts.defaults.capacitor_couplings);
  buildSelector(opts.substrates, sSelect, opts.defaults.substrate);

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

  const plotTabs = document.querySelectorAll('.plot-tab-button');
  const lorentzianControls = document.getElementById('lorentzian_controls');
  const saveLorentzianBtn = document.getElementById('save_lorentzian_btn');
  const clearLorentzianBtn = document.getElementById('clear_lorentzian_btn');
  const swapColumnsBtn = document.getElementById('swap_columns_btn');

  // Show Lorentzian controls by default
  lorentzianControls.classList.add('visible');

  // schedule simulation with debounce
  const doSimulate = debounce(async () => {
    const n = parseInt(modeNumber.value) || 1;

    // determine whether symmetric mode is active
    const symmetric = !!symmetricCheckbox.checked;
    let inputName = inSelect.value;
    let outputName = outSelect.value;

    // gather parameter objects from DOM
    const transitionParams = collectParams(tParamsContainer);
    const substrateParams = collectParams(sParamsContainer);

    let inputParams, outputParams;

    if (symmetric) {
      // authoritative control is symmetricSelect
      const symName = symmetricSelect.value;
      inputName = symName;
      outputName = symName;
      // params taken from symmetric params panel
      inputParams = collectParams(symmetricParamsContainer);
      outputParams = inputParams;
      // keep the hidden selects in sync
      inSelect.value = symName;
      outSelect.value = symName;
    } else {
      inputParams = collectParams(inParamsContainer);
      outputParams = collectParams(outParamsContainer);
    }

    const payload = {
      transition_line: tSelect.value,
      input_coupling: inputName,
      output_coupling: outputName,
      substrate: sSelect.value,
      transition_line_params: transitionParams,
      input_coupling_params: inputParams,
      output_coupling_params: outputParams,
      substrate_params: substrateParams,
      n: n,
      plot_type: currentPlotType,
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

      document.getElementById('w1').textContent = (data.w1 !== null && data.w1 !== undefined) ? Number(data.w1).toPrecision(3) : '-';
      document.getElementById('f1').textContent = (data.f1 !== null && data.f1 !== undefined) ? Number(data.f1).toPrecision(3) : '-';
      document.getElementById('q_i').textContent = (data.q_internal !== null && data.q_internal !== undefined) ? Number(data.q_internal).toPrecision(3) : '-';
      document.getElementById('q_e').textContent = (data.q_external !== null && data.q_external !== undefined) ? Number(data.q_external).toPrecision(3) : '-';
      document.getElementById('q_tot').textContent = (data.q_total !== null && data.q_total !== undefined) ? Number(data.q_total).toPrecision(3) : '-';

      // --- Plotting ---
      const plotDiv = document.getElementById('plot');
      let traces = [];
      let layout = { title: 'Plot', yaxis: {title: 'Y'}, xaxis: {title: 'X'}, margin: { l: 50, r: 20, t: 30, b: 40 } };

      if (currentPlotType === 'quality_factors') {
        const qNames = ['Q_internal', 'Q_external', 'Q_total'];
        const qVals = [data.q_internal || 0, data.q_external || 0, data.q_total || 0];
        traces.push({ x: qNames, y: qVals, type: 'bar' });
        layout.title = 'Quality Factors';
        layout.yaxis.title = 'Q';
        layout.xaxis.title = '';
      } else if (data.plot_data && data.plot_data.x && data.plot_data.y) {
        const currentTrace = {
          x: data.plot_data.x,
          y: data.plot_data.y,
          type: 'scatter',
          mode: 'lines',
          name: 'Current'
        };
        layout.title = data.plot_data.y_label + ' vs ' + data.plot_data.x_label;
        layout.xaxis.title = data.plot_data.x_label;
        layout.yaxis.title = data.plot_data.y_label;

        if (currentPlotType === 'lorentzian') {
          traces = [...lorentzianTraces, currentTrace];
          layout.title = 'Lorentzian Profile (S21)';
        } else {
          traces.push(currentTrace);
        }
      }

      if (window.Plotly) {
        Plotly.react(plotDiv, traces, layout, {responsive: true});
      }



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

        // helper to render a numeric field
        function appendNumeric(container, label, value) {
          const d = document.createElement('div');
          let txt = label + ': ';
          if (value === null || value === undefined) txt += '-';
          else if (typeof value === 'number') txt += Number(value).toPrecision(3);
          else txt += String(value);
          d.textContent = txt;
          container.appendChild(d);
        }

        // input coupling getters
        if (data.getters.input_coupling) {
          const ic = data.getters.input_coupling;
          if (ic.capacitance !== undefined) appendNumeric(ig, 'capacitance', ic.capacitance);
          if (ic.parallel_resistance !== undefined) appendNumeric(ig, 'parallel_resistance', ic.parallel_resistance);
          if (ic.parallel_resistance_approx !== undefined) appendNumeric(ig, 'parallel_resistance_approx', ic.parallel_resistance_approx);
          if (ic.k_factor !== undefined) appendNumeric(ig, 'k_factor', ic.k_factor);
        }

        // output coupling getters
        if (data.getters.output_coupling) {
          const oc = data.getters.output_coupling;
          if (oc.capacitance !== undefined) appendNumeric(og, 'capacitance', oc.capacitance);
          if (oc.parallel_resistance !== undefined) appendNumeric(og, 'parallel_resistance', oc.parallel_resistance);
          if (oc.parallel_resistance_approx !== undefined) appendNumeric(og, 'parallel_resistance_approx', oc.parallel_resistance_approx);
          if (oc.k_factor !== undefined) appendNumeric(og, 'k_factor', oc.k_factor);
        }

        // transition line getters
        if (data.getters.transition_line) {
          const tvals = data.getters.transition_line;
          Object.keys(tvals).forEach(k => {
            const v = tvals[k];
            const d = document.createElement('div');
            d.textContent = k + ': ' + (v === null || v === undefined ? '-' : (typeof v === 'number' ? Number(v).toPrecision(3) : String(v)));
            tg.appendChild(d);
          });
        }

        // substrate getters
        if (data.getters.substrate) {
          const svals = data.getters.substrate;
          Object.keys(svals).forEach(k => {
            const v = svals[k];
            const d = document.createElement('div');
            d.textContent = k + ': ' + (v === null || v === undefined ? '-' : (typeof v === 'number' ? Number(v).toPrecision(3) : String(v)));
            sg.appendChild(d);
          });
        }
        // if symmetric, render symmetric getter too (show same fields as coupling)
        if (symmetric && data.getters.input_coupling && sg_sym) {
          const ic = data.getters.input_coupling;
          if (ic.capacitance !== undefined) appendNumeric(sg_sym, 'capacitance', ic.capacitance);
          if (ic.parallel_resistance !== undefined) appendNumeric(sg_sym, 'parallel_resistance', ic.parallel_resistance);
          if (ic.parallel_resistance_approx !== undefined) appendNumeric(sg_sym, 'parallel_resistance_approx', ic.parallel_resistance_approx);
          if (ic.k_factor !== undefined) appendNumeric(sg_sym, 'k_factor', ic.k_factor);
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

    // trigger simulate after re-render
    doSimulate();
  };

  tSelect.addEventListener('change', () => { renderParamsFor('transition_lines', tSelect, tParamsContainer, opts.transition_lines, doSimulate); doSimulate(); });

  inSelect.addEventListener('change', () => {
    renderParamsFor('capacitor_couplings', inSelect, inParamsContainer, opts.capacitor_couplings, doSimulate);
    if (symmetricCheckbox.checked) {
      // when symmetric is on, update symmetric select to match input
      symmetricSelect.value = inSelect.value;
      renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
      copyParamValues(inParamsContainer, symmetricParamsContainer);
    }
    doSimulate();
  });

  outSelect.addEventListener('change', () => {
    renderParamsFor('capacitor_couplings', outSelect, outParamsContainer, opts.capacitor_couplings, doSimulate);
    if (symmetricCheckbox.checked) {
      // if user changes output while symmetric is on, keep symmetric in sync
      symmetricSelect.value = outSelect.value;
      renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
      copyParamValues(outParamsContainer, symmetricParamsContainer);
    }
    doSimulate();
  });

  symmetricSelect.addEventListener('change', () => {
    // when symmetric_select changes, copy its values to input and output panels and sync selects
    const sym = symmetricSelect.value;
    inSelect.value = sym;
    outSelect.value = sym;
    renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
    // re-render hidden panels and copy values from symmetric panel into them
    renderParamsFor('capacitor_couplings', inSelect, inParamsContainer, opts.capacitor_couplings, doSimulate);
    renderParamsFor('capacitor_couplings', outSelect, outParamsContainer, opts.capacitor_couplings, doSimulate);
    copyParamValues(symmetricParamsContainer, inParamsContainer);
    copyParamValues(symmetricParamsContainer, outParamsContainer);
    doSimulate();
  });

  sSelect.addEventListener('change', () => { renderParamsFor('substrates', sSelect, sParamsContainer, opts.substrates, doSimulate); doSimulate(); });

  symmetricCheckbox.addEventListener('change', () => {
    if (symmetricCheckbox.checked) {
      ioStack.style.display = 'none';
      symmetricContainer.style.display = 'block';
      symmetricSelect.value = inSelect.value;
      renderParamsFor('capacitor_couplings', symmetricSelect, symmetricParamsContainer, opts.capacitor_couplings, doSimulate);
      // copy current visible input values into symmetric panel
      copyParamValues(inParamsContainer, symmetricParamsContainer);
    } else {
      ioStack.style.removeProperty("display")
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

  // Plot tab logic
  plotTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      plotTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentPlotType = tab.dataset.plottype;
      if (currentPlotType === 'lorentzian') {
        lorentzianControls.classList.add('visible');
      } else {
        lorentzianControls.classList.remove('visible');
      }
      const resVsCouplingTab = document.querySelector('[data-plottype="res_vs_coupling"]');
      if (resVsCouplingTab) {
        resVsCouplingTab.disabled = !symmetricCheckbox.checked;
        if (!symmetricCheckbox.checked && currentPlotType === 'res_vs_coupling') {
            document.querySelector('[data-plottype="quality_factors"]').click();
        }
      }
      doSimulate();
    });
  });

  saveLorentzianBtn.addEventListener('click', () => {
    const currentTrace = document.getElementById('plot').data.find(t => t.name === 'Current');
    if (currentTrace) {
      lorentzianTraces.push({ ...currentTrace, name: `Saved ${lorentzianTraces.length + 1}` });
      doSimulate(); // re-render plot with saved trace
    }
  });
  clearLorentzianBtn.addEventListener('click', () => { lorentzianTraces = []; doSimulate(); });

  // Swap columns button
  swapColumnsBtn.addEventListener('click', () => {
    const container = document.querySelector('.container.two-column');
    container.classList.toggle('layout-swapped');

    // change the max-height of the control panel to match the new height
    const controls = document.querySelector('.controls-column')
    const results = document.querySelector('.results');
    const resultsHeight = results.clientHeight;
    const gap = window.getComputedStyle(container).gap
    controls.style.maxHeight = "calc(100vh - " + resultsHeight + "px - 120px - " + gap + ")";

    // After the CSS transition, tell Plotly to resize.
    Plotly.Plots.resize(document.getElementById('plot'));
  });

  renderAll();
}

window.addEventListener('DOMContentLoaded', main);
