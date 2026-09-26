import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Everything under tests/integration is an integration test; no per-file marking.
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)
