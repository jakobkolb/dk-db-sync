import json

import gspread
import pandas
import ramda as R
import requests
import yaml
from dateutil.parser import isoparse

# load secrets from file
with open("secrets.yaml", "r") as stream:
    try:
        secrets = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

trello_credentials = secrets["trello"]
res = requests.get(
    url=f"https://api.trello.com/1/boards/37FOxw04/cards?"
        f"token={trello_credentials['bearer-token']}&"
        f"key={trello_credentials['api-key']}"
)

cards = json.loads(res.text)


@R.curry
def has_label(label, card):
    return R.pipe(R.prop("labels"), R.map(R.prop("name")), R.contains(label))(card)


def select_sum_from_description(description: str):
    return R.pipe(
        R.split("\n"), R.find(lambda s: "Summe" in s), R.split(": "), lambda x: x[-1], lambda x: f"-{x}"
    )(description)


expense_cards = R.pipe(
    R.filter(has_label("Ausgaben")),
    R.map(
        R.apply_spec(
            {
                "title": R.prop("name"),
                "date": R.pipe(R.path(["badges", "due"]), R.tap(print), isoparse, R.invoker(0, 'date'), lambda d: d.strftime("%m/%d/%Y")),
                "amount": R.pipe(R.prop("desc"), select_sum_from_description),

            }
        )
    ),
    pandas.DataFrame,
)(cards)

print(expense_cards)

# Write Loans to google sheets
gc = gspread.service_account_from_dict(secrets["google"])
sh = gc.open("Cashflow Lizu")
worksheet = sh.get_worksheet(3)
return_value = worksheet.update(
    [expense_cards.columns.values.tolist()] + expense_cards.values.tolist(),
    value_input_option="USER_ENTERED",
)
