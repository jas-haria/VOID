from sqlalchemy import asc
from bs4 import BeautifulSoup
from collections.abc import Iterable
from datetime import datetime
from dateutil.relativedelta import relativedelta
from selenium.webdriver.common.keys import Keys
import time


from model.model import Division, QuoraKeyword, QuoraQuestion, Script, Constant, QuoraAccount, ExecutionLog, QuoraQuestionAccountDetails, QuoraAccountStats, QuoraAskedQuestionStats
from model.enum import TimePeriod
from service.util_service import get_new_session, scroll_to_bottom, get_driver, convert_list_to_json, paginate, replace_all, getConstantsDict

LOAD_TIME = 3
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
                scroll_to_bottom(driver, LOAD_TIME)
                soup = BeautifulSoup(driver.page_source, 'html.parser')

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
            scroll_to_bottom(driver, LOAD_TIME)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

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
        driver.get(account.link)
        scroll_to_bottom(driver, LOAD_TIME)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
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
                    question_link = ("https://www.quora.com"+k.get('href')).encode(encoding)
                    #SAVE QUESTION AS ANSWERED IN DB (TO DO)
                    question = session.query(QuoraQuestion).filter(QuoraQuestion.question_url == question_link).first()
                    if question is not None:
                        qqad = session.query(QuoraQuestionAccountDetails).filter(QuoraQuestionAccountDetails.account == account).filter(QuoraQuestionAccountDetails.question == question).first()
                        if qqad is None:
                            qqad = QuoraQuestionAccountDetails()
                            qqad.account = account
                            qqad.question = question
                        qqad.answered = True
                        session.add(qqad)

        # GET FOLLOWERS COUNT
        count = 0
        for i in soup.findAll('div', attrs={'class': 'q-box qu-display--flex'}):
            if count == 4:
                follower_count = replace_all(i.getText(), {"Follower": "", "s": ""})
                follower_count_object = session.query(QuoraAccountStats).filter(QuoraAccountStats.recorded_on == datetime.now().date()).filter(QuoraAccountStats.account_id == account.id).first()
                print(follower_count_object._asdict())
                if follower_count_object is None:
                    follower_count_object = QuoraAccountStats()
                    follower_count_object.account = account
                    follower_count_object.recorded_on = datetime.now().date()
                follower_count_object.total_followers = follower_count
                session.add(follower_count_object)
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
    time.sleep(LOAD_TIME)
    return

def refresh_requested_questions():
    session = get_new_session()
    accounts = session.query(QuoraAccount).all()
    default_division = session.query(Division).filter(Division.division == 'Vidyalankar').first()
    for account in accounts:
        driver = get_driver()
        login_to_account(driver, account)
        driver.get("https://www.quora.com/answer/requests")
        scroll_to_bottom(driver, LOAD_TIME)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # GET REQUESTED QUESTIONS
        for i in soup.findAll('a', attrs={'class': 'question_link'}):
            question_url = ("https://www.quora.com/" + i.get('href').replace('unanswered/', '', 1)).encode(encoding)
            question = session.query(QuoraQuestion).filter(QuoraQuestion.question_url == question_url).first()
            if question is None:
                question = QuoraQuestion()
                question.question_url = question_url
                question.question_text = i.find('span', attrs={'class': 'ui_qtext_rendered_qtext'}).text.encode(encoding)
                question.division = default_division
                session.add(question)
            qqad = session.query(QuoraQuestionAccountDetails).filter(QuoraQuestionAccountDetails.account == account).filter(QuoraQuestionAccountDetails.question == question).first()
            if qqad is None:
                qqad = QuoraQuestionAccountDetails()
                qqad.account = account
                qqad.question = question
            qqad.requested = True
            session.add(qqad)
        driver.quit()
    session.commit()
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
    return {}

def refresh_asked_questions_stats():
    session = get_new_session()
    driver = get_driver()
    questions_details = session.query(QuoraQuestionAccountDetails).filter(QuoraQuestionAccountDetails.asked == True).all()
    for question_detail in questions_details:
        driver.get(question_detail.question.question_url)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        qaqs = session.query(QuoraAskedQuestionStats).filter(QuoraAskedQuestionStats.question == question_detail.question).filter(QuoraAskedQuestionStats.recorded_on == datetime.now().date()).first()
        if qaqs is None:
            qaqs = QuoraAskedQuestionStats()
            qaqs.question = question_detail.question
            qaqs.recorded_on = datetime.now().date()
        # GET NUMBER OF ANSWERS
        for i in soup.findAll('div', attrs={'class': 'answer_count'}):
            qaqs.follower_count = int(replace_all(i.get_text(), {'Answer': '', 's': '', ',': ''}).strip())

        driver.get(question_detail.question.question_url+'/log')
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # IDENTIFIES STATS PER QUESTION
        for i in soup.findAll('div', attrs={'class': 'QuestionStats'}):
            for j in i.findAll('div', attrs={'class': 'u-flex u-flex-align--center u-padding-vert--xs u-text--gray-light pass_color_to_child_links u-sans-font-main--small'}):
                if "Public Follower" in j.get_text():
                    qaqs.follower_count = int(replace_all(j.get_text(), {'Public Follower': '', 's': '', ',': ''}).strip())
                if "View" in j.get_text():
                    qaqs.view_count = int(replace_all(j.get_text(), {'View': '', 's': '', ',': ''}).strip())
        session.add(qaqs)

    driver.quit()
    session.commit()
    return {}

