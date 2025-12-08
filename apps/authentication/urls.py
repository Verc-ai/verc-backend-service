"""
Authentication routes.
Frontend expects: /auth/login and /auth/signup
"""
from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # Support both with and without trailing slash to handle Cloud Run's URL normalization
    path('login', views.LoginView.as_view(), name='login'),
    path('login/', views.LoginView.as_view(), name='login-slash'),
    path('signup', views.SignupView.as_view(), name='signup'),
    path('signup/', views.SignupView.as_view(), name='signup-slash'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]

