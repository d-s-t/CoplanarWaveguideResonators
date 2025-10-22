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

PRESET_NAMES = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'
]

PRESETS_COUPLING_CAPACITANCE = [
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