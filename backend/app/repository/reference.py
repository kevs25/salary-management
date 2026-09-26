from sqlalchemy.orm import Session

from app.models import Country, Department, JobRole, Level


class ReferenceRepository:
    """Lookups on the reference dimensions, used to validate a payload's foreign keys.

    Primary-key gets, so repeated checks in one request hit the session identity map.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def department_exists(self, department_id: int) -> bool:
        return self.session.get(Department, department_id) is not None

    def level_exists(self, level_id: int) -> bool:
        return self.session.get(Level, level_id) is not None

    def role_department_id(self, role_id: int) -> int | None:
        role = self.session.get(JobRole, role_id)
        return role.department_id if role else None

    def country_currency(self, country_id: int) -> str | None:
        country = self.session.get(Country, country_id)
        return country.currency_code if country else None
