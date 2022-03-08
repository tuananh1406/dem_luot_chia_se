#!/usr/local/bin/python
# coding: utf-8
'''Tự động đăng nhập facebook
'''
import os
import pickle
import logging
import re

from datetime import datetime
from time import sleep
from typing import Union, AnyStr
from getpass import getpass
from configparser import ConfigParser
import sentry_sdk
from webdriver_manager.firefox import GeckoDriverManager
import requests

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains


class CustomLogFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'cookies_name'):
            record.cookies_name = EXTRA.get('cookies_name')
        return True


EXTRA = dict(cookies_name=None)
TESTING = None
URL = 'https://www.facebook.com/'
NAME = 'auto_fb'


def thiet_lap_logging(name):
    sentry_sdk.init(
        'https://2e084979867c4e8c83f0b3b8062afc5b@o1086935.'
        'ingest.sentry.io/6111285',
        traces_sample_rate=1.0,
    )

    log_format = ' - '.join([
        '%(asctime)s',
        '%(name)s',
        '%(levelname)s',
        '%(cookies_name)s',
        '%(message)s',
    ])
    formatter = logging.Formatter(log_format)
    file_handles = logging.FileHandler(
        filename='logs.txt',
        mode='a',
        encoding='utf-8',
    )
    file_handles.setFormatter(formatter)

    syslog = logging.StreamHandler()
    syslog.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addFilter(CustomLogFilter())

    logger.addHandler(syslog)
    if not TESTING:
        logger.addHandler(file_handles)

    return logger


LOGGER = thiet_lap_logging(NAME)


def tam_ngung_den_khi(
        driver: Union[
            type(webdriver.Firefox),
            type(webdriver.Chrome),
        ],
        _xpath: AnyStr) -> Union[
            type(webdriver.Firefox),
            type(webdriver.Chrome),
        ]:
    '''Hàm tạm ngưng đến khi xuất hiện đường dẫn xpath
    '''
    _tam_ngung = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            _xpath,
        )),
    )
    return _tam_ngung


def tam_ngung_va_tim(driver, _xpath):
    '''Hàm tạm ngưng đến khi xuất hiện đường dẫn xpath và chọn xpath đó
    '''
    tam_ngung_den_khi(driver, _xpath)
    return driver.find_element(by='xpath', value=_xpath)


def chay_trinh_duyet(headless=False):
    '''Mở trình duyệt và trả về driver
    '''
    options = Options()
    options.headless = headless
    service = Service(GeckoDriverManager().install())
    LOGGER.info('Chạy trình duyệt, headless=%s', headless)
    _driver = webdriver.Firefox(
        options=options,
        service=service,
    )
    # Hàm đặt thời gian tải trang, dùng khi tải trang quá lâu
    # _driver.set_page_load_timeout(5)
    return _driver


def dang_nhap_facebook(_driver, url):
    '''Hàm đăng nhập facebook
    '''
    print('Lấy thông tin tài khoản')
    _ten_dang_nhap = input('Nhập tên đăng nhập: ')
    _mat_khau = getpass(prompt='Nhập mật khẩu: ')

    # Mở trang
    _driver.get(url)

    _xpath_username = '//input[@id="email"]'
    _xpath_password = '//input[@id="pass"]'
    _xpath_login = '//button[@name="login"]'
    _username = _driver.find_element(by='xpath', value=_xpath_username)
    _username.send_keys(_ten_dang_nhap)
    _password = _driver.find_element(by='xpath', value=_xpath_password)
    _password.send_keys(_mat_khau)
    _button = _driver.find_element(by='xpath', value=_xpath_login)
    _button.click()
    return _driver


def dang_nhap_bang_cookies(_driver, _duong_dan_tep_cookie, url):
    '''Hàm đăng nhập facebook bằng cookies
    '''
    LOGGER.info('Đăng nhập %s bằng cookies', url)
    _driver.get(url)
    with open(_duong_dan_tep_cookie, 'rb') as _tep_cookie:
        for value in pickle.load(_tep_cookie):
            if 'expiry' in value:
                del value['expiry']
            _driver.add_cookie(value)

    # Tải lại trang để lấy cookies
    _driver.get(url)
    return _driver


