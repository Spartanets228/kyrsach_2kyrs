from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import platform
import psutil
from urllib.parse import quote, unquote

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
@app.get("/analizer", response_class=HTMLResponse)
def get_analyzer_page(request: Request, path: str | None = None):
    if path is None:
        # Список дисков
        drives = []
        system = platform.system()
        if system == "Windows":
            partitions = psutil.disk_partitions()
            drives = [p.device for p in partitions]
        else:
            drives = ["/"]
        return templates.TemplateResponse("analizer.html", {
            "request": request,
            "path": None,
            "items": drives,
            "is_drive_list": True
        })

    # Декодируем путь
    path = unquote(path)

    if not os.path.exists(path):
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    try:
        items = []
        for entry in os.scandir(path):
            if entry.is_dir():
                items.append({"name": entry.name, "type": "dir"})
            else:
                size = entry.stat().st_size
                items.append({"name": entry.name, "type": "file", "size": size})
        return templates.TemplateResponse("analizer.html", {
            "request": request,
            "path": path,
            "items": items,
            "is_drive_list": False
        })
    except PermissionError:
        return templates.TemplateResponse("analizer.html", {
            "request": request,
            "path": path,
            "items": [],
            "error": "Нет доступа к этой папке",
            "is_drive_list": False
        })


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)