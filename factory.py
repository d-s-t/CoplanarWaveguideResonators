from substrate import EffectiveSubstrate
from transition_line import DistributedTransitionLine, SimplifiedTransitionLine, GeometricTransitionLine
from capacitor_coupling import SimplifiedCapacitor, GapCapacitor, FingerCapacitor

TransitionLines = {
    "simplified": SimplifiedTransitionLine,
    "distributed": DistributedTransitionLine,
    "geometric": GeometricTransitionLine
}

CapacitorCouplings = {
    "simplified": SimplifiedCapacitor,
    "gap": GapCapacitor,
    "finger": FingerCapacitor
}

Substrates = {
    "effective": EffectiveSubstrate
}

PRESETS_COUPLING_CAPACITANCE = {
    'A': 56.4e-15,
    'B': 48.6e-15,
    'C': 42.9e-15,
    'D': 35.4e-15,
    'E': 26.4e-15,
    'F': 18.0e-15,
    'G': 11.3e-15,
    'H': 3.98e-15,
    'I': 0.44e-15,
    'J': 0.38e-15,
    'K': 0.32e-15,
    'L': 0.24e-15
}