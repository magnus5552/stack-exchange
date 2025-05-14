__version__ = "1.0.0"

API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

VERSION_INFO = {
    "name": "Stock Exchange API",
    "version": __version__,
    "api_version": API_VERSION,
    "description": "API для биржевой торговли",
}

def get_version_info():
    return VERSION_INFO.copy()
