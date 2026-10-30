"""Build small OpenDocument spreadsheets (.ods) with the standard library,
for tests.

Written the way LibreOffice writes them: an uncompressed `mimetype` entry
first, a manifest, and every sheet in one `content.xml`. Each row may end in
the repeated empty cells and each sheet in the repeated empty rows that
LibreOffice adds for the unused grid. `Raw` puts hand-written XML in place
of a cell or a row, for the awkward cases.
"""

import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from xml.sax.saxutils import escape, quoteattr

MIMETYPE = "application/vnd.oasis.opendocument.spreadsheet"
NAMESPACES = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"')


@dataclass
class Raw:
    """XML written as given, in place of a cell or a row."""
    xml: str


def _cell(value):
    if isinstance(value, Raw):
        return value.xml
    if value is None:
        return "<table:table-cell/>"
    if isinstance(value, bool):
        flag = "true" if value else "false"
        return (f'<table:table-cell office:value-type="boolean" office:boolean-value="{flag}">'
                f"<text:p>{flag.upper()}</text:p></table:table-cell>")
    if isinstance(value, (int, float)):
        return (f'<table:table-cell office:value-type="float" office:value="{value}">'
                f"<text:p>{value}</text:p></table:table-cell>")
    if isinstance(value, datetime):
        return (f'<table:table-cell office:value-type="date" office:date-value="{value.isoformat()}">'
                f"<text:p>{value}</text:p></table:table-cell>")
    if isinstance(value, date):
        return (f'<table:table-cell office:value-type="date" office:date-value="{value.isoformat()}">'
                f"<text:p>{value}</text:p></table:table-cell>")
    return (f'<table:table-cell office:value-type="string"><text:p>{escape(str(value))}</text:p>'
            "</table:table-cell>")


def _row(row, grid):
    if isinstance(row, Raw):
        return row.xml
    cells = "".join(_cell(v) for v in row)
    if grid:
        cells += '<table:table-cell table:number-columns-repeated="16380"/>'
    return f"<table:table-row>{cells}</table:table-row>"


def content_xml(sheets, grid=True):
    tables = []
    for name, rows in sheets:
        body = "".join(_row(r, grid) for r in rows)
        if grid:
            body += ('<table:table-row table:number-rows-repeated="1048000">'
                     '<table:table-cell table:number-columns-repeated="16384"/></table:table-row>')
        tables.append(f"<table:table table:name={quoteattr(name)}>{body}</table:table>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {NAMESPACES} '
            f'office:version="1.3"><office:body><office:spreadsheet>{"".join(tables)}'
            "</office:spreadsheet></office:body></office:document-content>")


def build_ods(sheets, grid=True, content=None):
    """sheets: [(name, [row, ...])], each row a list of values or a Raw."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE, compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml",
                         '<?xml version="1.0" encoding="UTF-8"?><manifest:manifest '
                         'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
                         'manifest:version="1.3"><manifest:file-entry manifest:full-path="/" '
                         f'manifest:media-type="{MIMETYPE}"/></manifest:manifest>',
                         compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("content.xml", content if content is not None else content_xml(sheets, grid),
                         compress_type=zipfile.ZIP_DEFLATED)
    return out.getvalue()
