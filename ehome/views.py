from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.forms.models import model_to_dict
from django.urls import reverse
from django.contrib.auth import hashers

import hmac
import json
import os
from datetime import datetime, timedelta
from django.utils import timezone

import ehome.settings as settings
from ehome.forms import LoginForm
from econ.models import User, Authenticator


# At the moment, if not debug should create users according to 
# origin users in SECRETS.json
def index(request):
	#FOR DEBUG PURPOSES ONLY
	if settings.DEBUG:
		username = "admin"
		password = "admin"
		passhash = hashers.make_password(password)

		try:
			User.objects.get(username = username)
		except User.DoesNotExist:
			User(username=username, passhash=passhash).save()
	else:
		#Create origin users
		with open('SECRETS.json') as f:
			secrets = json.loads(f.read())
		for userdict in secrets["ORIGIN_ACCOUNTS"]:
			try:
				User.objects.get(username = userdict["username"])
			except User.DoesNotExist:
				passhash = hashers.make_password(userdict["password"])
				User(username = userdict["username"], passhash = passhash).save()
		#destry admin user if it exists in this database, we dont want it in prod
		try:
			admin = User.objects.get(username = "admin")
			admin.delete()
		except User.DoesNotExist:
			pass


	user = authenticate_user(request)
	if not user:
		return HttpResponseRedirect('/login/')



	return HttpResponse("This page still under construction")


def login(request):
	form = LoginForm()
	text = " "
	# If we received a GET request instead of a POST request
	if request.method == 'GET':
		# display the login form page
		next = request.GET.get('next') or reverse('index')
		return render(request, 'login.html', {'form':form, 'login':True})

	# Creates a new instance of our login_form and gives it our POST data
	f = LoginForm(request.POST)


	# Check if the form instance is invalid
	if not f.is_valid():
	  # Form was bad -- send them back to login page
		return render(request, 'login.html', {'form':form})

	# Sanitize username and password fields
	username = f.cleaned_data['username']
	password = f.cleaned_data['password']

	try:
		user = User.objects.get(username = username)
	except User.DoesNotExist:
		return HttpResponse("no user")
		return HttpResponseRedirect("/login/")

	if not hashers.check_password(password, user.passhash):
		return HttpResponse("no pass")
		return HttpResponseRedirect("/login/")

	#Very low chance we independently generate an already used auth,
	#but might as well make sure
	while (True):
		authenticator = hmac.new(
			key=settings.SECRET_KEY.encode('utf-8'),
			msg=os.urandom(32),
			digestmod='sha256',
		).hexdigest()
		try:
			Authenticator.objects.get(authenticator=authenticator)
		except Authenticator.DoesNotExist:
			break

	try:
		Authenticator.objects.get(user_id=user).delete()
		auth = Authenticator.objects.create(user_id=user, authenticator=authenticator)
	except:
		auth = Authenticator.objects.create(user_id=user, authenticator=authenticator)

	auth.save()
	auth = model_to_dict(auth)


	# Ge t next page
	next = f.cleaned_data.get('next') or reverse('index')


	""" If we made it here, we can log them in. """
	# Set their login cookie and redirect to back to wherever they came from
	authenticator = auth['authenticator']
	response = HttpResponseRedirect(next)
	response.set_cookie("auth", authenticator)

	return response

def logout(request):
	user = authenticate_user(request)
	if user:
		try:
			Authenticator.objects.get(user_id=user).delete()
		except Authenticator.DoesNotExist:
			pass
	return HttpResponseRedirect('/login/')

def authenticate_user(request):

	try:  # tests if the user has an authenticator that matches the one the database has for them and is not expired
		auth = Authenticator.objects.get(authenticator=request.COOKIES['auth'])
		if (auth.date_created > timezone.now() - timedelta(days=1)):
			return auth.user_id
	except Authenticator.DoesNotExist:
		return None
	except KeyError as e: #they don't have a cookie with auth
		return None

#not yet adapted for creating users
#eventually, should make a form for this and allow it to be accessed when I generate a special link?
def createUser(request):
	if request.method == 'POST':
		try:
			username = request.POST.get('username', False)
			if not username:
				return JsonResponse({'results': 'You need a username'})

			password = request.POST.get('password', False)
			if not password:
				return JsonResponse({'results': 'You need a password'})

			email = request.POST.get('email', False)
			if not email:
				return JsonResponse({'results': 'You need an email'})

			try:
				User.objects.get(username=request.POST.get('username'))
				return JsonResponse({'results': 'That username is already taken'})
			except User.DoesNotExist:
				pass


			passhash = hashers.make_password(password)

			User(username=username, passhash=passhash,
									email=email).save()

			return JsonResponse({'results': 'Success'})

		except IntegrityError:
			return JsonResponse({'results': 'something went very wrong'})
		except ValueError:
			return JsonResponse({'results': 'You got a ValueError'})
	else:
		return JsonResponse({'results': "This is a POST method"})