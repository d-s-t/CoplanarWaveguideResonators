from flask import Flask, render_template, jsonify, request
from factory import TransitionLines, CapacitorCouplings, Substrates
from utilies import ValueRange
from resonator import Resonator
import math

app = Flask(__name__, static_folder='static', template_folder='templates')



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/options')
def options():
    # Build a JSON-friendly description of available components and their parameters
    data = {
        'transition_lines': {},
        'capacitor_couplings': {},
        'substrates': {}
    }

    for name, cls in TransitionLines.items():
        data['transition_lines'][name] = {
            'class': cls.__name__,
            'parameters': cls.PARAMETERS
        }

    for name, cls in CapacitorCouplings.items():
        data['capacitor_couplings'][name] = {
            'class': cls.__name__,
            'parameters': cls.PARAMETERS
        }

    for name, cls in Substrates.items():
        data['substrates'][name] = {
            'class': cls.__name__,
            'parameters': cls.PARAMETERS
        }

    # Provide default selection (first key in each mapping)
    data['defaults'] = {
        'transition_line': next(iter(TransitionLines.keys())),
        'input_coupling': next(iter(CapacitorCouplings.keys())),
        'output_coupling': next(iter(CapacitorCouplings.keys())),
        'substrate': next(iter(Substrates.keys())),
    }

    return jsonify(data)


@app.route('/api/simulate', methods=['POST'])
def simulate():
    payload = request.get_json(force=True)
    try:
        t_name = payload.get('transition_line')
        in_name = payload.get('input_coupling')
        out_name = payload.get('output_coupling')
        s_name = payload.get('substrate')

        t_params = payload.get('transition_line_params', {}) or {}
        in_params = payload.get('input_coupling_params', {}) or {}
        out_params = payload.get('output_coupling_params', {}) or {}
        s_params = payload.get('substrate_params', {}) or {}

        t_cls = TransitionLines[t_name]
        in_cls = CapacitorCouplings[in_name]
        out_cls = CapacitorCouplings[out_name]
        s_cls = Substrates[s_name]

        # Instantiate with defaults, then set attributes from params
        t_inst = t_cls()
        in_inst = in_cls()
        out_inst = out_cls()
        s_inst = s_cls()

        # Helper to set attributes safely
        def apply_params(inst, params):
            for k, v in params.items():
                # try setting attribute; skip if not present
                try:
                    setattr(inst, k, v)
                except Exception:
                    # ignore unknown or invalid attributes
                    pass

        apply_params(t_inst, t_params)
        apply_params(in_inst, in_params)
        apply_params(out_inst, out_params)
        apply_params(s_inst, s_params)

        # Build resonator
        reson = Resonator(t_inst, in_inst, out_inst, s_inst)

        # compute for n=1
        w1 = reson.resonance_frequency(1)
        f1 = None
        if w1 is not None:
            try:
                f1 = float(w1) / (2 * math.pi)
            except Exception:
                f1 = None

        q_i = reson.quality_factor_internal(1)
        q_e = reson.quality_factor_external(1)
        q_tot = reson.quality_factor(1)

        return jsonify({
            'w1': w1,
            'f1': f1,
            'q_internal': q_i,
            'q_external': q_e,
            'q_total': q_tot
        })

    except KeyError as e:
        return jsonify({'error': f'Unknown component: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)

