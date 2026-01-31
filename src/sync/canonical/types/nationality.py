"""
Nationality Type Module

Provides the Nationality dataclass and parse function for country codes.

This module exports:
    - Nationality: ISO 3166-1 alpha-3 country code
    - parse_nationality(): Parse country to ISO code

Supported formats:
    - ISO codes: "ISR", "USA", "ESP"
    - English names: "Israel", "United States", "Spain"
    - Hebrew names: "ישראל", "ארצות הברית"
    - Demonyms: "Israeli", "American", "Spanish"

Usage:
    from src.sync.canonical.types.nationality import Nationality, parse_nationality

    nat = parse_nationality("Israel")  # Nationality(code="ISR")
    nat = parse_nationality("ישראל")  # Nationality(code="ISR")
    nat = parse_nationality("Israeli")  # Nationality(code="ISR")
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Nationality:
    """
    ISO 3166-1 alpha-3 country code.

    Attributes:
        code: Three-letter ISO country code (e.g., "ISR", "USA")

    Example:
        >>> nationality = Nationality(code="ISR")
        >>> print(nationality.code)
        'ISR'
    """

    code: str

    def __post_init__(self) -> None:
        """Validate code is 3 uppercase letters."""
        if not isinstance(self.code, str) or len(self.code) != 3 or not self.code.isupper():
            raise ValueError(f"Invalid ISO country code: {self.code}")


# Comprehensive country mappings
# Keys are lowercase for case-insensitive matching
_NATIONALITY_MAP: dict[str, str] = {
    # ISO codes (pass through)
    "isr": "ISR",
    "usa": "USA",
    "esp": "ESP",
    "fra": "FRA",
    "deu": "DEU",
    "ger": "DEU",  # Common alias
    "ita": "ITA",
    "gbr": "GBR",
    "srb": "SRB",
    "hrv": "HRV",
    "cro": "HRV",  # Common alias
    "svn": "SVN",
    "slo": "SVN",  # Common alias
    "grc": "GRC",
    "gre": "GRC",  # Common alias
    "tur": "TUR",
    "ltu": "LTU",
    "lva": "LVA",
    "lat": "LVA",  # Common alias
    "rus": "RUS",
    "ukr": "UKR",
    "geo": "GEO",
    "nga": "NGA",
    "sen": "SEN",
    "aus": "AUS",
    "can": "CAN",
    "bra": "BRA",
    "arg": "ARG",
    "mne": "MNE",
    "blr": "BLR",
    "pol": "POL",
    "cze": "CZE",
    "fin": "FIN",
    "swe": "SWE",
    "nor": "NOR",
    "dnk": "DNK",
    "den": "DNK",  # Common alias
    "nld": "NLD",
    "ned": "NLD",  # Common alias
    "bel": "BEL",
    "aut": "AUT",
    "che": "CHE",
    "sui": "CHE",  # Common alias
    "prt": "PRT",
    "por": "PRT",  # Common alias
    "mex": "MEX",
    "jpn": "JPN",
    "chn": "CHN",
    "kor": "KOR",
    "prk": "PRK",
    "phl": "PHL",
    "nzl": "NZL",
    "cmr": "CMR",
    "civ": "CIV",
    "mli": "MLI",
    "cod": "COD",
    "ago": "AGO",
    "mar": "MAR",
    "egy": "EGY",
    "tun": "TUN",
    "zaf": "ZAF",
    "rsa": "ZAF",  # Common alias
    "dom": "DOM",
    "pur": "PRI",
    "pri": "PRI",
    "ven": "VEN",
    "col": "COL",
    "per": "PER",
    "chl": "CHL",
    "uru": "URY",
    "ury": "URY",
    "bih": "BIH",
    "mkd": "MKD",
    "alb": "ALB",
    "rou": "ROU",
    "rom": "ROU",  # Common alias
    "bgr": "BGR",
    "bul": "BGR",  # Common alias
    "hun": "HUN",
    "svk": "SVK",
    "est": "EST",
    "lbn": "LBN",
    "lib": "LBN",  # Common alias
    "irn": "IRN",
    "irq": "IRQ",
    "syr": "SYR",
    "jor": "JOR",
    # English names
    "israel": "ISR",
    "united states": "USA",
    "united states of america": "USA",
    "us": "USA",
    "america": "USA",
    "spain": "ESP",
    "france": "FRA",
    "germany": "DEU",
    "italy": "ITA",
    "united kingdom": "GBR",
    "uk": "GBR",
    "great britain": "GBR",
    "england": "GBR",
    "serbia": "SRB",
    "croatia": "HRV",
    "slovenia": "SVN",
    "greece": "GRC",
    "turkey": "TUR",
    "türkiye": "TUR",
    "lithuania": "LTU",
    "latvia": "LVA",
    "russia": "RUS",
    "russian federation": "RUS",
    "ukraine": "UKR",
    "georgia": "GEO",
    "nigeria": "NGA",
    "senegal": "SEN",
    "australia": "AUS",
    "canada": "CAN",
    "brazil": "BRA",
    "argentina": "ARG",
    "montenegro": "MNE",
    "belarus": "BLR",
    "poland": "POL",
    "czech republic": "CZE",
    "czechia": "CZE",
    "finland": "FIN",
    "sweden": "SWE",
    "norway": "NOR",
    "denmark": "DNK",
    "netherlands": "NLD",
    "holland": "NLD",
    "belgium": "BEL",
    "austria": "AUT",
    "switzerland": "CHE",
    "portugal": "PRT",
    "mexico": "MEX",
    "japan": "JPN",
    "china": "CHN",
    "south korea": "KOR",
    "korea": "KOR",
    "north korea": "PRK",
    "philippines": "PHL",
    "new zealand": "NZL",
    "cameroon": "CMR",
    "ivory coast": "CIV",
    "cote d'ivoire": "CIV",
    "mali": "MLI",
    "congo": "COD",
    "democratic republic of the congo": "COD",
    "angola": "AGO",
    "morocco": "MAR",
    "egypt": "EGY",
    "tunisia": "TUN",
    "south africa": "ZAF",
    "dominican republic": "DOM",
    "puerto rico": "PRI",
    "venezuela": "VEN",
    "colombia": "COL",
    "peru": "PER",
    "chile": "CHL",
    "uruguay": "URY",
    "bosnia": "BIH",
    "bosnia and herzegovina": "BIH",
    "north macedonia": "MKD",
    "macedonia": "MKD",
    "albania": "ALB",
    "romania": "ROU",
    "bulgaria": "BGR",
    "hungary": "HUN",
    "slovakia": "SVK",
    "estonia": "EST",
    "lebanon": "LBN",
    "iran": "IRN",
    "iraq": "IRQ",
    "syria": "SYR",
    "jordan": "JOR",
    # Hebrew names
    "ישראל": "ISR",
    "ארצות הברית": "USA",
    "ארה\"ב": "USA",
    "ארהב": "USA",
    "ספרד": "ESP",
    "צרפת": "FRA",
    "גרמניה": "DEU",
    "איטליה": "ITA",
    "בריטניה": "GBR",
    "אנגליה": "GBR",
    "סרביה": "SRB",
    "קרואטיה": "HRV",
    "סלובניה": "SVN",
    "יוון": "GRC",
    "טורקיה": "TUR",
    "ליטא": "LTU",
    "לטביה": "LVA",
    "רוסיה": "RUS",
    "אוקראינה": "UKR",
    "גאורגיה": "GEO",
    "ניגריה": "NGA",
    "סנגל": "SEN",
    "אוסטרליה": "AUS",
    "קנדה": "CAN",
    "ברזיל": "BRA",
    "ארגנטינה": "ARG",
    "מונטנגרו": "MNE",
    "בלארוס": "BLR",
    "פולין": "POL",
    "צ'כיה": "CZE",
    "פינלנד": "FIN",
    "שוודיה": "SWE",
    "נורבגיה": "NOR",
    "דנמרק": "DNK",
    "הולנד": "NLD",
    "בלגיה": "BEL",
    "אוסטריה": "AUT",
    "שווייץ": "CHE",
    "פורטוגל": "PRT",
    "מקסיקו": "MEX",
    "יפן": "JPN",
    "סין": "CHN",
    "דרום קוריאה": "KOR",
    "קוריאה": "KOR",
    "ניו זילנד": "NZL",
    "קמרון": "CMR",
    "חוף השנהב": "CIV",
    "מאלי": "MLI",
    "קונגו": "COD",
    "אנגולה": "AGO",
    "מרוקו": "MAR",
    "מצרים": "EGY",
    "תוניסיה": "TUN",
    "דרום אפריקה": "ZAF",
    "הרפובליקה הדומיניקנית": "DOM",
    "פורטו ריקו": "PRI",
    "ונצואלה": "VEN",
    "קולומביה": "COL",
    "פרו": "PER",
    "צ'ילה": "CHL",
    "אורוגוואי": "URY",
    "בוסניה": "BIH",
    "מקדוניה": "MKD",
    "אלבניה": "ALB",
    "רומניה": "ROU",
    "בולגריה": "BGR",
    "הונגריה": "HUN",
    "סלובקיה": "SVK",
    "אסטוניה": "EST",
    "לבנון": "LBN",
    "איראן": "IRN",
    "עיראק": "IRQ",
    "סוריה": "SYR",
    "ירדן": "JOR",
    # Demonyms
    "israeli": "ISR",
    "american": "USA",
    "spanish": "ESP",
    "french": "FRA",
    "german": "DEU",
    "italian": "ITA",
    "british": "GBR",
    "english": "GBR",
    "serbian": "SRB",
    "croatian": "HRV",
    "slovenian": "SVN",
    "greek": "GRC",
    "turkish": "TUR",
    "lithuanian": "LTU",
    "latvian": "LVA",
    "russian": "RUS",
    "ukrainian": "UKR",
    "georgian": "GEO",
    "nigerian": "NGA",
    "senegalese": "SEN",
    "australian": "AUS",
    "canadian": "CAN",
    "brazilian": "BRA",
    "argentinian": "ARG",
    "argentine": "ARG",
    "montenegrin": "MNE",
    "belarusian": "BLR",
    "polish": "POL",
    "czech": "CZE",
    "finnish": "FIN",
    "swedish": "SWE",
    "norwegian": "NOR",
    "danish": "DNK",
    "dutch": "NLD",
    "belgian": "BEL",
    "austrian": "AUT",
    "swiss": "CHE",
    "portuguese": "PRT",
    "mexican": "MEX",
    "japanese": "JPN",
    "chinese": "CHN",
    "south korean": "KOR",
    "korean": "KOR",
    "filipino": "PHL",
    "new zealander": "NZL",
    "cameroonian": "CMR",
    "ivorian": "CIV",
    "malian": "MLI",
    "congolese": "COD",
    "angolan": "AGO",
    "moroccan": "MAR",
    "egyptian": "EGY",
    "tunisian": "TUN",
    "south african": "ZAF",
    "dominican": "DOM",
    "puerto rican": "PRI",
    "venezuelan": "VEN",
    "colombian": "COL",
    "peruvian": "PER",
    "chilean": "CHL",
    "uruguayan": "URY",
    "bosnian": "BIH",
    "macedonian": "MKD",
    "albanian": "ALB",
    "romanian": "ROU",
    "bulgarian": "BGR",
    "hungarian": "HUN",
    "slovak": "SVK",
    "estonian": "EST",
    "lebanese": "LBN",
    "iranian": "IRN",
    "iraqi": "IRQ",
    "syrian": "SYR",
    "jordanian": "JOR",
}


def parse_nationality(raw: str | None) -> Nationality | None:
    """
    Parse country to ISO 3166-1 alpha-3 code.

    Case-insensitive parsing with support for:
    - ISO codes: "ISR", "USA", "ESP"
    - English names: "Israel", "United States"
    - Hebrew names: "ישראל", "ארצות הברית"
    - Demonyms: "Israeli", "American"

    Args:
        raw: Raw country/nationality string, or None.

    Returns:
        Nationality dataclass with ISO alpha-3 code, or None if:
        - Input is None or empty
        - Country cannot be identified

    Example:
        >>> parse_nationality("Israel")
        Nationality(code='ISR')
        >>> parse_nationality("ישראל")
        Nationality(code='ISR')
        >>> parse_nationality("Israeli")
        Nationality(code='ISR')
        >>> parse_nationality("ISR")
        Nationality(code='ISR')
        >>> parse_nationality("invalid")
        None
    """
    if raw is None:
        return None

    if not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    key = raw.lower()

    # Check direct mapping
    if key in _NATIONALITY_MAP:
        return Nationality(code=_NATIONALITY_MAP[key])

    # Check if it's already a valid 3-letter ISO code
    if len(raw) == 3 and raw.isalpha():
        code = raw.upper()
        # Verify it's in our known codes (values in the map)
        if code in set(_NATIONALITY_MAP.values()):
            return Nationality(code=code)

    return None
