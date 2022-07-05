from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime

import matplotlib
#import matplotlib.pyplot as plt
import argparse
import backtrader as bt
import numpy as np
#import matplotlib
#matplotlib.use('Qt5Agg')
#plt.switch_backend('Qt5Agg')

# class RSIStrategy(bt.Strategy):

#     def __init__(self):
#         self.rsi = bt.talib.RSI(self.data, period=14)

#     def next(self):
#         if self.rsi < 30 and not self.position:
#             self.buy(size=1)
        
#         if self.rsi > 70 and self.position:
#             self.close()

# class EMAstrategy(bt.Strategy):
    
#     def __init__(self):
#         self.ema = bt.talib.EMA(self.data,period=20)
        
# class SmaCross(bt.Strategy):
#     # list of parameters which are configurable for the strategy
#     params = dict(
#         pfast=10,  # period for the fast moving average
#         pslow=30   # period for the slow moving average
#     )

#     def __init__(self):
#         sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
#         sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
#         self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal
        
        
#     def next(self):
#         if not self.position:  # not in the market
#             if self.crossover > 0:  # if fast crosses slow to the upside
#                 self.buy()  # enter long

#         elif self.crossover < 0:  # in the market & cross to the downside
#             self.close()  # close long position

#datapath = args.dataname or '../../datas/2006-day-001.txt'
#data = btfeeds.BacktraderCSVData(dataname=datapath)
#cerebro.adddata(data)  # First add the original data - smaller timeframe
#tframes = dict(daily=bt.TimeFrame.Days, weekly=bt.TimeFrame.Weeks,
#                   monthly=bt.TimeFrame.Months)

# Handy dictionary for the argument timeframe conversion
# Resample the data
#args = parse_args()
#if args.noresample:
#    datapath = args.dataname2 or '../../datas/2006-week-001.txt'
#    data2 = btfeeds.BacktraderCSVData(dataname=datapath)
    # And then the large timeframe
#    cerebro.adddata(data2)
#else:
#    cerebro.resampledata(data, timeframe=tframes[args.timeframe],
#                             compression=args.compression)

            
class EmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        period=20,  # period for the fast moving average
        atrMinFilterSize = 0,
        atrMaxFilterSize=3,
        stopMultiplier=1,
        rr=1
    )

    def __init__(self):
        #ema filter
        ema1 = bt.ind.EMA(period=self.p.period,plot=False)  # fast moving average
        
        rocema1 = bt.indicators.ROC100(ema1,period=20,plot=False)
        #rocema2 = bt.indicators.ROC100(ema1,period=20)
        
        slope = bt.talib.ATAN(rocema1,plot=False) * (180/np.pi)
        #slope2 = bt.talib.ATAN(rocema2) * (180/np.pi)
        #bt.LinePlotterIndicator(slope, name='slope')
        slope_pos = slope > 45
        slope_neg= slope < -45
        self.dataclose = self.datas[0].close
        
        ## retracement bar check
        self.hilo_diff = abs(self.data.high - self.data.low)
        clop_diff = abs(self.data.close - self.data.open)
        rv = clop_diff < 0.45*self.hilo_diff
        ## Price Level for Retracement
        x = self.data.low + (0.45 * self.hilo_diff)
        y = self.data.high - (0.45 * self.hilo_diff)

        self.irbb = bt.And(rv == 1,self.data.high > y,self.data.close < y,self.data.open < y)
        self.irbs = bt.And(rv == 1,self.data.low < x,self.data.close > x,self.data.open > x)
        
        ##atr trailing stop/loss
        atr= bt.talib.ATR(self.data.high,self.data.low,self.data.close)
        
        atrMinFilter = bt.Or(((self.data.high - self.data.low) >= self.p.atrMinFilterSize * atr),self.p.atrMinFilterSize == 0.0)
        atrMaxFilter = bt.Or(((self.data.high - self.data.low) <= (self.p.atrMaxFilterSize * atr)),self.p.atrMaxFilterSize == 0.0)
        atrFilter = bt.And(atrMinFilter,atrMaxFilter)
        
        
        #Calculate long stops & targets
        longStop = self.data.low - (atr * self.p.stopMultiplier) 
        longStopDistance = self.data.close - longStop 
        longTarget = self.data.high + (longStopDistance * self.p.rr)
        
        #Calculate short(sellS) stops & targets
        shortStop = self.data.high + (atr * self.p.stopMultiplier) 
        shortStopDistance = shortStop - self.data.close 
        shortTarget = self.data.low - (shortStopDistance * self.p.rr) 
        
        self.inTrade = 0
        self.buys = bt.And(self.irbb,slope_pos,atrFilter,self.inTrade == 0)
        self.sells = bt.And(self.irbs,slope_neg,atrFilter,self.inTrade == 0)
        bt.LinePlotterIndicator(self.sells, name='slope')
        
    def next(self):
        self.log('Close, %.2f' % self.hilo_diff[0])
        
        if not self.position:  # not in the market
            if self.buys:  # if fast crosses slow to the upside
                self.buy()  # enter long

        elif self.sells:  # in the market & cross to the downside
            self.close()  # close long position
            
    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
        


cerebro = bt.Cerebro()

fromdate = datetime.datetime.strptime('2020-01-01', '%Y-%m-%d')

todate = datetime.datetime.strptime('2020-02-15', '%Y-%m-%d')

data = bt.feeds.GenericCSVData(dataname='data/2020_15min.csv', dtformat=2,compression=15, timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)

cerebro.adddata(data)

#data2 = bt.feeds.GenericCSVData(dataname='2020_daily.csv', dtformat=2)
#data = bt.feeds.GenericCSVData(dataname='2020_daily.csv', dtformat=2, compression=15, timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)

#cerebro.adddata(data2)

#cerebro.resampledata(data,timeframe=bt.)
cerebro.addstrategy(EmaCross)

cerebro.broker.setcommission(commission=0.001)

print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

result=cerebro.run()

print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

cerebro.plot(iplot = False)
#plt.pause(10) 