def luu_cookies(_driver, _ten_tep_cookie=None):
    '''Hàm lưu cookies trình duyệt
    '''
    _thu_muc_goc = os.getcwd()
    if _ten_tep_cookie is None:
        # Nếu không chỉ định tên thì lấy tên người dùng để lưu
        _link_facebook_ca_nhan = 'https://www.facebook.com/me'
        _driver.get(_link_facebook_ca_nhan)
        _xpath_ten_nguoi_dung = '//h1[@class="gmql0nx0 l94mrbxd p1ri9a11 '\
            'lzcic4wl bp9cbjyn j83agx80"]'
        _ten_nguoi_dung = _driver.find_element(
            by='xpath',
            value=_xpath_ten_nguoi_dung).text
        _ten_nguoi_dung = _ten_nguoi_dung.split('\n')[0]
        _duong_dan_tep_cookie = os.path.join(
            _thu_muc_goc,
            _ten_nguoi_dung + '.bak',
        )
    else:
        # Nếu có tên thì lưu bằng tên được chỉ định
        _duong_dan_tep_cookie = os.path.join(_thu_muc_goc, _ten_tep_cookie)

    # Lưu cookies
    with open(_duong_dan_tep_cookie, 'wb') as tep_tin:
        pickle.dump(_driver.get_cookies(), tep_tin)
    return _duong_dan_tep_cookie


def count_share(driver, url):
    LOGGER.info('Lấy số lượng share %s', url)
    driver.get(url)
    LOGGER.info('Tìm thông tin lượt share')
    xpath_shared = '/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/di'\
        'v[1]/div[4]/div[1]/div/div/div/div/div/div/div/div/div/div[1]/div/di'\
        'v[2]/div/div[4]/div/div/div[1]/div/div[1]/div/div[2]/div[3]/span'
    shared_button = tam_ngung_va_tim(
        driver,
        xpath_shared,
    )

    LOGGER.info('Mở bảng thông tin người share')
    shared_button.click()
    xpath_total_shared = '/html/body/div[1]/div/div[1]/div/div[4]/div/div/div'\
        '[1]/div/div[2]/div/div/div/div[3]'
    list_total_shared = tam_ngung_va_tim(
        driver,
        xpath_total_shared,
    )
    xpath_info_shared = '/html/body/div[1]/div/div[1]/div/div[4]/div/div/div['\
        '1]/div/div[2]/div/div/div/div[3]/div/div/div'
    list_info = list_total_shared.find_elements(
        by='xpath',
        value=xpath_info_shared,
    )

    LOGGER.info('Số lượng: %s', len(list_info))
    action_chains = ActionChains(driver)
    action_chains.move_to_element(list_total_shared).perform()
    LOGGER.info('Cuộn đến cuối danh sách')
    count_time = 0
    while True:
        count = len(list_info)
        driver.execute_script(
            "return arguments[0].scrollIntoView(true);",
            list_info[-2],
        )
        count_load = 0
        while True:
            list_info = list_total_shared.find_elements(
                by='xpath',
                value=xpath_info_shared,
            )
            if len(list_info) > (count + 1) or count_load == 5:
                break
            sleep(1)
            count_load += 1
        if count_time == 5:
            break
        if len(list_info) > (count + 1):
            count_time = 0
        sleep(1)
        count_time += 1
    LOGGER.info('Số lượng: %s', len(list_info))

    LOGGER.info('Lấy danh sách những người đã share')
    xpath_block_ten = './div/div/div/div[2]/div/div[2]/div/div[1]/span/h3'
    xpath_shared_ca_nhan = './span/a'
    xpath_shared_group = './div/div/span[1]/span/span/a'

    block_end_list = 'class="d2edcug0 hpfvmrgz qv66sw1b c1et5uql b0tq1wua a8c'\
        '37x1j fe6kdd0r mau55g9w c8b282yb keod5gw0 nxhoafnm aigsh9s9 tia6h79c'\
        ' iv3no6db e9vueds3 j5wam9gi lrazzd5p m9osqain hzawbc8m"'

    list_shared = []
    for block in list_info:
        if ('role="progressbar"' in block.get_attribute('innerHTML')) \
                or (block_end_list in block.get_attribute('innerHTML')) \
                or not block.get_attribute('innerHTML'):
            continue
        try:
            block_data = block.find_element(by='xpath', value=xpath_block_ten)
        except Exception as error:
            LOGGER.exception(error)
            LOGGER.info(block.get_attribute('innerHTML'))
            continue
        if '<div' in block_data.get_attribute("innerHTML"):
            block_ten = block_data.find_element(
                by='xpath',
                value=xpath_shared_group)
        else:
            block_ten = block_data.find_element(
                by='xpath',
                value=xpath_shared_ca_nhan)
        link_fb = block_ten.get_attribute('href')
        id_fb = None
        if '/profile.php' in link_fb:
            id_fb = re.search(
                r'\d+',
                link_fb,
            ).group()
        else:
            id_fb = link_fb.split('?')[0].split('/')[-1]
        LOGGER.info(id_fb)
        if id_fb:
            list_shared.append(id_fb)

    set_list_shared = set(list_shared)
    LOGGER.info('Số lượng share: %s', len(set_list_shared))
    LOGGER.info('List share: [%s]', ', '.join(set_list_shared))

    return driver


