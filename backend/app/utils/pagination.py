from dataclasses import dataclass

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class PageParams:
    """1-based page request, translated to LIMIT/OFFSET for repositories.

    page_size is capped so no request can pull the whole 10k-row table into the app.
    """

    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= self.page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
