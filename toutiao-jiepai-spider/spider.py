# -*- coding:UTF-8 -*-
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from config import *
import pymongo
from hashlib import md5
import os
from multiprocessing import Pool

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
driver = webdriver.Chrome(chrome_options=chrome_options)

def get_page_index(offset,keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3,
        'from': 'gallery'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None

def parse_page_index(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')

def get_page_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return url
        return None
    except RequestException:
        print('请求详情页出错', url)
        return None

def parse_page_detail(url):
    driver.get(url)
    title = driver.find_element_by_class_name('title')
    # print(title.text)
    # print(driver.page_source)
    images_pattern = re.compile('gallery: JSON.parse\("(.*)"\)',re.S)
    html =  driver.page_source
    html = html.replace('\\','')
    html = html.replace('\"','"')
    result =  re.search(images_pattern,html)
    if result:
        # print(result.group(1))
        data = json.loads(result.group(1))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                dowmload_image(image,title)
            return {
                'title': title.text,
                'url': url,
                'images': images
            }

def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False

def dowmload_image(url,title):
    print('正在下载', url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_image(response.content,title)
        return None
    except RequestException:
        print('请求图片出错', url)
        return None
    except FileNotFoundError:
        print('保存到本地失败', url)
        return None

def save_image(content,title):
    image_dir = os.getcwd() + os.path.sep + 'images' + os.path.sep + title.text
    folder = os.path.exists(image_dir)
    if not folder:
        os.makedirs(image_dir)
    file_path = '{0}/{1}.{2}'.format(image_dir,md5(content).hexdigest(),'jpg')
    print(file_path)
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)
            f.close()

def main(offset):
    html = get_page_index(offset,'街拍')
    for url in parse_page_index(html):
        url = url.replace('group/', 'a')
        url = get_page_detail(url)
        if url:
            # print(url)
            result = parse_page_detail(url)
            save_to_mongo(result)
    driver.quit()


if __name__ == '__main__':
    pool = Pool()
    groups = ([x * 20 for x in range(GROUP_START,GROUP_END + 1)])
    pool.map(main,groups)
    pool.close()
    pool.join()
    # main()