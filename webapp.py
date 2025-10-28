from flask import Flask, render_template, jsonify, request
from factory import TransitionLines, CapacitorCouplings, Substrates, PRESETS_COUPLING_CAPACITANCE, PRESET_NAMES
from resonator import Resonator
from transition_line import GeometricTransitionLine
from substrate import EffectiveSubstrate
from capacitor_coupling import SimplifiedCapacitor
import math
import inspect
import numpy as np

app = Flask(__name__, static_folder='static', template_folder='templates')

# Keep a module-level store of current instantiated components so we can update
# them via setters instead of recreating each time.
_current = {
    'transition_line': None,
    'input_coupling': None,
    'output_coupling': None,
    'substrate': None,
    'selection': {
        'transition_line': None,
        'input_coupling': None,
        'output_coupling': None,
        'substrate': None
    }
}

def _get_class_parameters(cls):
    return {k: v._asdict() for k, v in cls.PARAMETERS.items()}

def _instantiate_with_params(cls, params):
    # Try to construct using init kwargs first
    if params is None:
        params = {}
    sig = inspect.signature(cls.__init__)
    allowed = [p for p in sig.parameters.keys() if p != 'self']

    kwargs = {}
    for k, v in params.items():
        if k in allowed:
            kwargs[k] = v
    try:
        return cls(**kwargs)
    except Exception:
        # fallback: construct empty and set attributes using setters
        inst = cls()
        _update_instance_attributes(inst, params)
        return inst

def res_vs_length_data(resonator, n, num_points=500):
    original_length = resonator.transition_line.length
    length_range = resonator.transition_line.LENGTH_RANGE
    x_data = resonator.transition_line.length = np.linspace(length_range.min, length_range.max, num_points)
    w_res = resonator.resonance_frequency(n)
    y_data = w_res / (2 * math.pi)
    resonator.transition_line.length = original_length  # restore
    plot_data = {'x': list(x_data*1e3), 'y': list(y_data*1e-9), 'x_label': 'Transition Line Length (mm)', 'y_label': 'Resonance Frequency (GHz)'}
    return plot_data

def q_vs_coupling_data(resonator, n, num_points=500):
    """Compute total quality factor vs coupling capacitance (vectorized across capacitance presets).
    Uses the same approach as res_vs_coupling_data but returns Q_total for each coupling value.
    """
    in_coupling = resonator.input_coupling
    out_coupling = resonator.output_coupling

    coupling = resonator.input_coupling = resonator.output_coupling = CapacitorCouplings['simplified']()
    coupling.capacitance = np.exp(np.linspace(np.log(coupling.CAPACITANCE_RANGE.min), np.log(coupling.CAPACITANCE_RANGE.max), num_points))
    # quality_factor should be vectorized when coupling.capacitance is an array
    try:
        q_vals = resonator.quality_factor(n)
    finally:
        # restore instances
        resonator.input_coupling = in_coupling
        resonator.output_coupling = out_coupling

    plot_data = {'x': list(coupling.capacitance*1e15), 'y': list(q_vals), 'x_label': 'Coupling Capacitance (fF)', 'y_label': 'Q<sub>L</sub>'}
    return plot_data

def lorentzian(f0, df, points=4000):
    f_min, f_max = f0 - 3*df, f0 + 3*df
    freqs = np.linspace(f_min, f_max, points)
    return freqs, 2e5*df/((freqs - f0)**2 + (df/2)**2) - 75


def lorentzian_data(resonator, n, points=4000, **kwargs):
    w_0 = resonator.resonance_frequency(n)
    f0 = w_0 / (2 * math.pi)
    q_tot = resonator.quality_factor(n)
    df = f0 / q_tot
    return lorentzian(f0, df, points)

def lorentzian_data_wrapper(resonator, n):
    freqs, y_data = lorentzian_data(resonator, n)
    plot_data = {'x': list(freqs/1e9), 'y': list(y_data), 'x_label': 'Frequency (GHz)', 'y_label': 'S21 (dB)'}
    return plot_data

