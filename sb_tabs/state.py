"""Pure tab strip state machine."""

from __future__ import annotations

from sb_tabs.models import ALL_CHANNELS_TAB, TabInfo, TabStripState


def tab_label(tab_id: str) -> str:
    return "All" if tab_id == ALL_CHANNELS_TAB else tab_id


def short_title(label: str, max_chars: int = 28) -> str:
    text = (label or "").strip()
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1] + "…"


def normalize(
    state: TabStripState,
    open_channels: set[str],
    *,
    prefer_all: bool = False,
) -> TabStripState:
    """Reconcile order/hidden/active with currently open channels."""
    s = state.copy()
    valid = set(open_channels)
    valid.add(ALL_CHANNELS_TAB)
    s.hidden = {x for x in s.hidden if x in valid}
    ordered: list[str] = []
    for tab_id in s.order:
        if tab_id in valid and tab_id not in ordered:
            ordered.append(tab_id)
    if ALL_CHANNELS_TAB not in ordered:
        ordered.insert(0, ALL_CHANNELS_TAB)
    # Keep All first when present
    if ALL_CHANNELS_TAB in ordered and ordered[0] != ALL_CHANNELS_TAB:
        ordered = [ALL_CHANNELS_TAB] + [t for t in ordered if t != ALL_CHANNELS_TAB]
    for channel in sorted(open_channels):
        if channel not in ordered:
            ordered.append(channel)
    s.order = ordered
    s.unread = {
        k: v
        for k, v in s.unread.items()
        if (k == ALL_CHANNELS_TAB or k in open_channels) and v > 0
    }
    visible_ids = _visible_ids(s, open_channels)
    if s.active_id not in visible_ids:
        if prefer_all and ALL_CHANNELS_TAB in visible_ids:
            s.active_id = ALL_CHANNELS_TAB
        else:
            s.active_id = visible_ids[0] if visible_ids else None
    return s


def _visible_ids(state: TabStripState, open_channels: set[str]) -> list[str]:
    tabs: list[str] = []
    if ALL_CHANNELS_TAB not in state.hidden:
        tabs.append(ALL_CHANNELS_TAB)
    for tab_id in state.order:
        if tab_id == ALL_CHANNELS_TAB:
            continue
        if tab_id in open_channels and tab_id not in state.hidden:
            tabs.append(tab_id)
    return tabs


def visible_tabs(
    state: TabStripState,
    open_channels: set[str],
    *,
    titles: dict[str, str] | None = None,
    max_title_chars: int = 28,
) -> list[TabInfo]:
    titles = titles or {}
    out: list[TabInfo] = []
    for tab_id in _visible_ids(state, open_channels):
        raw = titles.get(tab_id) or tab_label(tab_id)
        out.append(
            TabInfo(
                tab_id=tab_id,
                title=short_title(raw, max_title_chars),
                unread=int(state.unread.get(tab_id, 0) or 0),
                closable=tab_id != ALL_CHANNELS_TAB,
            )
        )
    return out


def select_tab(
    state: TabStripState,
    tab_id: str,
    open_channels: set[str],
) -> TabStripState:
    s = normalize(state, open_channels)
    if tab_id != ALL_CHANNELS_TAB and tab_id not in open_channels:
        return s
    if tab_id in s.hidden:
        return s
    s.active_id = tab_id
    s.unread.pop(tab_id, None)
    return s


def close_tab(
    state: TabStripState,
    tab_id: str,
    open_channels: set[str],
) -> TabStripState:
    """Hide a tab (including All). Closable channels leave open_channels alone."""
    s = normalize(state, open_channels)
    if tab_id != ALL_CHANNELS_TAB and tab_id not in open_channels:
        return s
    s.hidden.add(tab_id)
    s.unread.pop(tab_id, None)
    if s.active_id == tab_id:
        visible = _visible_ids(s, open_channels)
        s.active_id = _neighbor_after_close(state, tab_id, visible) if visible else None
        if s.active_id is None and visible:
            s.active_id = visible[0]
    return s


def _neighbor_after_close(
    before: TabStripState,
    closed_id: str,
    remaining_visible: list[str],
) -> str | None:
    """Prefer right neighbor, else left, else first remaining."""
    if not remaining_visible:
        return None
    # Order before close among previously visible-ish order
    order = [t for t in before.order if t == ALL_CHANNELS_TAB or True]
    try:
        idx = order.index(closed_id)
    except ValueError:
        return remaining_visible[0]
    # look right
    for j in range(idx + 1, len(order)):
        if order[j] in remaining_visible:
            return order[j]
    # look left
    for j in range(idx - 1, -1, -1):
        if order[j] in remaining_visible:
            return order[j]
    return remaining_visible[0]


