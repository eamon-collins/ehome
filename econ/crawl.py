import requests
import json
import time
from datetime import datetime, date 
from bs4 import BeautifulSoup
from random import randint


from .models import Article, Issue
from ehome.views import authenticate_user
import ehome.settings as settings

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, NoSuchFrameException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#schedule edition scraping, called in econ.apps 
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.utils import timezone
from django_apscheduler.models import DjangoJobExecution
import sys

#relative import to private tool
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'alibabble'))
import playback as Playback


#whether the system will overwrite the old record of the article
#or stop and leave the current record. Doesnt really work as true rn
OVERWRITE = True

STATIC_IMG_URL = "econ/static/img/"
current_issue = None
req_session = None


#takes an edition date string
#scheduler for this is in econ.urls so that it starts in the background
#every time the server starts
def scrape(edition_date):
	#start a browser session
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--disable-infobars")
	#chrome_options.add_argument("--headless")
	chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0")
	browser = webdriver.Chrome('/home/eamon/repos/ehome/chromedriver', chrome_options=chrome_options)

	#this logs in and should leave you on home page
	login(browser)

	weekly_edition = "https://www.economist.com/weeklyedition/"+edition_date#datetime.date("2022-01-01").isoformat()
	browser.get(weekly_edition)
	local_issue_link = "/econ/"+edition_date+"/"

	try:
		title = browser.find_element_by_class_name("weekly-edition-header__headline").text
	except Exception as e:
		title = "Couldn't find issue title"




	#get cover pic
	cover_pic = browser.find_element_by_class_name("weekly-edition-header__image").find_element_by_tag_name("img")
	orig_link = cover_pic.get_attribute("src")

	#if this is the first image of an edition, we need to create a folder for it
	if not os.path.isdir(STATIC_IMG_URL + datetime.fromisoformat(edition_date).strftime("%Y-%m-%d")):
		os.mkdir(STATIC_IMG_URL + datetime.fromisoformat(edition_date).strftime("%Y-%m-%d"))

	s = get_logged_in_requests_session(browser)
	imgdata = s.get(orig_link, allow_redirects=True)
	cover_pic = transform_link(orig_link, edition_date)
	cover_pic_static = transform_link(orig_link, edition_date, static=True)
	open(cover_pic, 'wb').write(imgdata.content)

	#check for pre-existing issue matching this date in our database
	dupes = Issue.objects.filter(date = edition_date)
	if dupes.count() == 0:
		issue = Issue.objects.create(
			title = title,
			date = edition_date,
			cover_pic =  cover_pic_static,
			link = local_issue_link
			)
		print(title + repr(edition_date))
		issue.save()
		issue = Issue.objects.get(date = edition_date)
	elif OVERWRITE: 
		issue = dupes.get()
		issue.delete()

		issue = Issue.objects.create(
			title = title,
			date = edition_date,
			cover_pic =  cover_pic_static,
			link = local_issue_link
			)
		print(title + repr(edition_date))
		issue.save()
		issue = Issue.objects.get(date = edition_date)
	else:
		issue = dupes.get()
		print("We already have a record of an issue for this date")


	#set a global current issue when we scrape so everyone knows what it is
	global current_issue
	current_issue = issue


	#Now compose a list of article links in the latest weekly issue
	#get articles by following links and scrape them
	#then save them to db.
	headline_elements = browser.find_elements_by_class_name("headline-link")
	headline_elements += browser.find_elements_by_class_name("teaser-weekly-edition--leaders")
	headline_elements += browser.find_elements_by_class_name("teaser-weekly-edition--cols")
	#necessary to get links first so don't get StaleElements
	article_links = []
	for headline in headline_elements:
		headline_link = headline.find_element_by_tag_name("a")
		article_links.append(headline_link.get_attribute("href"))

	#now sanitize and store html after we are done using it, but before we change the browser page
	try:
		html = sanitize_html(browser.page_source, issue_date = issue.date, get_inside_main=True)
		issue.html = html 
		issue.save()
	except Exception as e:
		print(e)
		html = "Couldn't find html"

	article_objects = []
	for count, link in enumerate(article_links):
		# if count > 2: #so debugging is quicker
		# 	return
		#headline_elements = browser.find_elements_by_class_name("headline-link")
		article = scrape_article(browser, issue, link)#, headline_elements[count])

		if article: #makes sure a None was not returned, which denotes a skip.
			article_objects.append(article)
			
		
	#dont really need this and simpler without, never going to need speed
	#Article.objects.bulk_create(article_objects)


