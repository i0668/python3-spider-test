# -*- coding:UTF-8 -*-

import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
from config import *
import pymongo

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
# chrome_options.add_argument('blink-settings=imagesEnabled=false')
driver = webdriver.Chrome(chrome_options=chrome_options)
wait = WebDriverWait(driver, 10)

def search():
    try:
        driver.get('https://www.taobao.com')
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#q"))
        )
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"#J_TSearchForm > div.search-button > button")))
        input.send_keys(KEYWORD)
        submit.click()
        total = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))
        return total[0].text
        get_products()
    except TimeoutException:
        return search()

def next_page(page_number):
    try:
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > input"))
        )
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit")))
        input.clear()
        input.send_keys(page_number)
        submit.click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number)))
        get_products()
    except TimeoutException:
        next_page(page_number)

def get_products():
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')))
    html = driver.page_source
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()
    for item in items:
        product = {
            'iamge': item.find('.pic .img').attr('data-src').replace('//','http://'),
            'price': item.find('.price').text().strip().replace('\n',''),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text().replace('\n',' '),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()

        }
        # print(product)
        save_to_mongo(product)

def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('存储到MongoDB成功', result)
    except Exception:
        print('存储到MongoDB失败', result)

def main():
    total = search()
    total = int(re.compile('(\d+)').search(total).group(1))
    # print(total)
    for i in range(1, 10):
        print('正在爬第%s页' % i)
        next_page(i)
    driver.quit()

if __name__ == '__main__':
    main()

