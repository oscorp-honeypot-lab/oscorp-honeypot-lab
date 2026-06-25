from __future__ import annotations

import os

import psycopg

from risk.rules import ACTIVE_RULESET
from risk.storage import recalculate_scores


def main() -> int:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://oscorp:oscorp123@postgres:5432/oscorp",
    )
    with psycopg.connect(database_url) as connection:
        count = recalculate_scores(connection)
    print(f"rules_version={ACTIVE_RULESET.version}")
    print(f"sessions_scored={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
