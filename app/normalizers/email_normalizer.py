# app/normalizers/email_normalizer.py
#
# Cleans and validates email addresses.
# Normalization is simple for emails: lowercase + strip whitespace.
# We also validate the format.

from email_validator import validate_email, EmailNotValidError
# email-validator library checks if an email address is syntactically valid
# It checks format (has @, valid domain) but does NOT check if the mailbox actually exists.

from app.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_email(raw_email: str) -> str:
    """
    Normalize and validate an email address.

    Transformations:
        "John@Gmail.COM"     → "john@gmail.com"    (lowercase)
        "  john@gmail.com "  → "john@gmail.com"    (stripped)

    Parameters:
        raw_email (str): Email in any case/format

    Returns:
        str: Lowercase validated email, or "" if invalid
    """
    if not raw_email:
        return ""

    raw_email = raw_email.strip()

    try:
        # validate_email() both validates AND normalizes the email.
        # check_deliverability=False means we don't check if the domain has MX records.
        # We just check the format.
        # It returns a validated object with a .normalized attribute.
        validated = validate_email(raw_email, check_deliverability=False)

        # .normalized gives the properly formatted email (handles edge cases in domains)
        normalized = validated.normalized.lower()
        logger.debug(f"Email normalized: '{raw_email}' → '{normalized}'")
        return normalized

    except EmailNotValidError as e:
        logger.warning(f"Invalid email address: '{raw_email}' | {e}")
        return ""   # Return empty string for invalid emails
