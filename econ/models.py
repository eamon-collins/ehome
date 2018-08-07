from django.db import models

# Create your models here.
class Issue(models.Model):
	title =  models.CharField(max_length=40)
	date = models.DateField()



class Article(models.Model):
	title = models.CharField(max_length=40)
	issue = models.ForeignKey('Issue', models.CASCADE)
	category = models.CharField(max_length=20)
	text = models.TextField()

