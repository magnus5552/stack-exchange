import datetime
import os
import platform
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.core.init_db import create_admin_user, init_database
from app.core.logging import setup_logger
from app.routers import public, balance, order, admin

logger = setup_logger("app.main")
app = FastAPI(
    title="Stock Exchange API",
    description="API для биржевой торговли",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене необходимо ограничить!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Время запуска приложения для расчета uptime
APP_START_TIME = time.time()

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware для логирования всех HTTP запросов и ответов"""
    req_id = str(id(request))[:8]  # Уникальный ID запроса для отслеживания
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    query = str(request.url.query) if request.url.query else ""
    user_agent = request.headers.get("user-agent", "unknown")
    
    logger.info(f"[REQ:{req_id}] {client_ip} - {method} {path} - {query} - {user_agent}")
    
    start_time = time.time()
    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        status_code = response.status_code
        
        # Для быстрых запросов используем мс, для медленных - секунды
        if process_time < 1:
            time_str = f"{process_time * 1000:.2f}ms"
        else:
            time_str = f"{process_time:.2f}s"
            
        logger.info(f"[RES:{req_id}] {status_code} - {time_str}")
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"[ERR:{req_id}] Необработанное исключение: {str(e)}", exc_info=True)
        raise


# Инициализация базы данных
try:
    init_database()
    logger.info("База данных инициализирована успешно")
except Exception as e:
    logger.error(f"Ошибка инициализации базы данных: {e}", exc_info=True)

api_v1 = FastAPI(
    title="Stock Exchange API",
    description="API версии v1 для биржевой торговли",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

api_v1.include_router(public.router, prefix="/public")
api_v1.include_router(balance.router, prefix="/balance")
api_v1.include_router(order.router, prefix="/order")
api_v1.include_router(admin.router, prefix="/admin")

app.mount("/api/v1", api_v1)

@app.get("/api", include_in_schema=False)
async def api_root_redirect():
    """Перенаправляет с /api на актуальную версию API"""
    return RedirectResponse(url="/api/v1")

def get_system_info():
    """Собирает информацию о системе для логирования без использования psutil"""
    system_info = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor() or "Неизвестно",
        "cpu_cores": os.cpu_count() or 0,
        "hostname": platform.node(),
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_url": os.environ.get("DB_CONN_STRING", "").split("@")[-1] if os.environ.get("DB_CONN_STRING") else "default"  # безопасно скрываем пароль
    }
    return system_info


@app.on_event("startup")
async def startup_event():
    """Событие запуска приложения"""
    logger.info("=" * 50)
    logger.info("Инициализация приложения Stock Exchange API...")
    
    system_info = get_system_info()
    logger.info(f"Системная информация: {system_info}")
    
    try:
        db = next(get_db())
        logger.info("Соединение с базой данных успешно установлено")
        
        # Создаем административного пользователя
        try:
            logger.info("Создание администратора, если необходимо...")
            admin_key = create_admin_user(db)
            logger.info(f"API ключ администратора: {admin_key}")
            
            # Выводим ключ в консоль для администратора при запуске
            print(f"\nAdmin API key: {admin_key}\n")
        except Exception as admin_error:
            logger.error(f"Ошибка создания администратора: {admin_error}", exc_info=True)
        
        logger.info("Приложение успешно запущено")
        logger.info("=" * 50)
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}", exc_info=True)
        logger.error("Запуск приложения завершился с ошибками")
        logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """Событие завершения работы приложения"""
    logger.info("=" * 50)
    logger.info("Завершение работы Stock Exchange API...")
    logger.info("Приложение завершило работу")
    logger.info("=" * 50)


@app.get("/", include_in_schema=False)
async def root():
    """Корневая точка API"""
    logger.debug("Доступ к корневой точке API")
    return {"message": "Добро пожаловать в Stock Exchange API", "version": "0.1.0"}


@app.get("/health", include_in_schema=False)
async def health():
    logger.debug("Доступ к точке проверки здоровья системы")
    
    uptime_seconds = int(time.time() - APP_START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    
    health_data = {
        "status": "ok",
        "timestamp": time.time(),
        "uptime_seconds": uptime_seconds,
        "uptime": uptime_str,
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return health_data


@app.get("/api/v1/docs", include_in_schema=False)
async def get_api_v1_docs():
    """Рендерит Swagger UI для API v1"""
    root_path = "/api/v1"
    openapi_url = f"{root_path}/openapi.json"
    
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title="Stock Exchange API v1 - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/api/v1/redoc", include_in_schema=False)
async def get_api_v1_redoc():
    root_path = "/api/v1"
    openapi_url = f"{root_path}/openapi.json"
    
    return get_redoc_html(
        openapi_url=openapi_url,
        title="Stock Exchange API v1 - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

@app.get("/api/v1/openapi.json", include_in_schema=False)
async def get_api_v1_openapi():
    """Возвращает OpenAPI JSON схему для API v1"""
    return app.openapi()