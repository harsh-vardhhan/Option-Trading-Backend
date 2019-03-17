from rest_framework import routers
from django.conf.urls import url
from app.fn_views import get_redirect_url, get_access_token, get_master_contract

# To add a new path, first import the app:
# import blog
#
# Then add the new path:
# path('blog/', blog.urls, name="blog")
#
# Learn more here: https://docs.djangoproject.com/en/2.1/topics/http/urls/
router = routers.DefaultRouter()
urlpatterns = [
    url("redirecturl/", get_redirect_url),
    url("accesstoken/", get_access_token),
    url("mastercontract/", get_master_contract)
]

urlpatterns += router.urls
