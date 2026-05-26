"""pytest configuration — project-wide fixtures and CLI options.

Plan reference: ``003_Step03_GeometryPipeline_Plan.md`` §4.4 + S03-D10.

Registers the ``--update-goldens`` CLI flag and exposes it as the
``update_goldens`` fixture so per-stage golden tests can switch between
"assert" and "rewrite" modes without touching their own signatures.

Usage::

    pytest                            # normal mode: compare against goldens
    pytest --update-goldens           # rewrite goldens from current outputs
    pytest --update-goldens -s        # also see the [GOLDEN UPDATE] prints

Goldens updates **must** land as a dedicated commit so the PR diff makes
the change visible. See Plan §6 Risks.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help=(
            "Rewrite tests/golden/<case>/<stage>.json from current algorithm "
            "outputs instead of comparing. Use with -s to see writes."
        ),
    )


@pytest.fixture
def update_goldens(request) -> bool:
    """Truthy when ``pytest --update-goldens`` was passed."""
    return bool(request.config.getoption("--update-goldens"))
