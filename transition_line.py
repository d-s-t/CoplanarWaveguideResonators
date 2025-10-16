from abc import ABC, abstractmethod
from substrate import Substrate
from scipy import constants
from utilies import ValueRange, RangeCollectorMeta

class TransitionLine(ABC, metaclass=RangeCollectorMeta):
    """
    An abstract base class representing a transition line.
    This class defines the interface for different types of transition lines.
    """
    LENGTH_RANGE = ValueRange(5e-3, 1e-2, 4e-2)  # meters

    @abstractmethod
    def __init__(self, length=LENGTH_RANGE.default):
        self.length = length
        self.substrate: Substrate|None = None

    @property
    def substrate(self):
        return self.__substrate

    @substrate.setter
    def substrate(self, value: Substrate):
        if not isinstance(value, Substrate) and value is not None:
            raise ValueError("Substrate must be an instance of Substrate or None")
        self.__substrate = value

    @property
    @abstractmethod
    def parallel_capacitance(self):
        pass

    @abstractmethod
    def parallel_inductance(self, n):
        pass

    @property
    @abstractmethod
    def parallel_resistance(self):
        pass

    @property
    def length(self):
        return self.__length

    @length.setter
    def length(self, value):
        if value <= 0:
            raise ValueError("Length must be positive")
        self.__length = value

    def resonance_frequency(self, n):
        l = self.parallel_inductance(n)
        c = self.parallel_capacitance
        return (l*c) ** -0.5

    def quality_factor(self, n):
        w_n = self.resonance_frequency(n)
        r = self.parallel_resistance
        c = self.parallel_capacitance
        return w_n * r * c



class GeometricTransitionLine(TransitionLine):
    """
    A class representing the transition line of a resonator.
    This class can be expanded with specific attributes and methods as needed.
    attributes:
        length: Length of the transition line
        width: Width of the transition line
        separation: Separation between the transition line and the ground plane
        thickness: Thickness of the transition line
    """

    WIDTH_RANGE = ValueRange(1e-6, 1e-5, 2e-5)
    SEPARATION_RANGE = ValueRange(1e-6, 1e-5, 2e-5)
    THICKNESS_RANGE = ValueRange(1e-7, 2e-7, 4e-7)
    RESISTANCE_PER_LENGTH_RANGE = ValueRange(0, 1, 10)  # Ohm/meter

    def __init__(self,
                 length=TransitionLine.LENGTH_RANGE.default,
                 width=WIDTH_RANGE.default,
                 separation=SEPARATION_RANGE.default,
                 thickness=THICKNESS_RANGE.default,
                 resistance_per_length=RESISTANCE_PER_LENGTH_RANGE.default):
        super().__init__(length)
        self.width = width
        self.separation = separation
        self.thickness = thickness
        self.resistance_per_length = resistance_per_length

    @property
    def parallel_resistance(self):
        return self.resistance_per_length * self.length

    def parallel_inductance(self, n):
        return 2 * self.inductance_per_length * self.length / (n**2 * constants.pi**2)

    @property
    def parallel_capacitance(self):
        return self.capacitance_per_length * self.length / 2

    @property
    def width(self):
        return self.__width

    @width.setter
    def width(self, value):
        if value <= 0:
            raise ValueError("Width must be positive")
        self.__width = value

    @property
    def separation(self):
        return self.__separation

    @separation.setter
    def separation(self, value):
        if value <= 0:
            raise ValueError("Separation must be positive")
        self.__separation = value

    @property
    def thickness(self):
        return self.__thickness

    @thickness.setter
    def thickness(self, value):
        if value <= 0:
            raise ValueError("Thickness must be positive")
        self.__thickness = value

    @property
    def resistance_per_length(self):
        return self.__resistance_per_length
    @resistance_per_length.setter
    def resistance_per_length(self, value):
        if value < 0:
            raise ValueError("Resistance per length must be non-negative")
        self.__resistance_per_length = value

    @property
    def capacitance_per_length(self):
        return self.substrate.permittivity * self.thickness / self.separation

    @property
    def inductance_per_length(self):
        # Caution: This formula may not be correct at all...
        return self.substrate.permeability * 2 * self.separation / self.thickness

