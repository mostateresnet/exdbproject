from django.contrib import admin
from .models import SubType, Type, Category, Audience, Organization, Keyword, Experience, ExperienceComment

admin.site.register(SubType)
admin.site.register(Type)
admin.site.register(Category)
admin.site.register(Audience)
admin.site.register(Organization)
admin.site.register(Keyword)
admin.site.register(Experience)
admin.site.register(ExperienceComment)
