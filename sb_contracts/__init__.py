"""Signal Bridge target contracts (pure domain shapes)."""

from sb_contracts.addon_event import make_addon_event, row_to_addon_event
from sb_contracts.diagnostic_event import make_diagnostic_event, redact_context
from sb_contracts.intel_segment import IntelSegment, intel_segment_from_legacy, intel_segment_to_dict
from sb_contracts.pilot_info_snapshot import empty_pilot_info_snapshot
from sb_contracts.render_row import RenderRow, build_render_row
from sb_contracts.translation_decision import (
    TranslationDecision,
    make_translation_decision,
    translation_decision_to_dict,
)

__all__ = [
    "IntelSegment",
    "intel_segment_from_legacy",
    "intel_segment_to_dict",
    "TranslationDecision",
    "make_translation_decision",
    "translation_decision_to_dict",
    "RenderRow",
    "build_render_row",
    "make_diagnostic_event",
    "redact_context",
    "make_addon_event",
    "row_to_addon_event",
    "empty_pilot_info_snapshot",
]
