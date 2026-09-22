from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('connect/', views.connections, name='connections'),
    path('profile/', views.profile, name='profile'),
]
