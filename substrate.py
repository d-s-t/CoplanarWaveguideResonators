from abc import ABC, abstractmethod
from scipy import constants
from utilies import ValueRange, RangeCollectorMeta

class Substrate(ABC, metaclass=RangeCollectorMeta):
    """
    An abstract base class representing a substrate material.
    This class defines the interface for different types of substrates.
    it has the following attribute:
        permittivity: The permittivity of the substrate material
    """

    @property
    @abstractmethod
    def permittivity(self):
        pass

    @property
    @abstractmethod
    def permeability(self):
        pass

class EffectiveSubstrate(Substrate):
    """
    A class representing an effective substrate material.
    This class can be expanded with specific attributes and methods as needed.
    attributes:
        permittivity: The effective permittivity of the substrate material
    """
    RELATIVE_PERMITTIVITY_RANGE = ValueRange(1, 5.05, 20)  # Relative permittivity
    RELATIVE_PERMEABILITY_RANGE = ValueRange(1, 1, 5)

    def __init__(self, relative_permittivity=RELATIVE_PERMITTIVITY_RANGE.default,
                 relative_permeability=RELATIVE_PERMEABILITY_RANGE.default):
        self.relative_permittivity = relative_permittivity
        self.relative_permeability = relative_permeability

    @property
    def relative_permittivity(self):
        return self.__relative_permittivity

    @relative_permittivity.setter
    def relative_permittivity(self, value):
        if value <= 0:
            raise ValueError("Permittivity must be positive")
        self.__relative_permittivity = value

    @property
    def relative_permeability(self):
        return self.__relative_permeability
    @relative_permeability.setter
    def relative_permeability(self, value):
        if value <= 0:
            raise ValueError("Permeability must be positive")
        self.__relative_permeability = value

    @property
    def permittivity(self):
        return self.relative_permittivity * constants.epsilon_0

    @property
    def permeability(self):
        return self.relative_permeability * constants.mu_0

