from transition_line import TransitionLine
from capacitor_coupling import CapacitorCoupling
from substrate import Substrate

class Resonator:
    """
    A class representing a resonator with specific properties.
    The resonator has Transition Line, Input and Output Coupling, and substrate attributes.
    """
    def __init__(self,
                 transition_line: TransitionLine,
                 input_coupling: CapacitorCoupling,
                 output_coupling: CapacitorCoupling,
                 substrate: Substrate
                 ):
        self.substrate = None
        self.transition_line = transition_line
        self.input_coupling = input_coupling
        self.output_coupling = output_coupling
        self.substrate = substrate


    def resonance_frequency(self, n):
        """
        Calculate the resonance angular frequency of the resonator.
        """
        l_n = self.transition_line.parallel_inductance(n)
        c = self.transition_line.parallel_capacitance
        w_n = self.transition_line.resonance_frequency(n)
        c_in = self.input_coupling.parallel_capacitance(w_n)
        c_out = self.output_coupling.parallel_capacitance(w_n)
        return (l_n * (c + c_in + c_out)) ** -0.5

    def quality_factor_internal(self, n):
        """
        Calculate the internal quality factor of the resonator.
        """
        return self.transition_line.quality_factor(n)

    def quality_factor_external(self, n):
        """
        Calculate the external quality factor of the resonator.
        :param n:
        :return:
        """
        w_n = self.transition_line.resonance_frequency(n)
        c = self.transition_line.parallel_capacitance
        r_in = self.input_coupling.parallel_resistance(w_n)
        r_out = self.output_coupling.parallel_resistance(w_n)
        r = 1 / (1 / r_in + 1 / r_out)
        return w_n * r * c

    def quality_factor(self, n):
        """
        Calculate the total quality factor of the resonator.
        :param n:
        :return:
        """
        q_i = self.quality_factor_internal(n)
        q_e = self.quality_factor_external(n)
        return 1 / (1 / q_i + 1 / q_e)

    @property
    def transition_line(self):
        return self.__transition_line
    @transition_line.setter
    def transition_line(self, value):
        if not isinstance(value, TransitionLine):
            raise ValueError("Transition line must be an instance of TransitionLine")
        self.__transition_line = value
        value.substrate = self.substrate

    @property
    def input_coupling(self):
        return self.__input_coupling
    @input_coupling.setter
    def input_coupling(self, value):
        if not isinstance(value, CapacitorCoupling):
            raise ValueError("Input coupling must be an instance of CapacitorCoupling")
        self.__input_coupling = value
        value.substrate = self.substrate

    @property
    def output_coupling(self):
        return self.__output_coupling
    @output_coupling.setter
    def output_coupling(self, value):
        if not isinstance(value, CapacitorCoupling):
            raise ValueError("Output coupling must be an instance of CapacitorCoupling")
        self.__output_coupling = value
        value.substrate = self.substrate 

    @property
    def substrate(self):
        return self.__substrate
    @substrate.setter
    def substrate(self, value):
        if value is not None and not isinstance(value, Substrate):
            raise ValueError("Substrate must be an instance of Substrate")
        self.__substrate = value
        if value is None:
            return
        self.transition_line.substrate = value
        self.input_coupling.substrate = value
        self.output_coupling.substrate = value


if __name__ == '__main__':
    from transition_line import GeometricTransitionLine
    from capacitor_coupling import SimplifiedCapacitor
    from substrate import EffectiveSubstrate
    import numpy as np
    import math

    def res_vs_coupling_data(resonator, n, num_points=50):
        in_coupling = resonator.input_coupling
        out_coupling = resonator.output_coupling

        coupling = resonator.input_coupling = resonator.output_coupling = SimplifiedCapacitor()
        coupling.capacitance = np.linspace(coupling.CAPACITANCE_RANGE.min, coupling.CAPACITANCE_RANGE.max, num_points)
        w_res = resonator.resonance_frequency(n)
        y_data = w_res / (2 * math.pi)
        resonator.input_coupling = in_coupling
        resonator.output_coupling = out_coupling
        plot_data = {'x': list(coupling.capacitance), 'y': list(y_data), 'x_label': 'Coupling Capacitance (F)', 'y_label': 'Resonance Frequency (Hz)'}
        return plot_data

    tl = GeometricTransitionLine()
    coup = SimplifiedCapacitor()
    sub = EffectiveSubstrate()
    resonator = Resonator(tl, coup, coup, sub)
    print(res_vs_coupling_data(resonator, 1))
