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
from exdb import views

urlpatterns = [
    url(r'^$', views.WelcomeView.as_view(), name='welcome'),
    url(r'^create$', views.CreateExperienceView.as_view(), name='create-experience'),
    url(r'^pending$', views.PendingApprovalQueueView.as_view(), name='pending'),
    url(r'^pending/approval/(?P<pk>\d+)$', views.ExperienceApprovalView.as_view(), name='approval'),
    url(r'^home$', views.RAHomeView.as_view(), name='ra_home'),
]
