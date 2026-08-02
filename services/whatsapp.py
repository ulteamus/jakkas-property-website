from config import COMPANY_NAME, COMPANY_OWNER, COMPANY_PHONE
from utils.helpers import whatsapp_url


def interest_message(property_name, area, price, customer_name="", mobile=""):
    price_str = f"₹{float(price):,.0f}" if price else "On Request"
    msg = (
        f"🏡 {COMPANY_NAME}\n\n"
        f"I am interested in this property:\n"
        f"Property Name: {property_name}\n"
        f"Location: {area}\n"
        f"Price: {price_str}\n\n"
    )
    if customer_name:
        msg += f"My Name: {customer_name}\n"
    if mobile:
        msg += f"My Mobile: {mobile}\n"
    msg += f"\nPlease share more details.\nContact: {COMPANY_PHONE}"
    return whatsapp_url(msg)


def general_inquiry(name, mobile, message=""):
    msg = (
        f"Hello {COMPANY_OWNER},\n\n"
        f"I would like to inquire about properties listed by {COMPANY_NAME}.\n\n"
        f"Name: {name}\nMobile: {mobile}\n"
    )
    if message:
        msg += f"Message: {message}\n"
    return whatsapp_url(msg)
