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
        rr=1.5
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
        self.longStop = self.data.low - (atr * self.p.stopMultiplier) 
        longStopDistance = self.data.close - self.longStop 
        self.longTarget = self.data.high + (longStopDistance * self.p.rr)
        
        #Calculate short(sellS) stops & targets
        self.shortStop = self.data.high + (atr * self.p.stopMultiplier) 
        shortStopDistance = self.shortStop - self.data.close 
        self.shortTarget = self.data.low - (shortStopDistance * self.p.rr) 
        
        self.inTrade = 0
        self.buys = bt.And(self.irbb,slope_pos,atrFilter,self.inTrade == 0)
        self.sells = bt.And(self.irbs,slope_neg,atrFilter,self.inTrade == 0)
        bt.LinePlotterIndicator(self.buys, name='buys')
        
        self.t_stop = np.NaN
        self.t_target = np.NaN
        
        self.order = None
        
    #Keep track of orders here        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None    
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))    
    
    #Here we descirbe the strategy    
    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.inTrade)

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if (self.inTrade==0) and (self.buys or self.sells):  # not in the market and buy/sell signal
            if self.buys:  # if fast crosses slow to the upside
                self.t_stop = self.longStop[0]
                self.t_target = self.longTarget[0]
                self.order = self.buy()
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.inTrade = 1
            else:
                self.t_stop = self.shortStop[0]
                self.t_target = self.shortTarget[0]
                self.inTrade = 0
                self.order = self.close()
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                
        if self.inTrade ==1 :  # in the market & cross to the downside
            if (self.data.high >=self.t_target or self.data.low <=self.t_stop):
                self.inTrade=0
                self.order = self.sell()
                self.log('SELL CREATE, %.2f' % self.data.high[0])
        elif self.inTrade== -1:
            if (self.data.high >=self.t_stop or self.data.low <=self.t_target):
                self.inTrade=0
                self.order=self.close()
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
            
    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
        


cerebro = bt.Cerebro()
# Start date and end date of strategy
fromdate = datetime.datetime.strptime('2020-01-01', '%Y-%m-%d')
# datetime.date.today()+datetime.timedelta(days=1)
nr_of_days=40
todate = fromdate + datetime.timedelta(days=nr_of_days)

data = bt.feeds.GenericCSVData(dataname='data/alltime_1h.csv', dtformat=2, fromdate=fromdate, todate=todate)

cerebro.adddata(data)

#data2 = bt.feeds.GenericCSVData(dataname='2020_daily.csv', dtformat=2)
#data = bt.feeds.GenericCSVData(dataname='2020_daily.csv', dtformat=2, compression=15, timeframe=bt.TimeFrame.Minutes, fromdate=fromdate, todate=todate)

#cerebro.adddata(data2)

#cerebro.resampledata(data,timeframe=bt.)
cerebro.addstrategy(EmaCross)

cerebro.broker.setcommission(commission=0.001)
cerebro.broker.setcash(10000.0)
#cerebro.addsizer(bt.sizers.FixedSize, stake=0.1) #purchase 1 btcusdt, stake=1 default
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())


result=cerebro.run()

print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

cerebro.plot(iplot = False)
#plt.pause(10) 
