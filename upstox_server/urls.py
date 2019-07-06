from django.urls import path
from rest_framework.routers import DefaultRouter
from app.fn_views import (
    get_redirect_url, 
    get_access_token,
    save_option, 
    cache_full_quotes_redis, 
    save_full_quotes_db, 
    get_full_quotes, 
    validate_token,
    subscribe_quotes
)

router = DefaultRouter()

urlpatterns = [
    path('redirecturl/', get_redirect_url),
    path('accesstoken/', get_access_token),
    path('saveoption/', save_option),
    path('cachefullquotes/', cache_full_quotes_redis),
    path('savefullquotes/', save_full_quotes_db),
    path('quote/', get_full_quotes),
    path('validatetoken/', validate_token),
    path('subscribequotes/', subscribe_quotes)
]

urlpatterns += router.urls