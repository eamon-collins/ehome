from django.urls import path

from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', auth_views.login, name='login'),
    path('', views.index, name='index'),
]