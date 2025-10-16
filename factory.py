from substrate import EffectiveSubstrate
from transition_line import DistributedTransitionLine, SimplifiedTransitionLine
from capacitor_coupling import SimplifiedCapacitor, GapCapacitor, FingerCapacitor

TransitionLines = {
    "simplified": SimplifiedTransitionLine,
    "distributed": DistributedTransitionLine
}

CapacitorCouplings = {
    "simplified": SimplifiedCapacitor,
    "gap": GapCapacitor,
    "finger": FingerCapacitor
}

Substrates = {
    "effective": EffectiveSubstrate
}

