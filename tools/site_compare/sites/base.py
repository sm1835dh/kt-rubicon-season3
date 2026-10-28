"""Site driver interface. One implementation per site template."""
from __future__ import annotations

from typing import Iterator, Protocol

from ..model import Context, Product, State

Box = tuple[float, float, float, float]  # page coordinates: x, y, w, h


class OptionUnavailable(Exception):
    """The site positively refuses the option (its own message, or a disabled control)."""


class OptionNotFound(Exception):
    """No control matches the option at all: a driver/selector problem, recorded as an error."""


class SiteDriver(Protocol):
    def prepare(self, page, ctx: Context) -> list[str]:
        """Dismiss banners and apply the region. Returns warnings."""

    def select(self, page, axis: str, value: str, product: Product) -> None:
        """Click the option. OptionUnavailable on positive evidence, OptionNotFound if no control matches."""

    def read_state(self, page, ctx: Context, product: Product) -> State:
        """Read the selection and price texts shown on screen."""

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        """Buy-flow sections (title, box) in page order, plus "Price bar" and "Summary"."""

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        """Open one layer at a time and yield (title, box); close it when resumed."""

    def close_extras(self, page) -> None:
        """Close anything extra_shots may have left open."""