def scrape_article(browser, issue, article_url, art_elem=None):
	browser.get(article_url)
	time.sleep(1)
	#art_elem.click()
	print(article_url)


	dupes = Article.objects.filter(url = article_url)

	if dupes.count() and not OVERWRITE:
		print("This article url exists in our database, skipping")
		#go back to before the click
		#browser.execute_script("window.history.go(-1)")
		return None
	elif dupes.count(): #doesnt really overwrite
		print("This article url exists, re-scraping and overwriting")
		dupes.delete()
		#return dupes.get()


	#test if it's logged me out, get back in by simply clicking login
	try:
		regwall = browser.find_element_by_id('tp-regwall')
		#loginlink = browser.find_element_by_id('regwall-login-link')
		if regwall:
			browser.execute_script("window.scrollTo(0,0)")
			browser.find_element_by_link_text('Log in').click()
		#loginlink.click()
		print("Logged back in")
	except NoSuchElementException as e:
		print("No paywall present")
		pass

	#start building the article object
	article = Article()
	textbased = True
	article.issue = issue

	#save inline stylesheets
	#Get all of the style properties for this element into a dictionary
	
	# whole_article = browser.find_element_by_class_name("css-wvfzu8")
	# styleprops_dict = browser.execute_script('var items = {};'+
	# 							   'var compsty = getComputedStyle(arguments[0]);'+
	# 								'var len = compsty.length;'+
	# 								'for (index = 0; index < len; index++)'+
	# 								'{items [compsty[index]] = compsty.getPropertyValue(compsty[index])};'+
	# 								'return items;', whole_article)
	# #inlineCssText = whole_article.get_attribute("style")
	# with open("inline-style.css", 'w') as file:
	# 	file.write(json.dumps(styleprops_dict))
	# return

	try:# used to be "article__headline" but econ obfuscated their css classnames
		#hope they always use the same hash or someth or this will need updating
		article.title = browser.find_element_by_class_name("css-1bo5zl0").text
	except NoSuchElementException as e:
		try:
			article.title = browser.find_element_by_xpath("//*[@id='main']//h1").text
		except NoSuchElementException as e2:
			print("can't get article title, skipping.")
			return article

	try:#article__subheadline
		article.sub_title = browser.find_element_by_class_name("css-4vhs4z").text
	except NoSuchElementException as e:
		article.sub_title = ""

	try:
		article.description = browser.find_element_by_class_name("article__description").text 
	except NoSuchElementException as e:
		textbased = False
	article.url = article_url
	article.linky_title = transform_href_link(article_url, issue.date).rpartition('/')[2]
	

	print(article.html)


	#piece together the article text, they break it up for ads and such
	article_string = ""

	try: 
		pieces = browser.find_elements_by_class_name("article__body-text")
		for text_piece in pieces:
			#print(text_piece.text)
			try:
				article_string += text_piece.text 
				article_string += "\n"
				print("SUCCESSFUL")
			except StaleElementReferenceException as e:
				print("Stale element exception in article scraping url: " + article_url)
		article.text = article_string
	except NoSuchElementException as e:
		textbased = False 

	# #harvest all pictures
	# global current_issue
	# #if this is the first image of an edition, we need to create a folder for it
	# if not os.path.isdir(STATIC_IMG_URL + current_issue.date.strftime("%Y-%m-%d")):
	# 	os.mkdir(STATIC_IMG_URL + current_issue.date.strftime("%Y-%m-%d"))

	try:
		images = browser.find_elements_by_tag_name("img")
		link_map = dict()
		for img in images:
			orig_link = img.get_attribute("src")
			my_link = transform_link(orig_link, issue.date.strftime("%Y-%m-%d"))
			if my_link:
				link_map[orig_link] = my_link

		#now actually visit and screenshot each image
		#Economist forbids most other automated gets
		#actually, trying to set up logged requests session
		s = get_logged_in_requests_session(browser)
		for link, dest in link_map.items():
			#see if we've already stored this image
			if os.path.isfile(dest):
				print("already have image, skipping")
				continue
			#if this doesn't end with an image suffix, we don't want it
			if not link.lower().endswith(('.png','.jpg','.jpeg')):
				continue

			imgdata = s.get(link, allow_redirects=True)
			open(dest, 'wb').write(imgdata.content)

	except NoSuchElementException as e:
		pass


	#This sanitize method alters the html, do it after we extract original info
	article.html = sanitize_html(browser.page_source, issue_date=issue.date, get_inside_main=True)
	#this in when convenient
	article.save()
	return article


