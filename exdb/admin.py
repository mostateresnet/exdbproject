from django.contrib import admin
from .models import SubType, Type, Category, Organization, Keyword, Experience, ExperienceComment


class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_datetime', 'author')


admin.site.register(SubType)
admin.site.register(Type)
admin.site.register(Category)
admin.site.register(Organization)
admin.site.register(Keyword)
admin.site.register(Experience, ExperienceAdmin)
admin.site.register(ExperienceComment)
