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
    # symmetric true: set input to 'gap' with params, expect output to follow
    payload_sym = {
        'input_coupling': 'gap',
        'input_coupling_params': {'gap': 1e-6, 'width': 2e-5, 'thickness': 3e-7},
        'symmetric': True,
        'n': 1
    }
    print('--- Symmetric ON: set input to gap with custom params ---')
    r = post(payload_sym)
    print('selection:', r.get('selection'))
    print('input getter:', r.get('getters', {}).get('input_coupling'))
    print('output getter:', r.get('getters', {}).get('output_coupling'))
    print('w1 f1:', r.get('w1'), r.get('f1'))

    # symmetric false: set output separately to finger with different params
    payload_asym = {
        'input_coupling': 'gap',
        'input_coupling_params': {'gap': 1e-6, 'width': 2e-5, 'thickness': 3e-7},
        'output_coupling': 'finger',
        'output_coupling_params': {'length': 2e-4, 'thickness': 3e-7, 'count': 8, 'gap': 2e-6},
        'symmetric': False,
        'n': 1
    }
    print('\n--- Symmetric OFF: set input=gap and output=finger with different params ---')
    r2 = post(payload_asym)
    print('selection:', r2.get('selection'))
    print('input getter:', r2.get('getters', {}).get('input_coupling'))
    print('output getter:', r2.get('getters', {}).get('output_coupling'))
    print('w1 f1:', r2.get('w1'), r2.get('f1'))

    # Check defaults from /api/options
    print('\n--- Check defaults from /api/options ---')
    with urllib.request.urlopen(base + '/api/options') as r3:
        opts = json.loads(r3.read().decode('utf-8'))
    print('defaults:', opts.get('defaults'))

