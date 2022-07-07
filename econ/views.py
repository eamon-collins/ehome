from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from datetime import date, datetime
import time


from .models import Article, Issue
from .crawl import scrape
import econ.crawl as crawl
from ehome.views import authenticate_user
import ehome.settings as settings


from bs4 import BeautifulSoup

#serves list of issues in database
def index(request):
	user = authenticate_user(request)
	if not user:
		return HttpResponseRedirect('/login')

#"2022-07-02", "2022-06-25","2022-06-18",
	# dates = [ "2022-06-25"]
	# for date in dates:
	# 	scrape(date)

	#crawl.get_blank_economist_browser()


	#get all Issues in the database
	issues = Issue.objects.all().order_by("-date")

	return render(request, 'issue_list.html', {'user' : user, 'issue_list' : issues})


	return HttpResponse("Hello, " + user.username + ", this page is under construction")

#renders the main page for the issue with all articles
def weekly_issue_main(request, date):
	user = authenticate_user(request)
	if not user:
		return HttpResponseRedirect('/login')

	try:
		issue = Issue.objects.get(date=date)
	except Issue.DoesNotExist:
		return HttpResponseRedirect("/econ/")

	try:
		articles = Article.objects.filter(issue = issue)
	except Article.DoesNotExist:
		articles = []

	return render(request, 'issue_main.html', {'issue' : issue, 
												'articles' : articles})

def serve_article(request, issue_date, linky_title):
	user = authenticate_user(request)
	if not user:
		return HttpResponseRedirect('/login')
	
	try:
		article = Article.objects.get(linky_title = linky_title )
	except Article.DoesNotExist:
		return HttpResponse("Article does not exist in our database, check your link")

	try:
		issue = Issue.objects.get(date = issue_date)
	except Issue.DoesNotExist:
		issue = None
		print("can't find issue associated with article")
		#return HttpResponse("can't find issue associated with article")

	return render(request, 'article_main.html', {'issue': issue,
												'article' : article})


	return HttpResponse("article view under construction")


#should redirect to the most recent edition
#hardcoded atm, change later
def weekly_edition(request):
	user = authenticate_user(request)
	if not user:
		return HttpResponseRedirect('/login')

	last_edition = Issue.objects.order_by('-date')[0].date
	datestr = last_edition.strftime('%Y-%m-%d')

	return HttpResponseRedirect("/econ/"+datestr+"/")

