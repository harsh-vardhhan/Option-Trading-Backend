from apscheduler.schedulers.blocking import BlockingScheduler
import os
import redis
import json
from upstox_api.api import Upstox, LiveFeedType
from datetime import date
import numpy as np
import scipy.stats as si
import math
import itertools as it
from datetime import datetime, time
import pytz

sched = BlockingScheduler()

api_key = 'Qj30BLDvL96faWwan42mT45gFHyw1mFs8JxBofdx'
master_contract_FO = 'NSE_FO'

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r = redis.from_url(redis_url)

# NOTE token r.set only in DEV mode
# r.set("access_token", "d558bcfdbfcc7ce7ca45885af1003b1de0c8ef05")
access_token = r.get("access_token").decode("utf-8")

expiry_dates = [{
    "upstox_date": "19AUG",
    "expiry_date": date(2019, 8, 29),
    "label_date": "19 AUG (Monthly)",
    "future_date": "19AUG"
}]

symbols = [{
    "symbol": "NIFTY",
    "indices": "NIFTY_50",
    "symbol_type": "NSE_INDEX"
}, {
    "symbol": "BANKNIFTY",
    "indices": "NIFTY_BANK",
    "symbol_type": "NSE_INDEX"
}, {
    "symbol": "RELIANCE",
    "indices": "RELIANCE",
    "symbol_type": "NSE_EQ"
}]


