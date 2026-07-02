"""Minimal markdown -> Tk Text rendering for the in-app help viewer.

parse_markdown is pure (no Tk) and unit-tested. Supported subset:
#/##/### headings, **bold**, "- " bullets, `inline code`, bare https URLs.
Anything else renders as plain body text â€” deliberately not a full engine.
"""

import re
import webbrowser

from . import theme

_INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|https?://\S+)")


def parse_markdown(text: str) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        if line.startswith("### "):
            segments.append((line[4:] + "\n", "h3"))
        elif line.startswith("## "):
            segments.append((line[3:] + "\n", "h2"))
        elif line.startswith("# "):
            segments.append((line[2:] + "\n", "h1"))
        elif line.startswith("- "):
            segments.append(("  â€¢ ", "bullet"))
            _parse_inline(segments, line[2:])
            segments.append(("\n", "body"))
        elif not line:
            segments.append(("\n", "body"))
        else:
            _parse_inline(segments, line)
            segments.append(("\n", "body"))
    return segments


def _parse_inline(segments: list, line: str) -> None:
    pos = 0
    for match in _INLINE.finditer(line):
        if match.start() > pos:
            segments.append((line[pos:match.start()], "body"))
        token = match.group(0)
        if token.startswith("**"):
            segments.append((token[2:-2], "bold"))
        elif token.startswith("`"):
            segments.append((token[1:-1], "code"))
        else:
            segments.append((token, "link"))
        pos = match.end()
    if pos < len(line):
        segments.append((line[pos:], "body"))


def render_into(widget, segments: list, on_link=None) -> None:
    open_link = on_link or webbrowser.open
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.tag_configure("h1", font=theme.font(15, bold=True),
                         foreground=theme.COLORS["fg_bright"], spacing1=8, spacing3=6)
    widget.tag_configure("h2", font=theme.font(12, bold=True),
                         foreground=theme.COLORS["fg_bright"], spacing1=8, spacing3=4)
    widget.tag_configure("h3", font=theme.font(10, bold=True),
                         foreground=theme.COLORS["fg"], spacing1=6, spacing3=2)
    widget.tag_configure("body", font=theme.font(10), foreground=theme.COLORS["fg"])
    widget.tag_configure("bullet", font=theme.font(10), foreground=theme.COLORS["fg_muted"])
    widget.tag_configure("bold", font=theme.font(10, bold=True),
                         foreground=theme.COLORS["fg_bright"])
    widget.tag_configure("code", font=("Consolas", 9), foreground=theme.COLORS["gold"],
                         background=theme.COLORS["bg_input"])
    widget.tag_configure("link", font=theme.font(10), foreground="#5ad7ff", underline=True)
    link_count = 0
    for text, tag in segments:
        if tag == "link":
            name = f"link{link_count}"
            link_count += 1
            widget.insert("end", text, ("link", name))
            widget.tag_bind(name, "<Button-1>", lambda _e, u=text: open_link(u))
        else:
            widget.insert("end", text, (tag,))
    widget.tag_bind("link", "<Enter>", lambda _e: widget.configure(cursor="hand2"))
    widget.tag_bind("link", "<Leave>", lambda _e: widget.configure(cursor=""))
    widget.configure(state="disabled")
