# app/normalizers/phone_normalizer.py
#
# Converts any phone number format to the international E.164 standard.
#
# E.164 format: +[country_code][number]
# Example: +919876543210
#
# Why E.164?
# - It's unambiguous — no confusion about country codes
# - It's the format used by SMS providers and phone APIs
# - It makes deduplication easier (two different formats of the same number become identical)

import phonenumbers
# phonenumbers is a Python port of Google's libphonenumber library.
# It understands phone number formats from every country.

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default country code to assume when no country code is in the number.
# "IN" = India. In a real product this would be configurable per deployment.
DEFAULT_REGION = "IN"


def normalize_phone(raw_phone: str) -> str:
    """
    Parse and normalize a phone number to E.164 format.

    Handles many input formats:
        "9876543210"       → "+919876543210"   (Indian number, no country code)
        "+91 9876 543 210" → "+919876543210"   (spaces removed)
        "(987) 654-3210"   → "+19876543210"    (US format)
        "09876543210"      → "+919876543210"   (leading 0 removed)

    Parameters:
        raw_phone (str): Phone number in any format

    Returns:
        str: Phone number in E.164 format, or the original string if parsing fails
    """
    if not raw_phone:
        return ""

    # Strip whitespace from the input
    raw_phone = raw_phone.strip()

    try:
        # phonenumbers.parse() tries to understand the phone number.
        # Second argument is the default region — used when there's no country code.
        # If the number already has "+91", the region hint is ignored.
        parsed = phonenumbers.parse(raw_phone, DEFAULT_REGION)

        # is_valid_number() checks if the parsed number is actually valid
        # (correct length, valid area code etc.)
        if phonenumbers.is_valid_number(parsed):

            # format_number() converts to the requested format.
            # PhoneNumberFormat.E164 gives "+919876543210"
            normalized = phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
            logger.debug(f"Phone normalized: '{raw_phone}' → '{normalized}'")
            return normalized
        else:
            logger.warning(f"Phone number is not valid: '{raw_phone}'")
            return raw_phone   # Return original if it's not a valid number

    except phonenumbers.NumberParseException as e:
        # This error means the string couldn't be parsed as a phone number at all
        logger.warning(f"Could not parse phone number: '{raw_phone}' | {e}")
        return raw_phone   # Return original rather than losing the data
