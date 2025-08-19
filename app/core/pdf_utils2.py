# app/core/pdf_utils.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

# --- Try WeasyPrint (preferred)
try:
    from weasyprint import HTML  # CSS is optional; we inline @page below
    HAS_WEASYPRINT = True
except Exception as _we:
    HAS_WEASYPRINT = False

# ---- Paths (assumes this file is app/core/pdf_utils.py)
APP_DIR = Path(__file__).resolve().parents[1]           # .../app
STATIC_DIR = APP_DIR / "static"                         # .../app/static
PROJECT_ROOT = APP_DIR.parent                           # project root


def _file_url(p: Path) -> str:
    """Convert a filesystem path to a file:// URL (with forward slashes)."""
    return p.resolve().as_uri()  # returns file:///C:/... on Windows


def _service_rows(services: Iterable[Any]) -> list[dict]:
    """Normalize service rows (supports ORM objects or dicts)."""
    rows = []
    for s in services or []:
        if isinstance(s, dict):
            desc = s.get("description", "")
            price = float(s.get("price", 0.0))
        else:
            # prisma model-like
            desc = getattr(s, "description", "")
            price = float(getattr(s, "price", 0.0))
        if str(desc).strip():
            rows.append({"description": str(desc).strip(), "price": round(price, 2)})
    return rows


def _resolve_logo_for_pdf(logo_url_or_path: str | None) -> str | None:
    """
    Convert your template logo_url (often '/static/...') to a file:// URL so
    WeasyPrint/ReportLab can load it locally.
    """
    if not logo_url_or_path:
        return None

    # If it's already a file:// URL or an http(s) URL, just return it
    low = logo_url_or_path.strip().lower()
    if low.startswith("file://") or low.startswith("http://") or low.startswith("https://"):
        return logo_url_or_path

    # If it begins with /static/, map to app/static/...
    if logo_url_or_path.startswith("/static/"):
        rel = logo_url_or_path[len("/static/") :]
        fs_path = STATIC_DIR / rel
        if fs_path.exists():
            return _file_url(fs_path)

    # If it's a relative path inside static (e.g. 'logos/x.png')
    maybe = STATIC_DIR / logo_url_or_path
    if maybe.exists():
        return _file_url(maybe)

    # As a last resort, treat as project-root relative
    fs_path = PROJECT_ROOT / logo_url_or_path.lstrip("/\\")
    if fs_path.exists():
        return _file_url(fs_path)

    # Not found; let HTML render without logo
    return None


