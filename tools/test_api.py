import json
import urllib.request

base = 'http://127.0.0.1:5000'

def get(path):
    url = base + path
    print('GET', url)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as r:
        data = r.read().decode('utf-8')
    print(data[:1000])
    print('---')

def post_simulate():
    url = base + '/api/simulate'
    payload = {
        'transition_line': 'simplified',
        'input_coupling': 'simplified',
        'output_coupling': 'simplified',
        'substrate': 'effective',
        'transition_line_params': {},
        'input_coupling_params': {},
        'output_coupling_params': {},
        'substrate_params': {},
        'n': 3
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    print('POST', url, 'payload n=', payload['n'])
    with urllib.request.urlopen(req, timeout=5) as r:
        resp = r.read().decode('utf-8')
    print(resp)
    print('---')

if __name__ == '__main__':
    try:
        get('/api/options')
        get('/')
        post_simulate()
    except Exception as e:
        print('ERROR', e)

