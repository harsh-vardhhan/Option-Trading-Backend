from rest_framework.decorators import api_view
from rest_framework.views import Response
from upstox_api.api import Session, Upstox, LiveFeedType, OHLCInterval
import json
import itertools as it
from app.models import Instrument, Full_Quote, Expiry_Date
from datetime import datetime, date, timedelta
import calendar
from dateutil import relativedelta
from time import sleep
import redis
from rq import Queue
from rq_scheduler import Scheduler
from worker import conn
from app.background_process import full_quotes_queue
from statistics import stdev
from django.db import connection
import requests
import ast
import os
from math import sqrt
from app.background_process import cal_iv_queue

''' 
_strike_price : Instrument Options -> To fetch option strikes
_ : Full Quotes Options
_c : Calcuates Options
'''

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
redirect_uri = 'https://www.explainoid.com/home'
secret_key = 'pqmnwsq8ja'
master_contract_FO = 'NSE_FO'
master_contract_EQ = 'NSE_EQ'
nse_index = 'NSE_INDEX'
niftyit = 'niftyit'
symbols = ['NIFTY','BANKNIFTY']


@api_view()
def get_redirect_url(request):
    session = Session(api_key)
    session.set_redirect_uri(redirect_uri)
    session.set_api_secret(secret_key)
    return Response({"url": session.get_login_url()})


@api_view(['POST'])
def get_access_token(request):
    request_data = json.loads(json.dumps(request.data))
    session = Session(api_key)
    session.set_redirect_uri(redirect_uri)
    session.set_api_secret(secret_key)
    session.set_code(request_data['requestcode'])
    access_token = session.retrieve_access_token()
    u = Upstox (api_key, access_token)
    user_profile = u.get_profile()
    print(user_profile.client_id)
    return Response({"accessToken": access_token})

@api_view(['POST'])
def get_access_token_admin(request):
    request_data = json.loads(json.dumps(request.data))
    session = Session(api_key)
    session.set_redirect_uri(redirect_uri)
    session.set_api_secret(secret_key)

    
    session.set_code(request_data['requestcode'])
    access_token = session.retrieve_access_token()
    r.set("access_token", access_token)
    return Response({"accessToken": access_token})



@api_view(['POST'])
def historical_option(request):
    request_data = json.loads(json.dumps(request.data))
    access_token = request_data['accessToken']
    def create_session(request):
        upstox = Upstox(api_key, access_token)
        return upstox
    def fetch_option():
        upstox = create_session(request)
        upstox.get_master_contract(nse_index)
        historical =  upstox.get_ohlc(
            upstox.get_instrument_by_symbol(nse_index, 'NIFTY_50'), 
            OHLCInterval.Day_1, datetime.strptime('06/06/2018', '%d/%m/%Y').date(), 
            datetime.strptime('06/06/2019', '%d/%m/%Y').date()
        )
        historical_array = []
        for ops in historical:
             symbol = json.loads(json.dumps(ops))
             date = (datetime.fromtimestamp(int(symbol['timestamp'])/1000))
             closing = symbol['close']
             option_data = (date, closing)
             historical_array.append(option_data)
        return historical_array
    def historic_sigma():
        option_list = fetch_option()
        ltp_changes = []
        old_close = 0.0
        for idx, ops in enumerate(option_list):
            if(idx > 0):
                ltp_change_val = (float(ops[1])/float(old_close)) - 1.0
                ltp_changes.append(ltp_change_val)
            old_close = ops[1]
        historic_sigma = stdev(ltp_changes)* sqrt(252) * 100
    ltp_change()
    return Response({"historical": (fetch_option())})

 
