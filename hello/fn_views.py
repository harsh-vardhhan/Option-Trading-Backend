from rest_framework.decorators import api_view
from rest_framework.views import Response
from upstox_api.api import Session
import json


@api_view()
def getRedirectUrl(request):
    s = Session('Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx')
    s.set_redirect_uri('https://trakbit.com/')
    s.set_api_secret('pqmnwsq8ja')
    return Response({"url": s.get_login_url()})


@api_view(['POST'])
def getAccessToken(request):
    requestcode = json.dumps(request.data)
    requestcodedata = json.loads(requestcode)
    api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
    s = Session(api_key)
    s.set_redirect_uri('https://trakbit.com/')
    s.set_api_secret('pqmnwsq8ja')
    s.set_code(requestcodedata['requestcode'])
    access_token = s.retrieve_access_token()
    return Response({"accessToken": access_token})
