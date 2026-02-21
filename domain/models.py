"""Domain entities.

Plain dataclasses: no ORM decorators, no framework dependencies.
"""
from dataclasses import dataclass, field


@dataclass
class Country:
    """A country with measurable socioeconomic metrics."""

    code: str               # ISO 3166-1 alpha-3 (e.g. "GBR", "USA")
    name: str
    population: int
    area_km2: float
    gdp_usd_billions: float
    life_expectancy: float  # years
    id: int = field(default=0)

    @property
    def gdp_per_capita(self) -> float:
        return (self.gdp_usd_billions * 1_000_000_000) / self.population

    @property
    def population_density(self) -> float:
        return self.population / self.area_km2


@dataclass
class CountryComparison:
    """The persisted result of comparing two countries' metrics."""

    country_x_code: str
    country_y_code: str
    gdp_per_capita_ratio: float       # x / y
    population_ratio: float           # x / y
    life_expectancy_delta: float      # x − y  (years)
    population_density_ratio: float   # x / y
    id: int = field(default=0)
