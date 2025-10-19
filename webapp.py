from flask import Flask, render_template, jsonify, request
from factory import TransitionLines, CapacitorCouplings, Substrates
from resonator import Resonator
import math
import inspect

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
        elif k == 'resistance' and 'resistence' in allowed:
            kwargs['resistence'] = v
    try:
        return cls(**kwargs)
    except Exception:
        # fallback: construct empty and set attributes using setters
        inst = cls()
        _update_instance_attributes(inst, params)
        return inst


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
        # ensure substrate propagation
        _propagate_substrate()


def _propagate_substrate():
    s = _current['substrate']
    if _current['transition_line'] is not None:
        try:
            _current['transition_line'].substrate = s
        except Exception:
            pass
    for key in ('input_coupling', 'output_coupling'):
        inst = _current.get(key)
        if inst is not None:
            try:
                inst.substrate = s
            except Exception:
                pass


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


def _approx_parallel_resistance_for_capacitor(cap_inst, w_n):
    try:
        c_k = float(cap_inst.capacitance)
        r_l = float(cap_inst.resistance)
    except Exception:
        return None
    if w_n is None or w_n == 0 or c_k == 0:
        return None
    wcr = abs(w_n * c_k * r_l)
    # low-frequency asymptote when wcr << 1: R_par ≈ 1/(w^2 C^2 R)
    if wcr < 0.5:
        return 1.0 / (w_n ** 2 * c_k ** 2 * r_l)
    # high-frequency asymptote when wcr >> 1: R_par ≈ R
    if wcr > 5:
        return r_l
    # intermediate: blend between the two asymptotes (log-linear interpolation)
    # map wcr in [0.5,5] -> t in [0,1]
    t = (math.log(wcr) - math.log(0.5)) / (math.log(5) - math.log(0.5))
    low = 1.0 / (w_n ** 2 * c_k ** 2 * r_l)
    high = r_l
    return low * (1 - t) + high * t


@app.route('/api/simulate', methods=['POST'])
def simulate():
    _init_current_instances()

    payload = request.get_json(force=True)
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

        # propagate substrate into components
        _propagate_substrate()

        # Build resonator from current instances
        reson = Resonator(_current['transition_line'], _current['input_coupling'], _current['output_coupling'], _current['substrate'])

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
                    out['parallel_resistance_approx'] = _approx_parallel_resistance_for_capacitor(cap_inst, w_n)
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
            'selection': _current['selection']
        })

    except KeyError as e:
        return jsonify({'error': f'Unknown component: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    _init_current_instances()
    app.run(debug=True, port=5000)
