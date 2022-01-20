from django.contrib import admin

from econ.models import Issue, Article, User, Authenticator

# Register your models here.
admin.site.register(Issue)
admin.site.register(Article)
admin.site.register(User)
admin.site.register(Authenticator)
