from rest_framework.decorators import api_view
from rest_framework.views import Response
from upstox_api.api import Session, Upstox
import json
import itertools as it
from app.models import Instrument
from datetime import datetime
import calendar
from dateutil import relativedelta

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
redirect_uri = 'https://www.explainoid.com/home'
secret_key = 'pqmnwsq8ja'
master_contract_FO = 'NSE_FO'
master_contract_EQ = 'NSE_EQ'

@api_view()
def get_redirect_url(request):
    session = Session(api_key)
    session.set_redirect_uri(redirect_uri)
    session.set_api_secret(secret_key)
    return Response({"url": session.get_login_url()})


@api_view(['POST'])
def get_access_token(request):
    request_code = json.dumps(request.data)
    request_code_data = json.loads(request_code)
    session = Session(api_key)
    session.set_redirect_uri(redirect_uri)
    session.set_api_secret(secret_key)
    session.set_code(request_code_data['requestcode'])
    access_token = session.retrieve_access_token()
    return Response({"accessToken": access_token})

@api_view(['POST'])
def search_symbol(request):
    post_request = json.dumps(request.data)
    post_request_data = json.loads(post_request)
    upstox = Upstox(api_key, post_request_data['accessToken'])
    def obj_dict(obj):
        return obj.__dict__
    search_list = upstox.search_instruments(master_contract_FO, post_request_data['searchSymbol'])
    search_list_dump = json.dumps(search_list, default=obj_dict)
    search_list_load = json.loads(search_list_dump)
    return Response({"search": search_list_load})


@api_view(['POST'])
def get_master_contract(request):
    symbol = 'reliance'
    def create_session():
        access_token = json.dumps(request.data)
        access_token_data = json.loads(access_token)
        upstox = Upstox(api_key, access_token_data['accessToken'])
        return upstox
    def search_options():    
        upstox = create_session()
        upstox.get_master_contract(master_contract_FO)
        option_search = upstox.search_instruments(master_contract_FO, symbol)
        return option_search
    def search_equity():
        upstox = create_session()
        upstox.get_master_contract(master_contract_EQ)
        equity = upstox.get_instrument_by_symbol(master_contract_EQ, symbol)
        stock = Instrument(
                    equity[0], equity[1], equity[2], equity[3], equity[4],
                    equity[5], equity[6], equity[7], equity[8], equity[9],
                    equity[10], equity[11]
                )
        return stock
    def list_options():       
        #Get First and Last Day of the Current Month/Week
        def get_first_date():
            today = datetime.now().today() + relativedelta.relativedelta(weeks=1)
            first_day_date = datetime(today.year, today.month, 1).timestamp() * 1000
            return first_day_date
        def get_last_date():
            today = datetime.now().today() + relativedelta.relativedelta(weeks=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            last_day_date = datetime(today.year, today.month, last_day).timestamp() * 1000
            return last_day_date
        #Creating Python Objects of all options 
        all_options = []
        for ops in search_options():
            expiry = int(ops[6])
            if expiry >= get_first_date() and expiry <= get_last_date():
                all_options.append(Instrument(
                    ops[0], ops[1], ops[2], ops[3], ops[4],
                    ops[5], ops[6], ops[7], ops[8], ops[9],
                    ops[10], ops[11]
                ))
        return all_options
    #saperating calls and puts
    def pairing():
        option_pairs = []
        for a, b in it.combinations(list_options(), 2):
            if (a.strike_price == b.strike_price):           
                option_pair = (a, b)
                option_pairs.append(option_pair)
        return option_pairs
    #convert into Json format
    def obj_dict(obj):
        return obj.__dict__
    def stock_to_json():
        stock_dump = json.dumps(search_equity(), default=obj_dict)
        stock_load = json.loads(stock_dump)
        return stock_load
    def option_to_json():
        options_dump = json.dumps(pairing(), default=obj_dict)
        options_load = json.loads(options_dump)
        return options_load
    return Response({
        "Stock": stock_to_json(),
        "Options": option_to_json()
    })