def close_others(
    state: TabStripState,
    keep_tab_id: str,
    open_channels: set[str],
) -> TabStripState:
    s = normalize(state, open_channels)
    for tab_id in list(_visible_ids(s, open_channels)):
        if tab_id != keep_tab_id:
            s.hidden.add(tab_id)
            s.unread.pop(tab_id, None)
    if keep_tab_id == ALL_CHANNELS_TAB or keep_tab_id in open_channels:
        s.hidden.discard(keep_tab_id)
        s.active_id = keep_tab_id
    return s


def close_all_closable(
    state: TabStripState,
    open_channels: set[str],
) -> TabStripState:
    """Hide all channel tabs; keep All visible and active."""
    s = normalize(state, open_channels)
    for ch in open_channels:
        s.hidden.add(ch)
        s.unread.pop(ch, None)
    s.hidden.discard(ALL_CHANNELS_TAB)
    s.active_id = ALL_CHANNELS_TAB
    s.unread.pop(ALL_CHANNELS_TAB, None)
    return s


def restore_tab(
    state: TabStripState,
    tab_id: str,
    open_channels: set[str],
    *,
    focus: bool = False,
) -> TabStripState:
    s = state.copy()
    open_set = set(open_channels)
    if tab_id != ALL_CHANNELS_TAB:
        open_set.add(tab_id)
    s.hidden.discard(tab_id)
    if tab_id not in s.order:
        if tab_id == ALL_CHANNELS_TAB:
            s.order.insert(0, tab_id)
        else:
            s.order.append(tab_id)
    s = normalize(s, open_set if tab_id == ALL_CHANNELS_TAB else open_set)
    # normalize needs actual open set — caller must add channel to open_channels for channels
    if focus or not s.active_id:
        s.active_id = tab_id
        s.unread.pop(tab_id, None)
    return s


def reorder(
    state: TabStripState,
    from_index: int,
    to_index: int,
    open_channels: set[str],
) -> TabStripState:
    """Reorder among visible channel tabs; All stays first in full order."""
    s = normalize(state, open_channels)
    visible = [t for t in _visible_ids(s, open_channels) if t != ALL_CHANNELS_TAB]
    if not visible:
        return s
    if from_index < 0 or from_index >= len(visible):
        return s
    to_index = max(0, min(to_index, len(visible) - 1))
    item = visible.pop(from_index)
    visible.insert(to_index, item)
    # rebuild order: All first, then reordered channels, then any non-visible open
    rest = [t for t in s.order if t != ALL_CHANNELS_TAB and t not in visible]
    s.order = [ALL_CHANNELS_TAB] + visible + rest
    return s


def move_before(
    state: TabStripState,
    tab_id: str,
    target_id: str,
    open_channels: set[str],
) -> TabStripState:
    """Move tab_id to sit before target_id in channel order (All immovable first)."""
    s = normalize(state, open_channels)
    if tab_id == ALL_CHANNELS_TAB or target_id == ALL_CHANNELS_TAB:
        return s
    if tab_id not in s.order or target_id not in s.order:
        return s
    channels = [t for t in s.order if t != ALL_CHANNELS_TAB]
    if tab_id not in channels or target_id not in channels:
        return s
    channels.remove(tab_id)
    idx = channels.index(target_id)
    channels.insert(idx, tab_id)
    s.order = [ALL_CHANNELS_TAB] + channels
    return s


def mark_unread(
    state: TabStripState,
    tab_id: str,
    *,
    delta: int = 1,
    active_id: str | None = None,
) -> TabStripState:
    """Increment unread unless tab is the active one."""
    s = state.copy()
    current = active_id if active_id is not None else s.active_id
    if tab_id == current:
        return s
    s.unread[tab_id] = int(s.unread.get(tab_id, 0) or 0) + delta
    return s


def clear_unread(state: TabStripState, tab_id: str) -> TabStripState:
    s = state.copy()
    s.unread.pop(tab_id, None)
    return s


def overflow_split(
    visible: list[TabInfo],
    max_visible: int,
) -> tuple[list[TabInfo], list[TabInfo]]:
    if max_visible < 1:
        return [], list(visible)
    if len(visible) <= max_visible:
        return list(visible), []
    # Keep All + first channels in strip; overflow the rest
    primary = visible[:max_visible]
    overflow = visible[max_visible:]
    return primary, overflow


def hidden_count(state: TabStripState, open_channels: set[str]) -> int:
    s = normalize(state, open_channels)
    return len(
        [
            t
            for t in s.order
            if t in s.hidden and (t == ALL_CHANNELS_TAB or t in open_channels)
        ]
    )