# change the enitre function into a one time event saved to PostgreSQL
@api_view(['POST'])
def save_option(request):
    store_dates()
    def create_session():
        request_data = json.loads(json.dumps(request.data))
        upstox = Upstox(api_key, request_data['accessToken'])
        return upstox
    def search_options(symbol):
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
        for symbol in symbols:
            for ops in search_options(symbol):          
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
                    if closing_price_val != None:
                        # Avoid NIFTYIT since searching for 
                        # NIFTY and BANKNIFTY alongs brings
                        # along this and it lacks liquidity
                        if symbol_val[:7] != niftyit:
                            def save_option_db(expiry,
                                                exchange_val,
                                                token_val,
                                                parent_token_val,
                                                symbol_val,
                                                name_val,
                                                closing_price_val,
                                                expiry_val,
                                                strike_price_val,
                                                tick_size_val,
                                                lot_size_val,
                                                instrument_type_val,
                                                isin_val):
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
                                    r.set(symbol_val+"_strike_price", float(strike_price_val))
                                    #r.set(instrument.symbol, instrument)
                                    all_options.append(Instrument(
                                        ops[0], ops[1], ops[2], ops[3], ops[4],
                                        ops[5], ops[6], ops[7], ops[8], ops[9],
                                        ops[10], ops[11]
                                    ))
                            if symbol == "NIFTY":
                                symbol_len = len(symbol)
                                symbol_cache = symbol_val[:symbol_len]
                                if symbol == symbol_cache.upper():
                                    save_option_db(expiry,
                                                    exchange_val,
                                                    token_val,
                                                    parent_token_val,
                                                    symbol_val,
                                                    name_val,
                                                    closing_price_val,
                                                    expiry_val,
                                                    strike_price_val,
                                                    tick_size_val,
                                                    lot_size_val,
                                                    instrument_type_val,
                                                    isin_val)
                            else:
                                save_option_db(expiry,
                                                exchange_val,
                                                token_val,
                                                parent_token_val,
                                                symbol_val,
                                                name_val,
                                                closing_price_val,
                                                expiry_val,
                                                strike_price_val,
                                                tick_size_val,
                                                lot_size_val,
                                                instrument_type_val,
                                                isin_val)
        return all_options
    list_options()
    return Response({"Message": "Options Saved"})


# Step 1: Fetch all the  Full Quotes and cache it in redis
# NOTE - This is a time consuming process there instruments
# passed through this should be filtred. 
@api_view(['POST'])
def cache_full_quotes_redis(request):
    store_dates()
    request_data = json.loads(json.dumps(request.data))
    access_token = request_data['accessToken']
    list_options = Instrument.objects.all()
    q = Queue(connection=conn)
    def create_session(accessToken):
        upstox = Upstox(api_key, access_token)
        return upstox
    upstox = create_session(access_token)
    upstox.get_master_contract(master_contract_FO)
    # symbol = request_data['symbol']
    for symbol in symbols:
        symbol_len = len(symbol)
        for ops in list_options:
            # This has been done to differentiate between NIFTY and BANKNIFTY
            symbol_fetched = ops.symbol[:symbol_len]
            if (symbol_fetched.upper() == symbol):
                # This is to fetch Monthly Options only
                trim_symbol = ops.symbol[symbol_len:]
                expiry_dates = list(Expiry_Date.objects.all())
                for expiry_dated in expiry_dates:
                    expiry_date_fetched = trim_symbol[:len(expiry_dated.upstox_date)]
                    if(expiry_date_fetched.upper() == expiry_dated.upstox_date):
                        q.enqueue(full_quotes_queue, access_token, ops.symbol)
    return Response({"Message": "Quotes Saved"}) 

