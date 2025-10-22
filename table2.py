from resonator import Resonator
from transition_line import GeometricTransitionLine
from substrate import EffectiveSubstrate
from capacitor_coupling import SimplifiedCapacitor
import numpy as np

CAPACITANCE = [
    56.4e-15,
    48.6e-15,
    42.9e-15,
    35.4e-15,
    26.4e-15,
    18.0e-15,
    11.3e-15,
    3.98e-15,
    0.44e-15,
    0.38e-15,
    0.32e-15,
    0.24e-15
]

if __name__ == '__main__':
    tr = GeometricTransitionLine()
    sc = SimplifiedCapacitor(capacitance=np.array(CAPACITANCE))
    sub = EffectiveSubstrate()
    resonator = Resonator(transition_line=tr,
                          input_coupling=sc,
                          output_coupling=sc,
                          substrate=sub)
    n = 1
    f0 = resonator.resonance_frequency(n) / (2 * np.pi * 1e9)  # GHz
    ql = resonator.quality_factor(n)
    ks = resonator.input_coupling.k_factor(resonator.transition_line.resonance_frequency(n))
    print (f"C (fF) | f0 (GHz) |    Q_L   | k_factor")
    for c, f, q, k in zip(CAPACITANCE, f0, ql, ks):
        print(f"{c*1e15:6.3g} | {f:8.5g} | {q:8.2g} | {k:8.2g}")
