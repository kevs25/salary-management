"""Deterministic synthetic dataset for ACME: pure Python, no database, no wall clock.

generate() returns plain row dicts with explicit primary keys, so the same seed
always produces byte-identical data and the loader can bulk-insert without
round-tripping for generated ids.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.seed import reference_data as ref
from app.utils.currency import to_money, to_usd

Row = dict[str, Any]

# Pay rises applied when walking salary history backwards from today's pay.
MERIT_RANGE = (Decimal("0.03"), Decimal("0.08"))
PROMOTION_RANGE = (Decimal("0.10"), Decimal("0.18"))
MARKET_ADJUSTMENT_RANGE = (Decimal("0.05"), Decimal("0.10"))
PROMOTION_PROBABILITY = 0.12
MARKET_ADJUSTMENT_PROBABILITY = 0.05
REVIEW_MONTH_DAY = (4, 1)  # annual review cycle, effective 1 April

# Years of tenure by level rank: (min, max).
TENURE_YEARS = {1: (0.1, 2), 2: (1, 5), 3: (2, 8), 4: (3, 10), 5: (4, 12)}


@dataclass
class SeedData:
    countries: list[Row] = field(default_factory=list)
    fx_rates: list[Row] = field(default_factory=list)
    departments: list[Row] = field(default_factory=list)
    job_roles: list[Row] = field(default_factory=list)
    levels: list[Row] = field(default_factory=list)
    salary_bands: list[Row] = field(default_factory=list)
    employees: list[Row] = field(default_factory=list)
    salary_records: list[Row] = field(default_factory=list)


@dataclass(frozen=True)
class _Band:
    id: int
    currency_code: str
    min_amount: Decimal
    mid_amount: Decimal
    max_amount: Decimal


def _round_to(amount: Decimal, step: int) -> Decimal:
    return to_money((amount / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step)


def _uniform(rng: random.Random, low: Decimal, high: Decimal) -> Decimal:
    return low + (high - low) * Decimal(str(round(rng.random(), 6)))


def _weighted_pick(rng: random.Random, items: list[Any], weights: list[int]) -> Any:
    return rng.choices(items, weights=weights, k=1)[0]


def generate(
    seed: int = ref.DEFAULT_SEED, employee_count: int = ref.DEFAULT_EMPLOYEE_COUNT
) -> SeedData:
    rng = random.Random(seed)
    data = SeedData()

    _reference_rows(data)
    bands = _bands(data)
    _employees(data, rng, employee_count)
    _salary_histories(data, rng, bands)
    return data


def _reference_rows(data: SeedData) -> None:
    for i, (code, name, currency, _, _) in enumerate(ref.COUNTRIES, start=1):
        data.countries.append({"id": i, "code": code, "name": name, "currency_code": currency})
    for currency, rate in ref.FX_RATES_TO_USD.items():
        data.fx_rates.append({"currency_code": currency, "rate_to_usd": rate, "as_of": ref.AS_OF})
    for rank, (code, name, min_years, max_years, *_) in enumerate(ref.LEVELS, start=1):
        data.levels.append(
            {
                "id": rank,
                "code": code,
                "name": name,
                "rank": rank,
                "min_years": min_years,
                "max_years": max_years,
            }
        )
    role_id = 0
    for dept_id, (dept_name, (_, _, roles)) in enumerate(ref.DEPARTMENTS.items(), start=1):
        data.departments.append({"id": dept_id, "name": dept_name})
        for role_name, _ in roles:
            role_id += 1
            data.job_roles.append({"id": role_id, "department_id": dept_id, "name": role_name})


def _bands(data: SeedData) -> dict[tuple[int, int, int, int], _Band]:
    """One exact band per (department, role, level, country) cell."""
    bands: dict[tuple[int, int, int, int], _Band] = {}
    dept_base = {i: base for i, (base, _, _) in enumerate(ref.DEPARTMENTS.values(), start=1)}
    role_factor = {
        role["id"]: factor
        for role, factor in zip(
            data.job_roles,
            [f for _, _, roles in ref.DEPARTMENTS.values() for _, f in roles],
            strict=True,
        )
    }
    for role in data.job_roles:
        for level_rank, level in enumerate(ref.LEVELS, start=1):
            for country in data.countries:
                country_factor = ref.COUNTRIES[country["id"] - 1][3]
                currency = country["currency_code"]
                mid_usd = (
                    dept_base[role["department_id"]]
                    * role_factor[role["id"]]
                    * level[4]
                    * country_factor
                )
                mid = _round_to(mid_usd / ref.FX_RATES_TO_USD[currency], 1000)
                band = _Band(
                    id=len(bands) + 1,
                    currency_code=currency,
                    min_amount=_round_to(mid * (1 - ref.BAND_SPREAD), 100),
                    mid_amount=mid,
                    max_amount=_round_to(mid * (1 + ref.BAND_SPREAD), 100),
                )
                bands[(role["department_id"], role["id"], level_rank, country["id"])] = band
                data.salary_bands.append(
                    {
                        "id": band.id,
                        "department_id": role["department_id"],
                        "role_id": role["id"],
                        "level_id": level_rank,
                        "country_id": country["id"],
                        "currency_code": currency,
                        "min_amount": band.min_amount,
                        "mid_amount": band.mid_amount,
                        "max_amount": band.max_amount,
                    }
                )
    return bands


def _employees(data: SeedData, rng: random.Random, count: int) -> None:
    dept_ids = [d["id"] for d in data.departments]
    dept_weights = [w for _, w, _ in ref.DEPARTMENTS.values()]
    roles_by_dept: dict[int, list[int]] = {}
    for role in data.job_roles:
        roles_by_dept.setdefault(role["department_id"], []).append(role["id"])
    country_ids = [c["id"] for c in data.countries]
    country_weights = [c[4] for c in ref.COUNTRIES]
    level_ranks = list(range(1, len(ref.LEVELS) + 1))
    level_weights = [lvl[5] for lvl in ref.LEVELS]
    statuses = [s for s, _ in ref.STATUSES]
    status_weights = [w for _, w in ref.STATUSES]

    drafts = []
    for _ in range(count):
        dept_id = _weighted_pick(rng, dept_ids, dept_weights)
        drafts.append(
            {
                "department_id": dept_id,
                "role_id": rng.choice(roles_by_dept[dept_id]),
                "level_id": _weighted_pick(rng, level_ranks, level_weights),
                "country_id": _weighted_pick(rng, country_ids, country_weights),
                "first_name": rng.choice(ref.FIRST_NAMES),
                "last_name": rng.choice(ref.LAST_NAMES),
                "status": _weighted_pick(rng, statuses, status_weights),
            }
        )

    # Seniors first, so every manager_id points at an already-inserted row and the
    # self-referencing FK holds during a single bulk insert.
    drafts.sort(key=lambda d: -d["level_id"])

    email_counts: dict[str, int] = {}
    seniors_by_dept: dict[int, dict[int, list[int]]] = {}
    for emp_id, draft in enumerate(drafts, start=1):
        local = f"{draft['first_name']}.{draft['last_name']}".lower()
        email_counts[local] = email_counts.get(local, 0) + 1
        suffix = "" if email_counts[local] == 1 else str(email_counts[local])

        low, high = TENURE_YEARS[draft["level_id"]]
        tenure_days = int(rng.uniform(low, high) * 365)
        hire_date = ref.AS_OF - timedelta(days=max(tenure_days, 30))

        by_level = seniors_by_dept.setdefault(draft["department_id"], {})
        manager_id = None
        for rank in range(draft["level_id"] + 1, len(ref.LEVELS) + 1):
            if by_level.get(rank):
                manager_id = rng.choice(by_level[rank])
                break
        by_level.setdefault(draft["level_id"], []).append(emp_id)

        data.employees.append(
            {
                "id": emp_id,
                "employee_code": f"E{emp_id:05d}",
                "first_name": draft["first_name"],
                "last_name": draft["last_name"],
                "email": f"{local}{suffix}@acme.example",
                "department_id": draft["department_id"],
                "role_id": draft["role_id"],
                "level_id": draft["level_id"],
                "country_id": draft["country_id"],
                "manager_id": manager_id,
                "hire_date": hire_date,
                "status": draft["status"],
            }
        )


def _current_base(rng: random.Random, band: _Band, placement: str) -> Decimal:
    """Today's base pay: in band around the mid, or deliberately below/above it."""
    if placement == "below":
        ratio = _uniform(rng, Decimal("0.65"), Decimal("0.78"))
        return _round_to(band.mid_amount * ratio, 100)
    if placement == "above":
        ratio = _uniform(rng, Decimal("1.22"), Decimal("1.40"))
        return _round_to(band.mid_amount * ratio, 100)
    ratio = Decimal(str(round(min(max(rng.gauss(1.0, 0.07), 0.82), 1.18), 4)))
    base = _round_to(band.mid_amount * ratio, 100)
    return min(max(base, band.min_amount), band.max_amount)


