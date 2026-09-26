"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(14, 2)
FX = sa.Numeric(18, 8)
CREATED_AT = sa.text("CURRENT_TIMESTAMP")
UPDATED_AT = sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("code", sa.CHAR(2), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_countries"),
        sa.UniqueConstraint("code", name="uq_countries_code"),
    )
    op.create_table(
        "departments",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint("name", name="uq_departments_name"),
    )
    op.create_table(
        "levels",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("code", sa.String(8), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("min_years", sa.SmallInteger(), nullable=False),
        sa.Column("max_years", sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_levels"),
        sa.UniqueConstraint("code", name="uq_levels_code"),
        sa.UniqueConstraint("rank", name="uq_levels_rank"),
        sa.CheckConstraint(
            "max_years IS NULL OR max_years > min_years", name=op.f("ck_levels_years_range")
        ),
    )
    op.create_table(
        "fx_rates",
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("rate_to_usd", FX, nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("currency_code", name="pk_fx_rates"),
    )
    op.create_table(
        "job_roles",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("department_id", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_job_roles"),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name="fk_job_roles_department_id_departments"
        ),
        sa.UniqueConstraint("department_id", "name", name="uq_job_roles_department_id_name"),
    )

    op.create_table(
        "salary_bands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department_id", sa.SmallInteger(), nullable=False),
        sa.Column("role_id", sa.SmallInteger(), nullable=True),
        sa.Column("level_id", sa.SmallInteger(), nullable=False),
        sa.Column("country_id", sa.SmallInteger(), nullable=True),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("min_amount", MONEY, nullable=False),
        sa.Column("mid_amount", MONEY, nullable=False),
        sa.Column("max_amount", MONEY, nullable=False),
        # NULL -> 0 so the unique scope key also covers the fallback (NULL) bands.
        sa.Column(
            "role_key",
            sa.SmallInteger(),
            sa.Computed("COALESCE(role_id, 0)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "country_key",
            sa.SmallInteger(),
            sa.Computed("COALESCE(country_id, 0)", persisted=True),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=CREATED_AT, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UPDATED_AT, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_salary_bands"),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name="fk_salary_bands_department_id_departments"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["job_roles.id"], name="fk_salary_bands_role_id_job_roles"
        ),
        sa.ForeignKeyConstraint(
            ["level_id"], ["levels.id"], name="fk_salary_bands_level_id_levels"
        ),
        sa.ForeignKeyConstraint(
            ["country_id"], ["countries.id"], name="fk_salary_bands_country_id_countries"
        ),
        sa.CheckConstraint(
            "min_amount >= 0 AND min_amount <= mid_amount AND mid_amount <= max_amount",
            name=op.f("ck_salary_bands_min_mid_max_ordered"),
        ),
    )
    op.create_index(
        "uq_salary_bands_scope",
        "salary_bands",
        ["department_id", "level_id", "role_key", "country_key"],
        unique=True,
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_code", sa.String(16), nullable=False),
        sa.Column("first_name", sa.String(64), nullable=False),
        sa.Column("last_name", sa.String(64), nullable=False),
        sa.Column("email", sa.String(128), nullable=False),
        sa.Column("department_id", sa.SmallInteger(), nullable=False),
        sa.Column("role_id", sa.SmallInteger(), nullable=False),
        sa.Column("level_id", sa.SmallInteger(), nullable=False),
        sa.Column("country_id", sa.SmallInteger(), nullable=False),
        sa.Column("manager_id", sa.Integer(), nullable=True),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "on_leave", "terminated", name="employeestatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=CREATED_AT, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UPDATED_AT, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_employees"),
        sa.UniqueConstraint("employee_code", name="uq_employees_employee_code"),
        sa.UniqueConstraint("email", name="uq_employees_email"),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name="fk_employees_department_id_departments"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["job_roles.id"], name="fk_employees_role_id_job_roles"
        ),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], name="fk_employees_level_id_levels"),
        sa.ForeignKeyConstraint(
            ["country_id"], ["countries.id"], name="fk_employees_country_id_countries"
        ),
        sa.ForeignKeyConstraint(
            ["manager_id"], ["employees.id"], name="fk_employees_manager_id_employees"
        ),
    )
    op.create_index(
        "ix_employees_department_id_country_id_level_id",
        "employees",
        ["department_id", "country_id", "level_id"],
    )

    op.create_table(
        "salary_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("band_id", sa.Integer(), nullable=True),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("base_amount", MONEY, nullable=False),
        sa.Column("bonus_amount", MONEY, nullable=False),
        sa.Column("fx_rate_to_usd", FX, nullable=False),
        sa.Column("base_amount_usd", MONEY, nullable=False),
        sa.Column("bonus_amount_usd", MONEY, nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        # employee_id on the current row, NULL otherwise; unique => one current row each.
        sa.Column(
            "current_employee_id",
            sa.Integer(),
            sa.Computed("IF(is_current, employee_id, NULL)", persisted=True),
            nullable=True,
        ),
        sa.Column(
            "reason",
            sa.Enum(
                "hire",
                "promotion",
                "merit",
                "market_adjustment",
                "correction",
                name="changereason",
            ),
            nullable=False,
        ),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=CREATED_AT, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_salary_records"),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name="fk_salary_records_employee_id_employees"
        ),
        sa.ForeignKeyConstraint(
            ["band_id"], ["salary_bands.id"], name="fk_salary_records_band_id_salary_bands"
        ),
        sa.CheckConstraint(
            "base_amount >= 0 AND bonus_amount >= 0",
            name=op.f("ck_salary_records_amounts_non_negative"),
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name=op.f("ck_salary_records_period_ordered"),
        ),
        sa.CheckConstraint(
            "(is_current AND effective_to IS NULL)"
            " OR (NOT is_current AND effective_to IS NOT NULL)",
            name=op.f("ck_salary_records_current_is_open"),
        ),
    )
    op.create_index(
        "uq_salary_records_employee_id_effective_from",
        "salary_records",
        ["employee_id", sa.text("effective_from DESC")],
        unique=True,
    )
    op.create_index("ix_salary_records_is_current", "salary_records", ["is_current"])
    op.create_index(
        "uq_salary_records_current_employee_id",
        "salary_records",
        ["current_employee_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("salary_records")
    op.drop_table("employees")
    op.drop_table("salary_bands")
    op.drop_table("job_roles")
    op.drop_table("fx_rates")
    op.drop_table("levels")
    op.drop_table("departments")
    op.drop_table("countries")
