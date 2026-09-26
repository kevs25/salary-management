from typing import Protocol

from sqlalchemy.orm import Session


class UnitOfWork(Protocol):
    """Transaction boundary, as seen by services.

    Services take this instead of a Session so they stay free of SQLAlchemy and can
    be unit-tested with a fake that just records whether it was committed.
    """

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
