from django.db import models

# Create your models here.
class Issue(models.Model):
	title =  models.CharField(max_length=60)
	date = models.DateField()
	html = models.TextField(blank=True)
	cover_pic = models.CharField(blank=True, max_length = 150)
	#internal link to this issues main page
	link = models.CharField(blank=False, default="", max_length=40)

class Article(models.Model):
	title = models.CharField(max_length=40)
	sub_title = models.CharField(max_length = 40, blank=True)
	#url is external, don't expose it to user. link is internal,
	linky_title = models.CharField(max_length=60, default="/sorry/")
	url = models.URLField(max_length=500, blank=False, default="")
	link = models.CharField(blank=False, default="", max_length=80)
	issue = models.ForeignKey('Issue', models.CASCADE)
	category = models.CharField(max_length=20, blank=True)
	description = models.CharField(max_length=200, blank=True)
	text = models.TextField()
	html = models.TextField(blank=True)

class User(models.Model):
	username = models.CharField(max_length=20, blank=False, null=False)
	passhash = models.TextField(blank=False, null=False)
	email = models.EmailField(blank=True, null=True)


class Authenticator(models.Model):
	user_id = models.ForeignKey(User, on_delete=models.CASCADE)
	authenticator = models.TextField(blank=False, null=False)
	date_created = models.DateTimeField(auto_now=False, auto_now_add=True, blank=True, null=True)
