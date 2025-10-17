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
    # 1) set input coupling to gap with custom params
    payload1 = {
        'input_coupling': 'gap',
        'input_coupling_params': {'gap': 1e-6, 'width': 2e-5, 'thickness': 3e-7},
        'n': 1
    }
    print('Step 1: Set input coupling to gap with custom params')
    r1 = post(payload1)
    print('Getters after step1, input capacitance:', r1.get('getters', {}).get('input_coupling'))

    # 2) change transition line to distributed, do NOT send input_coupling params
    payload2 = {
        'transition_line': 'distributed',
        'transition_line_params': {'capacitance_per_length': 2e-11},
        'n': 1
    }
    print('\nStep 2: Change transition line to distributed (no input params)')
    r2 = post(payload2)
    print('Getters after step2, input capacitance:', r2.get('getters', {}).get('input_coupling'))
    print('Transition line getters (parallel_capacitance):', r2.get('getters', {}).get('transition_line'))

    # 3) now query again with no changes to ensure state persisted
    payload3 = {'n':1}
    print('\nStep 3: Post with no selection changes to confirm persistence')
    r3 = post(payload3)
    print('Getters after step3, input capacitance:', r3.get('getters', {}).get('input_coupling'))
    print('Selection state:', r3.get('selection'))