class DistributedTransitionLine(TransitionLine):
    """
    A class representing a distributed transition line.
    This class can be expanded with specific attributes and methods as needed.
    attributes:
        capacitance_per_length: Capacitance per unit length
        inductance_per_length: Inductance per unit length
        attenuation_constant: attenuation constant
    """
    CAPACITANCE_PER_LENGTH_RANGE = ValueRange(1e-12, 1e-11, 1e-10)  # F/m
    INDUCTANCE_PER_LENGTH_RANGE = ValueRange(1e-7, 1e-6, 1e-5)  # H/m
    ATTENUATION_CONSTANT_RANGE = ValueRange(0, 0.1, 1)  # Neper/m

    def __init__(self,
                 length=TransitionLine.LENGTH_RANGE.default,
                 capacitance_per_length=CAPACITANCE_PER_LENGTH_RANGE.default,
                 inductance_per_length=INDUCTANCE_PER_LENGTH_RANGE.default,
                 attenuation_constant=ATTENUATION_CONSTANT_RANGE.default):
        super().__init__(length)
        self.capacitance_per_length = capacitance_per_length
        self.inductance_per_length = inductance_per_length
        self.attenuation_constant = attenuation_constant

    @property
    def parallel_capacitance(self):
        return self.capacitance_per_length * self.length / 2

    def parallel_inductance(self, n):
        return 2 * self.inductance_per_length * self.length / (n**2 * constants.pi**2)

    @property
    def parallel_resistance(self):
        return self._z0() / (self.attenuation_constant * self.length)

    def _z0(self):
        return (self.inductance_per_length / self.capacitance_per_length) ** 0.5

    @property
    def capacitance_per_length(self):
        return self.__capacitance_per_length
    @capacitance_per_length.setter
    def capacitance_per_length(self, value):
        if value <= 0:
            raise ValueError("Capacitance per length must be positive")
        self.__capacitance_per_length = value

    @property
    def inductance_per_length(self):
        return self.__inductance_per_length
    @inductance_per_length.setter
    def inductance_per_length(self, value):
        if value <= 0:
            raise ValueError("Inductance per length must be positive")
        self.__inductance_per_length = value

    @property
    def attenuation_constant(self):
        return self.__attenuation_constant
    @attenuation_constant.setter
    def attenuation_constant(self, value):
        if value < 0:
            raise ValueError("Attenuation constant must be non-negative")
        self.__attenuation_constant = value

class SimplifiedTransitionLine(TransitionLine):
    """
    A simplified version of the TransitionLine class.
    This class can be expanded with specific attributes and methods as needed.
    attributes:
        capacitance: effective capacitance as parallel LCR circuit
        resistance: effective resistance as parallel LCR circuit
        base_inductance: effective inductance as parallel LCR circuit
    """
    CAPACITANCE_RANGE = ValueRange(1e-15, 1e-14, 1e-12)  # Farad
    RESISTANCE_RANGE = ValueRange(1, 100, 1e4)  # Ohm
    BASE_INDUCTANCE_RANGE = ValueRange(1e-9, 1e-8, 1e-6)  # Henry

    def __init__(self,
                 length=TransitionLine.LENGTH_RANGE.default,
                 capacitance=CAPACITANCE_RANGE.default,
                 resistance=RESISTANCE_RANGE.default,
                 base_inductance=BASE_INDUCTANCE_RANGE.default):
        super().__init__(length)
        self.capacitance = capacitance
        self.resistance = resistance
        self.base_inductance = base_inductance

    @property
    def parallel_capacitance(self):
        return self.capacitance

    def parallel_inductance(self, n):
        return self.base_inductance / (n**2)

    @property
    def parallel_resistance(self):
        return self.resistance

    @property
    def capacitance(self):
        return self.__capacitance
    @capacitance.setter
    def capacitance(self, value):
        if value <= 0:
            raise ValueError("Capacitance must be positive")
        self.__capacitance = value

    @property
    def resistance(self):
        return self.__resistance
    @resistance.setter
    def resistance(self, value):
        if value <= 0:
            raise ValueError("Resistance must be positive")
        self.__resistance = value

    @property
    def base_inductance(self):
        return self.__base_inductance
    @base_inductance.setter
    def base_inductance(self, value):
        if value <= 0:
            raise ValueError("Base inductance must be positive")
        self.__base_inductance = value


