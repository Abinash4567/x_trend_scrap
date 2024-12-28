import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pymongo import MongoClient
from flask import Flask, render_template_string, request
from webdriver_manager.chrome import ChromeDriverManager
import os

# Twitter credentials
TWITTER_EMAIL = "rayyadavabinash@gmail.com"
TWITTER_USERNAME = "rayyadav_abi"
TWITTER_PASSWORD = "Abin@sh9837X"

def connect_to_mongo():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["twitter_trends"]
    collection = db["trending_topics"]
    return collection

def generate_unique_id():
    return str(int(time.time()))

def get_driver_with_proxy():
    try:
        proxy_url = "http://abinash:j.hMMj3nEhx7Bg.@open.proxymesh.com:31280"
        
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")  # Added to block notifications
        # options.add_argument("--headless")  # Commented out for debugging
        # options.add_argument(f'--proxy-server={proxy_url}')
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        
        # Add user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(service=webdriver.ChromeService(ChromeDriverManager().install()), options=options)
        return driver
    except Exception as e:
        print(f"Driver creation error: {str(e)}")
        raise

def login_to_twitter(driver, wait):
    """Handle Twitter login process"""
    try:
        print("Starting login process...")
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(5)  # Increased wait time for initial load
        
        print("Entering email...")
        email_xpath = "//input[@autocomplete='username']"
        email_field = wait.until(EC.presence_of_element_located((By.XPATH, email_xpath)))
        email_field.clear()
        email_field.send_keys(TWITTER_USERNAME)
        time.sleep(1)
        email_field.send_keys(Keys.RETURN)
        time.sleep(3)
        
        print("Entering password...")
        password_xpath = "//input[@name='password']"
        password_field = wait.until(EC.presence_of_element_located((By.XPATH, password_xpath)))
        password_field.clear()
        password_field.send_keys(TWITTER_PASSWORD)
        time.sleep(1)
        password_field.send_keys(Keys.RETURN)
        time.sleep(5)
        
        # Verify login success
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-testid='primaryColumn']")))
            print("Login successful!")
            return True
        except TimeoutException:
            print("Login verification failed")
            return False
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return False

def get_trending_topics(driver, wait):
    """Extract trending topics from Twitter"""
    trending_topics = []
    try:
        print("Navigating to Explore page...")
        driver.get("https://twitter.com/explore")
        time.sleep(7)  # Increased wait time for page load
        
        print("Looking for trending topics...")
        # Try multiple XPath patterns for trends
        possible_xpaths = [
            "//div[@data-testid='trend']",
            "//div[contains(@class, 'trending')]//span",
            "//div[contains(@aria-label, 'Timeline: Trending')]"
        ]
        
        trends = None
        for xpath in possible_xpaths:
            try:
                trends = wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
                if trends:
                    break
            except TimeoutException:
                continue
        
        if not trends:
            print("No trends found")
            return ["N/A"] * 5
        
        # Extract top 5 trending topics
        for trend in trends[:5]:
            try:
                trend_text = trend.text.split('\n')[0]
                trending_topics.append(trend_text if trend_text else "N/A")
                print(f"Found trend: {trend_text}")
            except Exception as e:
                print(f"Error extracting trend: {str(e)}")
                trending_topics.append("N/A")
        
        # Ensure we have exactly 5 trends
        trending_topics = trending_topics[:5]
        while len(trending_topics) < 5:
            trending_topics.append("N/A")
            
        return trending_topics
        
    except Exception as e:
        print(f"Error getting trends: {str(e)}")
        return ["N/A"] * 5

def scrape_trending_topics():
    driver = None
    try:
        print("Initializing driver...")
        driver = get_driver_with_proxy()
        wait = WebDriverWait(driver, 30)  # Increased timeout further
        
        if not login_to_twitter(driver, wait):
            raise Exception("Failed to login to Twitter")
        
        trending_topics = get_trending_topics(driver, wait)
        
        print("Getting IP address...")
        driver.get("https://api64.ipify.org/?format=json")
        ip_address = json.loads(driver.find_element(By.TAG_NAME, "body").text)['ip']
        
        unique_id = generate_unique_id()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data = {
            "_id": unique_id,
            "trend1": trending_topics[0],
            "trend2": trending_topics[1],
            "trend3": trending_topics[2],
            "trend4": trending_topics[3],
            "trend5": trending_topics[4],
            "datetime": timestamp,
            "ip_address": ip_address
        }
        
        print("Storing data in MongoDB...")
        collection = connect_to_mongo()
        collection.insert_one(data)
        
        return data
        
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        return {
            "_id": generate_unique_id(),
            "trend1": "Error occurred",
            "trend2": "Error occurred",
            "trend3": "Error occurred",
            "trend4": "Error occurred",
            "trend5": "Error occurred",
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": "N/A",
            "error": str(e)
        }
    finally:
        if driver:
            driver.quit()

# Flask Web App
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Twitter Trending Topics</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            background-color: #f5f8fa;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .error { 
            color: #e0245e; 
            background-color: #fdd; 
            padding: 10px;
            border-radius: 5px;
        }
        pre { 
            background-color: #f5f5f5; 
            padding: 15px; 
            border-radius: 5px;
            overflow-x: auto;
        }
        button {
            background-color: #1da1f2;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #0c85d0;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            padding: 10px;
            border-bottom: 1px solid #e6ecf0;
        }
        li:last-child {
            border-bottom: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Twitter Trending Topics</h1>
        <form method="POST">
            <button type="submit">Fetch Latest Trends</button>
        </form>

        {% if data %}
            {% if data.get('error') %}
                <p class="error">Error: {{ data['error'] }}</p>
            {% else %}
                <p>These are the most happening topics as on {{ data['datetime'] }}</p>
                <ul>
                    <li>1. {{ data['trend1'] }}</li>
                    <li>2. {{ data['trend2'] }}</li>
                    <li>3. {{ data['trend3'] }}</li>
                    <li>4. {{ data['trend4'] }}</li>
                    <li>5. {{ data['trend5'] }}</li>
                </ul>
                <p>The IP address used for this query was {{ data['ip_address'] }}</p>
                <p>Here's a JSON extract of this record from the MongoDB:</p>
                <pre>{{ json_data }}</pre>
            {% endif %}
        </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    data = None
    json_data = None
    if request.method == "POST":
        data = scrape_trending_topics()
        json_data = json.dumps(data, indent=4)
    return render_template_string(HTML_TEMPLATE, data=data, json_data=json_data)

if __name__ == "__main__":
    app.run(debug=True)