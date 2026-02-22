"""Repository interfaces, expressed as Protocols.

Using typing.Protocol (PEP 544 structural subtyping) is the idiomatic
Python equivalent of a C# interface:

  - Concrete implementations do NOT need to inherit from these classes.
    The type checker (mypy/pyright) verifies structural compatibility
    at call sites – this is "duck typing with static guarantees".

  - @runtime_checkable allows isinstance() checks if needed, but the
    primary value is static analysis, not runtime enforcement.

Two separate protocols reflect two separate responsibilities:
  - CountryRepository   – read-only access to reference country data.
  - ComparisonRepository – write/read access to computed comparisons.
"""
from typing import Protocol, runtime_checkable

from domain.models import Country, CountryComparison


@runtime_checkable
class CountryRepository(Protocol):
    """Read-only access to country reference data."""

    def get_by_code(self, code: str) -> Country | None: ...
    def list_all(self) -> list[Country]: ...


@runtime_checkable
class ComparisonRepository(Protocol):
    """Persistence for computed country comparisons."""

    def get_by_id(self, comparison_id: int) -> CountryComparison | None: ...
    def list_all(self) -> list[CountryComparison]: ...
    def save(self, comparison: CountryComparison) -> CountryComparison: ...
