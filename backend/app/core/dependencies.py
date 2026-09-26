from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.unit_of_work import SqlAlchemyUnitOfWork, UnitOfWork

SessionDep = Annotated[Session, Depends(get_session)]


def get_unit_of_work(session: SessionDep) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