def login(browser):
	loginurl = 'https://economist.com'
	browser.get(loginurl)

	#waits for the cookie message and accepts if/when it pops up
	try:
		browser.switch_to_frame("sp_message_iframe_617100")
		WebDriverWait(browser, 5).until(EC.element_to_be_clickable((By.XPATH,'//button[@title="Accept"]'))).click()
		browser.switch_to_default_content()
	except TimeoutException as e:
		print("TimeOut waiting for cookie dialogue")
	except NoSuchFrameException as e:
		print("No cookie dialogue detected")

	#THESE LOGINS AREN"T TO A PAID ACCOUNT
	#execute manual one of 3 manual recordings
	rec_path = "econ/recordings/login" + str(randint(1,3)) +".rec"

	#THIS LOGIN IS TO A PAID ACCOUNT
	rec_path = "econ/recordings/banishcookiefast.rec"
	#rec_path = "econ/recordings/login-paid.rec"

	#rec_path = "econ/recordings/loginfast.rec"
	time.sleep(1)
	Playback.playback(os.path.abspath(rec_path), 1)

#returns a requests session with my auth cookies set
def get_logged_in_requests_session(browser):
	global req_session 

	if not req_session:
		
		headers = {
			"User-Agent":
			"Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
		}
		req_session = requests.session()
		req_session.headers.update(headers)


		for cookie in browser.get_cookies():
			c = {cookie['name']: cookie['value']}
			req_session.cookies.update(c)

	return req_session


#turns the economist image link into something we can use to store 
#only for images atm
#if static = false or unsupplied
#LOCAL LINK GIVE ACTUAL FOLDER PATH TO STORE AT
#if static = True
#STATIC LINK GIVES FROM STATIC URL, NOT FOLDER
def transform_link(orig_link, current_issue_date= None, static=False):
	my_link = None
	try:
		my_link = orig_link[orig_link.index(".com")+5:].replace("/","_")
		idx = my_link.find("media-assets")
		if idx != -1:
			my_link = my_link[idx:]
	except ValueError as e:
		return None

	diff = len(my_link) - 150 
	if diff > 0:
		my_link = my_link[diff:]

	if static:
		prefix = "img"
	else:
		prefix = STATIC_IMG_URL

	if not current_issue_date:
		global current_issue
		my_link = os.path.join(prefix, current_issue.date.strftime("%Y-%m-%d"), my_link)
	else:
		my_link = os.path.join(prefix, current_issue_date, my_link)

	# if static:
	# 	my_link = "{% static " + my_link + " %}"

	return my_link

