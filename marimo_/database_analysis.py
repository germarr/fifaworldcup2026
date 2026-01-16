import marimo

__generated_with = "0.19.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import sqlmodel

    DATABASE_URL = "sqlite:///../worldcup.db"
    engine = sqlmodel.create_engine(DATABASE_URL)
    return (engine,)


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    return


@app.cell
def _():
    import pandas as pd
    data_ = pd.read_csv('../app/core_files/matches.csv', index_col=0)
    data_['scheduled_datetime'] = pd.to_datetime(data_['scheduled_datetime'], format='mixed')

    data_.to_csv("../app/core_files/matches.csv")
    return


@app.cell
def _(engine, mo):
    df_stadiums = mo.sql(f"""
    SELECT *
    FROM fifa_teams
    """, engine=engine)

    df_stadiums
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
