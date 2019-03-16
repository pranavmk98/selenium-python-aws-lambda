import json
import os
import time
import warnings

from cryptography.fernet import Fernet

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from subprocess import check_call

# Define constants
COOKIE_FILE = 'cookies.json'
COOKIE_1 = '_shibsession_64656661756c7468747470733a2f2f6163636573732e686f7573696e672e636d752e6564752f73686962626f6c657468'
COOKIE_2 = 'defaultlang'

USER_AGENT = "Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36"
HOST = "https://access.housing.cmu.edu"

PIN_FILE = 'pin'

GOOGLE_CHROME_BIN = '/app/.apt/usr/bin/google-chrome'
CHROMEDRIVER_PATH = '/app/.chromedriver/bin/chromedriver'

# Define location of file (to be used in Flask because file structure is w a t)
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def login(driver):
    pwd = get_pass('enc', 'key')
    username = 'pmkumar'

    user_box = driver.find_element_by_name('j_username')
    pwd_box = driver.find_element_by_name('j_password')

    user_box.send_keys(username)
    pwd_box.send_keys(pwd)

    login_button = driver.find_element_by_class_name('loginbutton')
    login_button.click()


def call(driver):
    page = "/student/openmydoor.php"
    update_cookies = False

    driver.get(HOST + page)
    # warnings.warn('Got page')
    if "login.cmu.edu" in driver.title:

        # Set flag to denote that cookies need updating
        update_cookies = True
        # Perform login action
        login(driver)

        # If Duo authentication required
        if "Duo" in driver.title:

            # Switch to Duo IFrame
            iframe = driver.find_element_by_id('duo_iframe')
            driver.switch_to.frame(iframe)

            # Keep trying until page loads
            for i in range(10):
                try:
                    driver.find_element_by_class_name('positive')
                    break
                except Exception:
                    print('retry in 1s.')
                    time.sleep(1)

            # Find the authentication button
            auth = driver.find_element_by_xpath(".//*[contains(text(), 'Send')]")
            remember = driver.find_element_by_xpath(".//*[contains(text(), 'Remember')]")

            # Press the authentication button
            remember.click()
            time.sleep(1)
            auth.click()

    # Wait until open door page loads
    while 'Open' not in driver.title:
        # warnings.warn(driver.title)
        pass

    if update_cookies:
        # Store the cookies
        print("Updating cookies in file")
        store_cookies(driver)

    # Open door
    button = driver.find_element_by_xpath("//input[@value='Open My Door']")
    button.click()
    assert "Approved" in driver.page_source
    print("Success!")


# Return decrypted password from file
def get_pass(encfile, keyfile):
    with open(os.path.join(__location__, encfile), 'rb') as file:
        encrypted = file.readline()

    with open(os.path.join(__location__, keyfile), 'rb') as file:
        key = file.readline()

    f = Fernet(key)
    return f.decrypt(encrypted).decode('utf-8')


# Return list of loaded cookies from file
def load_cookies(driver):
    file = open(os.path.join(__location__, COOKIE_FILE), 'r')
    json_string = file.read()
    cookies = json.loads(json_string)
    final_dict = [{'name': x, 'value': cookies[x]} for x in cookies]
    return final_dict


# Store current cookies into file
def store_cookies(driver):
    cookies = driver.get_cookies()
    final_dict = {}
    for c in cookies:
        if c['name'] == COOKIE_1:
            final_dict[COOKIE_1] = c['value']
        if c['name'] == COOKIE_2:
            final_dict[COOKIE_2] = c['value']

    file = open(os.path.join(__location__, COOKIE_FILE), 'w')
    file.write(json.dumps(final_dict))
    file.close()


# Set the cookies in the driver
def add_cookies(driver):
    cookies = load_cookies(driver)
    for cookie in cookies:
        driver.add_cookie(cookie)


def validate(pin):
    with open(os.path.join(__location__, PIN_FILE), 'r') as file:
        real_pin = file.readline()

    return int(real_pin) == pin


def main(pin):
    # Validate PIN
    if not validate(pin):
        return

    chrome_shim = os.environ.get('GOOGLE_CHROME_SHIM', None)
    chrome_bin = os.environ.get('GOOGLE_CHROME_BIN', None)
    # chrome_bin = '/app/chromedriver'
    opts = webdriver.ChromeOptions()
    opts.add_argument('user-agent=' + str(USER_AGENT))
    # opts.binary_location = chrome_bin
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')

    # Make headless
    opts.add_argument("headless")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1280x1696')
    chrome_options.add_argument('--user-data-dir=/tmp/user-data')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--log-level=0')
    chrome_options.add_argument('--v=99')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('--data-path=/tmp/data-path')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--homedir=/tmp')
    chrome_options.add_argument('--disk-cache-dir=/tmp/cache-dir')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
    chrome_options.add_argument('user-agent=' + str(USER_AGENT))
    chrome_options.binary_location = os.getcwd() + '/bin/headless-chromium'

    # Create driver
    # driver = webdriver.Chrome(executable_path=chrome_shim, options=opts)
    caps = DesiredCapabilities.PHANTOMJS
    caps["phantomjs.page.settings.userAgent"] = str(USER_AGENT)

    warnings.warn('Going to start web driver')
    try:
        print(check_call(["ls", "-l", './bin']))
    except Exception:
        pass

    try:
        print(check_call([
            './bin/headless-chromium',
            '--headless',
            '--no-sandbox',
            '--disable-gpu',
            '--dump-dom',
            'https://api.ipify.org?format=json',
            ]))
    except Exception:
        pass

    # driver = webdriver.PhantomJS(desired_capabilities=caps)
    driver = webdriver.Chrome(os.getcwd() + '/bin/headless-chromium', chrome_options=chrome_options)

    # Open initial dummy page to set cookies
    dummy_path = "/404page"
    driver.get(HOST + dummy_path)

    # Set cookies
    warnings.warn('Going to add cookies')
    add_cookies(driver)
    warnings.warn('Added cookies')

    # Do the real stuff
    call(driver)

    # Close driver
    driver.close()

def lambda_handler(event, context):
    # TODO implement
    main(1234)
    # print("Starting google.com")
    # chrome_options = Options()
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--no-sandbox')
    # chrome_options.add_argument('--disable-gpu')
    # chrome_options.add_argument('--window-size=1280x1696')
    # chrome_options.add_argument('--user-data-dir=/tmp/user-data')
    # chrome_options.add_argument('--hide-scrollbars')
    # chrome_options.add_argument('--enable-logging')
    # chrome_options.add_argument('--log-level=0')
    # chrome_options.add_argument('--v=99')
    # chrome_options.add_argument('--single-process')
    # chrome_options.add_argument('--data-path=/tmp/data-path')
    # chrome_options.add_argument('--ignore-certificate-errors')
    # chrome_options.add_argument('--homedir=/tmp')
    # chrome_options.add_argument('--disk-cache-dir=/tmp/cache-dir')
    # chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
    # chrome_options.binary_location = os.getcwd() + "/bin/headless-chromium"

    # driver = webdriver.Chrome(chrome_options=chrome_options)
    # page_data = ""
    # if 'url' in event.keys():
    #     driver.get(event['url'])
    #     page_data = driver.page_source
    #     print(page_data)
    # driver.close()
    return "yeet"