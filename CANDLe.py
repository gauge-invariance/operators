import tkinter as tk
from tkinter import ttk
import pandas as pd
import numpy as np
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import requests
import json
from datetime import datetime, timedelta
import threading
from matplotlib.gridspec import GridSpecFromSubplotSpec
import time
from collections import defaultdict

class CryptoChartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CANDLe")
        self.root.geometry("1200x800")
        
        # 品种列表
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'XAUUSDT']
        self.current_symbol_index = 0
        
        # 时间周期列表（分钟）
        self.timeframes = [60, 120, 240, 480, 720, 1440]  # 1h, 2h, 4h, 8h, 12h, 1d
        self.timeframe_labels = ['1h', '2h', '4h', '8h', '12h', '1d']
        
        # 存储数据
        self.data = {symbol: {tf: None for tf in self.timeframes} for symbol in self.symbols}
        self.macd_data = {symbol: {tf: None for tf in self.timeframes} for symbol in self.symbols}
        self.is_loading = False
        
        # 创建界面
        self.setup_ui()
        
        # 加载数据
        self.load_all_data()
        
    def setup_ui(self):
        # 顶部控制栏
        control_frame = tk.Frame(self.root, bg='#2c2c2c', height=60)
        control_frame.pack(fill=tk.X, padx=0, pady=0)  # 去掉所有边距
        control_frame.pack_propagate(False)
        
        # 品种切换按钮
        btn_frame = tk.Frame(control_frame, bg='#2c2c2c')
        btn_frame.pack(side=tk.LEFT, padx=5, pady=10)
        
        self.symbol_buttons = []
        for i, symbol in enumerate(self.symbols):
            btn = tk.Button(
                btn_frame,
                text=symbol,
                font=('Arial', 12, 'bold'),
                bg='#4a4a4a' if i != 0 else '#0078d7',
                fg='white',
                width=10,
                command=lambda idx=i: self.switch_symbol(idx)
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.symbol_buttons.append(btn)
        
        # 状态标签
        self.status_label = tk.Label(
            control_frame,
            text="加载数据中...",
            font=('Arial', 10),
            bg='#2c2c2c',
            fg='#888888'
        )
        self.status_label.pack(side=tk.RIGHT, padx=20)
        
        # 刷新按钮
        refresh_btn = tk.Button(
            control_frame,
            text="刷新数据",
            font=('Arial', 10),
            bg='#4a4a4a',
            fg='white',
            command=self.refresh_data
        )
        refresh_btn.pack(side=tk.RIGHT, padx=10)
        
        # 创建主图表框架 - 去掉所有边距
        self.chart_frame = tk.Frame(self.root, bg='#1e1e1e')
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 创建6个子图（2行3列），每个子图分为上下两部分（80% K线 + 20% MACD）
        self.fig = Figure(figsize=(30, 20), dpi=50, facecolor='white')
        
        # 使用GridSpec创建2行3列的主网格，去掉所有边距
        # left, right, bottom, top 控制子图区域在figure中的位置
        main_gs = self.fig.add_gridspec(2, 3, hspace=0.06, wspace=0.06,
                                        left=0.01, right=0.98, bottom=0.02, top=0.99)
        
        self.kline_axes = []  # K线图轴
        self.macd_axes = []   # MACD图轴
        
        for i in range(6):
            row = i // 3
            col = i % 3
            
            # 每个单元格再分成上下两部分：80% K线 + 20% MACD
            inner_gs = GridSpecFromSubplotSpec(2, 1, subplot_spec=main_gs[row, col], 
                                               height_ratios=[4, 1], hspace=0)
            
            # K线图（上面80%）
            kline_ax = self.fig.add_subplot(inner_gs[0])
            kline_ax.set_facecolor('white')
            kline_ax.tick_params(colors='#888888')
            kline_ax.spines['bottom'].set_color("#0A9954")
            kline_ax.spines['top'].set_color("#0A9954")
            kline_ax.spines['left'].set_color('#0A9954')
            kline_ax.spines['right'].set_color('#0A9954')
            # 隐藏X轴标签（让MACD图显示）
            kline_ax.set_xticklabels([])
            kline_ax.tick_params(axis='x', labelsize=0)
            self.kline_axes.append(kline_ax)
            
            # MACD图（下面20%）
            macd_ax = self.fig.add_subplot(inner_gs[1], sharex=kline_ax)
            macd_ax.set_facecolor('white')
            macd_ax.tick_params(colors='#888888')
            macd_ax.spines['bottom'].set_color("#0A9954")
            macd_ax.spines['top'].set_color("#0A9954")
            macd_ax.spines['left'].set_color('#0A9954')
            macd_ax.spines['right'].set_color('#0A9954')
            macd_ax.set_ylabel('MACD', fontsize=8, color='#888888')
            self.macd_axes.append(macd_ax)
        
        self.canvas = FigureCanvasTkAgg(self.fig, self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def fetch_ohlcv(self, symbol, timeframe, limit=80):
        """从Binance获取OHLCV数据"""
        try:
            # Binance API端点
            #base_url = "https://api.binance.com/api/v3/klines"
            base_url = "https://fapi.binance.com/fapi/v1/klines"
            
            # 时间周期映射
            interval_map = {
                60: '1h',
                120: '2h',
                240: '4h',
                480: '8h',
                720: '12h',
                1440: '1d'
            }
            
            # 转换symbol格式
            symbol_map = {
                'BTCUSDT': 'BTCUSDT',
                'ETHUSDT': 'ETHUSDT',
                'XAUUSDT': 'XAUUSDT'
            }
            
            binance_symbol = symbol_map.get(symbol, symbol)
            
            params = {
                'symbol': binance_symbol,
                'interval': interval_map[timeframe],
                'limit': limit*2
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()
            
            if not data:
                print(f"警告: {symbol} {timeframe}分钟 数据为空")
                return None, None

            # 计算MACD
            macd_values = self.calc_MACD(data, 12, 26, 9)
            macdx = macd_values[limit:limit*2] if len(macd_values) >= limit*2 else macd_values[-limit:]

            segp,segn = extract_envl(data[limit:2*limit], macdx)
            infos = self.check_deviation(params,segp, segn)
            #print([round(x,1) for x in macdx])
            #for i in segp:
             #   print([round(y[0],0) for y in i])
            #for i in segn :
             #   print([round(y[0],0) for y in i])

            # 解析数据
            ohlcv = []
            for candle in data[limit:2*limit]:
                ohlcv.append({
                    'time': datetime.fromtimestamp(candle[0] / 1000),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            df = pd.DataFrame(ohlcv)
            df.set_index('time', inplace=True)
            
            return df, macdx, infos
            
        except Exception as e:
            print(f"获取数据失败 {symbol} {timeframe}分钟: {e}")
            return None, None

    def calc_MACD(self, data, fast, slow, window):

        cvals = []
        ema_fast = []
        ema_slow = []
        dif = []
        dea = []
        macd = []
        
        for idx in range(len(data)):
            candle = data[idx]
            cval = float(candle[4])
            cvals.append(cval)
            if(idx < fast - 1):
                ema_fast.append(0)
            elif(idx == fast-1):
                ema_fast.append(float(sum(cvals)/float(fast)))
            else:
                a = float(2.0/float(fast+1.0))
                ema_fast.append(cval*a+(1-a)*ema_fast[-1])
            
            if(idx < slow - 1):
                ema_slow.append(0)
            elif(idx == slow-1):
                ema_slow.append(float(sum(cvals)/float(slow)))
            else:
                b = float(2.0/float(slow+1.0))
                ema_slow.append(cval*b+(1-b)*ema_slow[-1])

            dif.append(ema_fast[-1]-ema_slow[-1])

            c = float(2.0/(float(window)+1.0))
            if (idx >= 1):
                dea.append(float(dif[-1])*c+(1-c)*float(dea[-1]))
            else:
                dea.append(float(0.0))

            macd.append(1.0*(dif[-1]-dea[-1]))
            #if(idx>= len(data)-10):
            #   print(round(macd[-1],1), round(ema_fast[-1],1) ,round(ema_slow[-1],1))
        return macd

    def load_all_data(self):
        """加载所有数据"""
        if self.is_loading:
            return
        
        self.is_loading = True
        self.status_label.config(text="正在加载数据...")
        self.root.update()
        
        def load_thread():
            try:
                infos  = []
                for symbol in self.symbols:
                    for tf in self.timeframes:
                        df, macd, info= self.fetch_ohlcv(symbol, tf)
                        for x in info:
                            infos.append(x)
                        if df is not None and not df.empty:
                            self.data[symbol][tf] = df
                            self.macd_data[symbol][tf] = macd
                        else:
                            # 如果获取失败，生成模拟数据
                            self.data[symbol][tf] = self.generate_mock_data(tf)
                            self.macd_data[symbol][tf] = [0] * len(self.data[symbol][tf])
                        self.root.after(10, lambda: None)

                groups = defaultdict(list)
                mapping = {1: "顶背离",-1: "底背离"}
                cmapping = {1:Colors.GREEN,-1:Colors.CYAN}
                labels = ['BTCUSDT','ETHUSDT','XAUUSDT']
                for x in infos:
                    groups[x[0]].append(x)

                for l in labels:
                    y = groups[l]
                    if len(y)> 0 :
                        print(f"{Colors.YELLOW}{l}{Colors.RESET}")
                    for x in y:
                         print(f"{cmapping[x[6]]}[{x[1]:<3}]  [{x[2]} {x[3]}]->[{x[4]} {x[5]}] [{mapping[x[6]]}]{Colors.RESET}")

                self.root.after(0, self.update_charts)
                self.root.after(0, lambda: self.status_label.config(text="数据已加载"))
                
            except Exception as e:
                print(f"加载数据出错: {e}")
                self.root.after(0, lambda: self.status_label.config(text=f"加载失败: {str(e)[:50]}"))
            finally:
                self.is_loading = False
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def generate_mock_data(self, timeframe):
        return pd.DataFrame()
    
    def update_charts(self):
        """更新图表"""
        symbol = self.symbols[self.current_symbol_index]
        
        for i, (tf, kline_ax, macd_ax) in enumerate(zip(self.timeframes, self.kline_axes, self.macd_axes)):
            df = self.data[symbol].get(tf)
            macd = self.macd_data[symbol].get(tf)
            
            # 清空K线轴
            kline_ax.clear()
            kline_ax.set_facecolor('white')
            kline_ax.tick_params(colors='#888888')
            kline_ax.spines['bottom'].set_color("#0A9954")
            kline_ax.spines['top'].set_color("#0A9954")
            kline_ax.spines['left'].set_color('#0A9954')
            kline_ax.spines['right'].set_color('#0A9954')
            kline_ax.set_xticklabels([])
            kline_ax.tick_params(axis='x', labelsize=0)
            
            # 清空MACD轴
            macd_ax.clear()
            macd_ax.set_facecolor('white')
            macd_ax.tick_params(colors='#888888')
            macd_ax.spines['bottom'].set_color("#0A9954")
            macd_ax.spines['top'].set_color("#0A9954")
            macd_ax.spines['left'].set_color('#0A9954')
            macd_ax.spines['right'].set_color('#0A9954')
            macd_ax.set_ylabel('MACD', fontsize=8, color='#888888')
            
            if df is not None and not df.empty:
                try:
                    # 准备数据
                    plot_data = df[['open', 'high', 'low', 'close']].copy()
                    plot_data.index = pd.to_datetime(plot_data.index)
                    
                    # 绘制K线图
                    custom_style = mpf.make_mpf_style(
                        base_mpf_style='charles',
                        marketcolors=mpf.make_marketcolors(
                            up="#83E0B3",
                            down="#ED5757",
                            edge='inherit',
                            wick='inherit',
                            volume='in'
                        ),
                        rc={
                            'font.size': 7,
                            'xtick.labelsize': 6,
                            'ytick.labelsize': 6,
                            'axes.facecolor': 'white',
                            'figure.facecolor': 'white'
                        }
                    )
                    
                    mpf.plot(
                        plot_data,
                        type='candle',
                        ax=kline_ax,
                        style=custom_style,
                        volume=False,
                        show_nontrading=False,
                        warn_too_much_data=1000
                    )
                    
                    # 绘制MACD在下方
                    if macd is not None and len(macd) == len(df):
                        # 获取MACD的最大绝对值
                        max_abs = max(abs(max(macd)), abs(min(macd))) if macd else 1
                        if max_abs == 0:
                            max_abs = 1
                        
                        # 绘制MACD柱状图
                        x_positions = range(len(macd))
                        for j, val in enumerate(macd):
                            if val >= 0:
                                # 正值：绿色柱子向上
                                color = '#83E0B3'
                                bar_bottom = 0
                                bar_height = val / max_abs
                            else:
                                # 负值：红色柱子向下
                                color = '#ED5757'
                                bar_bottom = val / max_abs
                                bar_height = -val / max_abs
                            
                            macd_ax.bar(j, bar_height, bottom=bar_bottom, 
                                       color=color, width=0.8, alpha=0.7)
                        
                        # 添加零线
                        macd_ax.axhline(y=0, color='#888888', linestyle='-', linewidth=0.5, alpha=0.5)
                        
                        # 设置Y轴范围
                        macd_ax.set_ylim(-1.3, 1.3)
                        
                        # 设置X轴范围与K线一致
                        macd_ax.set_xlim(0, len(df) - 1)
                        
                        # 显示X轴标签
                        macd_ax.tick_params(axis='x', labelsize=8)
                        
                    # 设置K线图标题
                    kline_ax.set_title(
                        f'{self.timeframe_labels[i]}',
                        color='black',
                        fontsize=25,
                        fontweight='bold',
                        x=0.95,
                        y=0.9,
                        loc='right'
                    )
                    kline_ax.tick_params(axis='y', labelsize=10, rotation=0, pad=-1)
                    kline_ax.tick_params(colors='#888888')
                    
                except Exception as e:
                    print(f"绘制 {symbol} {tf}分钟 图表失败: {e}")
                    kline_ax.text(0.5, 0.5, '数据加载失败', 
                                 transform=kline_ax.transAxes, ha='center', va='center',
                                 color='#888888', fontsize=10)
                    macd_ax.text(0.5, 0.5, 'MACD数据加载失败',
                                transform=macd_ax.transAxes, ha='center', va='center',
                                color='#888888', fontsize=8)
            else:
                # 无数据
                kline_ax.text(0.5, 0.5, '无数据', 
                             transform=kline_ax.transAxes, ha='center', va='center',
                             color='#888888', fontsize=10)
                kline_ax.set_title(f'{self.timeframe_labels[i]}', color='black', fontsize=2)
                macd_ax.text(0.5, 0.5, '无MACD数据',
                            transform=macd_ax.transAxes, ha='center', va='center',
                            color='#888888', fontsize=8)
        
        # 不使用tight_layout，而是使用subplots_adjust让子图紧贴边界
        self.fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
        self.canvas.draw()
    
    def switch_symbol(self, index):
        """切换品种"""
        if index == self.current_symbol_index:
            return
        
        self.current_symbol_index = index
        
        # 更新按钮样式
        for i, btn in enumerate(self.symbol_buttons):
            btn.config(bg='#0078d7' if i == index else '#4a4a4a')
        
        self.status_label.config(text=f"切换到 {self.symbols[index]}")
        self.update_charts()
    
    def refresh_data(self):
        """刷新数据"""
        self.load_all_data()

    def check_deviation(self,params,segp,segn):
        vp = []
        vn = []
        #print(f"segP={len(segp)} segn = {len(segn)}")
        #tuple 的结构 (包络macd峰值，包络中某些最高价格平均，包络macd长度， 包络起始时间戳，终止时间戳)
        for x in segp:
            highest_prices = [float(y[1][2]) for y in x]
            highest_prices = sorted(highest_prices,reverse=True)
            highest_prices = highest_prices[0:2]
            high_price_avg = sum(highest_prices)/len(highest_prices)
            macd_peak = max([abs(y[0]) for y in x])
            macd_lens  = len(x)
            start_time = str(datetime.fromtimestamp(x[0][1][0]/1000))
            end_time = str(datetime.fromtimestamp(x[-1][1][0]/1000))
            vp.append((macd_peak,high_price_avg,macd_lens, start_time,end_time))
        for xx in segn:
            lowest_prices = [float(y[1][3]) for y in xx]
            lowest_prices = sorted(lowest_prices, reverse=False)
            lowest_prices = lowest_prices[0:2]
            low_price_avg = sum(lowest_prices)/len(lowest_prices)
            macd_peak = max([abs(y[0]) for y in xx])
            macd_lens = len(xx)
            start_time =str(datetime.fromtimestamp(xx[0][1][0]/1000))
            end_time = str(datetime.fromtimestamp(xx[-1][1][0]/1000))
            vn.append((macd_peak,low_price_avg,macd_lens,start_time,end_time))

        tuple_infos =[]

        if len(vp)  > 1:
            pointer = -1
            for i in range(0,len(vp)-1):
                if vp[i][0] > vp[i+1][0] and vp[i][1]<vp[i+1][1] and vp[i][2] > vp[i+1][2]:
                    pointer = i
            if pointer >= 0:
                #记录最后一次出现背离的序列位置
                i = pointer
                tuple_info = (params['symbol'],params['interval'],vp[i][3],vp[i][4],vp[i+1][3],vp[i+1][4],1)
                tuple_infos.append(tuple_info)
                #print(f"顶背离 {vp[i][3]}->{vp[i+1][3]}")
        if len(vn) > 1:
            pointer = -1
            for j in range(0,len(vn)-1):
                if vn[j][0] > vn[j+1][0] and vn[j][1] > vn[j+1][1] and vn[j][2] + 1 >= vn[j+1][2]:
                    pointer = j
            if pointer >= 0:
                #记录最后一次出现背离的序列位置
                i = pointer
                tuple_info = (params['symbol'],params['interval'],vn[i][3],vn[i][4],vn[i+1][3],vn[i+1][4],-1)
                tuple_infos.append(tuple_info)
                #print(f"底背离 {vn[j][3]}->{vn[j+1][3]}")

        return tuple_infos
    
class Colors:
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    RESET = '\033[0m'
    GREEN = '\033[32m'


def extract_envl(data, macd):

        segp = [] #所有连续正数macd序列的集合
        segn = [] #所有连续负数macd的序列的集合

        temp  = [(macd[0], data[0])]

        for id in range(1,len(macd)):
            if macd[id] * temp[-1][0]< 0:
                #macd开始变号
                if len(temp)>=5:
                    if temp[-1][0]<0:
                        segn.append(temp)
                    else:
                        segp.append(temp)
                    temp  = [(macd[id], data[id])]
                else:
                    #序列太短，放弃这个序列，用新的macd作为新的序列的第一个元素
                    temp  = [(macd[id], data[id])]
            else:
                #macd连续保持同号
                temp.append((macd[id], data[id]))
                if id == len(macd)-1 and len(temp) >=5:
                    if macd[id] > 0:
                        segp.append(temp)
                    else:
                        segn.append(temp)

        return segp, segn

def main():
    root = tk.Tk()
    app = CryptoChartApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()