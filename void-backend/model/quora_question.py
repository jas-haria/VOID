from sqlalchemy import Column, Integer, String, inspect, Date, ForeignKey, Boolean
from model.base import Base, _asdictmethod
from datetime import date

class QuoraQuestion(Base):
    __tablename__ = "quora_questions"
    __table_args__ = {"schema": "void_dev"}

    id = Column('id', Integer, primary_key=True, nullable=False, autoincrement=True)
    question_url = Column('question_url', String, nullable=False)
    question_text = Column('question_text', String)
    division = Column('division', Integer, ForeignKey('void_dev.divisions.id'), nullable=False)
    asked_on = Column('asked_on', Date)
    evaluated = Column('evaluated', Boolean, default=False)

    def __repr__(self):
        return '<Question {}>'.format(self.question_url)

    def _asdict(self):
        return _asdictmethod(self)