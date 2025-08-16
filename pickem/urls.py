# pickem/urls.py
from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # login/logout/password
    path('accounts/signup/', views.signup, name='signup'),

    path('', views.home, name='home'),
    path('standings/', views.standings, name='standings'),
    path('pick/<int:game_id>/', views.make_pick, name='make_pick'),
]