def render_invoice_html(ctx: dict) -> str:
    """
    Build a clean HTML (A4) for PDF generation using ctx fields:
      - invoice, client, services, total, issue_date, due_date
      - company_name, company_email, company_site, company_phone
      - account_name, sort_code, account_number, iban
      - logo_url (web path); auto-converted to file:// for PDF
      - notes (optional)
    """
    invoice = ctx.get("invoice")
    client = ctx.get("client")
    services = _service_rows(ctx.get("services", []))
    total = float(ctx.get("total") or 0.0)

    company_name = ctx.get("company_name", "") or ""
    company_email = ctx.get("company_email", "") or ""
    company_site = ctx.get("company_site", "") or ""
    company_phone = ctx.get("company_phone", "") or ""
    account_name = ctx.get("account_name", "") or ""
    sort_code = ctx.get("sort_code", "") or ""
    account_number = ctx.get("account_number", "") or ""
    iban = ctx.get("iban", "") or ""
    notes = ctx.get("notes", "") or ""

    issue_date = ctx.get("issue_date", "")
    due_date = ctx.get("due_date", "")

    # Pretty invoice number for PDF email body alignment
    inv_number = ""
    try:
        inv_number = f"INV-{invoice.invoiceDate.strftime('%Y%m%d')}-{str(invoice.id)[:6].upper()}" if invoice else ""
    except Exception:
        pass

    # Convert logo URL to a file:// URL so WeasyPrint can embed it
    pdf_logo_url = _resolve_logo_for_pdf(ctx.get("logo_url"))

    # Build rows HTML
    rows_html = "\n".join(
        f"""<tr>
              <td>{r["description"]}</td>
              <td class="tright">£{r["price"]:.2f}</td>
            </tr>"""
        for r in services
    )

    html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Invoice {inv_number or ''}</title>
    <style>
      @page {{
        size: A4;
        margin: 12mm;
      }}
      body {{
        font-family: Arial, Helvetica, sans-serif;
        color: #111827;
        font-size: 12px;
      }}
      .header {{
        display:flex; justify-content:space-between; align-items:flex-end;
        border-bottom:1px solid #e5e7eb; padding-bottom:10px; margin-bottom:12px;
      }}
      .brand {{
        display:flex; gap:10px; align-items:center;
      }}
      .brand img {{
        height:70px; width:auto; object-fit:contain;
      }}
      h1 {{ margin: 0; font-size: 22px; }}
      .muted {{ color:#6b7280; }}
      .meta {{ text-align:right; }}
      .block {{
        display:flex; justify-content:space-between; gap:20mm; margin-top:10px;
      }}
      .subtitle {{ font-weight: 600; margin: 0 0 4px; }}
      .strong {{ font-weight: 700; }}
      table {{
        width:100%; border-collapse:collapse; margin-top:14px;
      }}
      th, td {{
        border-bottom:1px solid #e5e7eb; padding:6px 4px; text-align:left;
      }}
      th:last-child, td:last-child {{ text-align:right; }}
      .tright {{ text-align:right; }}
      .total-row td {{
        border-top:2px solid #111827; border-bottom:none; padding-top:8px;
        font-weight:700;
      }}
      .notes {{ margin-top: 12px; }}
    </style>
  </head>
  <body>
    <div class="header">
      <div class="brand">
        {"<img src='" + pdf_logo_url + "' alt='Logo'/>" if pdf_logo_url else ""}
        <div>
          <h1>Invoice {inv_number}</h1>
          <div class="muted">{company_name} • {company_site}</div>
        </div>
      </div>
      <div class="meta">
        <div><strong>Date:</strong> {issue_date or "-"}</div>
        <div><strong>Due:</strong> {due_date or "-"}</div>
        <div><strong>Total:</strong> £{total:.2f}</div>
      </div>
    </div>

    <div class="block">
      <div>
        <p class="subtitle">Bill To</p>
        <div class="strong">{getattr(client, 'name', '')} {getattr(client, 'surname', '')}</div>
        <div>{getattr(client, 'email', '')}</div>
        <div>{getattr(client, 'phone', '')}</div>
        <div class="muted">{getattr(client, 'address', '') or "—"}</div>
      </div>
      <div>
        <p class="subtitle">From</p>
        <div class="strong">{company_name}</div>
        <div>{company_email}</div>
        <div>{company_phone} • {company_site}</div>
        <div style="margin-top:6px;"><strong>Account Name:</strong> {account_name}</div>
        <div><strong>Sort Code:</strong> {sort_code}</div>
        <div><strong>Account Number:</strong> {account_number}</div>
        <div><strong>IBAN:</strong> {iban or "-"}</div>
      </div>
    </div>

    <table>
      <thead>
        <tr><th>Description</th><th>Price (£)</th></tr>
      </thead>
      <tbody>
        {rows_html}
        <tr class="total-row"><td class="tright">Total:</td><td>£{total:.2f}</td></tr>
      </tbody>
    </table>

    {"<div class='notes'><p class='subtitle'>Notes</p><div class='muted'>" + notes + "</div></div>" if notes else ""}
  </body>
</html>
"""
    return html


def html_to_pdf(html: str, out_path: str) -> None:
    """
    Convert HTML string to PDF using WeasyPrint. Raises if WeasyPrint isn't available.
    """
    if not HAS_WEASYPRINT:
        raise RuntimeError(
            "WeasyPrint is not available. Install it (and GTK on Windows) or use simple_invoice_pdf fallback."
        )
    # base_url helps resolve relative URLs; we’ve already converted /static/... to file://,
    # but this still helps if other relative refs appear later.
    HTML(string=html, base_url=STATIC_DIR.as_uri()).write_pdf(out_path)


# ---------- ReportLab fallback (no-HTML) ----------
def simple_invoice_pdf(invoice, services, client, ctx: dict, out_path: str) -> None:
    """
    Minimal, safe PDF generator using ReportLab. No HTML/CSS required.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
    except Exception as e:
        raise RuntimeError(
            "ReportLab is not installed. Run: pip install reportlab"
        ) from e

    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    y = height - 20 * mm

    # Header
    inv_number = ""
    try:
        inv_number = f"INV-{invoice.invoiceDate.strftime('%Y%m%d')}-{str(invoice.id)[:6].upper()}" if invoice else ""
    except Exception:
        pass

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, f"INVOICE {inv_number}".strip())
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    company_name = ctx.get("company_name", "")
    company_email = ctx.get("company_email", "")
    company_phone = ctx.get("company_phone", "")
    company_site = ctx.get("company_site", "")
    c.drawString(20 * mm, y, f"{company_name}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"{company_email} • {company_phone} • {company_site}".strip(" • "))
    y -= 8 * mm

    c.drawString(20 * mm, y, f"Issue: {ctx.get('issue_date','-')}   Due: {ctx.get('due_date','-')}")
    y -= 6 * mm

    # Bill To
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Bill To")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"{getattr(client,'name','')} {getattr(client,'surname','')}".strip())
    y -= 5 * mm
    if getattr(client, "email", None):
        c.drawString(20 * mm, y, f"{client.email}")
        y -= 5 * mm
    if getattr(client, "phone", None):
        c.drawString(20 * mm, y, f"{client.phone}")
        y -= 5 * mm
    addr = getattr(client, "address", "") or ""
    if addr:
        c.drawString(20 * mm, y, addr[:100])
        y -= 8 * mm

    # Services
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Description")
    c.drawRightString(190 * mm, y, "Price (£)")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    total = 0.0
    for r in _service_rows(services):
        c.drawString(20 * mm, y, r["description"][:90])
        c.drawRightString(190 * mm, y, f"£{r['price']:.2f}")
        total += float(r["price"])
        y -= 6 * mm
        if y < 30 * mm:
            c.showPage()
            y = height - 20 * mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(20 * mm, y, "Description")
            c.drawRightString(190 * mm, y, "Price (£)")
            y -= 6 * mm
            c.setFont("Helvetica", 10)

    # Total
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(190 * mm, y, f"Total: £{total:.2f}")
    y -= 10 * mm

    # Bank details
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Bank details")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Account name: {ctx.get('account_name','')}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Sort code: {ctx.get('sort_code','')}  •  Account no: {ctx.get('account_number','')}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"IBAN: {ctx.get('iban','-')}")

    # Notes (short)
    notes = str(ctx.get("notes") or "").strip()
    if notes:
        y -= 8 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, "Notes")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        for line in notes.splitlines():
            c.drawString(20 * mm, y, line[:100])
            y -= 5 * mm
            if y < 20 * mm:
                c.showPage()
                y = height - 20 * mm
                c.setFont("Helvetica", 10)

    c.showPage()
    c.save()
