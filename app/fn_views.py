from rest_framework.decorators import api_view
from rest_framework.views import Response
from upstox_api.api import Session, Upstox, LiveFeedType
import json
import itertools as it
from app.models import Instrument, Full_Quote
from datetime import datetime
import calendar
from dateutil import relativedelta
from time import sleep
from rq import Queue
from worker import conn
from app.background_process import full_quotes_queue
from django.db import connection
import requests
import ast
import os
import redis

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
redirect_uri = 'https://www.explainoid.com/home'
secret_key = 'pqmnwsq8ja'
master_contract_FO = 'NSE_FO'
master_contract_EQ = 'NSE_EQ'
symbol = 'RELIANCE'

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
    try:
        session = Session(api_key)
        session.set_redirect_uri(redirect_uri)
        session.set_api_secret(secret_key)
        session.set_code(request_code_data['requestcode'])
        access_token = session.retrieve_access_token()
    except:
        print("*********token error*******")
    return Response({"accessToken": access_token})

@api_view(['POST'])
def search_symbol(request):
    post_request = json.dumps(request.data)
    post_request_data = json.loads(post_request)
    upstox = Upstox(api_key, post_request_data['accessToken'])
    def obj_dict(obj):
        return obj.__dict__
    upstox.get_master_contract(master_contract_FO)
    search_list = upstox.search_instruments(
        master_contract_FO,
        post_request_data['searchSymbol'])
    search_list_dump = json.dumps(search_list, default=obj_dict)
    search_list_load = json.loads(search_list_dump)
    return Response({"search": search_list_load})

# change the enitre function into a one time event saved to PostgreSQL
@api_view(['POST'])
def save_option(request):
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
    def list_options():
        # Get First and Last Day of the Current Month/Week
        def get_first_date():
            today = datetime.now().today() + relativedelta.relativedelta(weeks=1)
            first_day_date = datetime(today.year, today.month, 1).timestamp() * 1000
            return first_day_date
        def get_last_date():
            today = datetime.now().today() + relativedelta.relativedelta(weeks=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            last_day_date = datetime(today.year, today.month, last_day).timestamp() * 1000
            return last_day_date
        # Creating Python Objects of all options
        all_options = []
        Instrument.objects.all().delete()
        for ops in search_options():
            expiry = int(ops[6])
            exchange_val = ops[0]
            token_val = ops[1]
            parent_token_val = ops[2]
            symbol_val = ops[3]
            name_val = ops[4]
            closing_price_val = ops[5]
            expiry_val = ops[6]
            strike_price_val = ops[7]
            tick_size_val = ops[8]
            lot_size_val = ops[9]
            instrument_type_val = ops[10]
            isin_val = ops[11]
            if strike_price_val != None:
                if expiry >= get_first_date() and expiry <= get_last_date():
                    if ops[5] is None:
                            closing_price_val = ''
                    if ops[11] is None:
                            isin_val = ''
                    if ops[7] is None:
                            strike_price_val = ''
                    Instrument(
                        exchange = exchange_val, 
                        token = token_val,
                        parent_token = parent_token_val, 
                        symbol = symbol_val, 
                        name = name_val,
                        closing_price = closing_price_val,
                        expiry = expiry_val,
                        strike_price = float(strike_price_val), 
                        tick_size = tick_size_val, 
                        lot_size = lot_size_val,
                        instrument_type = instrument_type_val, 
                        isin = isin_val
                    ).save()
                    all_options.append(Instrument(
                        ops[0], ops[1], ops[2], ops[3], ops[4],
                        ops[5], ops[6], ops[7], ops[8], ops[9],
                        ops[10], ops[11]
                    ))
        return all_options
    list_options()
    return Response({"Message": "Options Saved"})

# separate chaining into different function
@api_view(['POST'])
def get_option(request):
    list_options = Instrument.objects.all()
    def create_session():
        access_token = json.dumps(request.data)
        access_token_data = json.loads(access_token)
        upstox = Upstox(api_key, access_token_data['accessToken'])
        return upstox
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
    # saperating calls and puts
    # Saperate Full Quotes
    def pairing():
        option_pairs = []
        for a, b in it.combinations(list_options, 2):
            if (a.strike_price == b.strike_price):
                option_pair = (a, b)
                option_pairs.append(option_pair)
        return option_pairs
    # convert into Json format
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

def save_full_quotes_task(accessToken):
    r.flushall()
    list_options = Instrument.objects.all()
    q = Queue(connection=conn)
    def create_session(accessToken):
        upstox = Upstox(api_key, accessToken)
        return upstox  
    upstox = create_session(accessToken)
    upstox.get_master_contract(master_contract_FO)
    for ops in list_options:
        option = q.enqueue(full_quotes_queue, accessToken, ops.symbol)


@api_view(['POST'])
def save_full_quotes(request):
    access_token = json.dumps(request.data)
    access_token_data = json.loads(access_token)
    Full_Quote.objects.all().delete()
    save_full_quotes_task(access_token_data['accessToken'])
    return Response({"Message": "Quotes Saved"})

@api_view(['POST'])
def get_full_quotes(request): 
    def create_session(request):
        access_token = json.dumps(request.data)
        access_token_data = json.loads(access_token)
        upstox = Upstox(api_key, access_token_data['accessToken'])
        return upstox         
    def search_equity():
        upstox.get_master_contract(master_contract_EQ)
        equity = upstox.get_live_feed(upstox.get_instrument_by_symbol(
            master_contract_EQ, symbol),
            LiveFeedType.Full)
        equity_data = json.loads(json.dumps(equity))
        stock = Instrument(
            equity_data['exchange'],
            "",
            "",
            equity_data['symbol'],
            "",
            equity_data['ltp'],
            "",
            0.0,
            "",
            "",
            "",
            ""
        )
        return stock
    upstox = create_session(request)
    list_option = Instrument.objects.all()
    Full_Quote.objects.all().delete()
    for ops in list_option:
        val = r.get(ops.symbol).decode("utf-8")
        optionData = ast.literal_eval(val)
        Full_Quote(
            strike_price = ops.strike_price,
            exchange = optionData['exchange'],
            symbol = optionData['symbol'],
            ltp = optionData['ltp'],
            close = optionData['close'],
            open = optionData['open'],
            high = optionData['high'],
            low = optionData['low'],
            vtt = optionData['vtt'],
            atp = optionData['atp'],
            oi = optionData['oi'],
            spot_price = optionData['spot_price'],
            total_buy_qty = optionData['total_buy_qty'],
            total_sell_qty = optionData['total_sell_qty'],
            lower_circuit = optionData['lower_circuit'],
            upper_circuit = optionData['upper_circuit'],
            yearly_low = optionData['yearly_low'],
            yearly_high = optionData['yearly_high'],
            ltt = optionData['ltt']
        ).save()
    connection.close()
    list_options = Full_Quote.objects.all().order_by('strike_price')
    def pairing():
        option_pairs = []
        for a, b in it.combinations(list_options, 2):
            if (a.strike_price == b.strike_price):
                if (a.oi > 0.0 and b.oi > 0.0):
                    if (a.symbol[-2:] == 'CE'):
                        option_pair = (a, b, a.strike_price)
                        option_pairs.append(option_pair)
                    else:
                        option_pair = (b, a, a.strike_price)
                        option_pairs.append(option_pair)
        connection.close()
        return option_pairs
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
