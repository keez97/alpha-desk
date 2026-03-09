# AlphaDesk Database Migrations

This directory contains Alembic database migration files for the AlphaDesk Factor Backtester.

## Running Migrations

To upgrade your database to the latest schema:

```bash
alembic upgrade head
```

To downgrade to a specific revision:

```bash
alembic downgrade <revision_id>
```

To see the current revision:

```bash
alembic current
```

To see all revisions and their status:

```bash
alembic history
```

## Creating New Migrations

### Automatic Migration (requires live connection to both databases)

If you've modified the SQLModel models, you can generate a migration automatically:

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Manual Migration

To create a manual migration:

```bash
alembic revision -m "Description of changes"
```

Then edit the generated file in `versions/` to define the up and down migrations.

## Migration Files

- `001_initial_schema.py` - Initial schema creation with all Factor Backtester tables

## Database URL

Migrations read the DATABASE_URL from the environment or default to PostgreSQL:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/alphadesk"
alembic upgrade head
```

For SQLite development:

```bash
export DATABASE_URL="sqlite:///./alphadesk.db"
alembic upgrade head
```
