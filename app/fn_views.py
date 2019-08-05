from rest_framework.decorators import api_view
from rest_framework.views import Response
from upstox_api.api import Session, Upstox
import json
import itertools as it
from app.models import Instrument, Full_Quote, Expiry_Date
from datetime import datetime, date
import calendar
from dateutil import relativedelta
import redis
from rq import Queue
from worker import conn
from app.background_process import full_quotes_queue
from django.db import connection
import ast
import os
from app.consumers import start_subscription, start_update_option
from ctypes import cdll
from ctypes import c_float, c_int


'''
s_   : Instrument Options -> To fetch option strikes
_    : Full Quotes Options
c_   : Calcuates Options
sub_ : Subscribed Options
g_   : Gamma of option
v_   : Vega of option
dc_  : Delta Call of option
tc_  : Theta Call of option
dp_  : Delta Put of option
tp_  : Theta Put of option
ls_  : Lot Size
pp_  : Projected Profit
pps_ : Projected Profit at Buy and Sell strikes
'''

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)


api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
redirect_uri = 'https://www.trakbit.com/home'
secret_key = 'pqmnwsq8ja'
client_id = "245842"
master_contract_FO = 'NSE_FO'
master_contract_EQ = 'NSE_EQ'
nse_index = 'NSE_INDEX'
niftyit = 'niftyit'
symbols = ['NIFTY', 'BANKNIFTY']

# premium_lib = cdll.LoadLibrary("app/premium.so")

premium_lib = cdll.LoadLibrary(os.path.abspath("app/premium.so"))
# r.flushall()
# r.set("access_token", "5a545712a2406c77e87ac2da799248baad2c11f7")


def save_lot_size():
    r.set("ls_NIFTY", 75)
    r.set("ls_BANKNIFTY", 25)


save_lot_size()

# TODO test in with live data
@api_view()
def live_feed(request):
    def event_handler_quote_update(message):
        print("Quote Update: %s" % str(message))

    u = Upstox(api_key, r.get("access_token").decode("utf-8"))
    u.set_on_quote_update(event_handler_quote_update)
    u.start_websocket(True)
    return Response({"Socket": "Started"})


@api_view()
def subscribe_quotes(request):
    start_subscription()
    return Response({"Subcription": "Started"})


@api_view()
def update_option(request):
    start_update_option()
    return Response({"Update": "Started"})


@api_view()
def get_redirect_url(request):
    session = Session(api_key)
    session.set_redirect_uri(redirect_uri)
    session.set_api_secret(secret_key)
    url = session.get_login_url()
    print(url)
    return Response({"url": url})


