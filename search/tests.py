from django.test import TestCase
from django.urls import path
from . import views # Import views từ chính app 'search'

app_name = 'search' # Định danh app (tùy chọn nhưng nên có)

urlpatterns = [
    path('', views.search_results, name='search'),
    path('home/', views.search_home_view, name='search_home'),
]