def _review_dates(hire_date: date) -> list[date]:
    """1 April of each year after hire, once the employee has 6 months' tenure."""
    month, day = REVIEW_MONTH_DAY
    dates = []
    for year in range(hire_date.year, ref.AS_OF.year + 1):
        review = date(year, month, day)
        if review - hire_date >= timedelta(days=182) and review <= ref.AS_OF:
            dates.append(review)
    return dates


def _salary_histories(
    data: SeedData, rng: random.Random, bands: dict[tuple[int, int, int, int], _Band]
) -> None:
    out_of_band = round(len(data.employees) * ref.OUT_OF_BAND_SHARE)
    picked = rng.sample(range(len(data.employees)), out_of_band)
    placement = {i: "below" for i in picked[: out_of_band // 2]}
    placement.update({i: "above" for i in picked[out_of_band // 2 :]})

    bonus_target = {rank: lvl[6] for rank, lvl in enumerate(ref.LEVELS, start=1)}
    record_id = 0
    for index, emp in enumerate(data.employees):
        currency = data.countries[emp["country_id"] - 1]["currency_code"]
        rate = ref.FX_RATES_TO_USD[currency]

        def band_for(level_rank: int, emp: Row = emp) -> _Band:
            return bands[(emp["department_id"], emp["role_id"], level_rank, emp["country_id"])]

        # Walk backwards from today's pay: each review undoes one raise.
        level = emp["level_id"]
        base = _current_base(rng, band_for(level), placement.get(index, "in"))
        periods: list[tuple[date, Decimal, int, str]] = []
        for review in reversed(_review_dates(emp["hire_date"])):
            if level > 1 and rng.random() < PROMOTION_PROBABILITY:
                reason, pct = "promotion", _uniform(rng, *PROMOTION_RANGE)
            elif rng.random() < MARKET_ADJUSTMENT_PROBABILITY:
                reason, pct = "market_adjustment", _uniform(rng, *MARKET_ADJUSTMENT_RANGE)
            else:
                reason, pct = "merit", _uniform(rng, *MERIT_RANGE)
            periods.append((review, base, level, reason))
            base = _round_to(base / (1 + pct), 100)
            if reason == "promotion":
                level -= 1
        periods.append((emp["hire_date"], base, level, "hire"))
        periods.reverse()

        for i, (start, amount, level_rank, reason) in enumerate(periods):
            is_current = i == len(periods) - 1
            bonus = _round_to(
                amount * bonus_target[level_rank] * _uniform(rng, Decimal("0.5"), Decimal("1.3")),
                100,
            )
            record_id += 1
            data.salary_records.append(
                {
                    "id": record_id,
                    "employee_id": emp["id"],
                    "band_id": band_for(level_rank).id,
                    "currency_code": currency,
                    "base_amount": amount,
                    "bonus_amount": bonus,
                    "fx_rate_to_usd": rate,
                    "base_amount_usd": to_usd(amount, rate),
                    "bonus_amount_usd": to_usd(bonus, rate),
                    "effective_from": start,
                    "effective_to": None if is_current else periods[i + 1][0],
                    "is_current": is_current,
                    "reason": reason,
                    "note": None,
                }
            )
