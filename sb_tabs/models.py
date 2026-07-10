"""Tab strip domain models (no Tk)."""

from __future__ import annotations

from dataclasses import dataclass, field

# Must match historical Signal Bridge settings / GUI constant.
ALL_CHANNELS_TAB = "__ALL_CHANNELS__"


@dataclass(frozen=True)
class TabInfo:
    tab_id: str
    title: str
    unread: int = 0
    closable: bool = True


@dataclass
class TabStripState:
    order: list[str] = field(default_factory=lambda: [ALL_CHANNELS_TAB])
    active_id: str | None = ALL_CHANNELS_TAB
    hidden: set[str] = field(default_factory=set)
    unread: dict[str, int] = field(default_factory=dict)

    def copy(self) -> "TabStripState":
        return TabStripState(
            order=list(self.order),
            active_id=self.active_id,
            hidden=set(self.hidden),
            unread=dict(self.unread),
        )