# Step 2: From redis move all the Quotes to database
# NOTE: This Function should now run only after hours
# to prefilling of redis before websocket starts.
@api_view(['POST'])
def save_full_quotes_db(request):
    request_data = json.loads(json.dumps(request.data))
    # create_session method exclusively while developing in online mode
    def create_session():
        upstox = Upstox(api_key, request_data['accessToken'])
        return upstox
    list_option = Instrument.objects.all()
    Full_Quote.objects.all().delete()
    for symbol in symbols:
        for ops in list_option:
            # This has been done to differentiate between NIFTY and BANKNIFTY
            symbol_len = len(symbol)
            symbol_cache = ops.symbol[:symbol_len]
            if(symbol_cache.upper() == symbol):
                # This is to fetch Monthly Options only
                trim_symbol = ops.symbol[symbol_len:]
                expiry_dates = list(Expiry_Date.objects.all())
                for expiry_date in expiry_dates:
                    symbol_date = trim_symbol[:len(expiry_date.upstox_date)]
                    if (symbol_date.upper() == expiry_date.upstox_date):
                        symbol_key = r.get(ops.symbol)
                        if (symbol_key != None):                         
                            val = symbol_key.decode("utf-8")
                            option = ast.literal_eval(val)
                            Full_Quote(
                                strike_price = ops.strike_price,
                                exchange = option['exchange'],
                                symbol = option['symbol'],
                                ltp = option['ltp'],
                                close = option['close'],
                                open = option['open'],
                                high = option['high'],
                                low = option['low'],
                                vtt = option['vtt'],
                                atp = option['atp'],
                                oi = option['oi'],
                                spot_price = option['spot_price'],
                                total_buy_qty = option['total_buy_qty'],
                                total_sell_qty = option['total_sell_qty'],
                                lower_circuit = option['lower_circuit'],
                                upper_circuit = option['upper_circuit'],
                                yearly_low = option['yearly_low'],
                                yearly_high = option['yearly_high'],
                                ltt = option['ltt']
                            ).save()
    connection.close()
    return Response({"Message": "Full Quotes Saved"})

# First Fetches a value from redis
# if not available put's an 
# alternative value from database
# TODO Schedule this function
# TODO Perform IV Calculations here
def get_full_quotes_cache(request, symbol_req, expiry_date_req):
    request_data = json.loads(json.dumps(request.data))
    # create_session method exclusively while developing in online mode
    def create_session():
        upstox = Upstox(api_key, request_data['accessToken'])
        return upstox
    searched_symbol = symbol_req + expiry_date_req
    list_option = Full_Quote.objects\
                            .all()\
                            .filter(symbol__startswith = searched_symbol)\
                            .order_by('strike_price')
    full_quotes = []
    for symbol in symbols:
        for ops in list_option:
            # This has been done to differentiate between NIFTY and BANKNIFTY
            symbol_len = len(symbol)
            symbol_cache = ops.symbol[:symbol_len]
            if(symbol_cache.upper() == symbol):
                # This is to fetch Monthly Options only
                trim_symbol = ops.symbol[symbol_len:]
                expiry_dates = list(Expiry_Date.objects.all())
                for expiry_date in expiry_dates:
                    symbol_date = trim_symbol[:len(expiry_date.upstox_date)]
                    if (symbol_date.upper() == expiry_date.upstox_date):
                        lowercase_symbol = ops.symbol
                        symbol_key = r.get(lowercase_symbol.upper())
                        if (symbol_key != None):
                            symbol_decoded = symbol_key.decode("utf-8")
                            val = symbol_key.decode("utf-8")
                            option = ast.literal_eval(val)
                            full_quote_obj = Full_Quote(
                                strike_price = ops.strike_price,
                                exchange = option['exchange'],
                                symbol = option['symbol'],
                                ltp = option['ltp'],
                                close = option['close'],
                                open = option['open'],
                                high = option['high'],
                                low = option['low'],
                                vtt = option['vtt'],
                                atp = option['atp'],
                                oi = option['oi'],
                                spot_price = option['spot_price'],
                                total_buy_qty = option['total_buy_qty'],
                                total_sell_qty = option['total_sell_qty'],
                                lower_circuit = option['lower_circuit'],
                                upper_circuit = option['upper_circuit'],
                                yearly_low = option['yearly_low'],
                                yearly_high = option['yearly_high'],
                                ltt = option['ltt']
                            )
                            full_quotes.append(full_quote_obj)
                        else:
                            full_quote_obj = Full_Quote(
                                strike_price = ops.strike_price,
                                exchange =  ops.exchange,
                                symbol =  ops.symbol,
                                ltp =  ops.ltp,
                                close =  ops.close,
                                open =  ops.open,
                                high =  ops.high,
                                low =  ops.low,
                                vtt =  ops.vtt,
                                atp =  ops.atp,
                                oi =  ops.oi,
                                spot_price =  ops.spot_price,
                                total_buy_qty =  ops.total_buy_qty,
                                total_sell_qty =  ops.total_sell_qty,
                                lower_circuit =  ops.lower_circuit,
                                upper_circuit =  ops.upper_circuit,
                                yearly_low =  ops.yearly_low,
                                yearly_high = ops.yearly_high,
                                ltt =  ops.ltt,
                            )
                            full_quotes.append(full_quote_obj)
    connection.close()
    return full_quotes



