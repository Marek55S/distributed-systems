import httpx
import asyncio
from fastapi import HTTPException

async def fetch_external_data(country:str) -> tuple:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        info_resp = await client.get(f"https://disease.sh/v3/covid-19/countries/{country}")

        if info_resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Country '{country}' not found.")
        elif info_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Error communicating with disease.sh API.")

        country_info = info_resp.json()
        iso3 = country_info.get("countryInfo", {}).get("iso3")
        population = country_info.get("population",0)

        if not iso3:
            raise HTTPException(status_code=404, detail=f"ISO3 code not found for country '{country}'.")

        hist_url = f"https://disease.sh/v3/covid-19/historical/{country}?lastdays=all"
        wb_url = f"https://api.worldbank.org/v2/country/{iso3}/indicator/SH.MED.BEDS.ZS?format=json&mrnev=1"

        hist_resp, wb_resp = await asyncio.gather(
            client.get(hist_url),
            client.get(wb_url)
        )

        if hist_resp.status_code != 200 or wb_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Error fetching historical or World Bank data.")

        return country_info, hist_resp.json(), wb_resp.json(), population


def calculate_health_metrics(country: str, year:str,month:str,hist_data: dict, wb_data:list, population: int) -> dict:
    short_year = year[-2:]

    timeline = hist_data.get("timeline")

    if not timeline:
        raise HTTPException(status_code=404, detail=f"No historical data found for {country}.")

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
        raise HTTPException(status_code=404, detail=f"No data found for {country} in {month}/{year}.")

    first_day = list(month_cases.keys())[0]
    last_day = list(month_cases.keys())[-1]

    new_cases_this_month = month_cases[last_day] - month_cases[first_day]
    new_deaths_this_month = month_deaths[last_day] - month_deaths[first_day]

    beds_per_1000 = 0

    if len(wb_data) > 1 and wb_data[1]:
        beds_per_1000 = wb_data[1][0].get("value", 0)

    total_beds = (beds_per_1000 / 1000) * population

    cfr = (new_deaths_this_month / new_cases_this_month) * 100 if new_cases_this_month > 0 else 0
    hospital_load = (new_cases_this_month / total_beds) * 100 if total_beds > 0 else 0

    return {
        "country": country.capitalize(),
        "period": f"{month}/{year}",
        "new_cases": new_cases_this_month,
        "new_deaths": new_deaths_this_month,
        "cfr": round(cfr, 2),
        "total_beds": int(total_beds),
        "hospital_load": round(hospital_load, 2)
    }

