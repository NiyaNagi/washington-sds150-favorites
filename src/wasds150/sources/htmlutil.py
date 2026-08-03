"""Minimal, dependency-free HTML table extraction shared by the HTML-scraping
source adapters (NOAA NWR, USCG NAVCEN, NWAC). Deliberately simple: these
adapters target a single static ``<table>`` each, not a general-purpose HTML
parser — see each adapter's module docstring for the specific page shape it
targets.
"""
from __future__ import annotations

from html.parser import HTMLParser
from typing import List, Optional


class TableExtractor(HTMLParser):
    """Extracts every ``<table>``'s rows (each a list of cell text, from
    ``<td>``/``<th>``) as ``self.tables: List[List[List[str]]]``."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._current_table: Optional[List[List[str]]] = None
        self._current_row: Optional[List[str]] = None
        self._in_cell = False
        self._cell_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in ("td", "th") and self._current_row is not None:
            self._in_cell = True
            self._cell_parts = []
        elif tag == "br" and self._in_cell:
            self._cell_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._in_cell:
            self._in_cell = False
            text = "".join(self._cell_parts).strip()
            text = " ".join(text.split())
            self._current_row.append(text)
        elif tag == "tr" and self._current_row is not None:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)


def extract_tables(html_text: str) -> List[List[List[str]]]:
    parser = TableExtractor()
    parser.feed(html_text)
    return parser.tables


def extract_links(html_text: str, *, href_contains: str = "") -> List[str]:
    """Every ``href`` attribute value, optionally filtered by substring —
    used by the link-discovery/change-detection adapters (WA EMD, WA DNR,
    NIFC, IACC)."""

    class _LinkParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.hrefs: List[str] = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                for key, value in attrs:
                    if key == "href" and value:
                        self.hrefs.append(value)

    parser = _LinkParser()
    parser.feed(html_text)
    if href_contains:
        return [h for h in parser.hrefs if href_contains in h]
    return parser.hrefs
