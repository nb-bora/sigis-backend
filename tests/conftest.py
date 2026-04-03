import os

# Forcer la DB de test avant tout import de l'application
os.environ["SIGIS_DATABASE_URL"] = "sqlite+aiosqlite:///./sigis_test.db"
_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sigis_test.db"))
if os.path.isfile(_p):
    try:
        os.remove(_p)
    except PermissionError:
        # Sur Windows, la DB peut rester verrouillée quelques instants après
        # une session précédente. On la laisse en place ; create_all va la réutiliser.
        pass