def q_vs_n_data(resonator, _, num_points=7):
    """Compute total quality factor Q_L vs mode number n.
    Returns Q_total for integer modes from 1 to num_points (inclusive).
    """
    n_vals = list(range(1, num_points+1))
    q_vals = [resonator.quality_factor(n) for n in n_vals]
    plot_data = {'x': n_vals, 'y': q_vals, 'x_label': 'Resonance Mode, n', 'y_label': 'Quality factor, Q<sub>L</sub>'}
    return plot_data

def s21_vs_w_data(resonator, n, points=400000):
    """Compute S21 (in dB) vs angular frequency w.

    w is a linspace from w1/100 to 5.5*w1 where w1 is the resonance angular
    frequency for mode n=1 (or the provided n if desired). Returns x as a
    list of angular frequencies (rad/s) and y as S21 in dB.
    """
    # Use the fundamental (n=1) resonance for the requested baseline
    try:
        w1 = resonator.resonance_frequency(1)
    except Exception:
        w1 = None
    if w1 is None:
        return {'x': [], 'y': [], 'x_label': 'Angular frequency (rad/s)', 'y_label': 'S21 (dB)'}

    w_min = float(w1) *0.9
    w_max = float(w1) * 1.1
    w = np.linspace(w_min, w_max, points)
    x = w / (2 * math.pi * 1e9)
    s = resonator.s21(w)
    mag = np.abs(s)
    y = 20 * np.log10(mag + 1e-30)
    plot_data = {'x': list(x), 'y': list(y), 'x_label': 'frequency (GHz)', 'y_label': 'S21 (dB)'}
    return plot_data

plot_data_mapping = {
    'lorentzian': lorentzian_data_wrapper,
    'res_vs_length': res_vs_length_data,
    'q_vs_coupling': q_vs_coupling_data,
    'q_vs_n': q_vs_n_data,
    's21_vs_w': s21_vs_w_data,
}

def _find_candidate_attribute(inst, key):
    """Find a plausible attribute name on inst that corresponds to key.
    Heuristics: direct match, prefix with class-like token (e.g., 'finger_'), or any attribute name that endswith key.
    Returns attribute name or None.
    """
    # direct
    if hasattr(inst, key):
        return key
    # try prefix with common tokens (finger_)
    pref = f'finger_{key}'
    if hasattr(inst, pref):
        return pref
    # try any attribute that endswith the key
    for a in dir(inst.__class__):
        if a.endswith(key):
            return a
    return None

def _update_instance_attributes(inst, params):
    if not params:
        return
    for k, v in params.items():
        attr = _find_candidate_attribute(inst, k)
        if attr:
            try:
                setattr(inst, attr, v)
                continue
            except Exception:
                pass
        # last effort: try direct setattr anyway
        try:
            setattr(inst, k, v)
        except Exception:
            pass

