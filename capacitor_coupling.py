from abc import ABC, abstractmethod
from substrate import Substrate
from utilies import ValueRange, RangeCollectorMeta
import numpy as np

class CapacitorCoupling(ABC, metaclass=RangeCollectorMeta):
    """
    An abstract base class representing a coupling mechanism.
    This class defines the interface for different types of couplings.
    """
    RESISTANCE_RANGE = ValueRange(10, 30, 50, .1)  # Ohm

    @abstractmethod
    def __init__(self, resistence):
        self.resistance = resistence
        self.substrate = None

    def parallel_capacitance(self, w_n):
        c_k = self.capacitance
        r_l = self.resistance
        return c_k / (1 + (w_n * c_k * r_l) ** 2)

    def parallel_resistance(self, w_n):
        c_k = self.capacitance
        r_l = self.resistance
        return (1 + (w_n * c_k * r_l) ** 2) / (w_n ** 2 * c_k ** 2 * r_l)

    def parallel_resonance_approx(self, w_n):
        return self.resistance / (self.k_factor(w_n) ** 2)

    def k_factor(self, w_n):
        c_k = self.capacitance
        r_l = self.resistance
        return w_n * c_k * r_l

    @property
    def resistance(self):
        return self.__resistance
    @resistance.setter
    def resistance(self, value):
        if np.any(value <= 0):
            raise ValueError("Resistance must be positive")
        self.__resistance = value

    @property
    def substrate(self):
        return self.__substrate
    @substrate.setter
    def substrate(self, value):
        if not isinstance(value, Substrate) and value is not None:
            raise ValueError("Substrate must be an instance of Substrate or None")
        self.__substrate = value

    @property
    @abstractmethod
    def capacitance(self):
        pass

class SimplifiedCapacitor(CapacitorCoupling):
    """
    A class representing a basic capacitor coupling mechanism.
    This class can be expanded with specific attributes and methods as needed.
    attributes:
        capacitance: The capacitance of the capacitor
    """
    CAPACITANCE_RANGE = ValueRange(1e-17, 4e-15, 7e-14, 1e-17)  # Farad
    def __init__(self,
                 resistence=CapacitorCoupling.RESISTANCE_RANGE.default,
                 capacitance=CAPACITANCE_RANGE.default):
        super().__init__(resistence)
        self.capacitance = capacitance

    @property
    def capacitance(self):
        return self.__capacitance
    @capacitance.setter
    def capacitance(self, value):
        if np.any(value <= 0):
            raise ValueError("Capacitance must be positive")
        self.__capacitance = value

class GapCapacitor(CapacitorCoupling):
    """
    A class representing a gap capacitor coupling mechanism.
    This class can be expanded with specific attributes and methods as needed.
    attributes:
        gap: The gap size of the capacitor
        width: The width of the capacitor
        thickness: The thickness of the capacitor
    """
    GAP_RANGE = ValueRange(1e-6, 3e-5, 1e-4)
    WIDTH_RANGE = ValueRange(1e-6, 1e-5, 2e-5)
    THICKNESS_RANGE = ValueRange(1e-7, 2e-7, 4e-7)

    def __init__(self,
                 resistence=CapacitorCoupling.RESISTANCE_RANGE.default,
                 gap=GAP_RANGE.default,
                 width=WIDTH_RANGE.default,
                 thickness=THICKNESS_RANGE.default):
        super().__init__(resistence)
        self.gap = gap
        self.width = width
        self.thickness = thickness

    @property
    def capacitance(self):
        return self.substrate.permittivity * self.width * self.thickness / self.gap

    @property
    def gap(self):
        return self.__gap
    @gap.setter
    def gap(self, value):
        if np.any(value <= 0):
            raise ValueError("Gap must be positive")
        self.__gap = value

    @property
    def width(self):
        return self.__width
    @width.setter
    def width(self, value):
        if np.any(value <= 0):
            raise ValueError("Width must be positive")
        self.__width = value

    @property
    def thickness(self):
        return self.__thickness
    @thickness.setter
    def thickness(self, value):
        if np.any(value <= 0):
            raise ValueError("Thickness must be positive")
        self.__thickness = value

class FingerCapacitor(CapacitorCoupling):
    """
    A class representing a finger capacitor coupling mechanism.
    This class can be expanded with specific attributes and methods as needed.
    attributes:
        finger_length: Length of each finger
        finger_thickness: thickness of each finger
        finger_count: Number of fingers
        gap: Gap between fingers
    """
    LENGTH_RANGE = ValueRange(5e-5, 1e-4, 2e-4)
    THICKNESS_RANGE = ValueRange(1e-7, 2e-7, 4e-7)
    COUNT_RANGE = ValueRange(1, 5, 20, 1)
    GAP_RANGE = ValueRange(1e-6, 3.3e-6, 7e-6)

    def __init__(self,
                 resistence=CapacitorCoupling.RESISTANCE_RANGE.default,
                 length=LENGTH_RANGE.default,
                 thickness=THICKNESS_RANGE.default,
                 count=COUNT_RANGE.default,
                 gap=GAP_RANGE.default
                 ):
        super().__init__(resistence)
        self.finger_length = length
        self.finger_thickness = thickness
        self.finger_count = count
        self.finger_gap = gap

    @property
    def capacitance(self):
        return self.substrate.permittivity * self.finger_length * self.finger_thickness * self.finger_count / self.finger_gap

    @property
    def finger_length(self):
        return self.__finger_length
    @finger_length.setter
    def finger_length(self, value):
        if np.any(value <= 0):
            raise ValueError("Finger length must be positive")
        self.__finger_length = value

    @property
    def finger_thickness(self):
        return self.__finger_thickness
    @finger_thickness.setter
    def finger_thickness(self, value):
        if np.any(value <= 0):
            raise ValueError("Finger thickness must be positive")
        self.__finger_thickness = value

    @property
    def finger_count(self):
        return self.__finger_count
    @finger_count.setter
    def finger_count(self, value: int):
        if np.any(value <= 0):
            raise ValueError("Finger count must be positive")
        self.__finger_count = value

    @property
    def finger_gap(self):
        return self.__finger_gap
    @finger_gap.setter
    def finger_gap(self, value):
        if np.any(value <= 0):
            raise ValueError("Finger gap must be positive")
        self.__finger_gap = value

