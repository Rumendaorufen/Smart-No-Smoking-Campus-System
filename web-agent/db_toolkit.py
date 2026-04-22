from langchain_community.utilities.sql_database import SQLDatabase

from config import Settings


def build_sql_database(settings: Settings) -> SQLDatabase:
    if not settings.db_uri:
        raise ValueError("DB_URI is not configured.")

    return SQLDatabase.from_uri(
        settings.db_uri,
        include_tables=settings.include_tables,
        view_support=True,
        sample_rows_in_table_info=2,
        lazy_table_reflection=True,
    )
