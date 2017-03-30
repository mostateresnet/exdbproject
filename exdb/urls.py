"""exdb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url
from django.contrib.auth.views import login, logout_then_login
from exdb import views


urlpatterns = [

    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^create$', views.CreateExperienceView.as_view(), name='create_experience'),
    url(r'^approval/(?P<pk>\d+)$', views.ExperienceApprovalView.as_view(), name='approval'),
    url(r'^conclusion/(?P<pk>\d+)$', views.ExperienceConclusionView.as_view(), name='conclusion'),
    url(r'^view/(?P<pk>\d+)$', views.ViewExperienceView.as_view(), name='view_experience'),
    url(r'^edit/(?P<pk>\d+)$', views.EditExperienceView.as_view(), name='edit'),
    url(r'^login$', login, name='login', kwargs={'template_name': 'exdb/login.html'}),
    url(r'^logout$', logout_then_login, name='logout'),
    url(r'^list/upcoming$', views.ListExperienceByStatusView.as_view(readable_status="Upcoming"), name="upcoming_list"),
    url(r'^list/needs-evaluation$', views.ListExperienceByStatusView.as_view(readable_status="Needs Evaluation"), name="eval_list"),
    url(r'^list/(?P<status>[a-zA-Z\-]+)$', views.ListExperienceByStatusView.as_view(), name='status_list'),
    url(r'^experience/search/$', views.SearchExperienceResultsView.as_view(), name='search'),
    url(r'^complete/(?P<pk>\d+)$', views.CompletionBoardView.as_view(), name='completion_board'),
    url(r'^requirement-admin$', views.RequirementAdminView.as_view(), name='requirement-admin'),
    url(r'^rview/(?P<pk>\d+)$', views.ViewRequirementView.as_view(), name='view_requirement'),
    url(r'^section/complete/(?P<pk>\d+)$', views.SectionCompletionBoardView.as_view(), name='section_completion_board'),
]
