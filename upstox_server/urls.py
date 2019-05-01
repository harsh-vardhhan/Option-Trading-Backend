from django.urls import path
from rest_framework.routers import DefaultRouter
from app.fn_views import get_redirect_url, get_access_token, save_option, search_symbol, get_option, save_full_quotes

router = DefaultRouter()

urlpatterns = [
    path('redirecturl/', get_redirect_url),
    path('accesstoken/', get_access_token),
    path('saveoption/', save_option),
    path('searchsymbol/', search_symbol),
    path('option/', get_option),
    path('savefullquotes/', save_full_quotes)
]

urlpatterns += router.urls