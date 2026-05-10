"""palette.role_to_palette_key tests (Step 06 §4.7, S06-D11).

Step 03 frame silently fell back to "private" for unknown roles, hiding
typo bugs. Step 06 makes unknown roles a ValueError to match Stage 01's
strict role validation (S06-D10) — D004/D005 fail-loud policy.
"""
from __future__ import annotations

import pytest

from proto3.viz.palette import role_to_palette_key


@pytest.mark.parametrize("role,expected_key", [
    ("public",   "public-hub"),
    ("hub",      "public-hub"),
    ("private",  "private"),
    ("wet",      "wet-service"),
    ("service",  "wet-service"),
    ("corridor", "corridor"),
])
def test_role_to_palette_key_canonical_roles(role, expected_key):
    assert role_to_palette_key(role) == expected_key


@pytest.mark.parametrize("bad_role", ["rolee", "PUBLIC", "", "Private", "office"])
def test_role_to_palette_key_unknown_raises_value_error(bad_role):
    """No more silent private fallback — unknown role must fail loud."""
    with pytest.raises(ValueError, match="unknown role"):
        role_to_palette_key(bad_role)
