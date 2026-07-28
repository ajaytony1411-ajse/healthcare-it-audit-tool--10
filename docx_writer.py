"""A very small WordprocessingML writer, standard library only.

A .docx is a ZIP of XML parts. This builds the four parts Word needs for a
text-and-tables document, which is all an audit report requires. It exists so
the tool can issue a Word deliverable without pulling in python-docx.

Measurements are in DXA (twentieths of a point): 1440 DXA = 1 inch.
Font sizes are in half-points, so 20 = 10pt.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

A4_W, A4_H = 11906, 16838
MARGIN = 1134                      # 2cm
CONTENT_W = A4_W - 2 * MARGIN      # usable width for tables

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _style(sid: str, name: str, *, size: int, bold: bool = False,
           colour: str = "auto", before: int = 0, after: int = 120,
           outline: int | None = None, base: str = "Normal") -> str:
    parts = [f'<w:style w:type="paragraph" w:styleId="{sid}">',
             f'<w:name w:val="{name}"/>']
    if sid != "Normal":
        parts.append(f'<w:basedOn w:val="{base}"/>')
    parts.append("<w:pPr>")
    if outline is not None:
        parts.append(f'<w:outlineLvl w:val="{outline}"/>')
    parts.append(f'<w:spacing w:before="{before}" w:after="{after}" w:line="264" w:lineRule="auto"/>')
    parts.append("</w:pPr><w:rPr>")
    parts.append('<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>')
    if bold:
        parts.append("<w:b/>")
    parts.append(f'<w:color w:val="{colour}"/><w:sz w:val="{size}"/>')
    parts.append("</w:rPr></w:style>")
    return "".join(parts)


STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="20"/>
</w:rPr></w:rPrDefault></w:docDefaults>
{_style("Normal", "Normal", size=20)}
{_style("Title", "Title", size=40, bold=True, colour="1F3A5F", after=80)}
{_style("Subtitle", "Subtitle", size=20, colour="5C6B7A", after=240)}
{_style("Heading1", "heading 1", size=28, bold=True, colour="1F3A5F", before=320, after=140, outline=0)}
{_style("Heading2", "heading 2", size=23, bold=True, colour="1F3A5F", before=240, after=100, outline=1)}
{_style("Heading3", "heading 3", size=20, bold=True, colour="2C4A70", before=180, after=80, outline=2)}
{_style("Caption", "caption", size=16, colour="5C6B7A", after=180)}
</w:styles>"""


def _runs(runs) -> str:
    """runs: a string, or a list of (text, opts) where opts may set bold/colour/size/italic."""
    if isinstance(runs, str):
        runs = [(runs, {})]
    out = []
    for text, opts in runs:
        rpr = []
        if opts.get("bold"):
            rpr.append("<w:b/>")
        if opts.get("italic"):
            rpr.append("<w:i/>")
        if opts.get("colour"):
            rpr.append(f'<w:color w:val="{opts["colour"]}"/>')
        if opts.get("size"):
            rpr.append(f'<w:sz w:val="{opts["size"]}"/>')
        rpr_xml = f"<w:rPr>{''.join(rpr)}</w:rPr>" if rpr else ""
        out.append(f'<w:r>{rpr_xml}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>')
    return "".join(out)


class Docx:
    """Accumulates body XML, then writes the package."""

    def __init__(self):
        self.body: list[str] = []

    # -- block elements -------------------------------------------------

    def para(self, runs="", style: str | None = None, *, align: str | None = None,
             space_after: int | None = None, border_below: bool = False) -> "Docx":
        ppr = []
        if style:
            ppr.append(f'<w:pStyle w:val="{style}"/>')
        if border_below:
            ppr.append('<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="4" '
                       'w:color="1F3A5F"/></w:pBdr>')
        if align:
            ppr.append(f'<w:jc w:val="{align}"/>')
        if space_after is not None:
            ppr.append(f'<w:spacing w:after="{space_after}"/>')
        ppr_xml = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
        self.body.append(f"<w:p>{ppr_xml}{_runs(runs)}</w:p>")
        return self

    def heading(self, text: str, level: int = 1) -> "Docx":
        return self.para(text, f"Heading{level}")

    def title(self, text: str) -> "Docx":
        return self.para(text, "Title")

    def subtitle(self, text: str) -> "Docx":
        return self.para(text, "Subtitle")

    def bullets(self, items) -> "Docx":
        # A real numbering definition needs a numbering part; for a handful of
        # flat lists an indented paragraph with a bullet glyph is equivalent
        # on the page and keeps the package to four parts.
        for item in items:
            self.body.append(
                '<w:p><w:pPr><w:ind w:left="360" w:hanging="180"/>'
                '<w:spacing w:after="40"/></w:pPr>'
                f'{_runs([("•   ", {}), (item, {})])}</w:p>')
        return self

    def table(self, rows, widths, *, header: bool = True,
              shade_first_col: bool = False) -> "Docx":
        """rows: list of rows; each cell is a string or a list of (text, opts)."""
        total = sum(widths)
        if total != CONTENT_W:                      # normalise to the text width
            widths = [round(w * CONTENT_W / total) for w in widths]
            widths[-1] += CONTENT_W - sum(widths)

        border = ('<w:tblBorders>' + "".join(
            f'<w:{edge} w:val="single" w:sz="4" w:space="0" w:color="C9D3DE"/>'
            for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
        ) + "</w:tblBorders>")

        xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{CONTENT_W}" w:type="dxa"/>',
               border, '<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>']
        xml += [f'<w:gridCol w:w="{w}"/>' for w in widths]
        xml.append("</w:tblGrid>")

        for r, row in enumerate(rows):
            is_head = header and r == 0
            trpr = "<w:trPr><w:tblHeader/></w:trPr>" if is_head else ""
            xml.append(f"<w:tr>{trpr}")
            for c, cell in enumerate(row):
                shaded = is_head or (shade_first_col and c == 0)
                shd = ('<w:shd w:val="clear" w:color="auto" w:fill="F2F5F8"/>'
                       if shaded else "")
                content = cell
                if isinstance(content, str):
                    content = [(content, {"bold": True} if shaded else {})]
                xml.append(
                    f'<w:tc><w:tcPr><w:tcW w:w="{widths[c]}" w:type="dxa"/>{shd}'
                    '<w:tcMar><w:top w:w="60" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/>'
                    '<w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tcMar>'
                    '</w:tcPr>'
                    f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{_runs(content)}</w:p></w:tc>')
            xml.append("</w:tr>")
        xml.append("</w:tbl>")
        self.body.append("".join(xml))
        # Word requires a paragraph after a table; it also stops two adjacent
        # tables from being merged into one.
        self.para("", space_after=120)
        return self

    def page_break(self) -> "Docx":
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        return self

    # -- output ---------------------------------------------------------

    def _document(self) -> str:
        sect = (f'<w:sectPr><w:pgSz w:w="{A4_W}" w:h="{A4_H}"/>'
                f'<w:pgMar w:top="{MARGIN}" w:right="{MARGIN}" w:bottom="{MARGIN}" '
                f'w:left="{MARGIN}" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>')
        return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                f'<w:document xmlns:w="{W_NS}"><w:body>'
                f'{"".join(self.body)}{sect}</w:body></w:document>')

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", CONTENT_TYPES)
            z.writestr("_rels/.rels", ROOT_RELS)
            z.writestr("word/_rels/document.xml.rels", DOC_RELS)
            z.writestr("word/styles.xml", STYLES)
            z.writestr("word/document.xml", self._document())
        return path
