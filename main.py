import os
import platform
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor
import psutil
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import (HTTPException as StarletteHTTPException)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static",
)

templates = Jinja2Templates(
    directory="templates"
)


# Кэш
cache: dict[str, list[dict]] = {}

folder_size_cache: dict[str, int] = {}

# Максимальное число рабочих потоков
executor = ThreadPoolExecutor(max_workers=8)


# Размер дисков, папок, файлов
def format_size(size: int) -> str:
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ",]
    value = float(size)
    index = 0
    while ( value >= 1024 and index < len(units) - 1):
        value /= 1024
        index += 1
    if index == 0:
        return f"{int(value)} {units[index]}"
    return f"{value:.2f} {units[index]}"


def get_drive_root(path: str) -> str:

    if platform.system() == "Windows":

        return os.path.splitdrive(path)[0] + "\\"

    return "/"


# Размер папки
def get_folder_size(path: str):
    if path in folder_size_cache:
        return folder_size_cache[path]
    
    total = 0
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += get_folder_size(entry.path)
                except (PermissionError, FileNotFoundError, OSError,):
                    continue
    except (PermissionError, FileNotFoundError, OSError,):
        pass
    folder_size_cache[path] = total
    return total


# Главная страница
@app.get("/", response_class=HTMLResponse)
@app.get("/analizer", response_class=HTMLResponse)
def drive_list(request: Request):
    drives = []
    if platform.system() == "Windows":
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.device)
                drives.append(
                    {
                        "name": partition.device,
                        "type": "drive",
                        "size": usage.used,
                        "size_text":
                            (
                                f"{format_size(usage.used)}"
                                f" / "
                                f"{format_size(usage.total)}"
                            ),
                        "disk_total":
                            usage.total,
                        "disk_used":
                            usage.used,
                        "disk_free":
                            usage.free,
                        "percent":
                            round(usage.used / usage.total * 100, 2),
                    }
                )
            except Exception:
                continue
    else:
        usage = psutil.disk_usage("/")
        drives.append(
            {
                "name": "/",
                "type": "drive",
                "size": usage.used,
                "size_text":
                    (
                        f"{format_size(usage.used)}"
                        f" / "
                        f"{format_size(usage.total)}"
                    ),
                "disk_total":
                    usage.total,
                "disk_used":
                    usage.used,
                "disk_free":
                    usage.free,
                "percent":
                    round(usage.used / usage.total * 100, 2),
            }
        )
    drives.sort(key=lambda x: x["size"], reverse=True)

    return templates.TemplateResponse("analizer.html", {
            "request": request,
            "items": drives,
            "is_drive_list": True,
            "parent_path": None,
        })



@app.get("/analizer/{path:path}", response_class=HTMLResponse)
def open_folder(request: Request, path: str):
    path = unquote(path)
    if not os.path.exists(path):
        return templates.TemplateResponse("404.html",{"request": request,},status_code=404)
    drive_root = get_drive_root(path)
    usage = psutil.disk_usage(drive_root)

    disk_total = usage.total
    disk_used = usage.used

    if path in cache:
        items = cache[path]
    else:
        items = []
        futures = []
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(
                            follow_symlinks=False
                        ):
                            size = entry.stat(follow_symlinks=False).st_size
                            percent = 0
                            if disk_used > 0:
                                percent = (size / disk_used  * 100)
                            items.append(
                                {
                                    "name": entry.name,
                                    "type": "file",
                                    "size": size,
                                    "size_text":format_size(size),
                                    "percent":round(percent, 2)
                                })

                        elif entry.is_dir(follow_symlinks=False):
                            item = {
                                "name": entry.name,
                                "type": "dir",
                                "path": entry.path,
                            }
                            items.append(item)
                            futures.append((item,  executor.submit(get_folder_size, entry.path)))
                    except (PermissionError, FileNotFoundError, OSError,):
                        continue
        except PermissionError:
            return templates.TemplateResponse(
                "analizer.html",
                {
                    "request": request,
                    "path": path,
                    "items": [],
                    "error": "У вас нет доступа к данному элементу",
                    "is_drive_list": False,
                    "parent_path":os.path.dirname(path)
                } )
           
     
        for item, future in futures:
            try:
                size = future.result()
            except Exception:
                size = 0
            item["size"] = size
            item["size_text"] = format_size(size)

            if disk_used > 0:
                item["percent"] = round(size / disk_used * 100, 2)
            else:
                item["percent"] = 0
            if "path" in item:
                del item["path"]

        items.sort(key=lambda x: x["size"], reverse=True)

        cache[path] = items

    parent_path = None
    parent = os.path.dirname(path)
    if parent != path:
        parent_path = parent

    total_size = sum(item["size"] for item in items )
    if items:
        largest_item = items[0]["name"]
    else:
        largest_item = "-"
    return templates.TemplateResponse("analizer.html",{
            "request": request,
            "path": path,
            "items": items,
            "is_drive_list": False,
            "parent_path": parent_path,
            "total_size": format_size(total_size),
            "largest_item": largest_item,
            "disk_total": disk_total,
            "disk_total_text": format_size(disk_total),
            "disk_used": disk_used,
            "disk_used_text": format_size(disk_used)})


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException,):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request,},иstatus_code=404)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)