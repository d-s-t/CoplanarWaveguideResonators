from capacitor_coupling import GapCapacitor
from substrate import EffectiveSubstrate

if __name__ == '__main__':
    known_values = [
        {'gap': 1e-5, 'capacitance': 0.44e-15},
        {'gap': 2e-5, 'capacitance': 0.38e-15},
        {'gap': 3e-5, 'capacitance': 0.32e-15},
        {'gap': 5e-6, 'capacitance': 0.24e-15},
    ]
    cap = GapCapacitor()
    cap.substrate = EffectiveSubstrate()
    for kv in known_values:
        cap.gap = kv['gap']
        diff = abs(cap.capacitance - kv['capacitance'])
        assert diff / kv['capacitance'] < 0.1, f"Gap: {kv['gap']}, Expected: {kv['capacitance']}, Got: {cap.capacitance}"
