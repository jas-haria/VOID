from sqlalchemy import asc
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium.webdriver.common.keys import Keys
import time


from model.model import Division, QuoraKeyword, QuoraQuestion, Script, Constant, QuoraAccount, ExecutionLog, QuoraQuestionAccountDetails
from model.enum import TimePeriod
from service.util_service import get_new_session, scroll_to_bottom, get_driver, convert_list_to_json, paginate, replace_all, getConstantsDict

SCROLL_PAUSE_TIME = 3
encoding = 'utf-8'


def refresh_data(time, put_todays_date):
    session = get_new_session()
    divisions = session.query(Division).order_by(asc(Division.id))
    keywords = session.query(QuoraKeyword).all()
    question_list = []
    url_set = set()
    driver = get_driver()

    for row in session.query(QuoraQuestion.question_url).filter(QuoraQuestion.asked_on > get_time_interval(time)):
        url_set.add(replace_all(str(row.question_url), {"https://www.quora.com", ""}))

    for divisionIndexer in divisions:
        for keywordIndexer in keywords:
            if keywordIndexer.division == divisionIndexer:
                url = "https://www.quora.com/search?q=" + replace_all(keywordIndexer.keyword, {" ", "+"}) + "&time=" + time + "&type=question"
                driver.get(url)
                scroll_to_bottom(driver, SCROLL_PAUSE_TIME)
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
                        question.division_id = divisionIndexer.id
                        question_list.append(question)
    driver.quit()
    session.bulk_save_objects(fill_dates(question_list, put_todays_date, session))
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
    session = get_new_session()
    question_list = session.query(QuoraQuestion).filter_by(asked_on=None, evaluated=False).all()

    session.bulk_save_objects(fill_dates(question_list, False, session))
    session.commit()

    return {}


def fill_dates(question_list, put_todays_date, session):
    if put_todays_date:
        fixed_asked_on = datetime.now().date()
        for question in question_list:
            question.asked_on = fixed_asked_on

    else:
        driver = get_driver()
        for question in question_list:
            link = question.question_url
            if type(link) != str:
                link = link.decode(encoding)
            link += '/log'

            driver.get(link)
            scroll_to_bottom(driver, SCROLL_PAUSE_TIME)
            page = driver.page_source
            soup = BeautifulSoup(page, 'html.parser')

            # GET DATE
            for each_part in soup.select('div[class*="pagedlist_item"]'):
                if each_part.get_text().find("Question added by") >= 0:
                    date_text = each_part.get_text()
                    # FOR QUESTIONS ASKED LESS THAN 24 HOURS AGO
                    if 'ago' in date_text:
                        question.asked_on = datetime.now().date()
                        break
                    if 'yesterday' in date_text:
                        question.asked_on = (datetime.now() - relativedelta(days=1)).date()
                        break
                    # FOR QUESTIONS BEFORE
                    date_text = (date_text[-12:].strip())
                    if ',' in date_text:
                        question.asked_on = datetime.strptime(date_text, '%b %d, %Y').date()
                    else:
                        date_text = (date_text[-6:].strip())
                        question.asked_on = datetime.strptime(date_text, '%b %y').date()

        driver.quit()
    return question_list

def delete_questions(question_ids_list):
    print(question_ids_list)
    session = get_new_session()
    session.query(QuoraQuestion).filter(QuoraQuestion.id.in_(question_ids_list)).delete(synchronize_session=False)
    session.commit()
    return {}

def update_evaluated(question_ids_list, evaluated):
    session = get_new_session()
    session.query(QuoraQuestion).filter(QuoraQuestion.id.in_(question_ids_list)).update({QuoraQuestion.evaluated: evaluated}, synchronize_session=False)
    session.commit()
    return {}

def get_questions(division_ids, time, evaluated, page_number, page_size):
    session = get_new_session()
    query = session.query(QuoraQuestion).filter(QuoraQuestion.division_id.in_(division_ids))\
        .filter(QuoraQuestion.asked_on > get_time_interval(time)).filter((QuoraQuestion.evaluated).is_(evaluated))
    return paginate(query=query, page_number=int(page_number), page_limit=int(page_size))