def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC time
    return True
    tz = pytz.timezone('Asia/Kolkata')
    check_time = check_time or datetime.now(tz).time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else:
        # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def Greeks_call(S, X, T, r, sigma):
    d1 = (math.log(S/X) + (r + (sigma * sigma) / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    Delta_call = si.norm.cdf(d1)
    Gamma = si.norm.pdf(d1) / (S * sigma * math.sqrt(T))
    Vega = (S * math.sqrt(T) * si.norm.pdf(d1))/100
    Theta_call = (-(S * sigma * si.norm.pdf(d1)) / (2 * math.sqrt(T)) - r * X * math.exp(-r * T) * si.norm.cdf(d2))/365
    return (Delta_call, Gamma, Vega, Theta_call)


def Greeks_put(S, X, T, r, sigma):
    d1 = (math.log(S/X) + (r + (sigma * sigma) / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    Delta_put = si.norm.cdf(d1) - 1
    Gamma = si.norm.pdf(d1) / (S * sigma * math.sqrt(T))
    Vega = (S * math.sqrt(T) * si.norm.pdf(d1))/100
    Theta_put = (-(S * sigma * si.norm.pdf(d1)) / (2 * math.sqrt(T)) + r * X * math.exp(-r * T) * si.norm.cdf(-d2))/365
    return (Delta_put, Theta_put)


def calcImpliedVol(S, K, T, P, r, sigma, type):
    # S: future spot price
    # K: strike price
    # T: time to maturity
    # C: Call value
    # r: interest rate
    # sigma: volatility of underlying asset
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    vega = (1 / np.sqrt(2 * np.pi)) * S * np.sqrt(T) * np.exp(-(si.norm.cdf(d1, 0.0, 1.0) ** 2) * 0.5)
    if type == "call":
        fx = S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0) - P
    elif type == "put":
        fx = K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0) - P
    return fx / vega


def cal_iv(S, K, T, P, r, sigma=0.25, tolerance=0.0001, type="call"):
    xnew = sigma
    xold = sigma - 1
    while abs(xnew - xold) > tolerance:
        xold = xnew
        xnew = xold - calcImpliedVol(S, K, T, P, r, xold, type=type)
        iv = round(xnew * 100, 1)
        return iv


@sched.scheduled_job('interval', minutes=2)
def timed_job():
    def create_session():
        upstox = Upstox(api_key, r.get("access_token").decode("utf-8"))
        return upstox
    print("****Running Black Scholes")
    if is_time_between(time(9, 15), time(15, 30)):
        upstox = create_session()
        # values to be iterated

        future_date = "19AUG"
        # NOTE: hard coded date
        expiry_date = expiry_dates[0].get("expiry_date")

        for symbol in symbols:
            today = date.today()
            days_to_expiry = expiry_date - today
            r.set("days_to_expiry", days_to_expiry.days)
            time_to_maturity = days_to_expiry.days / 365

            upstox.get_master_contract(master_contract_FO)
            future = upstox.get_live_feed(upstox.get_instrument_by_symbol(
                    master_contract_FO, symbol.get("symbol") + future_date + 'FUT'),
                    LiveFeedType.Full)
            future_data = json.loads(json.dumps(future))
            future_price = future_data["ltp"]
            r.set("future_price"+symbol.get("symbol"), future_price)

            upstox.get_master_contract(symbol.get("symbol_type"))
            equity = upstox.get_live_feed(upstox.get_instrument_by_symbol(
                    symbol.get("symbol_type"), symbol.get("indices")),
                    LiveFeedType.Full)
            equity_data = json.loads(json.dumps(equity))
            equity_price = equity_data["ltp"]
            equity_symbol = equity_data["symbol"]
            r.set("stock_symbol"+symbol.get("symbol"), equity_symbol)
            r.set("stock_price"+symbol.get("symbol"), equity_price)

            call_OI = 0.0
            put_OI = 0.0
            biggest_OI = 0.0
            iv = 0

            def to_lakh(n):
                return float(round(n/100000, 1))
            closest_strike = 10000000
            closest_option = ""
            options_pairs = []

            for a, b in it.combinations(r.scan_iter((
                    symbol.get("symbol")).lower()+"*"), 2):
                instrument_symbol_a = (a).decode('utf-8')
                instrument_symbol_b = (b).decode('utf-8')
                instrument_a_strike = json.loads(r.get("s_"+instrument_symbol_a))
                instrument_b_strike = json.loads(r.get("s_"+instrument_symbol_b))

                if(instrument_a_strike == instrument_b_strike):
                    call_option_symbol = ""
                    put_option_symbol = ""
                    if(instrument_symbol_a[-2:] == "ce"):
                        call_option_symbol = instrument_symbol_a
                        put_option_symbol = instrument_symbol_b
                    elif(instrument_symbol_a[-2:] == "pe"):
                        call_option_symbol = instrument_symbol_b
                        put_option_symbol = instrument_symbol_a

                    # Option Chain CE-PE order from this point
                    iv = 0
                    call_option = json.loads(r.get(call_option_symbol))
                    put_option = json.loads(r.get(put_option_symbol))

                    call_OI = call_OI + call_option.get("oi")
                    put_OI = put_OI + put_option.get("oi")

                    diff = abs(float(
                        r.get("stock_price"+symbol.get("symbol"))) -
                        instrument_a_strike)

                    if(diff < closest_strike):
                        closest_strike = diff
                        closest_option = instrument_a_strike

                    if(to_lakh(call_option.get("oi")) > biggest_OI):
                        biggest_OI = to_lakh(call_option.get("oi"))

                    if(to_lakh(put_option.get("oi")) > biggest_OI):
                        biggest_OI = to_lakh(put_option.get("oi"))

                    if (instrument_a_strike > equity_price):
                        iv = cal_iv(
                                future_price,
                                instrument_a_strike,
                                time_to_maturity,
                                call_option.get("ltp"),
                                0.1,
                                0.25,
                                0.0001,
                                "call"
                                )
                        r.set("iv_"+instrument_symbol_a[:-2], iv)

                    if (instrument_a_strike < equity_price):
                        iv = cal_iv(
                                future_price,
                                instrument_a_strike,
                                time_to_maturity,
                                put_option.get("ltp"),
                                0.1,
                                0.25,
                                0.0001,
                                "put"
                                )

                        r.set("iv_"+instrument_symbol_a[:-2], iv)

                    Delta_call, Gamma, Vega, Theta_call = Greeks_call(
                            future_price,
                            instrument_a_strike,
                            time_to_maturity,
                            0.1,
                            iv
                            )

                    Delta_put, Theta_put = Greeks_put(
                            future_price,
                            instrument_a_strike,
                            time_to_maturity,
                            0.1,
                            iv
                            )
                    Gamma_val = round(Gamma, 4)
                    Vega_val = round(Vega, 2)
                    Delta_call_val = round(Delta_call, 2)
                    Theta_call_val = round(Theta_call, 2)
                    Delta_put_val = round(Delta_put, 2)
                    Theta_put_val = round(Theta_put, 2)

                    r.set("g_"+instrument_symbol_a[:-2], Gamma_val)
                    r.set("v_"+instrument_symbol_a[:-2], Vega_val)
                    r.set("dc_"+instrument_symbol_a[:-2], Delta_call_val)
                    r.set("tc_"+instrument_symbol_a[:-2], Theta_call_val)
                    r.set("dp_"+instrument_symbol_a[:-2], Delta_put_val)
                    r.set("tp_"+instrument_symbol_a[:-2], Theta_put_val)
                    option_pair = (
                            instrument_a_strike,
                            call_option_symbol,
                            put_option_symbol,
                            call_option.get("oi"),
                            put_option.get("oi"),
                    )
                    options_pairs.append(option_pair)

            # Calculate Max Pain
            sorted_option_pairs = sorted(options_pairs, key=lambda x: x[0])
            max_pain_list = []
            strike_difference = 0
            for i, a in enumerate(sorted_option_pairs):
                if i != 0:
                    strike_difference = strike_difference + 50
                max_pain_pair = (
                        sorted_option_pairs[i][0],
                        sorted_option_pairs[i][1],
                        sorted_option_pairs[i][2],
                        sorted_option_pairs[i][3],
                        sorted_option_pairs[i][4],
                        strike_difference
                )
                max_pain_list.append(max_pain_pair)

            cumilative_call_counter = 0
            cumilative_put_counter = len(max_pain_list)

            total_loss_list = []
            for i, a in enumerate(max_pain_list):
                strike_call_counter = 0
                cumilative_call_counter = i
                cumilative_call = 0

                cumilative_put_counter = i
                cumilative_put = 0
                strike_put_counter = 0  # This ensures a liquid strike is the max pain make it 1
                while cumilative_call_counter > 0:
                    cumilative_call_counter = cumilative_call_counter - 1

                    # print(max_pain_list[i][0] ,max_pain_list[cumilative_call_counter][3], max_pain_list[strike_call_counter][5])
                    cumilative_val = max_pain_list[cumilative_call_counter][3] * max_pain_list[strike_call_counter][5]
                    cumilative_call = cumilative_call + cumilative_val
                    strike_call_counter = strike_call_counter + 1
                while cumilative_put_counter < (len(max_pain_list) - 1):
                    cumilative_put_counter = cumilative_put_counter + 1
                    cumilative_val = max_pain_list[cumilative_put_counter][4] * max_pain_list[strike_put_counter][5]
                    strike_put_counter = strike_put_counter + 1
                    cumilative_put = cumilative_put + cumilative_val

                total_loss = cumilative_call + cumilative_put

                # print("*******",max_pain_list[i][0] ,max_pain_list[i][4], max_pain_list[i][5])
                total_loss_pair = (max_pain_list[i][0], total_loss)
                total_loss_list.append(total_loss_pair)
            r.set("max_pain"+symbol.get("symbol"), min(total_loss_list, key=lambda x: x[1])[0])

            if call_OI == 0.0:
                call_OI = 1.0
            pcr = round(put_OI/call_OI, 2)
            r.set("biggest_OI" + symbol.get("symbol"), biggest_OI)
            r.set("closest_strike" + symbol.get("symbol")+future_date, closest_option)
            r.set("PCR" + symbol.get("symbol") + future_date, pcr)


sched.start()
# timed_job()
