import marimo

__generated_with = "0.19.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return


@app.cell
def _():
    import sqlmodel
    import pycountry

    DATABASE_URL = "sqlite:///../worldcup.db"
    engine = sqlmodel.create_engine(DATABASE_URL)
    return engine, pycountry, sqlmodel


@app.cell
def _(engine, pd, sqlmodel):
    with sqlmodel.Session(engine) as session:
        query = "SELECT * FROM teams"
        matches_df = pd.read_sql_query(query, session.bind)

    matches_df
    return


@app.cell
def _():
    import pandas as pd
    return (pd,)


@app.cell
def _(pycountry):
    ## Helper Functions
    def get_country_code(country_name):
        try:
            # Handle special cases
            if country_name == "USA":
                return "US"
            elif country_name == "Ivory Coast":
                return "CI"
            elif country_name == "England":
                return "GB"
            elif country_name == "Scotland":
                return "GB"
            elif country_name == "Cape Verde Islands":
                return "CV"
            elif country_name == "Curaçao":
                return "CW"
            # Fetch ISO code using pycountry
            country = pycountry.countries.search_fuzzy(country_name)
            return country[0].alpha_2
        except LookupError:
            return None

    def get_country_code_alpha3(country_name):
        try:
            # Handle special cases
            if country_name == "USA":
                return "USA"
            elif country_name == "Ivory Coast":
                return "CIV"
            elif country_name == "England":
                return "GBR"
            elif country_name == "Scotland":
                return "GBR"
            elif country_name == "Cape Verde Islands":
                return "CPV"
            elif country_name == "Curaçao":
                return "CUW"
            # Fetch ISO alpha-3 code using pycountry
            country = pycountry.countries.search_fuzzy(country_name)
            return country[0].alpha_3
        except LookupError:
            return None
    return (get_country_code_alpha3,)


@app.cell
def _(get_country_code_alpha3, pd):
    _worlcdup_teams = pd.read_csv('../mockups/world-cup_2026.csv')\
        .assign(match_number=range(1, len(pd.read_csv('../mockups/world-cup_2026.csv')) + 1))\
        .rename(columns={"match_date":"date","home_team":"team1_name","away_team":"team2_name"})

    countries_list = _worlcdup_teams['team1_name'].drop_duplicates().to_list()
    countries_list_2 = _worlcdup_teams['team2_name'].drop_duplicates().to_list()
    merged_countries_list = list(set(countries_list + countries_list_2))

    _countries_df = pd.DataFrame({
        "team1_name": merged_countries_list,
        "team1_code": [get_country_code_alpha3(country) for country in merged_countries_list],
        "team2_name": merged_countries_list,
        "team2_code": [get_country_code_alpha3(country) for country in merged_countries_list]
    })

    _worlcdup_teams['round'] = ""
    _worlcdup_teams['group'] = ""
    _worlcdup_teams['actual_team1_score'] = ""
    _worlcdup_teams['actual_team2_score'] = ""
    _worlcdup_teams['is_finished'] = True
    _worlcdup_teams['datetime'] = pd.to_datetime(_worlcdup_teams['date'] + ' ' + _worlcdup_teams['time'])

    _worlcdup_teams\
        .merge(_countries_df[['team1_name','team1_code']], on='team1_name', how='left')\
        .merge(_countries_df[['team2_name','team2_code']], on='team2_name', how='left')\
        [["match_number", "round", "group", 'date', 'team1_code', 'team1_name', 'team2_code', 'team2_name', 
                 'actual_team1_score', 'actual_team2_score', 'stadium','time','datetime']]\
        .to_csv('../mockups/master_wd_file.csv', index=False)
    return (countries_list,)


@app.cell
def _(countries_list):
    countries_list
    return


@app.cell
def _(pd):
    pd.read_csv("../mockups/group_stage_matches.csv") 
    return


if __name__ == "__main__":
    app.run()
