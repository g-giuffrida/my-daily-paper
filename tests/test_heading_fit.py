from copy import deepcopy
from engine import compose_regions, demo_issue, register_fonts
from settings import DEFAULT


def test_subhead_is_not_left_alone_at_column_bottom():
    register_fonts()
    settings = deepcopy(DEFAULT)
    _, placements = compose_regions(settings, demo_issue(settings, "2026-10-10"))
    for i, (region, flow, x, y, _) in enumerate(placements):
        if getattr(flow, "_keep_with_next", False):
            next_region, next_flow, next_x, next_y, _ = placements[i + 1]
            assert next_region == region and next_x == x and next_y < y
