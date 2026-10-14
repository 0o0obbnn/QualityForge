"""Create or migrate the configured local SQLite database."""

from qf.config import settings
from qf.db.sqlite_store import SCHEMA_VERSION, SQLiteWorkflowStore


def main() -> None:
    store = SQLiteWorkflowStore(settings.sqlite_path)
    print(f"SQLite ready: {store.path} (schema v{SCHEMA_VERSION})")


if __name__ == "__main__":
    main()
