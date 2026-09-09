"""HTTP route modules, each exposing an ``APIRouter`` as ``router``."""
from . import auth, entries, health, settings, setup, stations, vehicles

routers = [
    health.router,
    setup.router,
    auth.router,
    vehicles.router,
    entries.router,
    stations.router,
    settings.router,
]
