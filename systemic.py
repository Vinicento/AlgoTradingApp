#systemic
import MetaTrader5 as mt5
from statsmodels.tsa.stattools import acf, pacf
import numpy as np
import pandas as pd
import arch
from statsmodels.tsa.arima.model import ARIMA


class systemic:
    def __init__(self,parameters):
        self.parameters=parameters
        self.positions=list(set(mt5.positions_get()))
   
    @staticmethod
    def find_filling_mode(symbol):

        for i in range(2):
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": mt5.symbol_info(symbol).volume_min,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "type_filling": i,
            "type_time": mt5.ORDER_TIME_GTC}

            result = mt5.order_check(request)
            
            if result.comment == "Done":
                break

        return i               

    @staticmethod
    def send_order(symbol, lot, buy, sell, id_position=None, pct_tp=0.02, pct_sl=0.01, comment=" No specific comment", magic=0,washing=0,data=None):
        
            # Initialize the bound between MT5 and Python
            if washing:
                point = mt5.symbol_info(symbol).point
                if buy:
                    target=data[1]
                    ask= mt5.symbol_info(symbol).ask
                    pct_sl=((ask-target)/point)*1.20
                    pct_tp=pct_sl*1.5
                elif sell:
                    target=data[0]
                    bid= mt5.symbol_info(symbol).bid
                    pct_sl=((target-bid)/point)*1.20
                    pct_tp=pct_sl*1.5

            # Extract filling_mode
            filling_type = systemic.find_filling_mode(symbol)
            point=mt5.symbol_info(symbol).point


            """ OPEN A TRADE """
            if buy and id_position==None:
                price = mt5.symbol_info_tick(symbol).ask
                tp = (price + int(pct_tp)*point)
                sl = (price - int(pct_sl)*point)
                request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": 10,
                "tp": tp,
                "sl": sl, 
                "magic": magic,
                "comment": comment,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC}

                result = mt5.order_send(request)
                
                return result

            elif sell and id_position==None:
                price = mt5.symbol_info_tick(symbol).bid

                tp = (price - int(pct_tp)*point)
                sl = (price + int(pct_sl)*point)
                request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 10,
                "tp": tp,
                "sl": sl, 
                "magic": magic,
                "comment": comment,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC}

                result = mt5.order_send(request)
                
                return result

    @staticmethod
    def garima_position(data):

        lag_pacf = pacf(data, nlags=(int(len(data) * 0.3)), method='ols')
        lag_acf = acf(data, nlags=(int(len(data) * 0.3)))

        highest_index_pacf = np.argmax(lag_pacf[1:]) + 1  # importand that we drop first one so+1
        highest_index_acf = np.argmax(lag_acf[1:]) + 1  # importand that we drop first one so+1

        model_arima = ARIMA(data, order=(highest_index_pacf, 2, highest_index_acf)).fit()
        arima_pred = model_arima.forecast(steps=10)
        arima_pred = list(arima_pred)

        data = data.pct_change(fill_method=None)
        data.reset_index(drop=True, inplace=True)
        data = data * 1000
        data.dropna(inplace=True)

        model_garch = arch.arch_model(data, vol='GARCH', p=int(highest_index_pacf), q=int(highest_index_acf))

        results_garch = model_garch.fit()

        results_garch = results_garch.forecast(horizon=10, reindex=False)
        results_garch = results_garch.residual_variance
        results_garch = list(results_garch.iloc[0])
        results_garch = [x / 1000 for x in results_garch]

        upper = np.array(arima_pred) + np.array(results_garch)

        lower = np.array(arima_pred) - np.array(results_garch)
        slope = np.gradient(arima_pred)

        return upper, lower, slope, arima_pred

    @staticmethod
    def position_check(parameters,profit_cache):
            positions=list(set(mt5.positions_get()))
            positions_symbols=[]
            tickets=[]
            
            for i in positions:


                positions_symbols.append(i.symbol)
                tickets.append(i.ticket)
                if int(parameters[i.symbol][2]) == 1: #BEP Control Variation
                    if (np.abs(i.price_current-i.price_open)> 0.5*np.abs(i.tp-i.price_open)) & (i.profit>0) & (i.sl!=i.price_open): # but must happen only once
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": i.ticket,
                            "sl": i.price_open,
                            "tp": i.tp,

                        }
                        mt5.order_send(request)


                elif (int(parameters[i.symbol][2]) == 2): # trailing_stop Control Variation:

                    
                    if i.ticket in profit_cache.keys():

                        if i.profit> profit_cache[i.ticket]:

                                profit_cache[i.ticket]=i.profit
                                symbol_info = mt5.symbol_info(i.symbol)
                                point = symbol_info.point
                                if i.type ==1:
                                    new_sl = i.price_current + (float(parameters[i.symbol][0]) * point)
                                else:
                                    new_sl = i.price_current - (float(parameters[i.symbol][0]) * point)
                                request = {
                                                "action": mt5.TRADE_ACTION_SLTP,
                                                "position": i.ticket,
                                                "sl": new_sl,
                                        }
                                mt5.order_send(request)  
                    elif i.profit > 0:
                         profit_cache[i.ticket]=i.profit

                elif (int(parameters[i.symbol][2]) == 3): # currently reg but ai in label

                    data = pd.DataFrame(mt5.copy_rates_from_pos(i.symbol, mt5.TIMEFRAME_M1, 0, 200)).iloc[:, 4:5]
                    upper, lower, slope, predictions_arima = systemic.garima_position(data["close"])
                    if (np.abs(i.price_current - i.price_open) > 0.5 * np.abs(i.sl - i.price_open)) & (i.profit > 0) & (i.sl != i.price_open):  # but must happen only once

                        if i.type == 0:
                            if (i.price_current>upper):
                                request={
                                    'action' : mt5.TRADE_ACTION_DEAL,
                                    'type' : mt5.ORDER_TYPE_SELL,
                                    'price' : mt5.symbol_info_tick(i.symbol).bid,
                                    'symbol' : i.symbol,
                                    'volume' : i.volume,
                                    'position' : i.ticket,
                                     }
                                mt5.order_send(request)
                        elif i.type == 1:
                            if (i.price_current<lower):
                                request={
                                    'action' : mt5.TRADE_ACTION_DEAL,
                                    'type' : mt5.ORDER_TYPE_BUY,
                                    'price' : mt5.symbol_info_tick(i.symbol).ask,
                                    'symbol' : i.symbol,
                                    'volume' : i.volume,
                                    'position' : i.ticket,
                                     }
                                mt5.order_send(request)


            profit_cache = {key: profit_cache[key] for key in profit_cache if key in tickets}
            return profit_cache,positions_symbols