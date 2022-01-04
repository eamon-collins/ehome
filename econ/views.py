from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import requests
from datetime import date, datetime
from bs4 import BeautifulSoup
from random import randint

from .models import Article, Issue

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

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

def scrape_article(browser, issue, article_url):
	browser.get(article_url)
	print(article_url)

	dupes = Article.objects.filter(url = article_url)

	if dupes.count() and not OVERWRITE:
		print("This article url exists in our database, skipping")
		return None
	elif dupes.count(): #doesnt really
		print("This article url exists, re-scraping and overwriting")
		return dupes.get()





	article = Article()

	article.title = browser.find_element_by_class_name("article__headline").text
	article.sub_title = browser.find_element_by_class_name("article__subheadline").text
	article.issue = issue
	article.description = browser.find_element_by_class_name("article__description").text 

	#piece together the article text
	article_string = ""
	for text_piece in browser.find_elements_by_class_name("article__body-text"):
		#print(text_piece.text)
		try:
			article_string += text_piece.text 
			article_string += "\n"
		except StaleElementReferenceException as e:
			print("Stale element exception in article scraping url: " + article_url)

	return article




def scrape(edition_date):
	#start a browser session
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--disable-infobars")
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
	for link in article_links:
		article = scrape_article(browser, issue, link)
		if article: #makes sure a None was not returned, which denotes a skip.
			article_objects.append(article)
		
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

