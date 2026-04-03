import os

# Forcer la DB de test avant tout import de l'application
os.environ["SIGIS_DATABASE_URL"] = "sqlite+aiosqlite:///./sigis_test.db"
_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sigis_test.db"))
if os.path.isfile(_p):
    os.remove(_p)