# METHOD TO REFRESH QUESTIONS ANSWERED AND FOLLOWERS FOR EVERY ACCOUNT (WITHOUT LOGIN)
def refresh_accounts_data():
    session = get_new_session()
    script = session.query(Script).filter(Script.name == 'Refresh_Quora_Accounts_Data').first()
    execution_log = session.query(ExecutionLog).filter(ExecutionLog.script_id == script.id).first()
    code_constants = session.query(Constant).filter(Constant.script_id == script.id).all()
    accounts = session.query(QuoraAccount).all()
    code_constant_dict = getConstantsDict(code_constants)
    driver = get_driver()
    for account in accounts:
        print(account.link)
        driver.get(account.link)
        scroll_to_bottom(driver, SCROLL_PAUSE_TIME)
        page = driver.page_source
        soup = BeautifulSoup(page, 'html.parser')
        breakLoop = False
        # LOOP IDENTIFIES CLASS OF EVERY QUESTION
        for i in soup.findAll(code_constant_dict.get('class_attr_name'), attrs={'class': code_constant_dict.get('class_name')}):
            if breakLoop:
                break
            # GET EACH QUESTION DATE
            for j in i.findAll(code_constant_dict.get('sub_class_1_attr_name'), attrs={'class': code_constant_dict.get('sub_class_1_name')}):
                date_string = replace_all(j.getText(), {"Answered": "", "Updated": ""})
                date_of_answer = datetime.strptime(date_string.strip(), code_constant_dict.get('date_format'))
                #TAKING ONE EXTRA DAY BECAUSE QUESTIONS CAN BE ASKED ON DIFFERENT TIMES ON THE SAME DAY
                if date_of_answer < execution_log.execution_time - relativedelta(days=1):
                    breakLoop = True
                    break

                # GET ALL QUESTIONS NEWLY ANSWERED
                for k in i.findAll(code_constant_dict.get('sub_class_2_attr_name'), attrs={'class': code_constant_dict.get('sub_class_2_name')}):
                    question_link = "https://www.quora.com"+k.get('href')
                    #SAVE QUESTION AS ANSWERED IN DB (TO DO)
                    question = session.query(QuoraQuestion).filter(QuoraQuestion.question_url == question_link).first()
                    if None != question:
                        qqad = session.query(QuoraQuestionAccountDetails).filter(QuoraQuestionAccountDetails.account == account).filter(QuoraQuestionAccountDetails.question == question).first()
                        if None == qqad:
                            qqad = QuoraQuestionAccountDetails()
                            qqad.account = account
                            qqad.question = question
                        qqad.answered = True
                        session.add(qqad)

        # GET FOLLOWERS COUNT
        count = 0
        for i in soup.findAll('div', attrs={'class': 'q-box qu-display--flex'}):
            if count == 4:
                follower_count = replace_all(i.getText(), {"Followers": "", "Follower": ""})
                print(follower_count)
                break
            count += 1

    driver.quit()
    #REFRESH LAST EXECUTED DATE
    execution_log.execution_time = datetime.now()
    session.add(execution_log)
    session.commit()
    return {}


# METHOD TO LOG INTO QUORA ACCOUNT
def login_to_account(driver, account):
    driver.get("https://www.quora.com/")
    form = driver.find_element_by_class_name('regular_login')
    username = form.find_element_by_name('email')
    username.send_keys(account.email)
    password = form.find_element_by_name('password')
    password.send_keys(account.password)
    password.send_keys(Keys.RETURN)
    time.sleep(3)
    return


def refresh_requested_questions():
    driver = get_driver()
    session = get_new_session()
    accounts = session.query(QuoraAccount).all()
    for account in accounts:
        login_to_account(driver, account)
        driver.get("https://www.quora.com/answer/requests")
        scroll_to_bottom(driver, SCROLL_PAUSE_TIME)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        # GET REQUESTED QUESTIONS
        for i in soup.findAll('a', attrs={'class': 'question_link'}):
            questions = "https://www.quora.com/" + i.get('href').replace('/unanswered', '', 1)
            print(questions)

    return {}

def add_asked_question(question_asked, account_id):
    session = get_new_session()
    question = QuoraQuestion()
    question.question_url = question_asked.get('question_url')
    question.question_text = question_asked.get('question_text')
    question.division_id = question_asked.get('division_id')
    question.asked_on = question_asked.get('asked_on')
    session.add(question)
    qqad = QuoraQuestionAccountDetails()
    qqad.account_id = account_id
    qqad.question = question
    qqad.asked = True
    session.add(qqad)
    session.commit()
    return{}