def main():
    LOGGER.info('Chạy chương trình')

    LOGGER.info('Load tele config')
    CONFIG = ConfigParser()
    CONFIG.read('tele.conf')
    BOT_TELE = CONFIG.get('config', 'BOT_TELE')
    CHAT_ID = CONFIG.get('config', 'CHAT_ID')

    THOI_GIAN_HIEN_TAI = datetime.now()
    LOGGER.info('Gửi thông báo qua telegram')
    url = f'https://api.telegram.org/bot{BOT_TELE}/sendMessage'
    params = {
        'chat_id': CHAT_ID,
        'text': f'Chạy count share facebook: {THOI_GIAN_HIEN_TAI}',
    }
    requests.post(url=url, data=params)
    DRIVER = None

    try:
        DRIVER = chay_trinh_duyet()
        DRIVER.maximize_window()
        SIZE = DRIVER.get_window_size()
        DRIVER.set_window_size(SIZE['width'] / 2, SIZE['height'])
        DRIVER.set_window_position(
            (SIZE['width'] / 2) + SIZE['width'],
            0,
            windowHandle='current',
        )

        # Lấy cookies
        COOKIES_PATH = ''
        if not COOKIES_PATH:
            # Nếu không có thì đăng  nhập lần đầu để set cookies
            DRIVER = dang_nhap_facebook(DRIVER, URL)
            LOGGER.info("Lưu cookies tài khoản")
            COOKIES_PATH = luu_cookies(DRIVER, 'facebook.bak')
            LOGGER.info('Tệp cookies được lưu tại: %s', COOKIES_PATH)
        EXTRA['cookies_name'] = COOKIES_PATH

        LOGGER.info('Tiến hành đăng nhập')
        DRIVER = dang_nhap_bang_cookies(DRIVER, COOKIES_PATH, URL)
        LOGGER.info('Mở url bài viết')
        url = 'https://www.facebook.com/permalink.php?story_fbid=116791727707'\
            '8815&id=197278237476062'
        DRIVER = count_share(DRIVER, url=url)
        THOI_GIAN_XU_LY = datetime.now() - THOI_GIAN_HIEN_TAI
        LOGGER.info('Thời gian xử lý: %s', THOI_GIAN_XU_LY)
        return DRIVER
    except Exception as error:
        LOGGER.exception(error)
        return None


if __name__ == '__main__':
    web_driver = main()
    if web_driver:
        web_driver.quit()
