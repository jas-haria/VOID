from sqlalchemy import asc
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta


from model.division import Division
from model.quora_keyword import QuoraKeyword
from model.quora_question import QuoraQuestion
from model.enum import TimePeriod
from service.util_service import getNewSession, scrollToBottom, getDriver, convertListToJson, paginate

SCROLL_PAUSE_TIME = 3
encoding = 'utf-8'


def refresh_data(time):
    session = getNewSession()
    divisions = session.query(Division).order_by(asc(Division.id))
    keywords = session.query(QuoraKeyword).all()
    question_list = []
    url_set = set()

    for row in session.query(QuoraQuestion.question_url).filter(QuoraQuestion.asked_on > get_time_interval(time)):
        url_set.add(str(row.question_url).replace('https://www.quora.com', ''))

    division = Division()
    division.id = 4

    for divisionIndexer in [division]:
        for keywordIndexer in keywords:
            if keywordIndexer.division == divisionIndexer.id:
                url = "https://www.quora.com/search?q=" + keywordIndexer.keyword.replace(' ', '+') + "&time=" + time + "&type=question"
                driver = getDriver()
                driver.get(url)
                scrollToBottom(driver, SCROLL_PAUSE_TIME)
                page = driver.page_source
                soup = BeautifulSoup(page, 'html.parser')

                # GET EACH QUESTION LINK & QUESTION TEXT
                for link in soup.findAll('a', attrs={'class': 'question_link'}):
                    question_link = link['href']
                    # UNANSWERED QUESTIONS WILL REDIRECT TO ORIGINAL URL ANYWAY
                    if '/unanswered' in question_link:
                        question_link = question_link.replace('/unanswered', '', 1)
                    if str(question_link) not in url_set:
                        url_set.add(question_link)
                        question = QuoraQuestion()
                        question.question_url = ('https://www.quora.com' + question_link).encode(encoding)
                        question.question_text = link.find('span', attrs={'class': 'ui_qtext_rendered_qtext'}).text.encode(encoding)
                        question.division = divisionIndexer.id
                        question_list.append(question)

                driver.close()

    session.bulk_save_objects(fill_dates(question_list))
    session.commit()

    return {}


def get_time_interval(time):
    timedelta_value = None
    if time == TimePeriod.DAY.value:
        timedelta_value = relativedelta(days=1)

    if time == TimePeriod.WEEK.value:
        timedelta_value = relativedelta(weeks=1)

    if time == TimePeriod.MONTH.value:
        timedelta_value = relativedelta(months=1)

    # RETURNING AN EXTRA DAY IN CASE OF OVERLAPPING TIMEZONES
    return datetime.now() - timedelta_value - relativedelta(days=1)

def fill_missing_dates():
    session = getNewSession()
    question_list = session.query(QuoraQuestion).filter_by(asked_on=None, evaluated=False).all()

    session.bulk_save_objects(fill_dates(question_list))
    session.commit()

    return {}


def fill_dates(question_list):
    for question in question_list:
        link = question.question_url
        if type(link) != str:
            link = link.decode(encoding)
        link += '/log'

        driver = getDriver()
        driver.get(link)
        scrollToBottom(driver, SCROLL_PAUSE_TIME)
        page = driver.page_source
        soup = BeautifulSoup(page, 'html.parser')

        # GET DATE
        for each_part in soup.select('div[class*="pagedlist_item"]'):
            if each_part.get_text().find("Question added by") >= 0:
                date_text = (each_part.get_text()[-12:].strip())
                # FOR QUESTIONS ASKED LESS THAN 24 HOURS AGO
                if 'ago' in date_text:
                    question.asked_on = datetime.now().date()
                    break
                if 'yesterday' in date_text:
                    question.asked_on = (datetime.now() - relativedelta(days=1)).date()
                    break
                # FOR QUESTIONS BEFORE 24 HOURS AGO
                question.asked_on = datetime.strptime(date_text, '%b %d, %Y').date()

        driver.close()

    return question_list

def delete_questions(question_ids_list):
    print(question_ids_list)
    session = getNewSession()
    session.query(QuoraQuestion).filter(QuoraQuestion.id.in_(question_ids_list)).delete(synchronize_session=False)
    session.commit()
    return {}

def update_evaluated(question_ids_list, evaluated):
    session = getNewSession()
    session.query(QuoraQuestion).filter(QuoraQuestion.id.in_(question_ids_list)).update({QuoraQuestion.evaluated: evaluated}, synchronize_session=False)
    session.commit()
    return {}

def get_questions(division_ids, time, evaluated, page_number, page_size):
    session = getNewSession()
    query = session.query(QuoraQuestion).filter(QuoraQuestion.division.in_(division_ids))\
        .filter(QuoraQuestion.asked_on > get_time_interval(time)).filter((QuoraQuestion.evaluated).is_(evaluated))
    return paginate(query=query, page_number=int(page_number), page_limit=int(page_size))