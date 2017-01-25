from django.contrib import admin
from .models import Type, Subtype, Section, Keyword, Experience, ExperienceComment, ExperienceApproval, Affiliation, EmailTask, EXDBUser, Requirement, Semester


class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_datetime', 'author')


class ExperienceApprovalAdmin(admin.ModelAdmin):
    list_display = ('experience', 'approver', 'timestamp')

admin.site.register(Type)
admin.site.register(Subtype)
admin.site.register(Section)
admin.site.register(Keyword)
admin.site.register(Experience, ExperienceAdmin)
admin.site.register(ExperienceComment)
admin.site.register(ExperienceApproval, ExperienceApprovalAdmin)
admin.site.register(EmailTask)
admin.site.register(Affiliation)
admin.site.register(EXDBUser)
admin.site.register(Requirement)
admin.site.register(Semester)
