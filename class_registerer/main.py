from enum import Enum
import pendulum
from datetime import date
import argparse
from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, ResultSet, Tag
from typing import List
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel, validator

URL = "https://vondelgym.nl/lesrooster-vondelgym-oost"
COOKIE = "" # TODO: --> env
TZ = "Europe/Amsterdam"

TRANSLATION = {
    "january": "januari",
    "february": "februari",
    "march": "maart",
    "april": "april",
    "may": "mei",
    "june": "juni",
    "july": "juli",
    "august": "augustus",
    "september": "september",
    "october": "oktober",
    "november": "november",
    "december": "december",
}


# parser = argparse.ArgumentParser()
# parser.add_argument("target_date", help="Date of class given as '13 maart'")
#
# args = parser.parse_args()
#
#
# target_date = args.target_date
# target_class = "Crossfit"


def in_future(e: Tag, now: pendulum.DateTime, target_date: str):
    t = pendulum.parse(
        f"{target_date} {e.find(class_='sp_time').string.split('-')[0].strip()}",
        tz=TZ,
        strict=False,
    )
    return t > now


def find_class(soup: ResultSet, target_class: str, target_date: str):
    now = pendulum.now()
    activities = soup.find_all(class_="res_name")
    candidates = [
        [
            y
            for y in (list(x.next_siblings) + list(x.previous_siblings))
            if type(y) == Tag
            and any(map(lambda z: z in ["res_time", "res_reserve"], y.get("class", [])))
        ]
        for x in activities
        if target_class in x.stripped_strings
    ]
    return [x for x in candidates if in_future(x[1], now, target_date)]


def find_day(soup: BeautifulSoup, target_date: str) -> ResultSet:
    return soup.find_all(class_="date_dd", string=target_date)[0].find_parent(
        class_="res_days"
    )


def pretty_print(r: List[Tag]):
    for c in r:
        print(c[1].prettify())
        print(c[0].prettify())


def table_format(target_date: str, result: List[List[Tag]]):
    table_rows = [
        f"""
        <tr>
            <td>{time_tag}</td>
            <td>{avail_tag}</td>
        </tr>
    """
        for avail_tag, time_tag in result
    ]
    return f"""
        <table>
            <thead>
                <tr>
                    <th colspan="2">Results for {target_date} (Scanned at: {pendulum.now()})</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
    """


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


class TargetClass(Enum):
    """Mapping constants to how the strings are given
    in the soup (the casing in the markup is inconsistent,
    thats why we use this enum)"""

    crossfit = "Crossfit"
    zaktraining = "Zaktraining"
    sweat_and_flow = "Sweat and Flow"
    circuittraining_outdoor = "Circuittraining outdoor"


class SearchParams(BaseModel):
    target_date: date
    target_class: str  # TODO: Make this a TargetClass enum

    def target_date_nl(self, obj):
        parsed = self.target_date.strftime("%d %B").lower()
        month = parsed.split()[1]
        return parsed.replace(month, TRANSLATION[month])


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "id": id})


@app.post("/login/", response_class=RedirectResponse)
def login(email: str, password: str):
    # TODO: login to vondelgym and get Cookie, or just get the Cookie if we turn out to have a session
    return RedirectResponse("/")


@app.post("/register/{reg_id}", response_class=RedirectResponse)
def register(reg_id: str):
    session_id = "" # TODO: --> env
    response = requests.post(
        f"https://vondelgym.nl/cs_reservations/reserve/{reg_id}?conf_id=1138&mode=",
        headers={
            "Cookie": f"_mysportpages_session_id_={session_id}; add_to_home_screen=true",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    response.raise_for_status()
    return RedirectResponse("/")


@app.post("/search/")
async def search(params: SearchParams):
    response = requests.get(URL, headers={"Cookie": COOKIE})
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    result = find_class(
        find_day(soup, params.target_date_nl(params.target_date)),
        params.target_class,
        params.target_date,
    )
    return {"rawHTML": table_format(params.target_date, result)}
