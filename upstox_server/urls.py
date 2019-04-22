from django.urls import path
from rest_framework.routers import DefaultRouter
from app.fn_views import get_redirect_url, get_access_token, save_option, search_symbol, get_option, get_full_quotes

# To add a new path, first import the app:
# import blog
#
# Then add the new path:
# path('blog/', blog.urls, name="blog")
#
# Learn more here: https://docs.djangoproject.com/en/2.1/topics/http/urls/
router = DefaultRouter()

urlpatterns = [
    path('redirecturl/', get_redirect_url),
    path('accesstoken/', get_access_token),
    path('saveoption/', save_option),
    path('searchsymbol/', search_symbol),
    path('option/', get_option),
    path('fullquotes/', get_full_quotes)
]

urlpatterns += router.urls
