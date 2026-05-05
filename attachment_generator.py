"""
attachment_generator.py
=======================
Generates fake-but-realistic-looking binary attachments without external
document libraries. All formats are produced using only Python stdlib.

Supported types: pdf, docx, xlsx, zip, txt
"""

import io
import os
import random
import struct
import time
import zipfile
from datetime import datetime
from faker import Faker

fk = Faker("en_US")


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _lorem(sentences: int = 5) -> str:
    return " ".join(fk.sentence() for _ in range(sentences))


def _table_rows(rows=6, cols=4) -> list[list]:
    headers = random.sample(
        ["Date", "Description", "Amount", "Category", "Status",
         "Owner", "Due", "Priority", "Notes", "Reference", "Qty", "Unit"], cols)
    data = []
    for _ in range(rows):
        row = []
        for h in headers:
            if h in ("Amount",):
                row.append(f"${random.randint(10,10000):,}")
            elif h in ("Date", "Due"):
                row.append(datetime.now().strftime("%-m/%-d/%Y"))
            elif h == "Status":
                row.append(random.choice(["Open", "Closed", "Pending", "Review", "Done"]))
            elif h == "Priority":
                row.append(random.choice(["High", "Medium", "Low"]))
            elif h == "Qty":
                row.append(str(random.randint(1, 100)))
            else:
                row.append(fk.bs().title()[:30])
        data.append(row)
    return [headers] + data


# --------------------------------------------------------------------------- #
# Minimal valid PDF generator (no external libs)                               #
# --------------------------------------------------------------------------- #

def _make_pdf(title: str, body_text: str) -> bytes:
    """Produce a tiny but syntactically valid PDF with text content."""
    lines = []
    for raw in body_text.split("\n"):
        cleaned = raw.strip()
        if not cleaned:
            continue
        # PDF text must have parens escaped
        escaped = cleaned.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")
        lines.append(escaped)

    page_content_lines = [
        "BT",
        "/F1 11 Tf",
        "50 750 Td",
        "14 TL",
    ]
    for line in lines[:60]:          # cap to avoid huge PDFs
        page_content_lines.append(f"({line}) Tj T*")
    page_content_lines.append("ET")
    page_content = "\n".join(page_content_lines)

    stream = page_content.encode("latin-1", errors="replace")
    stream_len = len(stream)

    pdf = []
    offsets = []

    pdf.append(b"%PDF-1.4\n")

    # obj 1 – catalog
    offsets.append(len(b"".join(pdf)))
    pdf.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    # obj 2 – pages
    offsets.append(len(b"".join(pdf)))
    pdf.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

    # obj 3 – page
    offsets.append(len(b"".join(pdf)))
    pdf.append(
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R\n"
        b"   /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R\n"
        b"   /Resources << /Font << /F1 5 0 R >> >> >>\n"
        b"endobj\n"
    )

    # obj 4 – content stream
    offsets.append(len(b"".join(pdf)))
    pdf.append(
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )

    # obj 5 – font
    offsets.append(len(b"".join(pdf)))
    pdf.append(
        b"5 0 obj\n"
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        b"endobj\n"
    )

    body = b"".join(pdf)
    xref_offset = len(body)

    xref = f"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"

    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )

    return body + xref.encode() + trailer.encode()


# --------------------------------------------------------------------------- #
# Minimal DOCX (ZIP of XML) generator                                          #
# --------------------------------------------------------------------------- #

_DOCX_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>"""

_DOCX_CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels"
    ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_DOCX_WORD_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>"""


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _make_docx(title: str, body_text: str) -> bytes:
    """Build a minimal .docx (OOXML ZIP) with the given text."""
    paragraphs = []
    for line in body_text.split("\n"):
        stripped = line.strip()
        text_elem = f"<w:t xml:space=\"preserve\">{_xml_escape(stripped)}</w:t>"
        paragraphs.append(
            f"<w:p><w:r>{text_elem}</w:r></w:p>"
        )

    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(paragraphs)
        + "</w:body></w:document>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _DOCX_CONTENT_TYPES)
        zf.writestr("_rels/.rels", _DOCX_RELS)
        zf.writestr("word/document.xml", doc_xml)
        zf.writestr("word/_rels/document.xml.rels", _DOCX_WORD_RELS)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Minimal XLSX (ZIP of XML) generator                                          #
# --------------------------------------------------------------------------- #

def _make_xlsx(title: str, rows: list[list]) -> bytes:
    """Build a minimal .xlsx from a list-of-lists (first row = header)."""

    def cell_ref(r, c):
        col = ""
        n   = c + 1
        while n:
            col = chr(64 + (n % 26 or 26)) + col
            n   = (n - 1) // 26
        return f"{col}{r + 1}"

    sheet_rows = []
    for ri, row in enumerate(rows):
        cells = ""
        for ci, val in enumerate(row):
            ref = cell_ref(ri, ci)
            cells += (
                f'<c r="{ref}" t="inlineStr">'
                f'<is><t>{_xml_escape(str(val))}</t></is></c>'
            )
        sheet_rows.append(f"<row r=\"{ri + 1}\">{cells}</row>")

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(sheet_rows) + "</sheetData>"
        "</worksheet>"
    )

    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets><sheet name=\"Sheet1\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
        "</workbook>"
    )

    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"'
        ' Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    ct = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
        ' Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# ZIP attachment                                                                #
# --------------------------------------------------------------------------- #

def _make_zip(title: str, body_text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # README inside
        zf.writestr("README.txt", body_text)
        # A fake data file
        rows = _table_rows(10, 4)
        csv_lines = [",".join(r) for r in rows]
        zf.writestr("data.csv", "\n".join(csv_lines))
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Public API                                                                    #
# --------------------------------------------------------------------------- #

MIME_TYPES = {
    "pdf":  "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip":  "application/zip",
}

FILENAME_PREFIXES = {
    "pdf":  ["Report", "Invoice", "Policy", "Guide", "Summary", "Notice",
              "Document", "Proposal", "Brief", "Statement"],
    "docx": ["Draft", "Document", "Form", "Template", "Agreement", "Memo",
              "Specification", "Review", "Assessment", "Plan"],
    "xlsx": ["Data", "Spreadsheet", "Budget", "Tracker", "Report",
              "Analysis", "Schedule", "Log", "Register", "Summary"],
    "zip":  ["Archive", "Package", "Bundle", "Release", "Backup", "Export"],
}


def generate_attachment(subject: str, body: str, attach_type: str) -> tuple[str, bytes, str]:
    """
    Returns (filename, content_bytes, mime_type).

    attach_type: one of 'pdf', 'docx', 'xlsx', 'zip'
    """
    attach_type = attach_type.lower()
    prefix  = random.choice(FILENAME_PREFIXES.get(attach_type, ["File"]))
    suffix  = f"_{datetime.now().strftime('%Y%m%d')}_{random.randint(100,999)}"
    filename = f"{prefix}{suffix}.{attach_type}"

    title = subject[:60]

    if attach_type == "pdf":
        data = _make_pdf(title, body)
    elif attach_type == "docx":
        data = _make_docx(title, body)
    elif attach_type == "xlsx":
        rows = _table_rows(random.randint(5, 20), random.randint(3, 6))
        data = _make_xlsx(title, rows)
    elif attach_type == "zip":
        data = _make_zip(title, body)
    else:
        data = body.encode("utf-8")
        filename = f"attachment_{random.randint(1000,9999)}.txt"

    mime = MIME_TYPES.get(attach_type, "application/octet-stream")
    return filename, data, mime
