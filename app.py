#main operating file with gui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTime, QTimer
from threading import Thread
import sys
import MetaTrader5 as mt5
import trade_module
import pandas as pd
import data_preparator

class Application:
    holding = True  #TODO
    def __init__(self):
        self.app = QApplication(sys.argv)
        #main app window
        self.window = QWidget()
        self.thread = None
        self.settings_to_trade=data_preparator.system_data.load_dicts()
        self.settings_to_show = {key: self.dict_to_frame(key) for key in self.settings_to_trade.keys()}
        self.window_visual_packet()
        self.strategy_choice=self.combobox3.currentText()
        self.algo_trader = None

        self.window.show()

   
    def window_visual_packet(self):
            ####TABELA USTAWIĆ WYGLĄDY ADA
            self.window_tb = QWidget()
            self.window_tb.setWindowTitle('DataFrame Editor')
            self.window_tb.setStyleSheet("background-color: #11131E;")

            self.layout = QVBoxLayout()
            self.window_tb.setLayout(self.layout)
            self.table_widget = QTableWidget()
            self.table_widget.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 12px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';"+
                "background: #11131E;}"
            )
            self.window_tb.setFixedWidth(400)
            self.window_tb.setFixedHeight(350)


            self.input_box = QLineEdit()
            self.layout.insertWidget(0, self.input_box)

            self.combo_box = QComboBox()
            self.combo_box.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"+
                "*:pressed{color: '#435CD1'}"
            )
            self.layout.addWidget(self.combo_box)
            self.input_box.setMinimumHeight(40)

            self.input_box.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"  
            )

            self.combo_box.setMinimumHeight(40)
            self.combo_box.addItems(self.settings_to_show.keys())
            self.control_label = QLabel("Controls: BEP-1 trailing_stop-2 AI-3 flat-4")
            self.layout.insertWidget(3,self.control_label)
            self.control_label.setStyleSheet(
                "*{font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"
            )
            self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # set row height to fixed
            self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
            self.table_widget.verticalHeader().setVisible(False)


            self.layout.addWidget(self.table_widget)

            self.add_row_button = QPushButton('Add Row')
            self.add_row_button.setMinimumHeight(30)
            self.add_row_button.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"+
                "*:hover{background: '#5271FF';}"+
                "*:hover{border: 1px solid '#5271FF';}"+
                "*:pressed{background: '#435CD1'}"
            )  
            self.layout.addWidget(self.add_row_button)

            self.save_button = QPushButton('Save Changes')
            self.save_button.setMinimumHeight(40)
            self.save_button.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"+
                "*:hover{background: '#5271FF';}"+
                "*:hover{border: 1px solid '#5271FF';}"+
                "*:pressed{background: '#435CD1'}"
            )  
            self.layout.addWidget(self.save_button)

            self.combo_box.currentIndexChanged.connect(self.change_dataframe)
            self.add_row_button.clicked.connect(self.add_row)
            self.save_button.clicked.connect(self.save_changes)

            self.table_widget.horizontalHeader().setStyleSheet("QHeaderView::section {background: '#1E233B';}")
            self.table_widget.verticalHeader().setStyleSheet("QHeaderView::section {background: '#1E233B';}")

            ###########

        ###########################
        #css nagłówków tabelki
        ##############
        #button otwierający ustawienia z tabelą
            self.open_button = QPushButton('Change settings')
            self.open_button.clicked.connect(self.show_table)
            self.open_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
            self.open_button.setMinimumSize(140, 40)
            self.open_button.setMaximumSize(140, 40)
            self.open_button.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 14px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"+
                "*:hover{background: '#5271FF';}"+
                "*:hover{border: 1px solid '#5271FF';}"+
                "*:pressed{background: '#435CD1'}"
            )

            #button start/hold
            self.start_button = QPushButton('Start')
            self.start_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
            self.start_button.setMinimumSize(130, 45)
            self.start_button.setMaximumSize(130, 45)
            self.start_button.setStyleSheet(
                "*{border: 1px solid '#FF66C4';"+
                "font-size: 17px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"+
                "*:hover{background: '#5271FF';}"+
                "*:hover{border: 1px solid '#5271FF';}"+
                "*:pressed{background: '#435CD1'}"
            )
            #wigdet łączący switch i onoff_label (podpis on/off)
            self.onoff = QWidget()
            self.onoff_label = QLabel("System status:")
            self.onoff_label.setStyleSheet(
                "*{font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"
            )
            #On/Off, niby ma się włączać/wyłączać, ale nie wiem kiedy
            self.switch = QLabel("Off")
            self.switch.setStyleSheet(
                "*{color: '#FF3A3A';"+
                "font-size: 18px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "border: 1px solid '#8C52FF';}"
                )
                
            self.switch.setMinimumSize(150, 50)




            #zmiana na hold i z powrotem
            self.start_button.clicked.connect(self.on_start_button_clicked)
            #layout okna z tabelką
            #layout widgetu On/Off
            self.onoff_layout = QVBoxLayout(self.onoff)
            self.onoff_layout.addWidget(self.onoff_label)
            self.onoff_layout.addWidget(self.switch)

            #logo w lewym górnym rogu okna window
            self.image = QtGui.QPixmap("4.png")
            self.logo = QLabel()
            self.logo.setPixmap(self.image.scaled(200, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.logo.setAlignment(QtCore.Qt.AlignLeft)
            self.logo.setStyleSheet("margin: 0px 0px 10px 10px;")
            #ikonka na pasku okna
            self.icon = QIcon("Trustbridge Analitics (3).png")
            self.app.setWindowIcon(self.icon)


            #linia oddzielająca logo od reszty
            self.line = QFrame()
            self.line.setFrameShape(QFrame.HLine)
            self.line.setFixedHeight(1)
            self.line.setStyleSheet("color: #010517;")

            #widget łączący combobox2(drop down) z jego labelem w głównym oknie window
            self.drop1 = QWidget()
            self.drop_layout1 = QVBoxLayout(self.drop1)

            self.combobox2 = QComboBox()
            self.combobox2.addItems(self.settings_to_show.keys())
            self.combobox2.setMinimumSize(120, 40)
            self.combobox2.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"+
                "*:pressed{color: '#435CD1'}"
            )
            #podpis combobox2
            self.drop_label1 = QLabel("Settings")
            self.drop_layout1.addWidget(self.drop_label1)
            self.drop_layout1.addWidget(self.combobox2)
            self.drop_label1.setStyleSheet(
                "*{font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"
            )
            self.combobox2.setCursor(QCursor(QtCore.Qt.PointingHandCursor))

            #widget łączący combobox3(drop down) z jego labelem w głównym oknie window
            self.drop2 = QWidget()
            self.drop_layout2 = QVBoxLayout(self.drop2)

            self.combobox3 = QComboBox()
            self.combobox3.addItems(["macd_trade",'macd_backtest',"SVM_scalp","system_testing"])
            self.combobox3.setMinimumSize(120, 40)
            self.combobox3.setStyleSheet(
                "*{border: 1px solid '#8C52FF';"+
                "font-size: 13px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"+
                "*:pressed{color: '#435CD1'}"
            )
            #podpis combobox3
            self.drop_label2 = QLabel("Select")
            self.drop_layout2.addWidget(self.drop_label2)
            self.drop_layout2.addWidget(self.combobox3)
            self.drop_label2.setStyleSheet(
                "*{font-size: 13px;"+
            "font-family: 'Ubuntu Medium', serif;"+
                "color: 'white';}"
            )
            self.combobox3.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
               
            #główny leyout głównego okna aplikacji
            self.grid = QGridLayout(self.window)
            self.window.setLayout(self.grid)

            self.grid.setColumnStretch(0, 1)
            self.grid.setColumnStretch(1, 1)
            self.grid.setColumnStretch(2, 1)
            self.grid.setRowStretch(0, 6)
            self.grid.setRowStretch(1, 1)
            self.grid.setRowStretch(2, 10)
            self.grid.setRowStretch(3, 10)

            self.grid.addWidget(self.logo, 0, 0, 0, 0, Qt.AlignLeft)
            self.grid.addWidget(self.open_button, 3, 1, Qt.AlignCenter)
            self.grid.addWidget(self.drop1, 2, 1, Qt.AlignCenter)
            self.grid.addWidget(self.drop2, 2, 2, Qt.AlignCenter)
            self.grid.addWidget(self.start_button, 3, 2, Qt.AlignCenter)
            self.grid.addWidget(self.line, 1, 0, 1, -1)
            self.grid.addWidget(self.onoff, 3, 0, Qt.AlignCenter)
    
            self.window.setWindowTitle("Trustbridge Analytics")
            self.window.setFixedWidth(600)
            self.window.setFixedHeight(280)
            self.window.setStyleSheet("background-color: #11131E;")


    
   
   
    def activate(self):
        self.choosen_setting= self.combobox2.currentText() 
        self.choosen_strategy=self.combobox3.currentText()
        self.action_dict=data_preparator.system_data.load_dicts()[self.choosen_setting]
        self.switch.setText("Activating platform...")
        self.switch.setStyleSheet(
            "*{color: '#FFAC3E';"+
            "font-size: 18px;"+
            "font-family: 'Ubuntu Medium', serif;"+
            "border: 1px solid '#69FF18';}"
            )
        try:

            mt5.initialize()
        except:
            self.switch.setText("Error! unable to activete platform...")
            self.switch.setStyleSheet(
            "*{color: '#FF3A3A';"+
            "font-size: 18px;"+
            "font-family: 'Ubuntu Medium', serif;"+
            "border: 1px solid '#FF3A3A';}"
            )

        self.switch.setText("Preparing data...")
   #     self.algo_trader = trade_module.system(self.action_dict,self.choosen_strategy,self.choosen_setting)
        try:    
            self.algo_trader = trade_module.system(self.action_dict,self.choosen_strategy,self.choosen_setting)
            self.algo_trader.system_hold = False
            
            self.thread = Thread(target=self.algo_trader.trade, args=(self.action_dict,))#TODO
            self.thread.start()



            """ 

            if self.choosen_strategy == "macd_trade":
                self.thread = Thread(target=self.algo_trader.trade, args=(self.action_dict,))
                self.thread.start()
            elif self.choosen_strategy == "SVM_scalp":
                self.thread = Thread(target=self.algo_trader.trade, args=(self.action_dict,))
                self.thread.start()
            elif self.choosen_strategy == "system_testing":
                self.thread = Thread(target=self.algo_trader.trade, args=(self.action_dict,))
                self.thread.start() """
            #elif self.choosen_strategy == "macd_backtest":
                #self.thread = Thread(target=backtest_module.system.backtest)
                #self.thread.start()   
            self.switch.setText("On")
            self.start_button.setText('Hold')
            self.switch.setStyleSheet(
                "*{color: '#69FF18';"+
                "font-size: 18px;"+
                "font-family: 'Ubuntu Medium', serif;"+
                "border: 1px solid '#69FF18';}"
                )                #          
        except Exception as e:
            print("An error occurred:", e)
            self.switch.setText("Error! unable to initialize system...")
            self.switch.setStyleSheet(
            "*{color: '#FF3A3A';"+
            "font-size: 18px;"+
            "font-family: 'Ubuntu Medium', serif;"+
            "border: 1px solid '#69FF18';}")


    def on_start_button_clicked(self):

        if self.algo_trader== None :
            self.activate()

        elif self.algo_trader.system_hold :
            self.algo_trader.system_hold = False
            self.activate()            
        else:
            self.start_button.setText('Start')
            self.algo_trader.system_hold = True
            self.switch.setText("OFF")
            self.switch.setStyleSheet(
            "*{color: '#FF3A3A';"+
            "font-size: 18px;"+
            "font-family: 'Ubuntu Medium', serif;"+
            "border: 1px solid '#FF3A3A';}"
            )


    ##############GUI

    def dict_to_frame(self,i):
        self.action_dict=data_preparator.system_data.load_dicts()
        self.action_dict_2=pd.DataFrame(self.action_dict[i].values())
        self.action_dict_2.insert(0, 'new_column',self.action_dict[i].keys())
        self.action_dict_2.columns =['Symbol','Sl', 'TP', 'Control','Bep']
        return self.action_dict_2

    def frame_to_dict(self,frame):
        self.dic ={}
        for i,row in frame.iterrows():
            self.dic[row[0]]=list(row[1:])
        return self.dic







    def load_data(self,data):
        self.table_widget.setRowCount(data.shape[0])
        
        self.table_widget.setColumnCount(data.shape[1])
        self.header_labels = list(data.columns)
    

        self.table_widget.setHorizontalHeaderLabels(self.header_labels)
        
        for row in range(data.shape[0]):
            for col in range(data.shape[1]):
                item = QTableWidgetItem(str(data.iat[row, col]))
                self.table_widget.setItem(row, col, item)
            
            

        self.table_widget.setColumnWidth(0,60)
        self.table_widget.setColumnWidth(1,70)
        self.table_widget.setColumnWidth(2,70)
        self.table_widget.setColumnWidth(3,70)
        self.table_widget.setColumnWidth(4,80)
        self.table_widget.setStyleSheet(
        "*{border: 1px solid '#8C52FF';"+
        "font-size: 12px;"+
        "font-family: 'Ubuntu Medium', serif;"+
        "color: 'white';"+
        "background: #11131E;}"
    )
        self.table_widget.horizontalHeader().setStyleSheet("QHeaderView::section {background: '#1E233B';}")
        self.table_widget.verticalHeader().setStyleSheet("QHeaderView::section {background: '#1E233B';}")
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # set row height to fixed
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table_widget.verticalHeader().setVisible(False)
        
    def change_dataframe(self,index):

        self.layout.removeWidget(self.table_widget)
        self.table_widget = QTableWidget()
        self.layout.insertWidget(3, self.table_widget)
        self.selected_option = self.combo_box.currentText()
        #layout.addWidget(table_widget)

        self.load_data(self.settings_to_show[self.selected_option])



    def save_changes(self):
        self.current_df = self.get_dataframe_from_table()
        self.index = self.combo_box.currentText() #Index
        self.input_name = self.input_box.text().strip()

        if self.input_name:
            self.new_df = pd.DataFrame(self.current_df)
            self.settings_to_show[self.input_name] = self.new_df
            self.base=data_preparator.system_data.load_dicts()
            self.base[self.input_name]=self.frame_to_dict(self.new_df)

            data_preparator.system_data.save_dicts(self.base)
            self.combo_box.addItem(self.input_name)
            self.combobox2.addItem(self.input_name)

            self.input_box.clear()

        else:
            self.settings_to_show[self.index] = self.current_df
            self.new_setting=self.frame_to_dict(self.current_df)
            self.base=data_preparator.system_data.load_dicts()
            self.base[self.index]=self.new_setting
            data_preparator.system_data.save_dicts(self.base)

            data_preparator.system_data.load_dicts()

    def get_dataframe_from_table(self):
        self.row_count = self.table_widget.rowCount()
        self.col_count = self.table_widget.columnCount()

        self.data = {}
        for col in range(self.col_count):
            self.column_data = []
            for row in range(self.row_count):
                self.item = self.table_widget.item(row, col)
                if self.item is not None:
                    self.column_data.append(self.item.text())
                else:
                    self.combobox = self.table_widget.cellWidget(row, col)
                    if self.combobox is not None:
                        self.column_data.append(self.combobox.currentText())
                    else:
                        self.column_data.append(None)
            self.data[self.table_widget.horizontalHeaderItem(col).text()] = self.column_data
        return pd.DataFrame(self.data)


    def add_row(self):
        self.current_row_count = self.table_widget.rowCount()
        self.table_widget.insertRow(self.current_row_count)


    def show_table(self):
        self.settings_to_trade=data_preparator.system_data.load_dicts()
        self.load_data(self.settings_to_show['default'])
        self.window_tb.show()

    









