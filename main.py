import os
import platform
import psutil
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from urllib.parse import quote, unquote

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_folder_size(path: str) -> int:
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        for f in files:
            try:
                fp = os.path.join(root, f)
                total += os.path.getsize(fp)
            except (PermissionError, FileNotFoundError):
                continue
    return total

@app.get("/", response_class=HTMLResponse)
@app.get("/analizer", response_class=HTMLResponse)
@app.get("/analizer/{path:path}", response_class=HTMLResponse)
def get_analyzer_page(request: Request, path: str | None = None):
    if path is None or path == "":
        system = platform.system()
        if system == "Windows":
            partitions = psutil.disk_partitions()
            drives = []
            for p in partitions:
                usage = psutil.disk_usage(p.device)
                drives.append({"name": p.device, "type": "drive", "size": usage.used})
        else:
            usage = psutil.disk_usage("/")
            drives = [{"name": "/", "type": "drive", "size": usage.used}]
        return templates.TemplateResponse("analizer.html", {
            "request": request,
            "path": None,
            "items": drives,
            "is_drive_list": True,
            "parent_path": None
        })

    path = unquote(path)
    if not os.path.exists(path):
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    try:
        items = []
        for entry in os.scandir(path):
            if entry.is_dir():
                size = get_folder_size(entry.path)
                items.append({"name": entry.name, "type": "dir", "size": size})
            else:
                size = entry.stat().st_size
                items.append({"name": entry.name, "type": "file", "size": size})

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
