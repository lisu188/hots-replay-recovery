"""Verified Dragon Shire talent packages retaining build 41810's authored map layout."""

from hashlib import sha256

HISTORICAL_PACKAGE = "662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800"
HISTORICAL_PACKAGES = frozenset({
    HISTORICAL_PACKAGE,
    "e8d151e5d574babf187e3c0b06cd4b29d2280ac085773afda36a3ebb9c79ffa7",
    "e6167145ee82e6c139f07336cd65fced5c86d162da19baad57a2d3e82b3a455e",
    "d41c5841a5719e76246265940d28b244bae91f4e3fef33e621f3a2e2a0ee7bbd",
    "f4d3b425cd9df5ed5390c45dc3c770300a64ba95449c82c228eed8b9928c7d6f",
})


def historical_package_digest(path):
    digest = sha256(path.read_bytes()).hexdigest()
    if digest not in HISTORICAL_PACKAGES:
        raise ValueError("Unverified historical Dragon Shire package")
    return digest
