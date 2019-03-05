from rest_framework.decorators import api_view
from rest_framework.views import Response
from upstox_api.api import Session, Upstox
import json

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'


@api_view()
def getRedirectUrl(request):
    s = Session('Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx')
    s.set_redirect_uri('https://trakbit.com/')
    s.set_api_secret('pqmnwsq8ja')
    return Response({"url": s.get_login_url()})


@api_view(['POST'])
def getAccessToken(request):
    requestCode = json.dumps(request.data)
    requestCodeData = json.loads(requestCode)
    s = Session(api_key)
    s.set_redirect_uri('https://trakbit.com/')
    s.set_api_secret('pqmnwsq8ja')
    s.set_code(requestCodeData['requestcode'])
    access_token = s.retrieve_access_token()
    return Response({"accessToken": access_token})


@api_view(['POST'])
def getMasterContract(request):
    accessToken = json.dumps(request.data)
    accessTokenData = json.loads(accessToken)
    upstox = Upstox(api_key, accessTokenData['accessToken'])
    upstox.get_master_contract('NSE_FO')
    optionSearch = upstox.search_instruments('NSE_FO', 'reliance19may')
    option = optionSearch[0]
    strikePrice = option[7]
    return Response({"NSE_FO": optionSearch})
