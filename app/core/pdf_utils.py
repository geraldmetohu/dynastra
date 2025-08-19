# app/core/pdf_utils.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---- Paths
BASE_DIR = Path(__file__).resolve().parents[2]        # project root
APP_DIR = BASE_DIR / "app"
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

# ---- Jinja env
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

def _file_url(p: Path) -> str:
    return p.resolve().as_uri()  # file:///C:/... on Windows

def _service_rows(services: Iterable[Any]) -> list[dict]:
    """Normalize service rows (supports ORM objects or dicts)."""
    rows: list[dict] = []
    for s in services or []:
        if isinstance(s, dict):
            desc = s.get("description", "")
            price = float(s.get("price", 0.0))
        else:
            desc = getattr(s, "description", "")
            price = float(getattr(s, "price", 0.0))
        if str(desc).strip():
            rows.append({"description": str(desc).strip(), "price": round(price, 2)})
    return rows

def render_invoice_html(ctx: Dict[str, Any], template_name: str = "pdf/invoice.html") -> str:
    """
    Render the PDF HTML from Jinja template.
    Expects ctx to include:
      - invoice, client, services (or invoice.services), total
      - issue_date, due_date
      - company_* fields, account_* fields, iban, notes (optional)
      - logo_src: file:// URL to logo (if not provided, we compute from /static/logos/dynastra_dark.png)
    """
    # Compute invoice number if possible
    inv = ctx.get("invoice")
    inv_num = ""
    try:
        inv_num = f"INV-{inv.invoiceDate.strftime('%Y%m%d')}-{str(inv.id)[:6].upper()}" if inv else ""
    except Exception:
        pass
    ctx["invoice_number"] = inv_num

    # Ensure logo_src is a file:// URL (so WeasyPrint embeds it)
    if not ctx.get("logo_src"):
        logo_path = STATIC_DIR / "logos" / "dynastra_dark.png"
        if logo_path.exists():
            ctx["logo_src"] = _file_url(logo_path)

    # Normalize rows + total
    rows = _service_rows(ctx.get("services") or (getattr(inv, "services", None)))
    ctx["rows"] = rows
    if "total" not in ctx or ctx["total"] in (None, ""):
        ctx["total"] = round(sum(r["price"] for r in rows), 2)

    # Defaults
    ctx.setdefault("company_name", "")
    ctx.setdefault("company_email", "")
    ctx.setdefault("company_site", "")
    ctx.setdefault("company_phone", "")
    ctx.setdefault("account_name", "")
    ctx.setdefault("sort_code", "")
    ctx.setdefault("account_number", "")
    ctx.setdefault("iban", "")
    ctx.setdefault("notes", "")

    template = env.get_template(template_name)
    return template.render(**ctx)

def html_to_pdf(html: str, out_path: str) -> None:
    """Render HTML → PDF using WeasyPrint with a base_url so assets resolve."""
    from weasyprint import HTML, CSS
    styles = [CSS(string="@page { size: A4; margin: 12mm }")]
    HTML(string=html, base_url=str(BASE_DIR)).write_pdf(out_path, stylesheets=styles)
