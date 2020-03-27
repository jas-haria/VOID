from sqlalchemy import asc

from model.division import Division
from service.util_service import getNewSession, convertListToJson

def getAllDivisions():
    session = getNewSession()
    return convertListToJson(session.query(Division).order_by(asc(Division.id)))