"""Торговый бот по 1 книге 6 главе Билла Вильямса Торговый хаос"""
import json
import time
import datetime
from urllib.parse import urljoin, urlencode
import hmac, hashlib
import requests
import talib
import numpy as np
import websocket

#общие настройки
API_KEY = ''
API_SECRET = ''
BASE_URL = 'https://api.binance.com'
PATH = '/api/v3/order'
headers = {'X-MBX-APIKEY': API_KEY}

trade_symbol = "XRPUSDT" #торговая пара
trade_symbol_low = trade_symbol.lower() #торговая пара в нижнем регистре для передечи в websocket
spend_sum = 20  # Сколько тратить базовой валюты для покупки квотируемой.

class BinanceException(Exception):
    def __init__(self, status_code, data):

        self.status_code = status_code
        if data:
            self.code = data['code']
            self.msg = data['msg']
        else:
            self.code = None
            self.msg = None
        message = f"{status_code} [{self.code}] {self.msg}"

        # Python 2.x
        # super(BinanceException, self).__init__(message)
        super().__init__(message)

def adjust_to_step(value, step, increase=True):
   return ((int(value * 100000000) - int(value * 100000000) % int(float(step) * 100000000)) / 100000000)+(float(step) if increase else 0)

tick_volume = "="
current_tick_volume = 1
previous_tick_volume = 0
symbol_price = 0
last_price = 0
previous_price = 0
volume = 0
open_price = 0
close_price = 0
high_price = 0
low_price = 0
interval = 0
open_in_interval = 0
close_in_interval = 0
previous_high_price = 0
previous_low_price = 0
average_price = 0
quick_dirty_trend = "="
mfi = "="
current_mfi = 0
previous_mfi = 0

trade_time = 0
kline_start_time_tick = 0
kline_close_time_tick = 0
buy_long = 1
buy_short = 1
trade_time_tick = 0

symbol = ""

squat_bar_long = 0
squat_bar_short = 0

ema2 = []
ema5 = []

price_buy_long = 0
price_sell = 0
profit = 0
all_profit = 0

order_id = 0
order_status = ""
client_orderid = ""

clist = requests.get("https://api.binance.com/api/v3/klines?symbol=XRPUSDT&interval=5m&limit=10").json()
close = []
for i in range(len(clist)):
    close.append(float(clist[i][4]))
ema2 = talib.EMA(np.array(close),2)
ema5 = talib.EMA(np.array(close),5)

def on_message(ws, message):
    #print(message)
    global tick_volume
    global current_tick_volume
    global previous_tick_volume
    global symbol_price
    global last_price
    global previous_price
    global volume
    global open_price
    global close_price
    global high_price
    global low_price
    global interval
    global open_in_interval
    global close_in_interval
    global previous_high_price
    global previous_low_price
    global average_price
    global quick_dirty_trend
    global previous_tick_volume
    global mfi
    global current_mfi
    global previous_mfi
    global trade_time_tick
    global kline_start_time_tick
    global kline_close_time_tick
    global buy_long
    global buy_short
    global symbol
    global squat_bar_long
    global squat_bar_short
    global ema2
    global ema5
    global close
    global price_buy_long
    global price_sell
    global profit
    global all_profit
    global order_id
    global client_orderid


    trade = json.loads(message)
    symbol = trade['s']

    if trade['e'] == "trade":
        last_price = float(trade['p'])
        trade_time_tick = float(trade['T'])
        if last_price != previous_price:
            current_tick_volume = current_tick_volume + 1
            previous_price = last_price

    if trade['e'] == "kline":
        open_price = float(trade['k']['o'])
        close_price = float(trade['k']['c'])
        high_price = float(trade['k']['h'])
        low_price = float(trade['k']['l'])
        kline_start_time_tick = float(trade['k']['t'])
        kline_close_time_tick = float(trade['k']['T'])
        is_this_kline_closed = trade['k']['x']

#"грязно" определяем направление тренда
        average_price = (high_price + low_price)/2

        if average_price > previous_high_price:
            quick_dirty_trend = "+"
        if previous_high_price >= average_price and average_price >= previous_low_price:
            quick_dirty_trend = "="
        if previous_low_price > average_price:
            quick_dirty_trend = "-"

#определяем "тип" бара
        interval = (high_price - low_price) / 3

        if high_price > open_price and open_price > high_price - interval or high_price == open_price:
            open_in_interval = 1
        if open_price > low_price + interval and high_price - interval > open_price:
            open_in_interval = 2
        if open_price > low_price and low_price + interval > open_price or open_price == low_price:
            open_in_interval = 3

        if high_price > close_price and close_price > high_price - interval or high_price == close_price:
            close_in_interval = 1
        if close_price > low_price + interval and high_price - interval > close_price:
            close_in_interval = 2
        if close_price > low_price and low_price + interval > close_price or close_price == low_price:
            close_in_interval = 3

#Тиковый объём
        if current_tick_volume > previous_tick_volume:
            tick_volume = "+"
        if current_tick_volume == previous_tick_volume:
            tick_volume = "="
        if previous_tick_volume > current_tick_volume:
            tick_volume = "-"

