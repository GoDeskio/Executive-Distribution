"""PDF generation for quotes / receipts / customs documents with a tiled logo watermark."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from PIL import Image as PILImage

STEEL = colors.HexColor("#3E5B70")
DARK = colors.HexColor("#1A1A1D")
MUTED = colors.HexColor("#71717A")
LIGHT = colors.HexColor("#F4F4F5")


def _make_watermark(logo_bytes):
    """Return a faded, tiled PIL image sized to a letter page, or None."""
    if not logo_bytes:
        return None
    try:
        logo = PILImage.open(io.BytesIO(logo_bytes)).convert("RGBA")
    except Exception:
        return None
    # fade
    alpha = logo.split()[3].point(lambda p: int(p * 0.06))
    logo.putalpha(alpha)
    tile = logo.copy()
    tile.thumbnail((150, 150))
    page_w, page_h = 1275, 1650  # 8.5x11 @150dpi
    canvas = PILImage.new("RGBA", (page_w, page_h), (255, 255, 255, 0))
    step_x = tile.width + 120
    step_y = tile.height + 160
    for y in range(0, page_h, step_y):
        for x in range(0, page_w, step_x):
            canvas.alpha_composite(tile, (x, y))
    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG")
    out.seek(0)
    return out


def generate_document_pdf(doc: dict, settings: dict, logo_bytes: bytes = None) -> bytes:
    buf = io.BytesIO()
    watermark = _make_watermark(logo_bytes)

    def on_page(canvas, docref):
        if watermark:
            watermark.seek(0)
            canvas.drawImage(
                __import__("reportlab.lib.utils", fromlist=["ImageReader"]).ImageReader(watermark),
                0, 0, width=letter[0], height=letter[1], mask="auto",
            )
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.75 * inch, 0.5 * inch, settings.get("footer_text", ""))
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {docref.page}")

    pdoc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch,
                             bottomMargin=0.75 * inch, leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    h_company = ParagraphStyle("company", parent=styles["Title"], fontSize=20, textColor=DARK, spaceAfter=2)
    h_type = ParagraphStyle("dtype", parent=styles["Normal"], fontSize=22, textColor=STEEL, alignment=TA_RIGHT, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, textColor=MUTED)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=10, textColor=DARK)
    label = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=8, textColor=STEEL, fontName="Helvetica-Bold")

    elems = []
    dtype = (doc.get("doc_type") or "quote").upper()

    header_left = []
    if logo_bytes:
        try:
            img = PILImage.open(io.BytesIO(logo_bytes))
            ratio = img.height / img.width
            w = 1.4 * inch
            header_left.append(Image(io.BytesIO(logo_bytes), width=w, height=w * ratio))
        except Exception:
            pass
    header_left.append(Paragraph(settings.get("company_name", "Executive Distribution"), h_company))
    header_left.append(Paragraph(settings.get("address", ""), small))
    header_left.append(Paragraph(f'{settings.get("contact_email","")} · {settings.get("phone","")}', small))

    header_right = [
        Paragraph(dtype, h_type),
        Spacer(1, 6),
        Paragraph(f'No. <b>{doc.get("number","")}</b>', normal),
        Paragraph(f'Date: {doc.get("date","")}', small),
    ]
    if doc.get("po_number"):
        header_right.append(Paragraph(f'PO: {doc["po_number"]}', small))
    if doc.get("tracking_number"):
        header_right.append(Paragraph(f'Tracking: {doc["tracking_number"]}', small))
    if doc.get("port"):
        header_right.append(Paragraph(f'Port: {doc["port"]}', small))

    ht = Table([[header_left, header_right]], colWidths=[3.6 * inch, 3.4 * inch])
    ht.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elems += [ht, Spacer(1, 18)]

    # bill to
    elems.append(Paragraph("BILL TO", label))
    elems.append(Spacer(1, 3))
    bill = f'<b>{doc.get("client_name","")}</b>'
    if doc.get("client_company"): bill += f'<br/>{doc["client_company"]}'
    if doc.get("client_email"): bill += f'<br/>{doc["client_email"]}'
    if doc.get("client_phone"): bill += f'<br/>{doc["client_phone"]}'
    if doc.get("destination"): bill += f'<br/>Ship to: {doc["destination"]}'
    elems += [Paragraph(bill, normal), Spacer(1, 18)]

    # line items
    data = [["Item / Description", "Qty", "Unit Price", "Fees", "Customs", "Amount"]]
    for li in doc.get("line_items", []):
        item_text = li.get("item", "")
        if li.get("hs_code"):
            item_text += f'<br/><font size="7" color="#71717A">HS {li["hs_code"]}</font>'
        data.append([
            Paragraph(item_text, normal),
            str(li.get("qty", 1)),
            f'${float(li.get("unit_price", 0)):,.2f}',
            f'${float(li.get("fees", 0)):,.2f}',
            f'${float(li.get("customs", 0)):,.2f}',
            f'${float(li.get("total", 0)):,.2f}',
        ])
    tbl = Table(data, colWidths=[2.9 * inch, 0.5 * inch, 1.0 * inch, 0.8 * inch, 0.8 * inch, 1.0 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), LIGHT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F4F5")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elems += [tbl, Spacer(1, 14)]

    # totals
    totals = [
        ["Subtotal", f'${float(doc.get("subtotal", 0)):,.2f}'],
        ["Fees", f'${float(doc.get("fees_total", 0)):,.2f}'],
        ["Customs / Duties", f'${float(doc.get("customs_total", 0)):,.2f}'],
        ["Tax / VAT", f'${float(doc.get("tax_total", 0)):,.2f}'],
    ]
    tot_tbl = Table(totals + [["TOTAL", f'${float(doc.get("grand_total", 0)):,.2f}']],
                    colWidths=[1.6 * inch, 1.4 * inch], hAlign="RIGHT")
    tot_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -2), MUTED),
        ("LINEABOVE", (0, -1), (-1, -1), 1, STEEL),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), DARK),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(tot_tbl)

    if doc.get("notes"):
        elems += [Spacer(1, 20), Paragraph("NOTES", label), Spacer(1, 3), Paragraph(doc["notes"].replace("\n", "<br/>"), small)]

    pdoc.build(elems, onFirstPage=on_page, onLaterPages=on_page)
    buf.seek(0)
    return buf.read()
