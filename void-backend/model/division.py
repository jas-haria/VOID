from sqlalchemy import Column, Integer, String
from model.base import Base, _asdictmethod

class Division(Base):
    __tablename__ = "divisions"
    __table_args__ = {"schema": "void_dev"}

    id = Column('id', Integer, primary_key=True, nullable=False, autoincrement=True)
    division = Column('division', String(20), nullable=False, unique=True)

    def __repr__(self):
        return '<Division {}>'.format(self.id)

    def _asdict(self):
        return _asdictmethod(self)