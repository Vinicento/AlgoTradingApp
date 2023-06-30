#trade module
from sklearn.preprocessing import StandardScaler
import pandas as pd
import MetaTrader5 as mt5
import joblib
import systemic
import data_preparator
from datetime import datetime,timedelta
class system:
    def __init__(self,parameters,strategy,setting):
        self.strategy=strategy
        self.setting = setting
        self.parameters=parameters
        self.symbols=tuple(parameters.keys())
        self.system_hold=True
        self.profit_cache={}
        self.strategy_arguments=[]
        self.timing={}
        if strategy == "macd_trade":
            self.data_prepare = data_preparator.operating_data.MACD_data_preparator
            self.data={}
            for i in self.symbols:
                self.data[i]=pd.DataFrame(mt5.copy_rates_from_pos(i, mt5.TIMEFRAME_M5, 0, 200)).iloc[:,1:5]
            self.washing = True
            
        elif strategy == "system_testing":
            self.data_prepare = data_preparator.operating_data.system_test_data_preparator
            self.washing = True
        elif strategy == "SVM_scalp":
            self.scaler=StandardScaler()
            self.data_prepare = data_preparator.operating_data.SVM_scalp_data_preparator
            self.model=joblib.load('svm_trader.pkl')
            self.strategy_arguments=[self.scaler,self.model]

        """ self.model={}
            for i in self.symbols:
                self.model[i]=joblib.load(f'{i}.pkl') """





         # Pass parameters to the systemic class

    def trade(self,action_dict):
        self.profit_cache={}

        while not self.system_hold:
             
            self.profit_cache,self.positions_symbols,=systemic.systemic.position_check(action_dict,self.profit_cache)
            self.free_symbols=set(self.symbols)-set(self.positions_symbols)
            self.free_symbols =[element for element in self.free_symbols if self.timing.get(element,0 ) < datetime.now().timestamp()]
            print(self.free_symbols)

            if mt5.terminal_info()[2] != True:
                print("connection_problem!!!!!!!!!!")
                print(mt5.last_error())
            for i in self.free_symbols:

                self.signal,self.data_rest = self.data_prepare(i,*self.strategy_arguments)
                
                if (self.signal==2):
                    self.timing[i]=(datetime.now()+timedelta(minutes=30)).timestamp()
                    systemic.systemic.send_order(i, 0.01, True, False, id_position=None, pct_tp=self.parameters[i][1], pct_sl=self.parameters[i][0], comment=" No specific comment", magic=0,washing=self.washing,data=self.data_rest)
                elif(self.signal==1):
                    self.timing[i]=(datetime.now()+timedelta(minutes=30)).timestamp()
                    systemic.systemic.send_order(i, 0.01, False, True, id_position=None, pct_tp=self.parameters[i][1], pct_sl=self.parameters[i][0], comment=" No specific comment", magic=0,washing=self.washing,data=self.data_rest)


