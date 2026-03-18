import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import asyncio

app = FastAPI(title="Health API Analyzer")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def start(request:Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_data(
        request: Request,
        country: str = Form(...),
        year: str = Form(...),
        month: str = Form(...),
        api_token: str = Form(...)
        ):
    if api_token != "password123":
        return templates.TemplateResponse("result.html",{
            "request": request,
            "result": "Access Denied. Invalid API token.",
            "data": {}
        })

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            info_resp = await client.get(f"https://disease.sh/v3/covid-19/countries/{country}")
            if info_resp.status_code != 200:
                return templates.TemplateResponse("result.html", {
                    "request": request,
                    "result": f"Error fetching data for {country}. Please check the country name.",
                    "data": {}
                })
            info_resp.raise_for_status()
            country_info = info_resp.json()

            iso3 = country_info.get("countryInfo", {}).get("iso3")
            population = country_info.get("population",0)

            hist_url = f"https://disease.sh/v3/covid-19/historical/{country}?lastdays=all"
            wb_url = f"https://api.worldbank.org/v2/country/{iso3}/indicator/SH.MED.BEDS.ZS?format=json&mrnev=1"

            hist_resp, wb_resp = await asyncio.gather(
                client.get(hist_url),
                client.get(wb_url)
            )

            hist_resp.raise_for_status()
            wb_resp.raise_for_status()

            hist_data = hist_resp.json()
            wb_data = wb_resp.json()

    except httpx.HTTPError as e:
        return templates.TemplateResponse("result.html",{
            "request": request, "error message": f"API Error: {e}", "data": {}
        })

    short_year = year[-2:]

    timeline = hist_data.get("timeline", None)
    if not timeline:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "result": f"No historical data found for {country}.",
            "data": {}
        })
    cases_timeline = timeline.get("cases",{})
    deaths_timeline = timeline.get("deaths",{})

    month_cases={}
    month_deaths={}

    for date_str, cases_count in cases_timeline.items():
        parts = date_str.split("/")
        if parts[0] == month and parts[2] == short_year:
            month_cases[date_str] = cases_count
            month_deaths[date_str] = deaths_timeline[date_str]

    if not month_cases:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "result": f"No data found for {country} in {month}/{year}.",
            "data": {}
        })

    first_day = list(month_cases.keys())[0]
    last_day = list(month_cases.keys())[-1]

    new_cases_this_month = month_cases[last_day] - month_cases[first_day]
    new_deaths_this_month = month_deaths[last_day] - month_deaths[first_day]

    beds_per_1000 = 0
    if len(wb_data)>1 and wb_data[1]:
        beds_per_1000 = wb_data[1][0].get("value", 0)

    total_beds = (population / 1000) * beds_per_1000

    cfr = 0
    if new_cases_this_month > 0:
        cfr = (new_deaths_this_month / new_cases_this_month) * 100

    hospital_load = 0
    if total_beds >0:
        hospital_load = (new_cases_this_month / total_beds) * 100

    results = {
        "country": country.capitalize(),
        "period": f"{month}/{year}",
        "new_cases": new_cases_this_month,
        "new_deaths": new_deaths_this_month,
        "cfr": round(cfr, 2),
        "total_beds": int(total_beds),
        "hospital_load": round(hospital_load, 2)
    }

    return templates.TemplateResponse("result.html", {"request": request, "data": results})