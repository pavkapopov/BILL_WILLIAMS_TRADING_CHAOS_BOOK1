import websocket
import json
import time
import datetime
import sqlite3

tick_volume = "="
current_tick_volume = 0
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

#{
#  "e": "trade",     // Event type
#  "E": 123456789,   // Event time
#  "s": "BNBBTC",    // Symbol
#  "t": 12345,       // Trade ID
#  "p": "0.001",     // Price
#  "q": "100",       // Quantity
#  "b": 88,          // Buyer order ID
#  "a": 50,          // Seller order ID
#  "T": 123456785,   // Trade time
#  "m": true,        // Is the buyer the market maker?
#  "M": true         // Ignore
#}

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

    trade = json.loads(message)

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
        #number_of_trades = trade['k']['n']
        base_asset_volume = float(trade['k']['v'])
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
        current_mfi = (high_price - low_price)/base_asset_volume

        if current_mfi > previous_mfi:
            mfi = "+"
        if current_mfi == previous_mfi:
            mfi = "="
        if previous_mfi > current_mfi:
            mfi = "-"

        #print(kline_start_time,kline_close_time,open_price,close_price,high_price,low_price,base_asset_volume,is_this_kline_closed,tick_volume)
        if is_this_kline_closed:
            kline_start_time = datetime.datetime.utcfromtimestamp(kline_start_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
            kline_close_time = datetime.datetime.utcfromtimestamp(kline_close_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
            print(kline_start_time,kline_close_time,quick_dirty_trend,open_in_interval,close_in_interval,tick_volume,mfi,open_price,close_price)
            previous_high_price = high_price
            previous_low_price = low_price
            previous_tick_volume = current_tick_volume
            current_tick_volume = 0
            previous_mfi = current_mfi
            buy_long = 1
            buy_short = 1

    if str(quick_dirty_trend) == "+" and int(open_in_interval) == 3 and int(close_in_interval) == 1 and str(tick_volume) == "+" and str(mfi) == "+" and buy_long == 1:
        trade_time = datetime.datetime.utcfromtimestamp(trade_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
        print(trade_time,last_price,"LONG")
        buy_long = 0

    if str(quick_dirty_trend) == "-" and int(open_in_interval) == 1 and int(close_in_interval) == 3 and str(tick_volume) == "+" and str(mfi) == "+" and buy_short == 1:
        trade_time = datetime.datetime.utcfromtimestamp(trade_time_tick/1000).replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).strftime('%d.%m.%Y %H:%M:%S')
        print(trade_time,last_price,"SHORT")
        buy_short = 0

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
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/adausdt@kline_15m/adausdt@trade",
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()

binance_socket()