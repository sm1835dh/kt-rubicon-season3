from .base import BaseDriver, Box, OptionNotFound, OptionUnavailable, SiteDriver


def get_driver(name: str) -> SiteDriver:
    if name == "hubble":
        from .hubble import HubbleDriver
        return HubbleDriver()
    if name == "us":
        from .us import UsDriver
        return UsDriver()
    if name == "pd":
        from .pd import PdDriver
        return PdDriver()
    if name == "us_pdp":
        from .us_pdp import UsPdpDriver
        return UsPdpDriver()
    if name == "watchbc":
        from .watchbc import WatchBcDriver
        return WatchBcDriver()
    raise ValueError(f"unknown driver {name!r}")


__all__ = ["BaseDriver", "Box", "OptionNotFound", "OptionUnavailable", "SiteDriver", "get_driver"]
