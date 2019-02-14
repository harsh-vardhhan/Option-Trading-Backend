from rest_framework.decorators import api_view
from rest_framework.views import Response


@api_view()
def sayhello(request):
    return Response({"Hey": "hello"})
