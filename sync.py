import nextcloud_client
import yaml
import sqlite3
import pandas
import gspread

# load secrets from file
with open("secrets.yaml", "r") as stream:
    try:
        secrets = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# download DB from nextcloud
nc_secrets = secrets["nextcloud"]
nc = nextcloud_client.Client(nc_secrets["url"])
nc.login(nc_secrets["user"], nc_secrets["password"])
nc.get_file(nc_secrets["file"])
nc.logout()

# connect to DB
db_name = nc_secrets["file"].split("/")[-1]
con = sqlite3.connect(db_name)

# load loans from DB
loans = pandas.read_sql(
    "SELECT Kennung, Vertragsdatum, Betrag FROM Vertraege ORDER BY Vertragsdatum;", con
)
loans["Betrag"] = loans["Betrag"] / 100
loans["Vertragsdatum"] = pandas.to_datetime(loans["Vertragsdatum"])
loans = pandas.concat(
    [
        loans,
        pandas.DataFrame(
            data=[
                [
                    "Einlage",
                    pandas.to_datetime("2021-09-01"),
                    25000,
                ]
            ],
            columns=loans.columns,
        ),
    ]
)
loans["Vertragsdatum"] = loans["Vertragsdatum"].dt.strftime("%m/%d/%Y")

# Write Loans to google sheets
gc = gspread.service_account_from_dict(secrets["google"])
sh = gc.open("Cashflow Lizu")
worksheet = sh.get_worksheet(1)
return_value = worksheet.update(
    [loans.columns.values.tolist()] + loans.values.tolist(),
    value_input_option="USER_ENTERED",
)

print(return_value)