def _init_current_instances():
    # initialize module globals with default component instances
    if _current['transition_line'] is None:
        tname = 'geometric' if 'geometric' in TransitionLines else next(iter(TransitionLines.keys()))
        iname = 'simplified' if 'simplified' in CapacitorCouplings else next(iter(CapacitorCouplings.keys()))
        oname = 'simplified' if 'simplified' in CapacitorCouplings else next(iter(CapacitorCouplings.keys()))
        sname = next(iter(Substrates.keys()))
        _current['transition_line'] = TransitionLines[tname]()
        _current['input_coupling'] = CapacitorCouplings[iname]()
        _current['output_coupling'] = CapacitorCouplings[oname]()
        _current['substrate'] = Substrates[sname]()
        _current['selection'] = {
            'transition_line': tname,
            'input_coupling': iname,
            'output_coupling': oname,
            'substrate': sname
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/options')
def options():
    data = {'transition_lines': {}, 'capacitor_couplings': {}, 'substrates': {}, 'defaults': {}}

    # Prefer 'simplified' for capacitors if present
    default_t = 'geometric' if 'geometric' in TransitionLines else next(iter(TransitionLines.keys()))
    default_s = next(iter(Substrates.keys()))
    default_c = 'simplified' if 'simplified' in CapacitorCouplings else next(iter(CapacitorCouplings.keys()))

    data['defaults'] = {
        'transition_line': default_t,
        'capacitor_couplings': default_c,
        'substrate': default_s
    }

    for name, cls in TransitionLines.items():
        data['transition_lines'][name] = {
            'class': cls.__name__,
            'parameters': _get_class_parameters(cls)
        }

    for name, cls in CapacitorCouplings.items():
        data['capacitor_couplings'][name] = {
            'class': cls.__name__,
            'parameters': _get_class_parameters(cls)
        }

    for name, cls in Substrates.items():
        data['substrates'][name] = {
            'class': cls.__name__,
            'parameters': _get_class_parameters(cls)
        }

    return jsonify(data)

@app.route('/api/simulate', methods=['POST'])
def simulate():
    _init_current_instances()

    payload = request.get_json(force=True)
    plot_type = payload.get('plot_type', 'lorentzian')
    try:
        # selections from payload; if missing, keep current selection
        t_name = payload.get('transition_line') or _current['selection']['transition_line']
        in_name = payload.get('input_coupling') or _current['selection']['input_coupling']
        out_name = payload.get('output_coupling') or _current['selection']['output_coupling']
        s_name = payload.get('substrate') or _current['selection']['substrate']

        t_params = payload.get('transition_line_params', {}) or {}
        in_params = payload.get('input_coupling_params', {}) or {}
        out_params = payload.get('output_coupling_params', {}) or {}
        s_params = payload.get('substrate_params', {}) or {}

        n = int(payload.get('n', 1) or 1)
        if n < 1:
            n = 1
        if n > 1000:
            n = 1000

        # transition_line
        if _current['selection']['transition_line'] != t_name:
            # create new instance for transition line, but preserve substrate and other components
            _current['transition_line'] = TransitionLines[t_name]()
            _current['selection']['transition_line'] = t_name
        # update attributes
        _update_instance_attributes(_current['transition_line'], t_params)

        # input coupling
        if _current['selection']['input_coupling'] != in_name:
            _current['input_coupling'] = CapacitorCouplings[in_name]()
            _current['selection']['input_coupling'] = in_name
        _update_instance_attributes(_current['input_coupling'], in_params)

        # output coupling (separate instance always)
        if _current['selection']['output_coupling'] != out_name:
            _current['output_coupling'] = CapacitorCouplings[out_name]()
            _current['selection']['output_coupling'] = out_name
        _update_instance_attributes(_current['output_coupling'], out_params)

        # substrate
        if _current['selection']['substrate'] != s_name:
            _current['substrate'] = Substrates[s_name]()
            _current['selection']['substrate'] = s_name
        _update_instance_attributes(_current['substrate'], s_params)

        # Build resonator from current instances
        reson = Resonator(_current['transition_line'], _current['input_coupling'], _current['output_coupling'], _current['substrate'])

        # --- Plot data generation ---
        plot_data = plot_data_mapping[plot_type](reson, n) if plot_type in plot_data_mapping else {}

        # compute for requested n
        w_n = reson.resonance_frequency(n)
        f_n = None
        if w_n is not None:
            try:
                f_n = float(w_n) / (2 * math.pi)
            except Exception:
                f_n = None

        # compute capacitances seen by resonator
        c_line = None
        c_in = None
        c_out = None
        try:
            c_line = _current['transition_line'].parallel_capacitance
        except Exception:
            c_line = None
        try:
            c_in = _current['input_coupling'].parallel_capacitance(w_n) if w_n is not None else None
        except Exception:
            c_in = None
        try:
            c_out = _current['output_coupling'].parallel_capacitance(w_n) if w_n is not None else None
        except Exception:
            c_out = None

        q_i = reson.quality_factor_internal(n)
        q_e = reson.quality_factor_external(n)
        q_tot = reson.quality_factor(n)

        # Build getters to return for UI display, extended for couplings
        getters = {
            'transition_line': {
                'parallel_capacitance': c_line,
                'parallel_resistance': getattr(_current['transition_line'], 'parallel_resistance', None),
                'parallel_inductance': None
            },
            'input_coupling': {
                'capacitance': c_in
            },
            'output_coupling': {
                'capacitance': c_out
            },
            'substrate': {
                'permittivity': getattr(_current['substrate'], 'permittivity', None),
                'permeability': getattr(_current['substrate'], 'permeability', None)
            }
        }
        # compute parallel_inductance for transition_line if available
        try:
            getters['transition_line']['parallel_inductance'] = _current['transition_line'].parallel_inductance(n)
        except Exception:
            getters['transition_line']['parallel_inductance'] = None

        try:
            getters['transition_line']['Q'] = _current['transition_line'].quality_factor(n)
        except Exception:
            getters['transition_line']['Q'] = None

        try:
            getters['transition_line'][f'f_{n}[GHz]'] = _current['transition_line'].resonance_frequency(n)/(math.pi*2e9)
        except Exception:
            getters['transition_line'][f'f_{n}[GHz]'] = None


        # augment input/output getters with parallel_resistance, approximate and k_factor
        total_c = None
        try:
            total_c = sum([v for v in (c_line, c_in, c_out) if v is not None])
        except Exception:
            total_c = None

        # helper to safe compute parallel resistance and k
        def coupling_getters(cap_inst, c_val):
            out = {}
            try:
                if w_n is not None:
                    # exact parallel resistance using existing method
                    r_par = None
                    try:
                        r_par = cap_inst.parallel_resistance(w_n)
                    except Exception:
                        r_par = None
                    out['parallel_resistance'] = r_par
                    # approximate
                    out['parallel_resistance_approx'] = cap_inst.parallel_resistance_approx(w_n)
                # k-factor = coupling capacitance / total capacitance
                if c_val is not None and total_c is not None and total_c != 0:
                    out['k_factor'] = float(c_val) / float(total_c)
                else:
                    out['k_factor'] = None
            except Exception:
                pass
            return out

        try:
            getters['input_coupling'].update(coupling_getters(_current['input_coupling'], c_in))
        except Exception:
            pass
        try:
            getters['output_coupling'].update(coupling_getters(_current['output_coupling'], c_out))
        except Exception:
            pass

        return jsonify({
            'w1': w_n,
            'f1': f_n,
            'q_internal': q_i,
            'q_external': q_e,
            'q_total': q_tot,
            'getters': getters,
            'plot_data': plot_data,
            'selection': _current['selection']
        })

    except KeyError as e:
        return jsonify({'error': f'Unknown component: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/presets', methods=['POST'])
def presets():
    """Compute preset resonance frequencies using PRESETS_COUPLING_CAPACITANCE as in table2.py.
    Expects JSON payload with optional 'n' (mode number, default 1).
    Returns list of {name, capacitance, frequency} where frequency is in Hz.
    """
    try:
        n = int(request.json.get('n', 1) or 1)
        if n < 1:
            n = 1
        # Build canonical components as in table2.py
        tr = GeometricTransitionLine()
        sc = SimplifiedCapacitor(capacitance=np.array(PRESETS_COUPLING_CAPACITANCE))
        sub = EffectiveSubstrate()
        resonator = Resonator(tr, sc, sc, sub)

        x,y = lorentzian_data(resonator, n)

        f0 = np.array([2.2678e9, 2.2763e9, 2.2848e9, 2.2943e9, 2.3086e9, 2.3164e9, 2.3259e9, 2.3343e9, 2.343e9, 2.3448e9, 2.3459e9, 2.3464e9])
        ql = np.array([3.7e2, 4.9e2, 7.5e2, 1.1e3, 1.7e3, 3.9e3, 9.8e3, 7.5e4, 2.0e5, 2.0e5, 2.3e5, 2.3e5])
        df = f0 / ql

        x2,y2 = lorentzian(f0, df)
        xs = [x]
        ys = [y]
        color = ('#000000', '#555588')

        presets_out = [{'name': name, 'x':list(x[:,i]), 'y':list(y[:,i]), 'color':c} for x,y,c in zip(xs,ys, color) for i, name in enumerate(PRESET_NAMES)]

        return jsonify({'presets': presets_out})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    _init_current_instances()
    app.run(debug=True, port=5000)
