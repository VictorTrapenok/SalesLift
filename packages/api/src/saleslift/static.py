"""Раздача собранной SPA.

Бэкенд отдаёт фронтенд сам, из того же образа и с того же порта. Поэтому
клиенту не нужен отдельный веб-сервер, запросы идут с одного origin и CORS не
нужен нигде.

В разработке этот модуль не участвует: там SPA отдаёт Vite со своим
hot-reload'ом, а `/api` он проксирует на бэкенд (см. vite.config.ts).
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from saleslift.utils.logger import get_logger

log = get_logger(__name__)

#: Каталог собранной SPA внутри образа (см. стейдж runtime в Dockerfile).
#:
#: Переопределяется переменной SPA_DIST_DIR. Это нужно не «на всякий случай»:
#: без неё раздачу статики нельзя проверить нигде, кроме собранного образа, —
#: то есть дымовой тест невозможно прогнать локально перед отправкой в CI.
SPA_DIST_DIR = Path(os.environ.get("SPA_DIST_DIR", "/app/packages/web/dist"))

#: Префиксы, которые обслуживает сам бэкенд и которые SPA перехватывать не должна.
_API_PREFIXES = ("/api/",)


def mount_spa(app: FastAPI, dist_dir: Path = SPA_DIST_DIR) -> None:
    """Подключает раздачу SPA, если она собрана.

    Если каталога нет — молча пропускаем: это нормальный режим разработки
    (`make dev-api`), где фронтенд отдаёт Vite. Ронять API из-за отсутствия
    статики было бы неверно.
    """
    index_file = dist_dir / "index.html"
    if not index_file.is_file():
        log.info("Сборка SPA не найдена — раздача статики отключена", dist_dir=str(dist_dir))
        return

    # Ассеты с хешем в имени: они неизменяемы, поэтому кэшируются надолго.
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, full_path: str) -> FileResponse:
        """Отдаёт index.html на любой не-API путь.

        Роутинг у SPA клиентский: браузер, открывающий /employees напрямую или
        перезагружающий страницу, должен получить index.html, а дальше маршрут
        разберёт react-router. Без этого любой прямой заход давал бы 404.
        """
        # API-пути сюда попадать не должны: их роутеры зарегистрированы раньше и
        # перехватывают запрос. Но если путь начинается с /api/ и дошёл до сюда —
        # значит, такого эндпоинта нет, и отдавать HTML вместо 404 нельзя:
        # клиент получил бы index.html вместо внятной ошибки.
        if request.url.path.startswith(_API_PREFIXES):
            raise HTTPException(status_code=404, detail="Not Found")

        return FileResponse(index_file)

    log.info("Раздача SPA включена", dist_dir=str(dist_dir))
