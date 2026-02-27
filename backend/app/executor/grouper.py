from math import floor

from ..models import Script


def group_scripts(scripts: list[Script]) -> list[list[Script]]:
    """Group scripts by floor(ordering_number), sorted by group key."""
    groups: dict[int, list[Script]] = {}
    for script in scripts:
        key = floor(script.ordering_number)
        groups.setdefault(key, []).append(script)
    return [members for _, members in sorted(groups.items())]
