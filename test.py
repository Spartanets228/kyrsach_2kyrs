from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@app.get("/analizer/{path:path}", response_class=HTMLResponse)
async def analyze_path(request: Request, path: str):
    ...
    return templates.TemplateResponse("analizer.html", {
        "request": request,
        "items": items,
        "path": path,
        "parent_path": parent_path,
        "is_drive_list": False,
        "error": error_message
    })
