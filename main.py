#python -m uvicorn main:app --reload
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import platform
import psutil
from urllib.parse import quote, unquote
import stat 

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
@app.get("/analizer", response_class=HTMLResponse)
@app.get("/analizer/{path:path}", response_class=HTMLResponse)
def get_analyzer_page(request: Request, path: str | None = None):
    # Если путь не указан — показываем список дисков
    if path is None or path == "":
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
            "is_drive_list": True,
            "parent_path": None
        })

    # Декодируем путь
    path = unquote(path)

    # Проверяем существование пути
    if not os.path.exists(path):
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    try:
        items = []
        for entry in os.scandir(path):
            if entry.is_dir():
                items.append({"name": entry.name, "type": "dir"})
            else:          
                size = entry.stat().st_size / 1024  # перевод байт в килобайты
                size = round(size, 2)  # округляем до двух знаков
                items.append({"name": entry.name, "type": "file", "size": size})


        # Родительская папка
        parent_path = None
        if path and os.path.dirname(path) != path:
            parent_path = os.path.dirname(path)

        return templates.TemplateResponse("analizer.html", {
            "request": request,
            "path": path,
            "items": items,
            "is_drive_list": False,
            "parent_path": parent_path
        })

    except PermissionError:
        return templates.TemplateResponse("analizer.html", {
            "request": request,
            "path": path,
            "items": [],
            "error": "Нет доступа к этой папке",
            "is_drive_list": False,
            "parent_path": os.path.dirname(path) if path else None
        })


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
