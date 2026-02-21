"""Domain exceptions.

A two-level hierarchy keeps the exception surface small while giving
callers a choice over how specifically they respond:

  - Catch the category base (NotFoundError, InvalidOperationError) when
    the handling is identical regardless of which entity or rule was
    involved — e.g. a presentation layer mapping all missing-entity cases
    to HTTP 404.
  - Catch the specific subclass when you need the entity-specific
    attribute (.code, .comparison_id) or need to distinguish between
    types of the same category.

This mirrors Python's own stdlib pattern: LookupError is the catchable
category; KeyError and IndexError are the specific subclasses.
"""


class DomainError(Exception):
    """Root for all domain exceptions.

    Catch this only at an outermost boundary (e.g. a global error handler)
    where the sole goal is to distinguish domain failures from unexpected
    runtime errors.
    """


class NotFoundError(DomainError):
    """An entity could not be located in the repository.

    Presentation layers that map all missing-entity cases to a single
    response (HTTP 404, a console message, etc.) should catch this base
    class rather than listing each specific subclass.
    """


class InvalidOperationError(DomainError):
    """A business rule was violated.

    Analogous to HTTP 422: the request was well-formed but cannot be
    processed given the current domain state.
    """


class CountryNotFoundError(NotFoundError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Country with code '{code}' was not found.")
        self.code = code


class ComparisonNotFoundError(NotFoundError):
    def __init__(self, comparison_id: int) -> None:
        super().__init__(f"Comparison with id {comparison_id} was not found.")
        self.comparison_id = comparison_id


class SameCountryComparisonError(InvalidOperationError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Cannot compare a country with itself ('{code}').")
        self.code = code
