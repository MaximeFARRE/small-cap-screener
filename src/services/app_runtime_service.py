from src.repositories.database import init_db


def initialize_application_storage() -> None:
    init_db()
