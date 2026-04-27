"""
Shared HTML-to-text conversion utilities for PVIM-MTP scripts.

This module is the SINGLE SOURCE OF TRUTH for HTML stripping across all
pvim-mtp scripts (extraction, verification, gap analysis). All scripts
MUST import from here — never duplicate HTMLStripper locally.

The canonical implementation was extracted from hsdes_mtp_descriptions.py
during the H3/L3 audit consolidation (2026-03-30).
"""

import re
from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    """Simple HTML-to-text converter preserving paragraph/line breaks."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._in_list = False

    def handle_starttag(self, tag, attrs):
        if tag in ("br",):
            self._parts.append("\n")
        elif tag in ("p", "div"):
            if self._parts and not self._parts[-1].endswith("\n"):
                self._parts.append("\n")
        elif tag in ("li",):
            self._parts.append("\n  - ")
            self._in_list = True
        elif tag in ("ul", "ol"):
            self._in_list = True

    def handle_endtag(self, tag):
        if tag in ("p", "div", "ul", "ol", "tr"):
            self._parts.append("\n")
        elif tag in ("li",):
            pass  # newline handled in next starttag
        elif tag in ("th", "td"):
            self._parts.append(" | ")

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_text(html: str) -> str:
    """Convert HTML string to plain text."""
    if not html:
        return ""
    stripper = HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()
