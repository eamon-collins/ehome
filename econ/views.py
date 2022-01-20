from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
import requests
from datetime import date, datetime
from bs4 import BeautifulSoup
from random import randint
import time
from datetime import datetime
import requests

from .models import Article, Issue
from ehome.views import authenticate_user


from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

#relative import to private tool
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'alibabble'))
import playback as Playback

#whether the system will overwrite the old record of the article
#or stop and leave the current record. Doesnt really work as true rn
OVERWRITE = False

STATIC_IMG_URL = "econ/static/img/"
current_issue = None
req_session = None


# Create your views here.
def index(request):

	user = authenticate_user(request)
	if not user:
		return HttpResponseRedirect('/login')

	#scrape("2022-01-01")

	#get_blank_economist_browser()

	return HttpResponse("Hello, " + user.username + ", this page is under construction")



def scrape(edition_date):
	#start a browser session
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--disable-infobars")
	chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0")
	browser = webdriver.Chrome('/home/eamon/repos/ehome/chromedriver', chrome_options=chrome_options)

	#this logs in and should leave you on home page
	login(browser)

	weekly_edition = "https://www.economist.com/weeklyedition/"+edition_date#datetime.date("2022-01-01").isoformat()
	browser.get(weekly_edition)

	try:
		title = browser.find_element_by_class_name("weekly-edition-header__headline").text
	except Exception as e:
		title = "Couldn't find issue title"

	#check for pre-existing issue matching this date in our database
	dupes = Issue.objects.filter(date = edition_date)
	if dupes.count() == 0:
		issue = Issue.objects.create(
			title = title,
			date = edition_date
			)
		print(title + repr(edition_date))
		issue.save()
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

	#necessary to get links first so don't get StaleElements
	article_links = []
	for headline in headline_elements:
		article_links.append(headline.get_attribute("href"))
	article_objects = []
	for count, link in enumerate(article_links):
		# if count > 1: #so debugging is quicker
		# 	return
		#headline_elements = browser.find_elements_by_class_name("headline-link")
		article = scrape_article(browser, issue, link)#, headline_elements[count])

		if article: #makes sure a None was not returned, which denotes a skip.
			article_objects.append(article)
			
		
	#dont really need this and simpler without, never going to need speed
	Article.objects.bulk_create(article_objects)


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
		return dupes.get()


	#test if it's logged me out, get back in by simply clicking login
	try:
		regwall = browser.find_element_by_id('tp-regwall')
		#loginlink = browser.find_element_by_id('regwall-login-link')
		if regwall:
			browser.execute_script("window.scrollTo(0,0)")
			browser.find_element_by_link_text('Sign in').click()
		#loginlink.click()
		print("Logged back in")
	except NoSuchElementException as e:
		print("No paywall present")
		pass

	#start building the article object
	article = Article()
	textbased = True

	article.title = browser.find_element_by_class_name("article__headline").text
	article.sub_title = browser.find_element_by_class_name("article__subheadline").text
	article.issue = issue
	try:
		article.description = browser.find_element_by_class_name("article__description").text 
	except NoSuchElementException as e:
		textbased = False
	article.url = article_url
	

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

	#harvest all pictures
	global current_issue
	#if this is the first image of an edition, we need to create a folder for it
	if not os.path.isdir(STATIC_IMG_URL + current_issue.date.strftime("%d-%m-%Y")):
		os.mkdir(STATIC_IMG_URL + current_issue.date.strftime("%d-%m-%Y"))

	try:
		images = browser.find_elements_by_tag_name("img")
		link_map = dict()
		for img in images:
			orig_link = img.get_attribute("src")
			my_link = transform_link(orig_link)
			if my_link:
				link_map[orig_link] = my_link

		#now actually visit and screenshot each image
		#Economist forbids most other automated gets
		#actually, trying to set up logged requests session
		s = get_logged_requests_session(browser)
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
	article.html = sanitize_html(browser.page_source)

	return article


def login(browser):
	loginurl = 'https://economist.com'
	browser.get(loginurl)

	#THESE LOGINS AREN"T TO A PAID ACCOUNT
	#execute manual one of 3 manual recordings
	rec_path = "econ/recordings/login" + str(randint(1,3)) +".rec"

	#THIS LOGIN IS TO A PAID ACCOUNT
	rec_path = "econ/recordings/login-paid.rec"

	#rec_path = "econ/recordings/loginfast.rec"
	Playback.playback(os.path.abspath(rec_path), 1)

def get_logged_requests_session(browser):
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
def transform_link(orig_link):
	try:
		my_link = orig_link[orig_link.index(".com")+5:].replace("/","_")
	except ValueError as e:
		return None

	diff = len(my_link) - 150 
	if diff > 0:
		my_link = my_link[diff:]

	global current_issue

	my_link = os.path.join(STATIC_IMG_URL, current_issue.date.strftime("%d-%m-%Y"), my_link)
			
	return my_link


def sanitize_html(html):
	soup = BeautifulSoup(html, "lxml")

	#remove all script tags
	for s in soup.select('script'):
		s.extract()

	#try to remove interruptive ads
	for ad in soup.find_all("div", {"class": "advert"}):
		ad.extract()

	#change image link so it works with our static path
	for img in soup.select('img'):
		orig_link = img['src']

		my_link = transform_link(orig_link)
		if my_link:
			img['src'] = my_link
		else:
			img.extract()

		

	return str(soup)

#debugging method to simply open up a browser with economist.com
#helps get a browser in the right position to record login mouse
#and keyboard movements.
def get_blank_economist_browser():
	#start a browser session
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--disable-infobars")
	browser = webdriver.Chrome('/home/eamon/repos/ehome/chromedriver', chrome_options=chrome_options)

	browser.get('https://economist.com')

