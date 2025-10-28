from transition_line import TransitionLine
from capacitor_coupling import CapacitorCoupling
from substrate import Substrate
import numpy as np

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

    def abcd_matrix(self, w):
        """
        Calculate the ABCD matrix of the resonator at angular frequency w.
        :param w: angular frequency (rad/s)
        :return:
        """
        # check if w is numpy array
        if not isinstance(w, np.ndarray):
            w = np.array(w).flatten()
        z_in = self.input_coupling.impedance(w)
        z_out = self.output_coupling.impedance(w)
        gamma_l = self.transition_line.gamma(w) * self.transition_line.length
        z0 = self.transition_line.z0()
        ones = np.ones_like(w)
        zeros = np.zeros_like(w)
        m_in = np.array([[ones, 1j*z_in.imag], [zeros, ones]]).T
        m_out = np.array([[ones, 1j*z_out.imag], [zeros, ones]]).T
        m_tl  = np.array([[np.cosh(gamma_l), z0 * np.sinh(gamma_l)],
                          [np.sinh(gamma_l) / z0, np.cosh(gamma_l)]]).T
        return m_in @ m_tl @ m_out

    def s21(self,  w):
        """
        Calculate the S21 parameter of the resonator at angular frequency w.
        :param w:
        :return:
        """
        abcd = self.abcd_matrix(w)
        a, b, c, d = abcd[:,0,0], abcd[:,0,1], abcd[:,1,0], abcd[:,1,1]
        r_in = self.input_coupling.impedance(w).real
        r_out = self.output_coupling.impedance(w).real
        return 2 / (a + b / r_out + c * r_in + d * r_in / r_out)

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
    w1 = resonator.resonance_frequency(1)
    w_min = float(w1) / 100.0
    w_max = float(w1) * 5.5
    w = np.linspace(w_min, w_max, 1000)
    x = w / (2 * math.pi * 1e9)
    s = resonator.s21(w)
    mag = np.abs(s)
    y = 20 * np.log10(mag + 1e-30)
