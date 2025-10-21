import json
import urllib.request

base = 'http://127.0.0.1:5000'

def post(payload):
    url = base + '/api/simulate'
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

if __name__ == '__main__':
    # default gap capacitor
    payload_default = {
        'transition_line': 'simplified',
        'input_coupling': 'gap',
        'output_coupling': 'simplified',
        'substrate': 'effective',
        'transition_line_params': {},
        'input_coupling_params': {},
        'output_coupling_params': {},
        'substrate_params': {},
        'n': 1
    }
    print('Posting default gap capacitor...')
    d1 = post(payload_default)
    print('Response getters (input capacitance):', d1.get('getters', {}).get('input_coupling'))
    print('w1 f1:', d1.get('w1'), d1.get('f1'))

    # changed gap value (smaller gap -> larger capacitance)
    payload_changed = payload_default.copy()
    payload_changed['input_coupling_params'] = {'gap': 1e-6, 'width': 2e-5, 'thickness': 3e-7}
    print('\nPosting changed gap capacitor params (gap=1e-6, width=2e-5, thickness=3e-7)...')
    d2 = post(payload_changed)
    print('Response getters (input capacitance):', d2.get('getters', {}).get('input_coupling'))
    print('w1 f1:', d2.get('w1'), d2.get('f1'))

    # even larger gap (smaller capacitance)
    payload_changed2 = payload_default.copy()
    payload_changed2['input_coupling_params'] = {'gap': 1e-4, 'width': 1e-5, 'thickness': 1e-7}
    print('\nPosting changed gap capacitor params (gap=1e-4, width=1e-5, thickness=1e-7)...')
    d3 = post(payload_changed2)
    print('Response getters (input capacitance):', d3.get('getters', {}).get('input_coupling'))
    print('w1 f1:', d3.get('w1'), d3.get('f1'))

