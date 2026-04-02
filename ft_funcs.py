import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
import datetime
import warnings
from matplotlib.patches import Patch
warnings.filterwarnings('ignore')

def data_collector(ticker:dict, start_date:datetime, end_date:datetime):
    data = yf.download(list(ticker.keys()), start = start_date, end = end_date)
    data = data.stack().reset_index()
    data.columns = ['Date', 'Ticker', 'Close', 'High', 'Low', 'Open', 'Volume']
    data['Pick'] = data['Ticker'].map(ticker)
    sp = yf.download('^GSPC', start=start_date, end=end_date)
    sp = sp.stack().reset_index()
    sp.columns = ['Date', 'Ticker', 'Close', 'High', 'Low', 'Open', 'Volume']
    data2 = pd.merge(data, sp, on='Date', how='left', suffixes=('', '_SP'))
    if data2['Close_SP'].isnull().any():
        data2['Close_SP'] = data2['Close_SP'].fillna(method='ffill')
    if data2['Open_SP'].isnull().any():
        data2['Open_SP'] = data2['Open_SP'].fillna(method='ffill')
    return data2

def performance_stock(ticker:str, data:pd.DataFrame):
    pick = data[data['Ticker'] == ticker]['Pick'].iloc[0]
    change = data[(data['Ticker'] == ticker) & (data['Date'] == data['Date'].max())]['Close'].reset_index(drop = True)[0] - data[(data['Ticker'] == ticker) & (data['Date'] == data['Date'].min())]['Open'].reset_index(drop = True)[0]
    if pick == 'Sell':
        ret = -change /data[(data['Ticker'] == ticker) & (data['Date'] == data['Date'].min())]['Open'].reset_index(drop = True)[0] * 100
    else:
        ret = change / data[(data['Ticker'] == ticker) & (data['Date'] == data['Date'].min())]['Open'].reset_index(drop = True)[0] * 100
    sp_change = data[(data['Ticker'] == ticker) & (data['Date'] == data['Date'].max())]['Close_SP'].reset_index(drop = True)[0] - data[(data['Ticker'] == ticker) & (data['Date'] == data['Date'].min())]['Open_SP'].reset_index(drop = True)[0]
    sp_ret = sp_change / data[(data['Ticker'] == ticker) & (data['Date'] == data['Date'].min())]['Open_SP'].reset_index(drop = True)[0] * 100
    return ret, pick, sp_ret

def results_summary(data:pd.DataFrame, tickers:dict):
    results = {ticker: performance_stock(ticker, data) for ticker in list(tickers.keys())}
    return pd.DataFrame(results, index=['Return (%)', 'Pick', 'SP Return (%)']).T

def merge_and_evaluate(results_list:list, key_list:list, tol:float): 
    all_results = pd.concat(results_list, keys=key_list)
    all_results.index.names = ['Date', 'Ticker']
    all_results['Success'] = np.where((all_results['Pick'] == 'Buy') & (all_results['Return (%)'] - all_results['SP Return (%)'] > tol), 1,
                                np.where((all_results['Pick'] == 'Sell') & (all_results['Return (%)'] - all_results['SP Return (%)'] > tol), 1, 
                                         np.where((all_results['Pick'] == 'Hold') & (abs(all_results['Return (%)'] - all_results['SP Return (%)']) <= tol), 1,
                                         0)))
    return all_results

def plot_results(data:pd.DataFrame, tickers:dict, steps:int):
    plt.figure(figsize=(10, 6))
    for ticker in tickers.keys():
        ticker_data = data[data['Ticker'] == ticker]
        ticker_data['Vals_base'] = ticker_data['Close'] / ticker_data['Close'].iloc[0] * 100
        plt.plot(ticker_data['Date'], ticker_data['Vals_base'], label=f"{ticker} Base Value", linewidth=2)
    sp_data = data[data['Ticker'] == list(tickers.keys())[0]]
    sp_data['Vals_base_SP'] = sp_data['Close_SP'] / sp_data['Close_SP'].iloc[0] * 100
    plt.plot(sp_data['Date'], sp_data['Vals_base_SP'], label="S&P 500 Base Value", linestyle='--', linewidth=2)
    plt.hlines(100, xmin=data['Date'].min(), xmax=data['Date'].max(), colors='black', linestyles='dotted')
    plt.title("Stock and S&P 500 Performance")
    plt.xlabel("Date")
    plt.ylabel("Base Value % change")
    plt.legend()
    plt.xticks(ticks=np.arange(data['Date'].min(), data['Date'].max(), step=datetime.timedelta(days=steps)))
    return plt.gcf()

def performance_by_date(data:pd.DataFrame, date:str, weight_buy:float, weight_sell:float, weight_hold:float):
    if weight_buy + weight_sell + weight_hold == 1:
        date_data = data[data.index.get_level_values('Date') == date]
        weight_buy_return = pd.Series(0, index=date_data.index)
        weight_sell_return = pd.Series(0, index=date_data.index)
        weight_hold_return = pd.Series(0, index=date_data.index)
        for i in range(len(date_data)):
            if date_data['Pick'].iloc[i] == 'Buy':
                weight_buy_return.iloc[i] = date_data['Return (%)'].iloc[i] * weight_buy
            elif date_data['Pick'].iloc[i] == 'Sell':
                weight_sell_return.iloc[i] = date_data['Return (%)'].iloc[i] * weight_sell
            else:
                weight_hold_return.iloc[i] = date_data['Return (%)'].iloc[i] * weight_hold
        avg_return = weight_buy_return.sum() + weight_sell_return.sum() + weight_hold_return.sum() 
        avg_sp_return = date_data['SP Return (%)'].mean()
        return avg_return, avg_sp_return
    else: print("Weights must sum up to 1")

def plot_all_results(data:pd.DataFrame, date_list:list, weight_buy:float, weight_sell:float, weight_hold:float):
    plt.figure(figsize=(10,6))
    avg_sp_returns = []
    for date in date_list:
        avg_return, avg_sp_return = performance_by_date(data, date, weight_buy, weight_sell, weight_hold)
        avg_sp_returns.append(avg_sp_return)
        plt.bar(date, avg_return, color = 'green' if avg_return > 0 else 'red') 
    plt.plot(date_list, avg_sp_returns, '-x', label=f'SP Return', color = 'black')
    plt.hlines(0, xmin=date_list[0], xmax=date_list[-1], colors='black')
    legend_elements = [
        plt.Line2D([0], [0], marker='x', color='black', label='SP Return', linestyle='-', markersize=8),
        Patch(facecolor='green', label='FT Return (Positive)'),
        Patch(facecolor='red', label='FT Return (Negative)')
    ]
    plt.legend(handles=legend_elements)
    plt.xlabel('Date')
    plt.ylabel('Average Return (%)')
    plt.title('Average Return of FT Picks vs SP Return by Date of Pick')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return plt.gcf()