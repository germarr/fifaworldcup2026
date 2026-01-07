FIFA_TO_FLAGCDN = {
    "ARG": "ar",
    "AUS": "au",
    "BEL": "be",
    "BRA": "br",
    "CAN": "ca",
    "CMR": "cm",
    "CRC": "cr",
    "CRO": "hr",
    "DEN": "dk",
    "ECU": "ec",
    "ENG": "gb-eng",
    "ESP": "es",
    "FRA": "fr",
    "GER": "de",
    "GHA": "gh",
    "IRN": "ir",
    "JPN": "jp",
    "KOR": "kr",
    "KSA": "sa",
    "MAR": "ma",
    "MEX": "mx",
    "NED": "nl",
    "POL": "pl",
    "POR": "pt",
    "QAT": "qa",
    "SEN": "sn",
    "SRB": "rs",
    "SUI": "ch",
    "TUN": "tn",
    "URU": "uy",
    "USA": "us",
    "WAL": "gb-wls",
}


def flag_url(team_code: str | None, size: int) -> str | None:
    if not team_code:
        return None
    flag_code = FIFA_TO_FLAGCDN.get(team_code)
    if not flag_code:
        return None
    return f"https://flagcdn.com/w{size}/{flag_code}.png"
