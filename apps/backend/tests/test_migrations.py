"""Migration immutability and schema-coverage tests."""

import ast
import re
from pathlib import Path

from app.db import Base
from app.db import models as registered_models  # noqa: F401

MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20260723_0001_initial_schema.py"
)


def test_initial_migration_is_static_and_valid_python() -> None:
    """The released baseline must not import mutable application metadata."""
    source = MIGRATION.read_text(encoding="utf-8")
    ast.parse(source)
    assert "from app" not in source
    assert "import app" not in source


def test_initial_migration_covers_every_application_table() -> None:
    """Every registered table must be present in the baseline migration."""
    source = MIGRATION.read_text(encoding="utf-8")
    expected_tables = set(Base.metadata.tables)
    created_tables = {
        table
        for table in expected_tables
        if re.search(rf"op\.create_table\(\s*[\"']{table}[\"']", source)
    }
    assert created_tables == expected_tables