#for transforming their links to articles to our links for articles
def transform_href_link(orig_link, current_issue_date=None):
	#get last bit of article title
	link_arr = orig_link.split('/')
	linky_title = link_arr[-1]


	if len(link_arr) < 3 :
		return "econ/"

	yearind = -1
	for ind, el in enumerate(link_arr):
		if el in ['2018', '2019', '2020', '2021', '2022']:
			yearind = ind
	if yearind != -1:
		date_str = link_arr[yearind]+"-"+ link_arr[yearind+1]+"-"+ link_arr[yearind+2]
	else:
		if current_issue_date:
			date_str = current_issue_date.isoformat()
		else:
			return "econ/"

	my_link = os.path.join("econ",date_str,linky_title)

	#print("LINKED:" + linky_title)

	return my_link


	# if current_issue_date:
	# 	linky_title = os.path.join("econ",current_issue_date.isoformat(), linky_title)
	# else: #assuming it is 3 slashes back
	# 	date_arr = orig_link.split('/')[-4:]
	# 	if len(date_arr) < 3:
	# 		return orig_link
	# 	date_str = ""
	# 	for i in range(3):
	# 		date_str += str(date_arr[i]) + "/"
	# 	linky_title = date_str + linky_title

	# return linky_title


def sanitize_html(html, issue_date =None, get_inside_main=False):
	soup = BeautifulSoup(html, "lxml")

	#remove all script tags
	for s in soup.select('script'):
		s.extract()

	#try to remove interruptive ads
	for ad in soup.find_all("div", {"class": "advert"}):
		ad.extract()
	#internal ads
	for ad in soup.find_all("div", {"class": "layout-article-promo"}):
		ad.extract()

	#remove links to share article
	for share in soup.find_all("div", {"class": "layout-article-sharing"}):
		share.extract()

	#remove annoying banner. After css hashing :/
	for listenbanner in soup.find_all("div", {"class": "css-1uzxrld"}):
		listenbanner.extract()
	for listenbanner in soup.find_all("div", {"class": "css-11m9t22"}):
		listenbanner.extract()


	for m in soup.select('meta'):
		m.extract()

	#change image link so it works with our static path
	for img in soup.select('img'):
		orig_link = img['src']

		my_link = transform_link(orig_link, static=True)
		if my_link:
			img['src'] = settings.STATIC_URL + my_link
			del img['srcset']
			del img['sizes']
		else:
			img.extract()

	for a in soup.select('a'):
		try:
			a['href'] = "/" + transform_href_link(a['href'], issue_date)
		except KeyError as e: #doesn't have a href link, we don't care for now, may want to remove tho
			pass

	if get_inside_main:
		main_block = soup.find_all(id='content')[0]
		return main_block.decode_contents()


	return str(soup)

#debugging method to simply open up a browser with economist.com
#helps get a browser in the right position to record login mouse
#and keyboard movements.
def get_blank_economist_browser():
	#start a browser session
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--disable-infobars")
	#chrome_options.add_argument("--headless")
	browser = webdriver.Chrome('/home/eamon/repos/ehome/chromedriver', chrome_options=chrome_options)

	browser.get('https://economist.com')

def scrape_this_week():
	#check if there is likely a new edition. this should be run on a friday
	now = datetime.today()
	if now.weekday() == 4:
		oneday = timedelta(day=1)
		datestr = (now + oneday).strftime('%Y-%m-%d')
		scrape(datestr)


def delete_old_job_executions(max_age=604_800):
	"""This job deletes all apscheduler job executions older than `max_age` from the database."""
	DjangoJobExecution.objects.delete_old_job_executions(max_age)

def setup_timed_scraping():
	scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
	scheduler.add_jobstore(DjangoJobStore(), "default")

	scheduler.add_job(
	  scrape_this_week,
	  trigger=CronTrigger(day_of_week="fri", hour="06", minute="00"), 
	  id="scrape_this_week", 
	  max_instances=1,
	  replace_existing=True,
	)


	scheduler.add_job(
	  delete_old_job_executions,
	  trigger=CronTrigger(
		day_of_week="fri", hour="05", minute="00"
	  ),  
	  id="delete_old_job_executions",
	  max_instances=1,
	  replace_existing=True,
	)