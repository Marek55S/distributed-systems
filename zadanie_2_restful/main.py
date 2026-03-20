from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from services import fetch_external_data, calculate_health_metrics

app = FastAPI(title="COVID-19 Health Metrics API")
templates = Jinja2Templates(directory="templates")

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request , exc: HTTPException):
    return templates.TemplateResponse(
        "result.html",
        {"request": request, "error_message": exc.detail, "data":{}},
        status_code=exc.status_code
    )

def verify_token(api_token: str = Form(...)):
    if api_token != "password123":
        raise HTTPException(status_code=401, detail="Access Denied. Invalid API token")
    return api_token

@app.get("/", response_class=HTMLResponse)
async def start(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_data(
        request:Request,
        country: str = Form(...),
        year: str = Form(...),
        month: str = Form(...),
        api_token: str = Depends(verify_token)
):
    try:
        country_info, hist_data, wb_data, population = await fetch_external_data(country)
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500,detail=f"Internal or Network Error: {str(e)}")
        raise e

    results = calculate_health_metrics(country, year, month, hist_data, wb_data, population)

    return templates.TemplateResponse("result.html",{"request": request, "data": results})

# clean RESTful endpoint (if standard analyze_data with HTML response isnt right in this task)
@app.post("/api/analyze")
async def analaze_data_json(
        country: str = Form(...),
        year: str = Form(...),
        month: str = Form(...),
        api_token: str = Depends(verify_token)
):
    try:
        country_info, hist_data, wb_data, population = await fetch_external_data(country)
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500,detail=f"Internal or Network Error: {str(e)}")
        raise e

    results = calculate_health_metrics(country, year, month, hist_data, wb_data, population)

    return {
        "status": "success",
        "message": "Data successfully analyzed",
        "data": results
    }
