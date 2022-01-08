from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import requests
from datetime import date, datetime
from bs4 import BeautifulSoup
from random import randint
import time

from .models import Article, Issue

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


# Create your views here.
def index(request):


	scrape("2022-01-01")

	#get_blank_economist_browser()

	return HttpResponse("Under construction")

def scrape_article(browser, issue, article_url, art_elem=None):
	browser.get(article_url)
	time.sleep(1)
	#art_elem.click()
	print(article_url)


	dupes = Article.objects.filter(url = article_url)

	if dupes.count() and not OVERWRITE:
		print("This article url exists in our database, skipping")
		#go back to before the click
		browser.execute_script("window.history.go(-1)")
		return None
	elif dupes.count(): #doesnt really overwrite
		print("This article url exists, re-scraping and overwriting")
		return dupes.get()




	article = Article()

	article.title = browser.find_element_by_class_name("article__headline").text
	article.sub_title = browser.find_element_by_class_name("article__subheadline").text
	article.issue = issue
	article.description = browser.find_element_by_class_name("article__description").text 
	article.url = article_url
	article.html = browser.page_source

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
		print(e)
		pass

	#piece together the article text, they break it up for ads and such
	article_string = ""
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
	#go back to before the click
	#browser.execute_script("window.history.go(-1)")

	return article




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
		if count > 1: #so debugging is quicker
			return
		#headline_elements = browser.find_elements_by_class_name("headline-link")
		article = scrape_article(browser, issue, link)#, headline_elements[count])

		if article: #makes sure a None was not returned, which denotes a skip.
			article_objects.append(article)
			
		
	#dont really need this and simpler without, never going to need speed
	Article.objects.bulk_create(article_objects)






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
 

#debugging method to simply open up a browser with economist.com
#helps get a browser in the right position to record login mouse
#and keyboard movements.
def get_blank_economist_browser():
	#start a browser session
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--disable-infobars")
	browser = webdriver.Chrome('/home/eamon/repos/ehome/chromedriver', chrome_options=chrome_options)

	browser.get('https://economist.com')

