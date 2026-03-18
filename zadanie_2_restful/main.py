from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Health API Analyzer")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def start(request:Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_data(
        request: Request,
        country: str = Form(...),
        api_token: str = Form(...)
        ):
    if api_token != "password123":
        return templates.TemplateResponse("result.html",{
            "request": request,
            "result": "Access Denied. Invalid API token."
        })

    results = {
        "country": country,
        "message": "placeholder"
    }

    return templates.TemplateResponse("result.html", {"request": request, "data": results})