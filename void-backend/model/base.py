from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import inspect
from datetime import date

Base = declarative_base()

def _asdictmethod(object):
    return {c.key: (str(getattr(object, c.key)) if isinstance(getattr(object, c.key), date) else getattr(object, c.key))
            for c in inspect(object).mapper.column_attrs}