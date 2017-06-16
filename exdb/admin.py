from django.contrib import admin
from .models import Type, Subtype, Section, Keyword, Experience, ExperienceComment, ExperienceApproval, Affiliation, EmailTask, EXDBUser


class SubtypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'needs_verification')
    search_fields = ('name',)


class ExperienceCommentInline(admin.TabularInline):
    model = ExperienceComment
    raw_id_fields = ('author',)


class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_datetime', 'author')
    search_fields = (
        'name',
        'description',
        'author__first_name',
        'author__last_name',
        'author__email',
        'author__username',
        'planners__first_name',
        'planners__last_name',
        'planners__email',
        'planners__username',
    )
    raw_id_fields = ('author', 'recognition', 'next_approver')
    inlines = (ExperienceCommentInline,)


class ExperienceApprovalAdmin(admin.ModelAdmin):
    list_display = ('experience', 'approver', 'timestamp')
    search_fields = (
        'experience__name',
        'approver__first_name',
        'approver__last_name',
        'approver__email',
        'approver__username',
    )
    raw_id_fields = ('experience', 'approver')


class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'affiliation')
    search_fields = ('name', 'affiliation__name')


class EXDBUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email')
    search_fields = ('username', 'first_name', 'last_name', 'email')


admin.site.register(Type)
admin.site.register(Subtype, SubtypeAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Keyword)
admin.site.register(Experience, ExperienceAdmin)
admin.site.register(ExperienceApproval, ExperienceApprovalAdmin)
admin.site.register(EmailTask)
admin.site.register(Affiliation)
admin.site.register(EXDBUser, EXDBUserAdmin)
