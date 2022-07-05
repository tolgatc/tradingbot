# -*- coding: utf-8 -*-
"""
Created on Thu May 26 14:31:34 2022
this script connects to binance api

feches candlestick data

puts them in csv file

for post processing


@author: tolga
"""

import websocket,json,pprint,numpy,talib, keydata
import csv
from binance import Client
from binance.enums import *

client = Client(api_key=(keydata.apiKey),api_secret=(keydata.apiSec),testnet=False)

# prices = client.get_all_tickers()

# for price in prices:
#     print(price)

candles= client.get_klines(symbol='BTCUSDT',interval=Client.KLINE_INTERVAL_15MINUTE)

f = open('2020_1h.csv','w',newline='')
candlewriter=csv.writer(f,delimiter=',')


#for candlestick in candles:
#    print(candlestick)
#    candlewriter.writerow(candlestick)
    
candles_old = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "1 Jan, 2020", "11 Jul, 2020")
for candlestick in candles_old:
    #print(candlestick)
    candlestick[0]=candlestick[0]/1000
    candlewriter.writerow(candlestick)

    
f.close()