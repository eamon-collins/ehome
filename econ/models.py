from django.db import models

# Create your models here.
class Issue(models.Model):
	title =  models.CharField(max_length=40)
	date = models.DateField()



class Article(models.Model):
	title = models.CharField(max_length=40)
	sub_title = models.CharField(max_length = 40, blank=True)
	url = models.URLField(max_length=500, blank=False, default="")
	issue = models.ForeignKey('Issue', models.CASCADE)
	category = models.CharField(max_length=20, blank=True)
	description = models.CharField(max_length=200, blank=True)
	text = models.TextField()
	html = models.TextField(blank=True)

