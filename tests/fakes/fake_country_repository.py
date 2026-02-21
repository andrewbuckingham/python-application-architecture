"""In-memory fake for CountryRepository – used in tests only."""
from domain.models import Country


class FakeCountryRepository:
    def __init__(self, countries: list[Country] | None = None) -> None:
        # Pre-populate from an optional seed list so tests can provide
        # known data without going through a service method.
        self._store: dict[str, Country] = {
            c.code: c for c in (countries or [])
        }

    # ------------------------------------------------------------------
    # CountryRepository protocol implementation
    # ------------------------------------------------------------------

    def get_by_code(self, code: str) -> Country | None:
        return self._store.get(code.upper())

    def list_all(self) -> list[Country]:
        return list(self._store.values())
