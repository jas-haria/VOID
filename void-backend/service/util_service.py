from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def getNewSession():
    engine = create_engine("mysql://root:rootroot@localhost/VOID_DEV")
    engine.connect()
    Session = sessionmaker(bind=engine)
    return Session()

def getDriver():
    print("get driver")
    options = Options()
    options.headless = True
    return webdriver.Chrome(r"C:\Users\jasha\PycharmProjects\void\driver\chromedriver.exe", options=options)

def scrollToBottom(driver, SCROLL_PAUSE_TIME):
    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def convertListToJson(list):
    json_list = []
    for item in list:
        json_list.append(item._asdict())

    return json_list

def paginate(query, page_number, page_limit):
    length = query.count()
    print(page_number, page_limit)
    if page_number > 0:
        query = query.offset((page_number)*page_limit)
    query = query.limit(page_limit)
    return {'totalLength': length, 'content': convertListToJson(query.all())}