def refresh_accounts_stats(time_period):
    session = get_new_session()
    accounts = session.query(QuoraAccount).all()
    for account in accounts:
        driver = get_driver()
        login_to_account(driver, account)
        driver.get('https://quora.com/stats')
        list = driver.find_element_by_class_name("menu_link")
        list.click()
        time.sleep(LOAD_TIME)
        lastWeek = driver.find_element_by_name("1")
        lastWeek.click()
        time.sleep(LOAD_TIME)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        stats_count = []
        for i in soup.findAll("a", attrs={"heads_up_item"}):
            for j in soup.findAll("p", attrs={"big_num"}):
                stats_count.append(j.get_text(strip=True))
            break

        xaxis_dates = []
        stats_arrays_object = {}
        quora_account_stats_array = []
        for i in [[0, 'Views'], [1, 'Upvotes'], [2, 'Shares']]:
            if int(stats_count[i[0]]) == 0:
                continue
            if xaxis_dates.__len__() == 0:
                xaxis_dates = get_qas_xaxis_dates(soup)
                for date_object in xaxis_dates:
                    qas = QuoraAccountStats()
                    qas.recorded_on = date_object
                    qas.account = account
                    quora_account_stats_array.append(qas)

            stats_arrays_object[i[1]] = get_qas_graph_data(soup)

            if i[0] < 2:
                next_stat_element = driver.find_elements_by_class_name("heads_up_item")[i[0]+1]
                next_stat_element.click()
                time.sleep(LOAD_TIME)
                soup = BeautifulSoup(driver.page_source, 'html.parser')

        count = 0
        for qas_element in quora_account_stats_array:
            if "Views" in stats_arrays_object and stats_arrays_object["Views"].__len__() > 0:
                qas_element.view_count = stats_arrays_object["Views"][count]
            if "Upvotes" in stats_arrays_object and stats_arrays_object["Upvotes"].__len__() > 0:
                qas_element.upvote_count = stats_arrays_object["Upvotes"][count]
            if "Shares" in stats_arrays_object and stats_arrays_object["Shares"].__len__() > 0:
                qas_element.share_count = stats_arrays_object["Shares"][count]
            saved_element = session.query(QuoraAccountStats).filter(QuoraAccountStats.account == qas_element.account).filter(QuoraAccountStats.recorded_on == qas_element.recorded_on).first()
            if saved_element is None:
                session.add(qas_element)
            else:
                if qas_element.view_count is not None:
                    saved_element.view_count = qas_element.view_count
                if qas_element.upvote_count is not None:
                    saved_element.upvote_count = qas_element.upvote_count
                if qas_element.share_count is not None:
                    saved_element.share_count = qas_element.share_count
            count = count + 1

        driver.quit()

    session.commit()
    return {}

# GET DATES ON XAXIS
def get_qas_xaxis_dates(soup):
    xaxis_dates = []
    xaxis_dates_tmp = []
    for i in soup.findAll('div', attrs={'class': 'x_tick plain'}):
        xaxis_date = datetime.strptime(i.get_text().strip(), '%b %d').date()
        if xaxis_date in xaxis_dates_tmp:
            for j in soup.findAll('div', attrs={'class': 'x_tick plain last_tick'}):
                xaxis_dates_tmp.append(datetime.strptime(j.get_text().strip(), '%b %d').date())
                for value in xaxis_dates_tmp:
                    if value.month == 12 and datetime.now().month == 1:
                        year_value = datetime.now().year - 1
                    else:
                        year_value = datetime.now().year
                    xaxis_dates.append(datetime(year_value, value.month, value.day).date())
                break
            break
        xaxis_dates_tmp.append(xaxis_date)
    return xaxis_dates

def  fill_qas_object_array(qas, xaxis_dates, account):
    qas_array = []
    for date_object in xaxis_dates:
        qas = QuoraAccountStats()
        qas.recorded_on = date_object
        qas.account = account
    qas_array.append(qas)
    return qas_array

def get_qas_graph_data(soup):
    # GET YAXIS VALUES AND HEIGHT FOR 1 UNIT
    yaxis_values = []
    for i in soup.findAll('g', attrs={'style': 'opacity: 1;'}):
        yaxis_value = {}
        yaxis_value['pixel'] = float(replace_all(i['transform'], {'translate(0,': '', ')': ''}))
        yaxis_value['number'] = int(i.get_text())
        if yaxis_values.__len__() == 2:
            break
        yaxis_values.append(yaxis_value)
    height_for_one = (yaxis_values[0]['pixel'] - yaxis_values[1]['pixel']) / (
                yaxis_values[1]['number'] - yaxis_values[0]['number'])
    values = []
    for i in soup.findAll('div', attrs={'class': 'rickshaw_graph'}):
        for j in i.findAll('rect'):
            values.append(round(float(j['height']) / height_for_one))
        break
    return values