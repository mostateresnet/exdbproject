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
from django.urls import path, re_path
from django.contrib.auth.views import LoginView, logout_then_login
from exdb import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('create', views.CreateExperienceView.as_view(), name='create_experience'),
    path('approval/<int:pk>', views.ExperienceApprovalView.as_view(), name='approval'),
    path('conclusion/<int:pk>', views.ExperienceConclusionView.as_view(), name='conclusion'),
    path('view/<int:pk>', views.ViewExperienceView.as_view(), name='view_experience'),
    path('edit/<int:pk>', views.EditExperienceView.as_view(), name='edit'),
    path('login', LoginView.as_view(template_name='exdb/login.html'), name='login'),
    path('logout', logout_then_login, name='logout'),
    path('list/upcoming', views.ListExperienceByStatusView.as_view(readable_status="Upcoming"), name="upcoming_list"),
    path('list/needs-evaluation', views.ListExperienceByStatusView.as_view(readable_status="Needs Evaluation"), name="eval_list"),
    re_path(r'^list/(?P<status>[a-zA-Z\-]+)$', views.ListExperienceByStatusView.as_view(), name='status_list'),
    path('experience/search/', views.SearchExperienceResultsView.as_view(), name='search'),
    path('experience/search/report', views.SearchExperienceReport.as_view(), name='search_report'),
    re_path(r'^complete/(?P<pk>\d+)?$', views.CompletionBoardView.as_view(), name='completion_board'),
    path('requirement/view/<int:pk>', views.ViewRequirementView.as_view(), name='view_requirement'),
    re_path(r'^section/complete/(?P<pk>\d+)?$', views.SectionCompletionBoardView.as_view(), name='section_completion_board'),
]
