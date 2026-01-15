FIFA_TO_FLAGCDN = {
    "ARG": "ar",  # Argentina
    "AUS": "au",  # Australia
    "AUT": "at",  # Austria
    "BEL": "be",  # Belgium
    "BOL": "bo",  # BOL
    "BRA": "br",  # Brazil
    "CAN": "ca",  # Canada
    "CHE": "ch",  # Switzerland
    "CIV": "ci",  # Ivory Coast
    "CMR": "cm",
    "COL": "co",  # Colombia
    "CPV": "cv",  # Cape Verde Islands
    "CRC": "cr",
    "CRO": "hr",
    "CUW": "cw",  # Curaçao
    "DEN": "dk",  # DEN
    "DEU": "de",  # Germany
    "DZA": "dz",  # Algeria
    "ECU": "ec",  # Ecuador
    "EGY": "eg",  # Egypt
    "ENG": "gb-eng",  # England
    "ESP": "es",  # Spain
    "FRA": "fr",  # France
    "GER": "de",
    "GHA": "gh",  # Ghana
    "HRV": "hr",  # Croatia
    "HTI": "ht",  # Haiti
    "IRN": "ir",  # Iran
    "ITA": "it",  # ITA
    "JOR": "jo",  # Jordan
    "JPN": "jp",  # Japan
    "KOR": "kr",  # South Korea
    "KSA": "sa",
    "MAR": "ma",  # Morocco
    "MEX": "mx",  # Mexico
    "NCL": "nc",  # NCL
    "NED": "nl",
    "NLD": "nl",  # Netherlands
    "NOR": "no",  # Norway
    "NZL": "nz",  # New Zealand
    "PAN": "pa",  # Panama
    "POL": "pl",
    "POR": "pt",
    "PRT": "pt",  # Portugal
    "PRY": "py",  # Paraguay
    "QAT": "qa",  # Qatar
    "SAU": "sa",  # Saudi Arabia
    "SCO": "gb-sct",  # Scotland
    "SEN": "sn",  # Senegal
    "SRB": "rs",
    "SUI": "ch",
    "TUN": "tn",  # Tunisia
    "TUR": "tr",  # TUR
    "UKR": "ua",  # UKR
    "URU": "uy",
    "URY": "uy",  # Uruguay
    "USA": "us",  # USA
    "UZB": "uz",  # Uzbekistan
    "WAL": "gb-wls",
    "ZAF": "za"  # South Africa
}


def flag_url(team_code: str | None, size: int) -> str | None:
    if not team_code:
        return None
    flag_code = FIFA_TO_FLAGCDN.get(team_code)
    if not flag_code:
        return None
    return f"https://flagcdn.com/w{size}/{flag_code}.png"
