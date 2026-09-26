"""Reference data and calibration for the synthetic ACME dataset.

All figures are illustrative, not market data. They only need to be internally
coherent, so that the analytics screens tell a plausible story.

Band calibration: the band mid for (department, role, level, country) is
    DEPARTMENT_BASE_USD[dept] * ROLE_FACTOR[role] * LEVEL_FACTOR[level]
        * COUNTRY_FACTOR[country]
converted to local currency with the FX snapshot. min/max are mid -/+ BAND_SPREAD.
"""

from datetime import date
from decimal import Decimal

AS_OF = date(2026, 9, 1)  # "today" for the dataset; never the wall clock
DEFAULT_SEED = 20260926
DEFAULT_EMPLOYEE_COUNT = 10_000

# code, name, currency, cost-of-labour factor vs US, headcount weight
COUNTRIES: list[tuple[str, str, str, Decimal, int]] = [
    ("US", "United States", "USD", Decimal("1.00"), 25),
    ("IN", "India", "INR", Decimal("0.28"), 30),
    ("GB", "United Kingdom", "GBP", Decimal("0.70"), 12),
    ("DE", "Germany", "EUR", Decimal("0.75"), 10),
    ("SG", "Singapore", "SGD", Decimal("0.80"), 8),
    ("BR", "Brazil", "BRL", Decimal("0.35"), 15),
]

# 1 unit of currency = rate USD. Committed snapshot, deliberately not live.
FX_RATES_TO_USD: dict[str, Decimal] = {
    "USD": Decimal("1.00000000"),
    "INR": Decimal("0.01190000"),
    "GBP": Decimal("1.27000000"),
    "EUR": Decimal("1.08000000"),
    "SGD": Decimal("0.74000000"),
    "BRL": Decimal("0.18000000"),
}

# code, name, min_years, max_years, pay factor vs L3, headcount weight,
# target bonus as a share of base
LEVELS: list[tuple[str, str, int, int | None, Decimal, int, Decimal]] = [
    ("L1", "Associate", 0, 2, Decimal("0.60"), 25, Decimal("0.050")),
    ("L2", "Intermediate", 2, 5, Decimal("0.80"), 30, Decimal("0.075")),
    ("L3", "Senior", 5, 8, Decimal("1.00"), 24, Decimal("0.100")),
    ("L4", "Lead", 8, 12, Decimal("1.30"), 14, Decimal("0.150")),
    ("L5", "Principal", 12, None, Decimal("1.70"), 7, Decimal("0.200")),
]

# department -> (US L3 base mid in USD, headcount weight, [(role, pay factor)])
DEPARTMENTS: dict[str, tuple[Decimal, int, list[tuple[str, Decimal]]]] = {
    "Engineering": (
        Decimal("150000"),
        35,
        [
            ("Backend Engineer", Decimal("1.00")),
            ("Frontend Engineer", Decimal("0.97")),
            ("Data Engineer", Decimal("1.02")),
            ("Machine Learning Engineer", Decimal("1.10")),
            ("Site Reliability Engineer", Decimal("1.05")),
            ("QA Engineer", Decimal("0.85")),
        ],
    ),
    "Product": (
        Decimal("145000"),
        8,
        [
            ("Product Manager", Decimal("1.00")),
            ("Technical Product Manager", Decimal("1.05")),
            ("Product Analyst", Decimal("0.85")),
        ],
    ),
    "Design": (
        Decimal("125000"),
        6,
        [
            ("Product Designer", Decimal("1.00")),
            ("UX Researcher", Decimal("0.95")),
            ("Visual Designer", Decimal("0.88")),
        ],
    ),
    "Sales": (
        Decimal("110000"),
        18,
        [
            ("Account Executive", Decimal("1.00")),
            ("Sales Development Representative", Decimal("0.70")),
            ("Solutions Engineer", Decimal("1.15")),
            ("Account Manager", Decimal("0.92")),
        ],
    ),
    "Marketing": (
        Decimal("105000"),
        8,
        [
            ("Growth Marketer", Decimal("1.00")),
            ("Content Strategist", Decimal("0.88")),
            ("Product Marketing Manager", Decimal("1.08")),
            ("Marketing Analyst", Decimal("0.90")),
        ],
    ),
    "Finance": (
        Decimal("115000"),
        6,
        [
            ("Financial Analyst", Decimal("1.00")),
            ("Accountant", Decimal("0.90")),
            ("FP&A Manager", Decimal("1.12")),
        ],
    ),
    "People": (
        Decimal("95000"),
        5,
        [
            ("HR Business Partner", Decimal("1.00")),
            ("Recruiter", Decimal("0.88")),
            ("People Operations Specialist", Decimal("0.85")),
        ],
    ),
    "Operations": (
        Decimal("90000"),
        14,
        [
            ("Operations Analyst", Decimal("1.00")),
            ("Program Manager", Decimal("1.12")),
            ("Customer Support Specialist", Decimal("0.72")),
            ("IT Support Engineer", Decimal("0.85")),
        ],
    ),
}

BAND_SPREAD = Decimal("0.20")  # min = mid * 0.8, max = mid * 1.2

# Share of employees deliberately paid outside their band, so the compliance
# screen has real content. Split evenly between below-min and above-max.
OUT_OF_BAND_SHARE = Decimal("0.04")

# status, weight (per mille)
STATUSES: list[tuple[str, int]] = [("active", 960), ("on_leave", 25), ("terminated", 15)]

FIRST_NAMES = [
    "Aarav", "Aditi", "Akira", "Alejandro", "Amara", "Ana", "Arjun", "Ben", "Camila",
    "Chen", "Chloe", "Daniel", "Divya", "Elena", "Emma", "Farah", "Felix", "Gabriel",
    "Hannah", "Hiro", "Ines", "Isaac", "Jonas", "Julia", "Kavya", "Leon", "Lucas",
    "Maya", "Mei", "Mateo", "Nadia", "Noah", "Olivia", "Omar", "Priya", "Rafael",
    "Rahul", "Sara", "Sofia", "Tariq", "Thomas", "Wei", "Yusuf", "Zara",
]  # fmt: skip

LAST_NAMES = [
    "Almeida", "Bauer", "Brown", "Chandra", "Costa", "Das", "Fischer", "Garcia", "Gupta",
    "Hoffmann", "Iyer", "Johnson", "Khan", "Kumar", "Lee", "Lim", "Martins", "Mehta",
    "Menon", "Meyer", "Miller", "Nair", "Ng", "Oliveira", "Patel", "Pereira", "Rao",
    "Reddy", "Santos", "Schmidt", "Sharma", "Silva", "Singh", "Smith", "Souza", "Tan",
    "Taylor", "Wagner", "Walker", "Weber", "Williams", "Wilson", "Wong", "Zimmermann",
]  # fmt: skip
