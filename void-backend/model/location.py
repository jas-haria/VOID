from sqlalchemy import Column, String
from model.base import Base, _asdictmethod

class Location(Base):
    __tablename__ = "center_locations"
    __table_args__ = {"schema": "void_dev"}

    location_id = Column('location_id', String(25), primary_key=True, nullable=False)
    center_name = Column('center_name', String(50), nullable=False)

    def __repr__(self):
        return '<Location {}>'.format(self.location_id)

    def _asdict(self):
        return _asdictmethod(self)