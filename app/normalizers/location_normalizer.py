# app/normalizers/location_normalizer.py
#
# Normalizes location information.
# Converts country names to ISO 3166-1 alpha-2 codes (2-letter codes).
# Example: "India" → "IN", "United States" → "US"

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────
# COUNTRY NAME → ISO ALPHA-2 CODE MAP
# A partial map of commonly seen country names and their codes.
# This handles variations like "USA", "United States", "US", "America".
# ──────────────────────────────────────────────────────────────────────
COUNTRY_MAP = {
    # India
    "india": "IN",
    "in": "IN",

    # United States
    "united states": "US",
    "usa": "US",
    "us": "US",
    "america": "US",
    "united states of america": "US",

    # United Kingdom
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "england": "GB",

    # Canada
    "canada": "CA",

    # Australia
    "australia": "AU",

    # Germany
    "germany": "DE",
    "deutschland": "DE",

    # Singapore
    "singapore": "SG",

    # UAE
    "uae": "AE",
    "united arab emirates": "AE",
    "dubai": "AE",

    # Others
    "france": "FR",
    "japan": "JP",
    "china": "CN",
    "brazil": "BR",
    "netherlands": "NL",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "switzerland": "CH",
}


def normalize_country(raw_country: str) -> str:
    """
    Convert a country name or code to ISO 3166-1 alpha-2 format.

    Parameters:
        raw_country (str): Country name in any form

    Returns:
        str: 2-letter ISO code (uppercase), or original string if not found

    Examples:
        "India"          → "IN"
        "USA"            → "US"
        "united kingdom" → "GB"
        "Mars"           → "Mars"  (not in map, return as-is)
    """
    if not raw_country:
        return ""

    lookup = raw_country.strip().lower()
    code = COUNTRY_MAP.get(lookup)

    if code:
        logger.debug(f"Country normalized: '{raw_country}' → '{code}'")
        return code

    # If not found, return uppercase version (might already be a valid code)
    return raw_country.strip().upper() if len(raw_country.strip()) == 2 else raw_country.strip()


def normalize_location(city: str = "", region: str = "", country: str = "") -> dict:
    """
    Build a normalized location dictionary.

    Parameters:
        city    (str): City name
        region  (str): State/province/region
        country (str): Country name or code

    Returns:
        dict: {"city": str, "region": str, "country": str}

    Example:
        normalize_location("Chennai", "Tamil Nadu", "India")
        → {"city": "Chennai", "region": "Tamil Nadu", "country": "IN"}
    """
    return {
        "city":    city.strip().title() if city else "",
        "region":  region.strip().title() if region else "",
        "country": normalize_country(country) if country else "",
    }
