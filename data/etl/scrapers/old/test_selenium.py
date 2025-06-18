import os
os.system("pkill -f 'chromedriver'")

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import tempfile

chrome_options = Options()
user_data_dir = tempfile.mkdtemp()
chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
# Comment out the rest for now
# chrome_options.add_argument("user-agent=...")
# chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
# chrome_options.add_experimental_option('useAutomationExtension', False)

print("Before Service/Driver init")
service = Service(ChromeDriverManager().install())
print("Service created")
driver = webdriver.Chrome(service=service, options=chrome_options)
print("Driver created")
driver.get("https://www.google.com")
print(driver.title)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
          get: () => undefined
        })
    """
})
driver.quit()