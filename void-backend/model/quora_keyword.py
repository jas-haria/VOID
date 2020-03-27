from sqlalchemy import Column, Integer, String, ForeignKey
from model.base import Base, _asdictmethod

class QuoraKeyword(Base):
    __tablename__ = "quora_keywords"
    __table_args__ = {"schema": "void_dev"}

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    division = Column('division', Integer, ForeignKey('divisions.id'), nullable=False)
    keyword = Column('keyword', String(50), nullable=False)

    def __repr__(self):
        return '<Division {} & KeyWord {}>'.format(self.division, self.keyword)

    def _asdict(self):
        return _asdictmethod(self)