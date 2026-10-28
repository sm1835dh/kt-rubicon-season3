from .base import BaseDriver, Box, OptionNotFound, OptionUnavailable, SiteDriver


def get_driver(name: str) -> SiteDriver:
    if name == "hubble":
        from .hubble import HubbleDriver
        return HubbleDriver()
    if name == "us":
        from .us import UsDriver
        return UsDriver()
    raise ValueError(f"unknown driver {name!r}")


__all__ = ["BaseDriver", "Box", "OptionNotFound", "OptionUnavailable", "SiteDriver", "get_driver"]
