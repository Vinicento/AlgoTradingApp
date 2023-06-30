import json
import os
import ta
from ta import momentum, trend
import numpy as np
import pandas as pd
from datetime import datetime
import MetaTrader5 as mt5
import joblib
from sklearn.preprocessing import StandardScaler
from scipy import signal
from datetime import datetime, timedelta
from sklearn.ensemble import BaggingClassifier


class operating_data:

    def __init__(self, symbols, strategy):
        self.symbols = symbols
        self.data = {}
        self.signal = 0
        if strategy == "macd_trade":

            self.data_prepare = self.MACD_data_preparator
            self.data = {}
            for i in self.symbols:
                self.data[i] = pd.DataFrame(mt5.copy_rates_from_pos(i, mt5.TIMEFRAME_M5, 0, 400)).iloc[:, 1:5]
        elif strategy == "system_testing":
            self.data_prepare = self.system_test_data_preparator
        elif strategy == "SVM_scalp":
            self.scaler = StandardScaler()
            self.data_prepare = self.SVM_scalp_data_preparator
            self.model = joblib.load('GBPUSD.pkl')
        """ self.model={}
            for i in self.symbols:
                self.model[i]=joblib.load(f'{i}.pkl') """

    # SVM DATA
    @staticmethod
    def SVM_scalp_data_preprocess(tick_data, h1_data, d1_data, scaler, *args):
        tick_data = tick_data.fillna(method='ffill')


        h1_data['dir'] = int(0)
        h1_data.loc[h1_data['close'] > h1_data['close'].shift(), 'dir'] = int(2)
        h1_data.loc[h1_data['close'] == h1_data['close'].shift(), 'dir'] = int(1)
        h1_data['dir'] = h1_data['dir'].shift()

        d1_data["datetime"] = d1_data["datetime"].apply(
            lambda x: datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'))
        d1_data['dir_d1'] = 0
        d1_data.loc[d1_data['close'] > d1_data['close'].shift(), 'dir_d1'] = 2
        d1_data.loc[d1_data['close'] == d1_data['close'].shift(), 'dir_d1'] = 1
        d1_data['dir_d1'] = d1_data['dir_d1'].shift()

        d1_data['date'] = d1_data['datetime'].str.split().str[0]
        h1_data['date'] = h1_data['datetime'].str.split().str[0]
        tick_data['date'] = tick_data['datetime'].str.split().str[0]

        h1_data['time'] = h1_data['datetime'].str.split().str[1]
        h1_data['time'] = h1_data["datetime"].apply(lambda x: int(x[0:2]))
        tick_data['time'] = tick_data['datetime'].str.split().str[1]
        tick_data['time'] = tick_data["datetime"].apply(lambda x: int(x[0:2]))

        h1_data.dropna(inplace=True)
        tick_data.dropna(inplace=True)
        d1_data.dropna(inplace=True)


        data = pd.merge(tick_data, h1_data, on=['date', 'time'], how='left')

        data = pd.merge(data, d1_data, on=['date'], how='left')

        data = data[['time', 'bid', 'ask', 'dir', 'dir_d1']]

        #tutaj wrzuciliśmy pełen dataset z api do bezpośredniego przeniesienia do  predict

        data = data.fillna(method='ffill')

        # zmiana wartości z konkretnych kwot na procent zmiany
        data["ask_change"] = data["ask"].pct_change(fill_method=None)
        data["bid_change"] = data["bid"].pct_change(fill_method=None)

        # Atrybuty : średnie
        data['price'] = data['ask'] + data['bid'] / 2
        # wybrane zostało kilka okresów i policzona została procentowa odległość ceny od średniej
        data['sma500_distance'] = 1 - (data["price"].rolling(500).mean() / data['price'])
        data['sma200_distance'] = 1 - (data["price"].rolling(200).mean() / data['price'])
        data['sma50_distance'] = 1 - (data["price"].rolling(50).mean() / data['price'])
        data['sma20_distance'] = 1 - (data["price"].rolling(20).mean() / data['price'])

        # oraz średnia dla procentowej zmiany ceny rozdzielona na cenę kupna i sprzedaży
        data['sma50_ask'] = data["ask_change"].rolling(50).mean()
        data['sma50_bid'] = data["bid_change"].rolling(50).mean()
        data['sma150_ask'] = data["ask_change"].rolling(150).mean()
        data['sma150_bid'] = data["bid_change"].rolling(150).mean()

        # pozostałe atrybuty

        stoch_rsi_ask = ta.momentum.StochRSIIndicator(data['ask_change'], 140, 30, 30, False)
        stoch_rsi_bid = ta.momentum.StochRSIIndicator(data['bid_change'], 140, 30, 30, False)

        aaron_ask = ta.trend.AroonIndicator(data['ask_change'], 250)
        aaron_bid = ta.trend.AroonIndicator(data['bid_change'], 250)

        data['aaron_bid'] = aaron_bid.aroon_indicator()
        data['aaron_ask'] = aaron_ask.aroon_indicator()

        data['roc_ask'] = ta.momentum.roc(data['ask_change'], 140)

        data['ulcer_index_ask'] = ta.volatility.ulcer_index(data['ask_change'], 140)
        data['ulcer_index_bid'] = ta.volatility.ulcer_index(data['bid_change'], 140)

        data['stoch_ask'] = stoch_rsi_ask.stochrsi()
        data['stoch_bid'] = stoch_rsi_bid.stochrsi()

        data["std200_ask"] = 1 - (data["ask_change"].rolling(200).std() / data['ask_change'])
        data["std200_bid"] = 1 - (data["bid_change"].rolling(200).std() / data['bid_change'])

        # usunięcie zbędnych kolumn oraz zamiana wartoći nieskońćzonych
        data = data.drop(columns=['price','bid', 'ask'])
        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.fillna(method='ffill')
        # usuniecie wierszy pustych ( ostatnie wiersze dla których nie dało się policzyć wskaźników)
        data.dropna(inplace=True)

        # TODO kluczowe jest skalowanie czasu pod instrument wgl wartości mają duże znaczenie i wutrenowany na btc ( duże kwoty ) na eurusd nie ta skala
        # usuniecie wierszy pustych ( ostatnie wiersze dla których nie dało się policzyć wskaźników)
        data_scaled = scaler.fit_transform(data)
        data_scaled = pd.DataFrame(data_scaled, columns=data.columns)
        data_scaled = data_scaled.fillna(0)


        return data_scaled.iloc[-1:]

    @staticmethod
    def SVM_scalp_data_preparator(i, scaler, model, *args):

        tick_param = mt5.copy_ticks_range(i, datetime.now() - timedelta(hours=6),datetime.now() + timedelta(hours=4), mt5.COPY_TICKS_ALL)
        tick_param = pd.DataFrame(tick_param)
        tick_param['time'] = pd.to_datetime(tick_param['time'], unit='s')
        tick_param.reset_index()
        tick_param = tick_param[['time', 'bid', 'ask']]
        tick_param.rename(columns={'time': 'datetime'}, inplace=True)
        tick_param['datetime'] = tick_param['datetime'].astype(str)

        h1_data = mt5.copy_rates_range(i, mt5.TIMEFRAME_H1, datetime.now() - timedelta(hours=10),datetime.now() + timedelta(hours=4))
        h1_data = pd.DataFrame(h1_data)
        h1_data['time'] = pd.to_datetime(h1_data['time'], unit='s')
        h1_data.reset_index()
        h1_data.rename(columns={'time': 'datetime'}, inplace=True)
        h1_data['datetime'] = h1_data['datetime'].astype(str)

        d1_data = mt5.copy_rates_from(i, mt5.TIMEFRAME_D1, datetime.now(), 5)
        d1_data = [list([x[0], x[4]]) for x in d1_data]
        d1_data = pd.DataFrame(d1_data, columns=['datetime', 'close'])

        new_ticks = operating_data.SVM_scalp_data_preprocess(tick_param.iloc[-505:, :], h1_data, d1_data, scaler)
        new_ticks = new_ticks.fillna(0)

        predict_row = model.predict(new_ticks)
        return predict_row, None

    # System_testing_data
    @staticmethod
    def system_test_data_preparator(i, *args):
        data = pd.DataFrame(mt5.copy_rates_from_pos(i, mt5.TIMEFRAME_M5, 0, 5)).iloc[:, 1:5]
        signal = 0
        if (data["close"].iloc[-1]) < (data["close"].iloc[-2]):
            signal = 1
        elif (data["close"].iloc[-1]) > (data["close"].iloc[-2]):
            signal = 2
        maxes = data['high'].tail(5).max()
        lows = data['low'].tail(5).min()
        return signal, [maxes, lows]

    # MACD DATA

    @staticmethod
    def timestamp_to_readable(shit, timestamp):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def peaks_and_valleys(data):
        # Find peaks(max)
        widths = np.arange(1, 5)  # Widths range should cover the expected width of peaks of interest.
        peaks = signal.find_peaks_cwt(data['macd'], widths)
        inv_data_y = data['macd'] * (-1)  # Tried 1/data_y but not better.
        valleys = signal.find_peaks_cwt(inv_data_y, widths)
        range_size = 8  # Range size to look for neighboring indices
        # Replace peak indices

        for b in range(0, 2):
            for i in range(len(peaks)):
                peak_index = peaks[i]
                start_index = max(peak_index - range_size, 0)
                end_index = min(peak_index + range_size, len(data) - 1)
                range_data = data[start_index:end_index + 1]
                max_close_index = range_data['high'].idxmax()   #zmiana macd to high
                peaks[i] = max_close_index

        peaks = np.unique(peaks)
        # Replace valley indices
        for b in range(0, 2):
            for i in range(len(valleys)):
                valley_index = valleys[i]
                start_index = max(valley_index - range_size, 0)
                end_index = min(valley_index + range_size, len(data) - 1)
                range_data = data[start_index:end_index + 1]
                min_close_index = range_data['low'].idxmin()   #zmiana macd to low
                valleys[i] = min_close_index
            valleys = np.unique(valleys)

        data['peak_valleys'] = 0
        # Set 1 for peaks where MACD > 0
        data.loc[(data.index.isin(peaks)) & (data['macd'] > 0), 'peak_valleys'] = 1
        # Set 2 for valleys where MACD < 0
        data.loc[(data.index.isin(valleys)) & (data['macd'] < 0), 'peak_valleys'] = 2

        data.loc[(data['peak_valleys'] == 1) & ((data['high'].shift(1) > data['high']) | (data['high'].shift(-1) > data['high'])), 'peak_valleys'] = 0 #zmiana macd to high
        # Check if the previous or next row's 'macd' is lower for 'peak_valley' == 2
        data.loc[(data['peak_valleys'] == 2) & ((data['low'].shift(1) < data['low']) | (data['low'].shift(-1) < data['low'])), 'peak_valleys'] = 0 #zmiana macd to low
        return data

    @staticmethod
    def MACD_data_preparator(i, *args):
        data = pd.DataFrame(mt5.copy_rates_from_pos(i, mt5.TIMEFRAME_M5, 0, 800)).iloc[:, 1:5]
        data['macd'] = ta.trend.macd(data['close'], 26, 12)  # macd
        data['macdiff'] = ta.trend.ema_indicator(data['close'], window=12, fillna=False) - ta.trend.ema_indicator(
            data['close'], window=26, fillna=False)
        conditions = [(data['macdiff'] > 0) & (data['macdiff'] > data['macdiff'].shift()),
                      (data['macdiff'] > 0) & (data['macdiff'] <= data['macdiff'].shift()),
                      (data['macdiff'] <= 0) & (data['macdiff'] > data['macdiff'].shift()),
                      (data['macdiff'] <= 0) & (data['macdiff'] <= data['macdiff'].shift()),
                      ]
        # 0 equal 1-red 2-green
        data["candle"] = np.where(data["open"] > data["close"], 1, np.where(data["open"] < data["close"], 2, 0))

        # green-4,greenish-3,reddish-2,red-1
        choices = [4, 2, 3, 1]

        data['macd_color'] = np.select(conditions, choices, default=0)

        data = operating_data.peaks_and_valleys(data)
        data_copy_peaks = data[data['peak_valleys'] == 1].copy()  # peaks of prices
        data_copy_valleys = data[data['peak_valleys'] == 2].copy()  # valleys of prices

        mean_close = np.mean(abs(data['high'] - data['low']))/2




        #classic approach
        peak_1=( ((data_copy_peaks['high'] - mean_close) > (data_copy_peaks['high'].shift())) & (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift()))
        peak_2=( ((data_copy_peaks['high'] - mean_close) > (data_copy_peaks['high'].shift(2))) & (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift(2)) & (data_copy_peaks['high'].shift(2)>data_copy_peaks['high'].shift()))
        peak_3=( ((data_copy_peaks['high'] - mean_close) > (data_copy_peaks['high'].shift(3))) & (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift(3)) & (data_copy_peaks['high'].shift(3)>data_copy_peaks['high'].shift(2)) & (data_copy_peaks['high'].shift(2)>data_copy_peaks['high'].shift()) )
        peak_4=( ((data_copy_peaks['high'] - mean_close) > (data_copy_peaks['high'].shift(4))) & (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift(4)) & (data_copy_peaks['high'].shift(4)>data_copy_peaks['high'].shift(3)) & (data_copy_peaks['high'].shift(3)>data_copy_peaks['high'].shift(2)) & (data_copy_peaks['high'].shift(3)>data_copy_peaks['high'].shift()))

        valley_1=(( (data_copy_valleys['low'] + mean_close) < (data_copy_valleys['low'].shift())) & (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift()))
        valley_2 = (((data_copy_valleys['low'] + mean_close) < (data_copy_valleys['low'].shift(2))) & (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift(2)) & (data_copy_valleys['low'].shift(2) < data_copy_valleys['low'].shift()))
        valley_3 = (((data_copy_valleys['low'] + mean_close) < (data_copy_valleys['low'].shift(3))) & (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift(3)) & (data_copy_valleys['low'].shift(3) < data_copy_valleys['low'].shift(2)) & (data_copy_valleys['low'].shift(2) < data_copy_valleys['low'].shift()))
        valley_4 = (((data_copy_valleys['low'] + mean_close) < (data_copy_valleys['low'].shift(4))) & (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift(4)) & (data_copy_valleys['low'].shift(4) < data_copy_valleys['low'].shift(3)) & (data_copy_valleys['low'].shift(3) < data_copy_valleys['low'].shift(2)) & (data_copy_valleys['low'].shift(3) < data_copy_valleys['low'].shift()))

        #reversed approach
        #ra_peak_1=( ((data_copy_peaks['high'] + mean_close) < (data_copy_peaks['high'].shift())) & (data_copy_peaks['macd'] > data_copy_peaks['macd'].shift()))
        #ra_peak_2=( ((data_copy_peaks['high'] + mean_close) < (data_copy_peaks['high'].shift(2))) & (data_copy_peaks['macd'] > data_copy_peaks['macd'].shift(2)) & (data_copy_peaks['high'].shift(2)>data_copy_peaks['high'].shift()))
        #ra_peak_3=( ((data_copy_peaks['high'] + mean_close) < (data_copy_peaks['high'].shift(3))) & (data_copy_peaks['macd'] > data_copy_peaks['macd'].shift(3)) & (data_copy_peaks['high'].shift(3)>data_copy_peaks['high'].shift(2)) & (data_copy_peaks['high'].shift(2) > data_copy_peaks['high'].shift()) )
        #ra_peak_4=( ((data_copy_peaks['high'] + mean_close) < (data_copy_peaks['high'].shift(4))) & (data_copy_peaks['macd'] > data_copy_peaks['macd'].shift(4)) & (data_copy_peaks['high'].shift(4)>data_copy_peaks['high'].shift(3)) & (data_copy_peaks['high'].shift(3) > data_copy_peaks['high'].shift(2)) & (data_copy_peaks['high'].shift(3)>data_copy_peaks['high'].shift()))

        #ra_valley_1=(( (data_copy_valleys['low'] - mean_close) > (data_copy_valleys['low'].shift())) & (data_copy_valleys['macd'] < data_copy_valleys['macd'].shift()))
        #ra_valley_2 = (((data_copy_valleys['low'] - mean_close) > (data_copy_valleys['low'].shift(2))) & (data_copy_valleys['macd'] < data_copy_valleys['macd'].shift(2)) & (data_copy_valleys['low'].shift(2) < data_copy_valleys['low'].shift()))
        #ra_valley_3 = (((data_copy_valleys['low'] - mean_close) > (data_copy_valleys['low'].shift(3))) & (data_copy_valleys['macd'] < data_copy_valleys['macd'].shift(3)) & (data_copy_valleys['low'].shift(3) < data_copy_valleys['low'].shift(2)) & (data_copy_valleys['low'].shift(2) < data_copy_valleys['low'].shift()))
        #ra_valley_4 = (((data_copy_valleys['low'] - mean_close) > (data_copy_valleys['low'].shift(4))) & (data_copy_valleys['macd'] < data_copy_valleys['macd'].shift(4)) & (data_copy_valleys['low'].shift(4) < data_copy_valleys['low'].shift(3)) & (data_copy_valleys['low'].shift(3) < data_copy_valleys['low'].shift(2)) & (data_copy_valleys['low'].shift(3) < data_copy_valleys['low'].shift()))





        divergency_indexes_peaks = data_copy_peaks[peak_1 | peak_2 | peak_3 | peak_4].index.tolist()

        divergency_indexes_valleys = data_copy_valleys[valley_1 | valley_2 | valley_3 | valley_4].index.tolist()

        '''
        divergency_indexes_peaks = data_copy_peaks[( ((data_copy_peaks['high'] - mean_close) > data_copy_peaks['high'].shift()) & (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift())) |
                                                             ( ((data_copy_peaks['high'] - mean_close) > data_copy_peaks['high'].shift(2)) &
                                                             (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift(2))) & (data_copy_peaks['macd']>0)].index.tolist()


        divergency_indexes_valleys = data_copy_valleys[( ((data_copy_valleys['low'] + mean_close) < data_copy_valleys['low'].shift()) &
                                                                 (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift())) |
                                                                 ( ((data_copy_valleys['low'] + mean_close) < data_copy_valleys['low'].shift(2)) &
                                                                 (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift(2))) & (data_copy_valleys['macd']<0)].index.tolist()
        '''
        #full version
        '''divergency_indexes_peaks = data_copy_peaks[( ((data_copy_peaks['close'] - mean_close) > data_copy_peaks['close'].shift()) &
                                                     (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift())) |
                                                     ( ((data_copy_peaks['close'] - mean_close) > data_copy_peaks['close'].shift(2)) &
                                                     (data_copy_peaks['close'].shift() < (data_copy_peaks['id'].shift() * data_copy_peaks['slope_2'] + data_copy_peaks['inter_2'])) &
                                                     (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift(2))) & (data_copy_peaks['macd']>0)].index.tolist()


        divergency_indexes_valleys = data_copy_valleys[( ((data_copy_valleys['close'] + mean_close) < data_copy_valleys['close'].shift()) &
                                                         (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift())) |
                                                         ( ((data_copy_valleys['close'] + mean_close) < data_copy_valleys['close'].shift(2)) &
                                                         (data_copy_valleys['close'].shift() > (data_copy_valleys['id'].shift() * data_copy_valleys['slope_2'] + data_copy_valleys['inter_2'])) &
                                                         (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift(2))) & (data_copy_valleys['macd']<0)].index.tolist()'''


        '''divergency_indexes_peaks = data_copy_peaks[( ((data_copy_peaks['close']) > data_copy_peaks['close'].shift()) &
                                                     (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift())) |
                                                     ( ((data_copy_peaks['close']) > data_copy_peaks['close'].shift(2)) &
                                                     (data_copy_peaks['close'].shift() < (data_copy_peaks['id'].shift() * data_copy_peaks['slope_2'] + data_copy_peaks['inter_2'])) &
                                                     (data_copy_peaks['macd'] < data_copy_peaks['macd'].shift(2))) & (data_copy_peaks['macd']>0)].index.tolist()'''

        '''divergency_indexes_valleys = data_copy_valleys[( ((data_copy_valleys['close'] ) < data_copy_valleys['close'].shift()) &
                                                         (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift())) |
                                                         ( ((data_copy_valleys['close'] ) < data_copy_valleys['close'].shift(2)) &
                                                         (data_copy_valleys['close'].shift() > (data_copy_valleys['id'].shift() * data_copy_valleys['slope_2'] + data_copy_valleys['inter_2'])) &
                                                         (data_copy_valleys['macd'] > data_copy_valleys['macd'].shift(2))) & (data_copy_valleys['macd']<0)].index.tolist()'''

        data_copy_valleys['close'].shift()
        data['divergence'] = 0
        data.loc[divergency_indexes_peaks, 'divergence'] = 1
        data.loc[divergency_indexes_valleys, 'divergence'] = 2

        # signals long 2 short 0 neutral 1
        data["signal"] = 0



        # indices_signal_long= data[((data['macd_color'].shift()!=1)&(data['macd_color'].shift(2)==1)) & (data['macd']<0-macd_mean)&(((data['divergence'].shift(2)==2) & long_div_2)|((data['divergence'].shift(3)==2)&long_div_3))].index.tolist()
        # indices_signal_short= data[((data['macd_color'].shift()!=4)&(data['macd_color'].shift(2)==4))& (data['macd']>0+macd_mean)&(((data['divergence'].shift(2)==0)&short_div_2)|((data['divergence'].shift(3)==0)&short_div_3))].index.tolist()

        #not flat market restriction

        macd_color_long = ((data['macd_color'].shift(2) == 1) & (data['macd_color'].shift(3) == 1) & (data['macd_color'].shift(4) == 1))
        macd_color_short= ((data['macd_color'].shift(2) == 4) & (data['macd_color'].shift(3) == 4) & (data['macd_color'].shift(4) == 4))



        indices_signal_long = data[( ((data['divergence'].shift() == 2) & (data['macd'] >= data['macd'].shift())) |
                                     ((data['divergence'].shift(2) == 2) & ((data['macd'] >= data['macd'].shift()) & (data['macd'].shift() >= data['macd'].shift(2)))) |
                                     ((data['divergence'].shift(3) == 2) & ((data['macd'] >= data['macd'].shift()) & (data['macd'].shift() >= data['macd'].shift(2)) & (data['macd'].shift(2) >= data['macd'].shift(3))))) &
                                     ((data['macd_color'].shift() == 3) | (data['macd_color'].shift() ==4) ) & macd_color_long].index.tolist()

        indices_signal_short = data[( ((data['divergence'].shift() == 1) & (data['macd'] <= data['macd'].shift())) |
                                      ((data['divergence'].shift(2) == 1) & ((data['macd'] <= data['macd'].shift()) & (data['macd'].shift() <= data['macd'].shift(2)))) |
                                      ((data['divergence'].shift(3) == 1) & ((data['macd'] <= data['macd'].shift()) & (data['macd'].shift() <= data['macd'].shift(2)) & (data['macd'].shift(2) <= data['macd'].shift(3))))) &
                                      ((data['macd_color'].shift() == 2) | (data['macd_color'].shift() == 1) ) & macd_color_short].index.tolist()

        # base doesnt open positions
        #indices_signal_long = data[(((data['divergence'].shift() == 2) & (data['macd'] > data['macd'].shift()+(data['macd'].shift()*0.5))) | ((data['divergence'].shift(2) == 2) & (data['macd'] > (data['macd'].shift()+(data['macd'].shift()*0.5))) & (data['macd'].shift() > (data['macd'].shift(2)+(data['macd'].shift(2)*0.5)))) | ((data['divergence'].shift(3) == 2) & ((data['macd'] > data['macd'].shift()+(data['macd'].shift()*0.5))) & (data['macd'].shift() > (data['macd'].shift(2)+(data['macd'].shift(2)*0.5))) & (data['macd'].shift(2) > (data['macd'].shift(3)+(data['macd'].shift(3)*0.5))))) & ( (data['macd_color'].shift() ==2) | (data['macd_color'] ==4))].index.tolist()
        #indices_signal_short = data[(((data['divergence'].shift() == 1) & (data['macd'] < (data['macd'].shift()-(data['macd'].shift()*0.5)))) | ((data['divergence'].shift(2) == 1) & (data['macd'] < (data['macd'].shift()-(data['macd'].shift()*0.5))) & (data['macd'].shift() < (data['macd'].shift(2)-(data['macd'].shift(2)*0.5)))) | ((data['divergence'].shift(3) == 1) & (data['macd'] < (data['macd'].shift()-(data['macd'].shift()*0.5))) & (data['macd'].shift() < (data['macd'].shift(2)-(data['macd'].shift(2)*0.5))) & (data['macd'].shift(2) < (data['macd'].shift(3)-(data['macd'].shift(3)*0.5))))) & ( (data['macd_color'].shift() ==3) | (data['macd_color'] ==1))].index.tolist()

        data.loc[indices_signal_long, 'signal'] = 2
        data.loc[indices_signal_short, 'signal'] = 1
        prediction = data['signal'].iloc[-1]
        maxes = data['high'].tail(5).max()
        lows = data['low'].tail(5).min()

        return prediction, [maxes, lows]


class system_data:

    @staticmethod
    def load_dicts():
        file_path = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'settings.json')

        with open(file_path, "r") as f:
            dicts = json.load(f)
        return dicts

    @staticmethod
    def save_dicts(dicts):
        file_path = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'settings.json')

        with open(file_path, "w") as f:
            json.dump(dicts, f)

    def timestamp_to_readable(shit, timestamp):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
