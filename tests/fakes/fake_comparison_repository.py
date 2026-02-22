"""In-memory fake for ComparisonRepository – used in tests only."""
from domain.models import CountryComparison


class FakeComparisonRepository:
    def __init__(self) -> None:
        self._store: dict[int, CountryComparison] = {}
        self._next_id: int = 1

    # ------------------------------------------------------------------
    # ComparisonRepository protocol implementation
    # ------------------------------------------------------------------

    def get_by_id(self, comparison_id: int) -> CountryComparison | None:
        return self._store.get(comparison_id)

    def list_all(self) -> list[CountryComparison]:
        return list(self._store.values())

    def save(self, comparison: CountryComparison) -> CountryComparison:
        comparison.id = self._next_id
        self._next_id += 1
        self._store[comparison.id] = comparison
        return comparison
