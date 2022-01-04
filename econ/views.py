from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import requests
from datetime import date, datetime
from bs4 import BeautifulSoup
from random import randint

from .models import Article, Issue

from selenium import webdriver

#relative import to private tool
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'alibabble'))
import playback as Playback



# Create your views here.
def index(request):
	#diagresults = scrape()
	scrape("2022-01-01")
	return HttpResponse("Under construction")

def scrape_article(browser, issue, article_url):
	browser.get(article_url)
	print(article_url)

	article = Article()

	article.title = browser.find_element_by_class_name("article__headline").text
	article.sub_title = browser.find_element_by_class_name("article__subheadline").text
	article.issue = issue
	article.description = browser.find_element_by_class_name("article__description").text 

	#piece together the article text
	article_string = ""
	for text_piece in browser.find_elements_by_class_name("article__body-text"):
		print(text_piece.text)
		article_string += text_piece.text 






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
		title = "Couldn't find"
	issue = Issue.objects.create(
		title = title,
		date = edition_date
		)
	print(title + repr(edition_date))
	issue.save()

	#select articles and scrape them
	headline_elements = browser.find_elements_by_class_name("headline-link")

	#necessary to get links first so don't get StaleElements
	article_links = []
	for headline in headline_elements:
		article_links.append(headline.get_attribute("href"))
	article_objects = []
	for link in article_links:
		article_objects.append(scrape_article(browser, issue, link))
		

	Article.objects.bulk_create(article_objects)



	#Now compose a list of articles in the latest weekly issue



def login(browser):
	loginurl = 'https://economist.com'
	browser.get(loginurl)

	#execute manual one of 3 manual recordings
	rec_path = "econ/recordings/login" + str(randint(1,3)) +".rec"
	#rec_path = "econ/recordings/loginfast.rec"
	Playback.playback(os.path.abspath(rec_path), 1)
 



def OLD_scrape():
	#if it's saturday
	if datetime.now().weekday() == 5 or True:

		destinationurl = 'https://www.economist.com/user/login?destination=%2Fna%2Fprintedition%2F2018-05-26' #2018-05-26'
		#destinationurl += datetime.today().isoformat()


		headers = requests.utils.default_headers()
		headers.update(
		    {
		        'User-Agent': 'Mozilla/5.0',
		    }
		)
		
		s = requests.Session()
		loginurl = 'https://authenticate.economist.com/login'
		payload = {'state': '-rwGqfTTxshJUaBJx6ov88bc2Z_5Al-H',
					'client': 'IARGLj7TVzFnBSYoW94mIzZJAe3U5vaq',
					'protocol': 'oauth2',
					'response_type': 'token%20id_token',
					'redirect_uri': destinationurl,
					'scope': 'openid%20profile',
					'nonce': 'ff5bcmjcshrizlmzb8iml',
					'additional_parameters':'e30%3D',
					'auth0Client':'eyJuYW1lIjoiYXV0aDAuanMiLCJ2ZXJzaW9uIjoiOS42LjEifQ%3D%3D'}
		login_page = s.get(loginurl, headers=headers, params=payload)
		login = BeautifulSoup(login_page.text, 'lxml')
		form = login.find('body')#works attrs={'name': "form_build_id"}
		print(form)
		for script in login(["noscript", "style"]):
			script.decompose()
		for script in login(["script", "style"]):
			script.decompose()

		text = login.get_text()
		return JsonResponse({'result':text})

		# payload = {
		#             'name' : 'ec3bd@virginia.edu',
		#             'pass' : 'zizou361',
		#             'form_build_id' : form['value'],
		#             'form_id' : 'user_login',
		#             'securelogin_original_baseurl' : 'https://www.economist.com',
		#             'op' : 'Log in'
		#             }

		response = s.post(loginurl, data=payload, headers=headers)

		edition = BeautifulSoup(response.text, 'lxml')
		#print(edition.find('href'))


		return None