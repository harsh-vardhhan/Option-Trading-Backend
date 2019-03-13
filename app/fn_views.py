from rest_framework.decorators import api_view
from rest_framework.views import Response
from upstox_api.api import Session, Upstox
import json
import itertools as it
from app.models import Option
from datetime import datetime
import calendar
from dateutil import relativedelta

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
redirect_uri = 'https://www.explainoid.com/home'

@api_view()
def getRedirectUrl(request):
    s = Session('Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx')
    s.set_redirect_uri(redirect_uri)
    s.set_api_secret('pqmnwsq8ja')
    return Response({"url": s.get_login_url()})


@api_view(['POST'])
def getAccessToken(request):
    requestCode = json.dumps(request.data)
    requestCodeData = json.loads(requestCode)
    s = Session(api_key)
    s.set_redirect_uri(redirect_uri)
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
    optionSearch = upstox.search_instruments('NSE_FO', 'reliance')
    #Get First and Last Day of the Current Month/Week
    today = datetime.now().today() + relativedelta.relativedelta(weeks=1)
    first_day_date = datetime(today.year, today.month, 1).timestamp() * 1000
    last_day = calendar.monthrange(today.year, today.month)[1]
    last_day_date = datetime(today.year, today.month, last_day).timestamp() * 1000
    #Creating Python Objects of all options
    allOptions = []
    for ops in optionSearch:
        expiry = int(ops[6])
        if expiry >= first_day_date and expiry <= last_day_date:
            allOptions.append(Option(
                ops[0], ops[1], ops[2], ops[3], ops[4],
                ops[5], ops[6], ops[7], ops[8], ops[9],
                ops[10], ops[11]
            ))
    #saperating calls and puts
    optionPairs = []
    for a, b in it.combinations(allOptions, 2):
        if (a.strike_price == b.strike_price):           
            optionPair = (a, b)
            optionPairs.append(optionPair)
    #convert into Json format
    def obj_dict(obj):
        return obj.__dict__
    options_dump = json.dumps(optionPairs, default=obj_dict)
    options_load = json.loads(options_dump)
    return Response({
        "Options": options_load
    })
