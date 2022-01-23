from django.urls import path

from . import views
from django.contrib.auth import views as auth_views
from django.urls import path, register_converter
from datetime import datetime

class DateConverter:
    regex = '\d{4}-\d{2}-\d{2}'

    def to_python(self, value):
        return datetime.strptime(value, '%Y-%m-%d')

    def to_url(self, value):
        return value

register_converter(DateConverter, 'yyyy')

urlpatterns = [
    #path('login/', auth_views.login, name='login'),
    path('', views.index, name='index'),
    path('<yyyy:date>/', views.weekly_issue_main, name="weekly_issue_main"),
    path('<yyyy:issue_date>/<slug:linky_title>/', views.serve_article, name="serve_article"),
]