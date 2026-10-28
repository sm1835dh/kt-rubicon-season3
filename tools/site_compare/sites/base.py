"""Site driver interface. One implementation per page template."""
from __future__ import annotations

from typing import Iterator, Protocol

from ..model import Context, Option, Product, SpecItem, State

Box = tuple[float, float, float, float]  # page coordinates: x, y, w, h


class OptionUnavailable(Exception):
    """The site positively refuses the option (its own message, or a disabled control)."""


class OptionNotFound(Exception):
    """No control matches the option at all: a driver/selector problem, recorded as an error."""


class SiteDriver(Protocol):
    def prepare(self, page, ctx: Context) -> list[str]:
        """Dismiss banners and check the region. Returns warnings."""

    def select(self, page, axis: str, value: str, product: Product) -> None:
        """Click mode: click the option. OptionUnavailable on positive evidence, OptionNotFound if no control."""

    def options(self, page, ctx: Context, axis: str) -> list[Option]:
        """Discover mode: the axis' options in the current state (Option.sku = SKU after choosing it, if known)."""

    def choose(self, page, ctx: Context, option: Option) -> None:
        """Discover mode: click an option found by options() and wait until the page reflects it."""

    def sku_url(self, ctx: Context, sku: str | None) -> str | None:
        """URL that opens the page directly in that SKU's state, or None when the template has none."""

    def read_state(self, page, ctx: Context, product: Product) -> State:
        """Read the selection and price texts shown on screen."""

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        """Buy-flow sections (title, box) in page order, plus "Price bar" and "Summary"."""

    def specs(self, page) -> tuple[list[SpecItem], list[tuple[str, Box]]]:
        """Expand the spec section; return its items and the boxes to screenshot."""

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        """Open one layer at a time and yield (title, box); close it when resumed."""

    def close_extras(self, page) -> None:
        """Close anything extra_shots may have left open."""


class BaseDriver:
    """Defaults so a template driver implements only what its pages have."""

    def prepare(self, page, ctx: Context) -> list[str]:
        return []

    def select(self, page, axis: str, value: str, product: Product) -> None:
        raise OptionNotFound(f"{type(self).__name__} has no click-mode selection")

    def options(self, page, ctx: Context, axis: str) -> list[Option]:
        return []

    def choose(self, page, ctx: Context, option: Option) -> None:
        raise OptionNotFound(f"{type(self).__name__} cannot choose {option.axis}")

    def sku_url(self, ctx: Context, sku: str | None) -> str | None:
        return None

    def specs(self, page) -> tuple[list[SpecItem], list[tuple[str, Box]]]:
        return [], []

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        return []

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        return iter(())

    def close_extras(self, page) -> None:
        pass
