import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from database import execute, query_all, query_one

CENT = Decimal("0.01")
DEFAULT_SALE_BROKERAGE_RATE = Decimal("0.02")
DEFAULT_GST_RATE = Decimal("18")
DEAL_TYPES = ("sale", "rent")
PAYMENT_METHODS = ("cash", "upi", "bank_transfer", "cheque", "card", "other")
STATUS_UNPAID = "unpaid"
STATUS_PARTIAL = "partial"
STATUS_PAID = "paid"
STATUS_VOID = "void"
MAX_AMOUNT = Decimal("999999999999.99")


def to_money(value, field="Amount", allow_zero=True):
    """Parse user/DB input into a 2dp Decimal; raise ValueError on bad input."""
    if isinstance(value, Decimal):
        amount = value
    else:
        text = str(value if value is not None else "").replace(",", "").strip()
        if not text:
            text = "0"
        try:
            amount = Decimal(text)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{field} must be a number.") from exc
    if not amount.is_finite():
        raise ValueError(f"{field} must be a number.")
    amount = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    if amount < 0:
        raise ValueError(f"{field} cannot be negative.")
    if not allow_zero and amount == 0:
        raise ValueError(f"{field} must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise ValueError(f"{field} is too large.")
    return amount


def normalize_deal_type(value):
    text = (value or "").strip().lower()
    if text in {"rent", "rental", "lease"}:
        return "rent"
    return "sale"


def suggested_brokerage(deal_type, deal_amount):
    """Prefill: 2% of sale price, or one month's rent for rentals."""
    amount = to_money(deal_amount, "Deal amount")
    if normalize_deal_type(deal_type) == "rent":
        return amount
    return (amount * DEFAULT_SALE_BROKERAGE_RATE).quantize(CENT, rounding=ROUND_HALF_UP)


def compute_totals(brokerage_amount, gst_enabled=False, gst_rate=DEFAULT_GST_RATE):
    brokerage = to_money(brokerage_amount, "Brokerage", allow_zero=False)
    rate = to_money(gst_rate, "GST rate") if gst_enabled else Decimal("0.00")
    gst = (brokerage * rate / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
    return {
        "brokerage_amount": brokerage,
        "gst_enabled": bool(gst_enabled),
        "gst_rate": rate if gst_enabled else to_money(DEFAULT_GST_RATE),
        "gst_amount": gst,
        "total_amount": brokerage + gst,
    }


def compute_pending(total_amount, payments):
    total = to_money(total_amount)
    paid = sum((to_money(p.get("amount") if isinstance(p, dict) else p) for p in payments or []), Decimal("0.00"))
    return {"paid_total": paid, "pending": total - paid}


def status_for(total_amount, paid_total):
    total = to_money(total_amount)
    paid = to_money(paid_total)
    if paid <= 0:
        return STATUS_UNPAID
    if paid >= total:
        return STATUS_PAID
    return STATUS_PARTIAL


def format_receipt_no(receipt_id, created=None):
    year = (created or datetime.now()).year
    return f"JK-{year}-{int(receipt_id):05d}"


def _clean(value, max_len=500):
    return (str(value).strip() if value is not None else "")[:max_len]


GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def normalize_gstin(value):
    """Optional client GSTIN: blank -> None, otherwise uppercase 15-char format or ValueError."""
    text = re.sub(r"\s+", "", str(value or "")).upper()
    if not text:
        return None
    if not GSTIN_RE.match(text):
        raise ValueError("Client GSTIN must be a valid 15-character GSTIN (e.g. 24ABCDE1234F1Z5).")
    return text


def _hydrate(row):
    if not row:
        return None
    data = dict(row)
    for key in ("deal_amount", "brokerage_amount", "gst_rate", "gst_amount", "total_amount"):
        data[key] = to_money(data.get(key) if data.get(key) is not None else 0)
    data["gst_enabled"] = bool(int(data.get("gst_enabled") or 0))
    return data


def create_receipt(data, created_by_admin_id=None, property_row=None):
    """Create a receipt with snapshot fields; returns the hydrated receipt."""
    client_name = _clean(data.get("client_name"), 160)
    if not client_name:
        raise ValueError("Client name is required.")
    deal_type = normalize_deal_type(data.get("deal_type") or (property_row or {}).get("listing_type"))
    deal_amount = to_money(data.get("deal_amount"), "Deal amount")
    brokerage_raw = data.get("brokerage_amount")
    if brokerage_raw in (None, ""):
        brokerage_raw = suggested_brokerage(deal_type, deal_amount)
    gst_enabled = str(data.get("gst_enabled") or "").strip().lower() in {"1", "true", "on", "yes"}
    totals = compute_totals(brokerage_raw, gst_enabled, data.get("gst_rate") or DEFAULT_GST_RATE)
    client_gstin = normalize_gstin(data.get("client_gstin"))

    prop = property_row or {}
    receipt_id = execute(
        """INSERT INTO billing_receipts
           (property_id, property_name, property_address, deal_type, client_name, client_mobile,
            client_email, client_address, client_gstin, deal_amount, brokerage_amount, gst_enabled,
            gst_rate, gst_amount, total_amount, status, notes, created_by_admin_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            prop.get("id") or None,
            _clean(data.get("property_name") or prop.get("property_name"), 200) or None,
            _clean(data.get("property_address") or prop.get("address"), 400) or None,
            deal_type,
            client_name,
            _clean(data.get("client_mobile"), 20) or None,
            _clean(data.get("client_email"), 160) or None,
            _clean(data.get("client_address"), 400) or None,
            client_gstin,
            str(deal_amount),
            str(totals["brokerage_amount"]),
            totals["gst_enabled"],
            str(totals["gst_rate"]),
            str(totals["gst_amount"]),
            str(totals["total_amount"]),
            STATUS_UNPAID,
            _clean(data.get("notes"), 1000) or None,
            created_by_admin_id,
        ),
    )
    if not receipt_id:
        raise ValueError("Could not create receipt.")
    execute(
        "UPDATE billing_receipts SET receipt_no=%s WHERE id=%s",
        (format_receipt_no(receipt_id), receipt_id),
    )
    return get_receipt(receipt_id)


def list_payments(receipt_id):
    rows = query_all(
        """SELECT id, receipt_id, amount, payment_date, method, reference, note,
                  recorded_by_admin_id, created_at
           FROM billing_payments WHERE receipt_id=%s ORDER BY created_at, id""",
        (receipt_id,),
    )
    payments = []
    for row in rows or []:
        item = dict(row)
        item["amount"] = to_money(item.get("amount"))
        payments.append(item)
    return payments


def get_receipt(receipt_id):
    receipt = _hydrate(query_one("SELECT * FROM billing_receipts WHERE id=%s", (receipt_id,)))
    if not receipt:
        return None
    payments = list_payments(receipt_id)
    receipt["payments"] = payments
    receipt.update(compute_pending(receipt["total_amount"], payments))
    return receipt


def list_receipts(limit=100, offset=0, status=None):
    sql = """SELECT r.*, COALESCE(p.paid, 0) AS paid_total
             FROM billing_receipts r
             LEFT JOIN (
               SELECT receipt_id, SUM(amount) AS paid FROM billing_payments GROUP BY receipt_id
             ) p ON p.receipt_id = r.id"""
    params = []
    if status:
        sql += " WHERE r.status=%s"
        params.append(status)
    sql += " ORDER BY r.created_at DESC, r.id DESC LIMIT %s OFFSET %s"
    params.extend([int(limit), int(offset)])
    receipts = []
    for row in query_all(sql, tuple(params)) or []:
        item = _hydrate(row)
        item["paid_total"] = to_money(row.get("paid_total") or 0)
        item["pending"] = item["total_amount"] - item["paid_total"]
        receipts.append(item)
    return receipts


def add_payment(receipt_id, data, recorded_by_admin_id=None):
    receipt = get_receipt(receipt_id)
    if not receipt:
        raise ValueError("Receipt not found.")
    if receipt.get("status") == STATUS_VOID:
        raise ValueError("Cannot record payments on a void receipt.")
    amount = to_money(data.get("amount"), "Payment amount", allow_zero=False)
    if amount > receipt["pending"]:
        raise ValueError(f"Payment exceeds pending balance of {receipt['pending']}.")
    method = _clean(data.get("method"), 30).lower() or "cash"
    if method not in PAYMENT_METHODS:
        method = "other"
    payment_date = _clean(data.get("payment_date"), 10)
    try:
        payment_date = date.fromisoformat(payment_date).isoformat() if payment_date else date.today().isoformat()
    except ValueError as exc:
        raise ValueError("Payment date must be YYYY-MM-DD.") from exc
    execute(
        """INSERT INTO billing_payments
           (receipt_id, amount, payment_date, method, reference, note, recorded_by_admin_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (
            receipt_id,
            str(amount),
            payment_date,
            method,
            _clean(data.get("reference"), 120) or None,
            _clean(data.get("note"), 500) or None,
            recorded_by_admin_id,
        ),
    )
    return _refresh_status(receipt_id)


def _refresh_status(receipt_id):
    receipt = get_receipt(receipt_id)
    if receipt and receipt.get("status") != STATUS_VOID:
        new_status = status_for(receipt["total_amount"], receipt["paid_total"])
        execute(
            "UPDATE billing_receipts SET status=%s, updated_at=NOW() WHERE id=%s",
            (new_status, receipt_id),
        )
        receipt["status"] = new_status
    return receipt


def void_receipt(receipt_id, reason=""):
    receipt = get_receipt(receipt_id)
    if not receipt:
        raise ValueError("Receipt not found.")
    if receipt.get("status") == STATUS_VOID:
        return receipt
    execute(
        "UPDATE billing_receipts SET status=%s, void_reason=%s, voided_at=NOW(), updated_at=NOW() WHERE id=%s",
        (STATUS_VOID, _clean(reason, 300) or None, receipt_id),
    )
    return get_receipt(receipt_id)


def tables_available():
    try:
        query_one("SELECT COUNT(*) AS n FROM billing_receipts")
        return True
    except Exception:
        return False