@api_view(['POST'])
def validate_token(request):
    access_token = json.dumps(request.data)
    access_token_data = json.loads(access_token)
    try:
        upstox = Upstox(api_key, access_token_data['accessToken'])
        return Response({"status": 1})
    except:
        return Response({"status": 0})


def store_dates():
    Expiry_Date.objects.all().delete()
    Expiry_Date(
        upstox_date = "19JUN",
        expiry_date = str(date(2019, 6, 27)),
        label_date = "27 JUNE (Monthly)",
        future_date = "19JUN"
    ).save()
    connection.close()

@api_view(['POST'])
def get_full_quotes(request):
    def obj_dict(obj):
        return obj.__dict__
    def toJson(func):
        return json.loads(json.dumps(func, default=obj_dict))
    store_dates()
    request_data = json.loads(json.dumps(request.data))
    access_token = request_data['accessToken']
    indices = request_data['indices']
    symbol = request_data['symbol']
    expiry_date = request_data['expiry_date']
    days_to_expiry = 0
    dates = list(Expiry_Date.objects.all())
    connection.close()
    if expiry_date == "0":
        expiry_date = dates[0].upstox_date
        d1 = date.today()
        expiry_date_string = dates[0].expiry_date
        d2 = datetime.strptime(expiry_date_string, '%Y-%m-%d').date()
        d = d2 - d1
        days_to_expiry = d.days
    else:
        expiry_date_list = list(Expiry_Date\
                                    .objects\
                                    .all()\
                                    .filter(upstox_date=expiry_date))
        connection.close()
        d1 = date.today()
        expiry_date_string = expiry_date_list[0].expiry_date
        d2 = datetime.strptime(expiry_date_string, '%Y-%m-%d').date()
        d = d2 - d1
        days_to_expiry = d.days
    def create_session(request):
        upstox = Upstox(api_key, access_token)
        return upstox
    def search_equity():
        upstox = create_session(request)
        upstox.get_master_contract(nse_index)
        equity = upstox.get_live_feed(upstox.get_instrument_by_symbol(
            nse_index, indices),
            LiveFeedType.Full)
        equity_data = json.loads(json.dumps(equity))
        stock = Instrument(
            equity_data['exchange'], "", "", 
            equity_data['symbol'], "", 
            equity_data['ltp'], "", 0.0, "", "", "", ""
        )
        return stock
    def search_future():
        upstox = create_session(request)
        upstox.get_master_contract(master_contract_FO)
        list_options = list(Expiry_Date
                            .objects\
                            .all()\
                            .filter(upstox_date=expiry_date))
        connection.close()
        future = upstox.get_live_feed(upstox.get_instrument_by_symbol(
            master_contract_FO, symbol+list_options[0].future_date+'FUT'),
            LiveFeedType.Full)
        future_data =  json.loads(json.dumps(future))
        future_stock = Full_Quote(
            strike_price = 0,
            exchange = future_data['exchange'],
            symbol = future_data['symbol'],
            ltp = future_data['ltp'],
            close = future_data['close'],
            open = future_data['open'],
            high = future_data['high'],
            low = future_data['low'],
            vtt = future_data['vtt'],
            atp = future_data['atp'],
            oi = future_data['oi'],
            spot_price = future_data['spot_price'],
            total_buy_qty = future_data['total_buy_qty'],
            total_sell_qty = future_data['total_sell_qty'],
            lower_circuit = future_data['lower_circuit'],
            upper_circuit = future_data['upper_circuit'],
            yearly_low = future_data['yearly_low'],
            yearly_high = future_data['yearly_high'],
            ltt = future_data['ltt']
        )
        return future_stock
    def pairing():
        q = Queue(connection=conn)
        list_options = get_full_quotes_cache(request, symbol, expiry_date)
        def to_lakh(n):
            return float(round(n/100000, 1))
        option_pairs = []
        closest_strike = 10000000
        closest_option = ""
        equity = search_equity()
        call_OI = 0.0
        put_OI = 0.0
        iv = 0.0
        future = search_future()
        for a, b in it.combinations(list_options, 2):
            if (a.strike_price == b.strike_price):
                # filter strikes to 100 multiples
                if(a.strike_price % 100 == 0):
                    # remove strikes which are less than ₹ 10,000 
                    if (to_lakh(a.oi) > 0.0 and to_lakh(b.oi) > 0.0):
                        # arrange option pair always in CE and PE order
                        diff = abs(float(equity.name) - float(a.strike_price))
                        call_OI = call_OI + to_lakh(a.oi)
                        put_OI = put_OI + to_lakh(b.oi)       
 
                        if(diff < closest_strike):
                            closest_strike = diff
                            closest_option = a
                        if (a.symbol[-2:] == 'CE'):
                            if ( a.strike_price > equity.name):
                                q.enqueue(
                                    cal_iv_queue, 
                                    a.symbol, 
                                    future.ltp, 
                                    a.strike_price, 
                                    days_to_expiry/365,
                                    float(a.ltp), 
                                    0.1, 
                                    type="call"
                                )
                                new_iv = r.get(a.symbol+"_iv") 
                                if (new_iv != None):
                                    val = new_iv.decode("utf-8")
                                    iv = ast.literal_eval(val)
                            else:
                                q.enqueue(
                                    cal_iv_queue, 
                                    b.symbol, 
                                    future.ltp, 
                                    b.strike_price, 
                                    days_to_expiry/365,
                                    float(b.ltp), 
                                    0.1, 
                                    type="put"
                                )
                                new_iv = r.get(b.symbol+"_iv") 
                                if (new_iv != None):
                                    val = new_iv.decode("utf-8")
                                    iv = ast.literal_eval(val)

                            option_pair = (a, b, a.strike_price, iv)
                            option_pairs.append(option_pair)
                        else:
                            if (b.strike_price > equity.name):
                                q.enqueue(
                                    cal_iv_queue, 
                                    b.symbol, 
                                    future.ltp, 
                                    b.strike_price, 
                                    days_to_expiry/365,
                                    float(b.ltp), 
                                    0.1, 
                                    type="call"
                                )
                                new_iv = r.get(b.symbol+"_iv") 
                                if (new_iv != None):
                                    val = new_iv.decode("utf-8")
                                    iv = ast.literal_eval(val)
                            else:
                                q.enqueue(
                                    cal_iv_queue, 
                                    a.symbol, 
                                    future.ltp, 
                                    a.strike_price, 
                                    days_to_expiry/365,
                                    float(a.ltp), 
                                    0.1, 
                                    type="put"
                                )
                                new_iv = r.get(a.symbol+"_iv") 
                                if (new_iv != None):
                                    val = new_iv.decode("utf-8")
                                    iv = ast.literal_eval(val)

                            option_pair = (b, a, a.strike_price, iv)
                            option_pairs.append(option_pair)
        if call_OI == 0.0:
            call_OI = 1.0                
        pcr = round(put_OI/call_OI, 2)
        connection.close()
        return option_pairs, closest_option, pcr
    option_pairs, closest_option, pcr = pairing()
    def lot_size(symbol):
        if (symbol == "NIFTY"):
            return 75
        elif ("BANKNIFTY"):
            return 20
    return Response({
        "stock": toJson(search_equity()),
        "options": toJson(option_pairs),
        "symbol": symbol,
        "closest_strike" : toJson(closest_option),
        "future": toJson(search_future()),
        "lot_size": toJson(lot_size(symbol)),
        "days_to_expiry": days_to_expiry,
        "expiry_dates": toJson(dates),
        "expiry_date": expiry_date,
        "pcr": pcr
    })
