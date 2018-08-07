from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import requests
from datetime import date, datetime
from bs4 import BeautifulSoup

from selenium import webdriver



# Create your views here.
def index(request):
	#diagresults = scrape()
	selenlogin = login()
	return selenlogin
	return HttpResponse("Under construction")


def login():
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--disable-infobars")
	browser = webdriver.Chrome('/home/eamon/Downloads/chromedriver', chrome_options=chrome_options)
	loginurl = 'https://authenticate.economist.com/login'
	browser.get(loginurl)

def scrape():
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