@api_view(['POST'])
def cal_strategy(request):
    request_data = json.loads(json.dumps(request.data))
    symbols = request_data['symbol']
    parent_symbol = request_data['parent_symbol']
    max_profit_expiry = 0
    max_loss_expiry = 0
    symbol_len = len(symbols)
    last_iteration = symbol_len - 1
    premium_paid = 0
    analysis_chart = []
    mini_analysis_chart = []
    buy_sell_strike = []
    list_option = Full_Quote.objects\
                            .all()\
                            .filter(symbol__startswith=parent_symbol)\
                            .order_by('strike_price')
    connection.close()

    option_len = len(list_option)
    last_instrument = option_len - 1
    second_last_instrument = option_len - 3
    lot_size = json.loads(r.get("ls_"+parent_symbol))

    max_profit_expiry = 0
    max_profit_numerical = 0
    max_loss_expiry = 100000000000000000000000
    max_loss_numerical = 0

    def toJson(func):
        return json.loads(json.dumps(func))

    for i, symbol in enumerate(symbols):

        second_last = 0
        last = 0
        first = 0
        second = 0

        Buy_Call = symbol[0].get("Buy")
        Sell_Call = symbol[0].get("Sell")
        Buy_Put = symbol[1].get("Buy")
        Sell_Put = symbol[1].get("Sell")
        Call_Symbol = symbol[0].get("symbol").lower()
        Put_Symbol = symbol[1].get("symbol").lower()
        Call_Symbol_Strike = symbol[0].get("symbol")[:-2]
        Put_Symbol_Strike = symbol[1].get("symbol")[:-2]

        # calculate premium for current spot price
        if(Buy_Call is not None and Buy_Call != 0
           or Sell_Call is not None and Sell_Call != 0):
            instrument = json.loads(r.get((symbol[0].get("symbol").lower())))
            premium = instrument.get('ltp')

            buy_sell_strike.append(Call_Symbol_Strike)

            # Calcualte new premium
            premium_lib.call_premium_spot.argtypes = [
                c_int, c_int, c_float, c_float]
            premium_lib.call_premium_spot.restype = c_float
            new_premium_paid = premium_lib.call_premium_spot(
                Buy_Call,
                Sell_Call,
                premium,
                lot_size)

            # Add to previous premium
            premium_lib.premium_paid.argtypes = [
                c_float, c_float]
            premium_lib.premium_paid.restype = c_float
            premium_paid = premium_lib.premium_paid(
                premium_paid,
                new_premium_paid)

        if(Buy_Put is not None and Buy_Put != 0
           or Sell_Put is not None and Sell_Put != 0):
            instrument = json.loads(r.get((symbol[1].get("symbol").lower())))
            premium = instrument.get('ltp')

            buy_sell_strike.append(Put_Symbol_Strike)

            # Calcualte new premium
            premium_lib.put_premium_spot.argtypes = [
                c_int, c_int, c_float, c_float, c_float]
            premium_lib.put_premium_spot.restype = c_float
            new_premium_paid = premium_lib.call_premium_spot(
                Buy_Put,
                Sell_Put,
                premium,
                lot_size)

            # Add to previous premium
            premium_lib.premium_paid.argtypes = [
                c_float, c_float]
            premium_lib.premium_paid.restype = c_float
            premium_paid = premium_lib.premium_paid(
                premium_paid,
                new_premium_paid)

        # treat every strike as a spot price
        for j, ops in enumerate(list_option):

            spot_price = ops.strike_price
            spot_symbol = ops.symbol
            spot_symbol_trim = spot_symbol[:-2]
            spot_symbol_type = spot_symbol[-2:]

            # enumerate & clear keys holding the returns using symbols
            # when on the first key
            if (i == 0):
                r.set("pp_"+spot_symbol_trim, 0)

            if(Buy_Call is not None and Buy_Call != 0
               or Sell_Call is not None and Sell_Call != 0):

                instrument = json.loads(r.get((Call_Symbol)))
                premium = instrument.get('ltp')
                strike_price = json.loads(r.get(("s_"+Call_Symbol)))

                # Calls
                if(spot_symbol_type == "CE"):
                    premium_lib.call_premium.argtypes = [
                        c_int, c_int, c_float, c_float, c_float, c_float]
                    premium_lib.call_premium.restype = c_float
                    max_return = premium_lib.call_premium(
                        Buy_Call,
                        Sell_Call,
                        spot_price,
                        strike_price,
                        premium,
                        lot_size)

                    if (r.get("pp_"+spot_symbol_trim) is None):
                        r.set("pp_"+spot_symbol_trim, max_return)
                    else:
                        old_max_return = json.loads(
                            r.get("pp_"+spot_symbol_trim))

                        premium_lib.new_max_return.argtypes = [
                            c_float, c_float]
                        premium_lib.new_max_return.restype = c_float
                        new_max_return = premium_lib.new_max_return(
                            max_return,
                            old_max_return)

                        r.set("pp_"+spot_symbol_trim, new_max_return)

            if(Buy_Put is not None and Buy_Put != 0
               or Sell_Put is not None and Sell_Put != 0):

                instrument = json.loads(r.get((Put_Symbol)))
                premium = instrument.get('ltp')
                strike_price = json.loads(r.get(("s_"+Put_Symbol)))

                # Puts
                if(spot_symbol_type == "PE"):
                    premium_lib.put_premium.argtypes = [
                        c_int, c_int, c_float, c_float, c_float, c_float]
                    premium_lib.put_premium.restype = c_float
                    max_return = premium_lib.put_premium(
                        Buy_Put,
                        Sell_Put,
                        spot_price,
                        strike_price,
                        premium,
                        lot_size)

                    if (r.get("pp_"+spot_symbol_trim) is None):
                        r.set("pp_"+spot_symbol_trim, max_return)
                    else:
                        old_max_return = json.loads(
                            r.get("pp_" + spot_symbol_trim))

                        premium_lib.new_max_return.argtypes = [
                            c_float, c_float]
                        premium_lib.new_max_return.restype = c_float
                        new_max_return = premium_lib.new_max_return(
                            max_return,
                            old_max_return)
                        r.set("pp_"+spot_symbol_trim, new_max_return)

            # last iteration
            if (i == last_iteration):
                max_profit = json.loads(r.get("pp_"+ops.symbol[:-2]))
                if (max_profit > max_profit_expiry):
                    max_profit_expiry = max_profit
                    max_profit_numerical = max_profit

                if (max_profit < max_loss_expiry):
                    max_loss_expiry = max_profit

                if (j == 0):
                    first = max_profit
                if (j == 1):
                    second = max_profit
                    if(first > second):
                        max_loss_expiry = "Unlimited"

                if (j == second_last_instrument):
                    second_last = max_profit
                if (j == last_instrument):
                    last = max_profit
                    if(last > second_last):
                        max_profit_expiry = "Unlimited"
                        max_profit_numerical = last
                    elif(last < second_last):
                        max_loss_expiry = "Unlimited"
                        max_loss_numerical = last
                    if(isinstance(max_profit_expiry, float)):
                        max_profit_expiry = round(max_profit_expiry, 0)
                        max_profit_numerical = round(max_profit_expiry, 0)
                    if(isinstance(max_loss_expiry, float)):
                        max_loss_numerical = round(max_loss_expiry, 0)
                        max_loss_expiry = abs(round(max_loss_expiry, 0))
                    elif(isinstance(max_loss_expiry, int)):
                        max_loss_numerical = round(max_loss_expiry, 0)
                        max_loss_expiry = abs(max_loss_expiry)

                # Mini Chart
                if(spot_symbol_type == "PE"):
                    if j == 1:
                        mini_chart = {
                            "symbol": spot_symbol_trim,
                            "strike_price": round(spot_price),
                            "profit": r.get("pp_"+spot_symbol_trim)
                                       .decode("utf-8")
                        }
                        mini_analysis_chart.append(toJson(mini_chart))
                    for strike_symbol in buy_sell_strike:
                        if (spot_symbol_trim == strike_symbol):
                            mini_chart = {
                                "symbol": spot_symbol_trim,
                                "strike_price": round(spot_price),
                                "profit": r.get("pp_"+spot_symbol_trim)
                                           .decode("utf-8")
                            }
                            mini_analysis_chart.append(toJson(mini_chart))
                    if j == last_instrument:
                        mini_chart = {
                            "symbol": spot_symbol_trim,
                            "strike_price": round(spot_price),
                            "profit": r.get("pp_"+spot_symbol_trim)
                                       .decode("utf-8")
                        }
                        mini_analysis_chart.append(toJson(mini_chart))

                    chart = {
                        "symbol": spot_symbol_trim,
                        "strike_price": spot_price,
                        "profit": r.get("pp_"+spot_symbol_trim).decode("utf-8")
                    }

                    analysis_chart.append(toJson(chart))

    if (premium_paid >= 0):
        premium_paid = f'Get {premium_paid}'
    else:
        premium_paid = f'Pay {abs(round(premium_paid))}'

    premium_lib.max_loss_numerical_graph.argtypes = [
        c_float]
    premium_lib.max_loss_numerical_graph.restype = c_float
    max_loss_numerical_graph = premium_lib.max_loss_numerical_graph(
        max_loss_numerical)

    premium_lib.max_profit_numerical_graph.argtypes = [
        c_float]
    premium_lib.max_profit_numerical_graph.restype = c_float
    max_profit_numerical_graph = premium_lib.max_profit_numerical_graph(
        max_profit_numerical)

    return Response({
        "max_profit_expiry": max_profit_expiry,
        "max_loss_expiry": max_loss_expiry,
        "max_profit_numerical": max_profit_numerical,
        "max_loss_numerical": max_loss_numerical,
        "max_loss_numerical_graph": max_loss_numerical_graph,
        "max_profit_numerical_graph": max_profit_numerical_graph,
        "premium": premium_paid,
        "chart": analysis_chart,
        "mini_chart": mini_analysis_chart
    })


