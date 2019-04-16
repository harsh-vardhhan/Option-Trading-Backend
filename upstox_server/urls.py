from django.urls import path
from rest_framework.routers import DefaultRouter
from app.fn_views import get_redirect_url, get_access_token, get_master_contract, search_symbol

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
    path('mastercontract/', get_master_contract),
    path('searchsymbol/', search_symbol),
]

urlpatterns += router.urls
