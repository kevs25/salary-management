from sqlalchemy.orm import Session

from app.models.base import Base


class SqlAlchemyRepository[ModelT: Base]:
    """Shared plumbing for repositories. Holds persistence only, no business rules.

    Repositories flush, they never commit. Committing is the UnitOfWork's job, so
    one service call spanning several repositories is still one transaction.
    """

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()
        return entity

    def flush(self) -> None:
        """Send pending changes now, so the next statement sees them.

        Needed when statement order matters to a constraint, e.g. closing the old
        current salary record before inserting the new one (unique current index).
        """
        self.session.flush()