@api_view(['POST'])
def get_access_token(request):
    request_data = json.loads(json.dumps(request.data))
    session = Session(api_key)
    session.set_redirect_uri(redirect_uri)
    session.set_api_secret(secret_key)
    session.set_code(request_data['requestcode'])
    access_token = session.retrieve_access_token()
    u = Upstox(api_key, access_token)
    user_profile = u.get_profile()
    if (user_profile.get('client_id') == client_id):
        r.set("access_token", access_token)
    return Response({"accessToken": access_token})


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
            today = datetime.now().today() +\
                    relativedelta.relativedelta(weeks=1)
            first_day_date = datetime(
                today.year,
                today.month, 1).timestamp()*1000
            return first_day_date

        def get_last_date():
            today = datetime.now().today() +\
                    relativedelta.relativedelta(weeks=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            last_day_date = datetime(
                today.year,
                today.month,
                last_day).timestamp()*1000
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
                if strike_price_val is not None:
                    if closing_price_val is not None:
                        # Avoid NIFTYIT since searching for
                        # NIFTY and BANKNIFTY alongs brings
                        # along this and it lacks liquidity
                        if symbol_val[:7] != niftyit:
                            def save_option_db(
                                expiry,
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
                                if expiry >= get_first_date() and\
                                   expiry <= get_last_date():
                                    if ops[5] is None:
                                        closing_price_val = ''
                                    if ops[11] is None:
                                        isin_val = ''
                                    if ops[7] is None:
                                        strike_price_val = ''
                                    Instrument(
                                        exchange=exchange_val,
                                        token=token_val,
                                        parent_token=parent_token_val,
                                        symbol=symbol_val,
                                        name=name_val,
                                        closing_price=closing_price_val,
                                        expiry=expiry_val,
                                        strike_price=float(strike_price_val),
                                        tick_size=tick_size_val,
                                        lot_size=lot_size_val,
                                        instrument_type=instrument_type_val,
                                        isin=isin_val
                                    ).save()
                                    r.set("s_"+symbol_val,
                                          float(strike_price_val))
                                    # r.set(instrument.symbol, instrument)
                                    all_options.append(Instrument(
                                        ops[0], ops[1], ops[2], ops[3], ops[4],
                                        ops[5], ops[6], ops[7], ops[8], ops[9],
                                        ops[10], ops[11]
                                    ))
                            if symbol == "NIFTY":
                                symbol_len = len(symbol)
                                symbol_cache = symbol_val[:symbol_len]
                                if symbol == symbol_cache.upper():
                                    save_option_db(
                                        expiry,
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
                                save_option_db(
                                    expiry,
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
                        if (symbol_key is not None):
                            val = symbol_key.decode("utf-8")
                            option = ast.literal_eval(val)
                            Full_Quote(
                                strike_price=ops.strike_price,
                                exchange=option['exchange'],
                                symbol=option['symbol'],
                                ltp=option['ltp'],
                                close=option['close'],
                                open=option['open'],
                                high=option['high'],
                                low=option['low'],
                                vtt=option['vtt'],
                                atp=option['atp'],
                                oi=option['oi'],
                                spot_price=option['spot_price'],
                                total_buy_qty=option['total_buy_qty'],
                                total_sell_qty=option['total_sell_qty'],
                                lower_circuit=option['lower_circuit'],
                                upper_circuit=option['upper_circuit'],
                                yearly_low=option['yearly_low'],
                                yearly_high=option['yearly_high'],
                                ltt=option['ltt']
                            ).save()
    connection.close()
    return Response({"Message": "Full Quotes Saved"})


# First Fetches a value from redis
# if not available put's an
# alternative value from database
# TODO Schedule this function
# TODO Perform IV Calculations here
def get_full_quotes_cache(request, symbol_req, expiry_date_req):

    def toJson(func):
        return json.loads(json.dumps(func))

    expiry_dates = []
    date_one = {
        "upstox_date": "19AUG",
        "expiry_date": str(date(2019, 8, 19)),
        "label_date": "19 AUG (Monthly)",
        "future_date": "19AUG"
    }
    expiry_dates.append(date_one)

    # create_session method exclusively while developing in online mode
    '''
    request_data = toJson(request.data)
    def create_session():
        upstox = Upstox(api_key, request_data['accessToken'])
        return upstox
    '''

    searched_symbol = symbol_req + expiry_date_req
    list_option = Full_Quote.objects\
                            .all()\
                            .filter(symbol__startswith=searched_symbol)\
                            .order_by('strike_price')
    connection.close()
    full_quotes = []
    for ops in list_option:
        # This has been done to differentiate between NIFTY and BANKNIFTY
        symbol_len = len(symbol_req)
        symbol_cache = ops.symbol[:symbol_len]
        if(symbol_cache.upper() == symbol_req):
            # This is to fetch Monthly Options only
            trim_symbol = ops.symbol[symbol_len:]
            for expiry_date in expiry_dates:
                symbol_date = trim_symbol[:len(expiry_date.get("upstox_date"))]
                if (symbol_date.upper() == expiry_date.get("upstox_date")):
                    uppercase_symbol = ops.symbol
                    symbol_key = r.get(uppercase_symbol.lower())
                    if (symbol_key is not None):
                        symbol_decoded = symbol_key.decode('utf-8')
                        option = json.loads(symbol_decoded)
                        ask = (option['asks'][0]).get('price')
                        bid = (option['bids'][0]).get('price')
                        full_quote_obj = {
                            "strike_price": ops.strike_price,
                            "exchange": option['exchange'],
                            "symbol": option['symbol'],
                            "ltp": option['ltp'],
                            "close": option['close'],
                            "open": option['open'],
                            "high": option['high'],
                            "low": option['low'],
                            "vtt": option['vtt'],
                            "atp": option['atp'
                            ],
                            "oi": option['oi'],
                            "spot_price": option['spot_price'],
                            "total_buy_qty": option['total_buy_qty'],
                            "total_sell_qty": option['total_sell_qty'],
                            "lower_circuit": option['lower_circuit'],
                            "upper_circuit": option['upper_circuit'],
                            "yearly_low": option['yearly_low'],
                            "yearly_high": option['yearly_high'],
                            "ltt": option['ltt'],
                            "bid": bid,
                            "ask": ask
                        }
                        full_quotes.append(toJson(full_quote_obj))
    return full_quotes


@api_view(['POST'])
def validate_token(request):
    access_token = json.dumps(request.data)
    access_token_data = json.loads(access_token)
    try:
        Upstox(api_key, access_token_data['accessToken'])
        return Response({"status": 1})
    except:
        return Response({"status": 0})


def store_dates():
    Expiry_Date.objects.all().delete()
    Expiry_Date(
        upstox_date="19AUG",
        expiry_date=str(date(2019, 8, 19)),
        label_date="19 AUG (Monthly)",
        future_date="19AUG"
    ).save()
    connection.close()


@api_view(['POST'])
def get_full_quotes(request):

    def toJson(func):
        return json.loads(json.dumps(func))

    request_data = json.loads(json.dumps(request.data))
    # access_token = request_data['accessToken']
    # indices = request_data['indices']
    symbol = request_data['symbol']
    expiry_date = request_data['expiry_date']
    if (expiry_date == "0"):
        expiry_date = "19AUG"

    dates = []
    date_one = {
        "upstox_date": "19AUG",
        "expiry_date": str(date(2019, 8, 19)),
        "label_date": "19 AUG (Monthly)",
        "future_date": "19AUG"
    }
    dates.append(date_one)
    '''
    def create_session(request):
        upstox = Upstox(api_key, access_token)
        return upstox
    '''
    def pairing():
        list_options = get_full_quotes_cache(request, symbol, expiry_date)
        option_pairs = []
        iv = 0.0,
        delta_call = 0
        theta_call = 0
        delta_put = 0
        theta_put = 0

        for a, b in it.combinations(list_options, 2):
            if (a.get("strike_price") == b.get("strike_price")):
                # arrange option pair always in CE and PE order

                trimmed_symbol = (a.get("symbol").lower())[:-2]
                if r.get("g_"+trimmed_symbol) is not None:

                    gamma = r.get("g_"+trimmed_symbol).decode('utf-8')
                    vega = r.get("v_"+trimmed_symbol).decode('utf-8')
                    iv = r.get("iv_" + trimmed_symbol).decode("utf-8")

                    if (a.get("symbol")[-2:] == 'CE'):
                        delta_call = r.get("dc_"+trimmed_symbol)\
                                      .decode('utf-8')
                        theta_call = r.get("tc_"+trimmed_symbol)\
                                      .decode('utf-8')
                        option_pair = (a, b, a.get("strike_price"), iv,
                                       gamma,
                                       vega,
                                       delta_call,
                                       theta_call,
                                       delta_put,
                                       theta_put)
                        option_pairs.append(option_pair)
                    else:
                        delta_put = r.get("dp_"+trimmed_symbol).decode('utf-8')
                        theta_put = r.get("tp_"+trimmed_symbol).decode('utf-8')
                        option_pair = (b, a, a.get("strike_price"), iv,
                                       gamma,
                                       vega,
                                       delta_call,
                                       theta_call,
                                       delta_put,
                                       theta_put)
                        option_pairs.append(option_pair)

        return option_pairs
    option_pairs = pairing()
    return Response({
        "stock_price": r.get("stock_price"+symbol),
        "stock_symbol": r.get("stock_symbol"+symbol),
        "options": toJson(option_pairs),
        "symbol": symbol,
        "closest_strike": float(
            r.get("closest_strike"+symbol+expiry_date)
             .decode("utf-8")),
        "future": r.get("future_price"+symbol),
        "lot_size": json.loads(r.get("ls_"+symbol)),
        "days_to_expiry": r.get("days_to_expiry"),
        "expiry_dates": toJson(dates),
        "expiry_date": expiry_date,
        "pcr": r.get("PCR"+symbol+expiry_date),
        "biggest_OI": float(r.get("biggest_OI"+symbol)),
        "max_pain":  float(r.get("max_pain"+symbol))
    })
