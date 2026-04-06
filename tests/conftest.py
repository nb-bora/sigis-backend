import os
import tempfile

# Base SQLite hors du dépôt — ne pas utiliser sigis-backend/sigis.db (réservée au dev local)
_fd, _test_db = tempfile.mkstemp(suffix=".db", prefix="sigis_test_")
os.close(_fd)
os.environ["SIGIS_DATABASE_URL"] = "sqlite+aiosqlite:///" + os.path.abspath(_test_db).replace(
    os.sep, "/"
)