#mfi
        current_mfi = (high_price - low_price)/current_tick_volume

        if current_mfi > previous_mfi:
            mfi = "+"
        if current_mfi == previous_mfi:
            mfi = "="
        if previous_mfi > current_mfi:
            mfi = "-"

        #print(kline_start_time,kline_close_time,open_price,close_price,high_price,low_price,base_asset_volume,is_this_kline_closed,tick_volume)
        if is_this_kline_closed:
            close.append(close_price)
            del close[1]
            ema2 = talib.EMA(np.array(close),2)
            ema5 = talib.EMA(np.array(close),5)

            squat_bar_long = squat_bar_long - 1
            squat_bar_short = squat_bar_short - 1
            if str(quick_dirty_trend) == "-" and int(open_in_interval) == 1 and int(close_in_interval) == 3 and str(tick_volume) == "+" and str(mfi) == "-":
                squat_bar_long = 5
            if str(quick_dirty_trend) == "+" and int(open_in_interval) == 3 and int(close_in_interval) == 1 and str(tick_volume) == "+" and str(mfi) == "-":
                squat_bar_short = 5
            kline_start_time = datetime.datetime.utcfromtimestamp(kline_start_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
            kline_close_time = datetime.datetime.utcfromtimestamp(kline_close_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
            print(symbol,kline_start_time,kline_close_time,quick_dirty_trend,open_in_interval,close_in_interval,tick_volume,mfi,high_price,low_price,open_price,close_price,current_tick_volume)
            previous_high_price = high_price
            previous_low_price = low_price
            previous_tick_volume = current_tick_volume
            current_tick_volume = 1
            previous_mfi = current_mfi

    if ema2[-1] > ema5[-1] and buy_long == 1 and squat_bar_long > 0 and squat_bar_long <= 5:
        print("Выполнилось условие на покупку!")
        timestamp = requests.get("https://api.binance.com/api/v3/time").json()
        params = {'symbol': 'XRPUSDT','side': 'BUY','type': 'MARKET','quantity': 14,'recvWindow': 5000,'timestamp': timestamp['serverTime']}
        query_string = urlencode(params)
        params['signature'] = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        url = urljoin(BASE_URL, PATH)
        r = requests.post(url, headers=headers, params=params)
        if r.status_code == 200:
            buy_long = 0
            squat_bar_long = 0
            data = r.json()
            order_id = data["orderId"]
            client_orderid = data["clientOrderId"]
            trade_time = datetime.datetime.utcfromtimestamp(trade_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
            print(trade_time,data["fills"][0]["price"],"BUY_LONG")
        else:
            raise BinanceException(status_code=r.status_code, data=r.json())

    if ema5[-1] > ema2[-1] and buy_long == 0:
        print("Выполнилось условие на продажу!")
#получаем данные по ордеру
        timestamp = requests.get("https://api.binance.com/api/v3/time").json()
        params = {'symbol': 'XRPUSDT','orderId': order_id, 'origClientOrderId': client_orderid,'recvWindow': 5000,'timestamp': timestamp['serverTime']}
        query_string = urlencode(params)
        params['signature'] = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        url = urljoin(BASE_URL, PATH)
        r = requests.get(url, headers=headers, params=params)
        if r.status_code == 200:
            data = r.json()
            order_status = data["status"]
            price_buy_long = float(data['cummulativeQuoteQty'])/float(data['executedQty'])
            print("Статус ордера на покупку:","ORDER:", order_id, "STATUS:", order_status,"PRICE",price_buy_long)
        else:
            raise BinanceException(status_code=r.status_code, data=r.json())

        if order_status == "FILLED":
            print("Ордер выполнен можно продавать!")

# если тренд не получился выставляем отложенный ордер на продажу по чуть завышенной цене.        
            if last_price <= price_buy_long * (0.001*2) and buy_long == 0:
                limit_sell_price =  price_buy_long + price_buy_long * (0.001*2) + price_buy_long * 0.005
                timestamp = requests.get("https://api.binance.com/api/v3/time").json()
                params = {'symbol': 'XRPUSDT','side': 'SELL','type': 'LIMIT','timeInForce': 'GTC','quantity': 14, 'price': adjust_to_step(limit_sell_price,0.00010000),'recvWindow': 5000,'timestamp': timestamp['serverTime']}
                query_string = urlencode(params)
                params['signature'] = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
                url = urljoin(BASE_URL, PATH)
                r = requests.post(url, headers=headers, params=params)
                if r.status_code == 200:
                    buy_long = 1
                    data = r.json()
                    print("Лимитный ордер выставлен успешно:", "ORDER:",data["orderId"], "STATUS:",data["status"], "ORDER_PRICE:",data["price"], "ASK_PRICE",limit_sell_price)
                else:
                    raise BinanceException(status_code=r.status_code, data=r.json())

#тренд удался выставляем ордер по текущей цене
            if last_price > price_buy_long * (0.001*2) and buy_long == 0:
                trade_time = datetime.datetime.utcfromtimestamp(trade_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
                timestamp = requests.get("https://api.binance.com/api/v3/time").json()
                params = {'symbol': 'XRPUSDT','side': 'SELL','type': 'MARKET','quantity': 14,'recvWindow': 5000,'timestamp': timestamp['serverTime']}
                query_string = urlencode(params)
                params['signature'] = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
                url = urljoin(BASE_URL, PATH)
                r = requests.post(url, headers=headers, params=params)
                if r.status_code == 200:
                    buy_long = 1
                    data = r.json()
                    print("Маркет ордер выставлен успешно:",trade_time,"PRICE:", data["fills"][0]["price"])
                else:
                    raise BinanceException(status_code=r.status_code, data=r.json())

def on_error(ws, error):
    print("### error ###")
    print(error)
    time.sleep(5)
    binance_socket()

def on_close(ws):
    print("### closed ###")
    time.sleep(5)
    binance_socket()

def on_open(ws):
    print("### connected ###")

#if __name__ == "__main__":
def binance_socket():
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/xrpusdt@kline_5m/xrpusdt@trade",
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()

binance_socket()
