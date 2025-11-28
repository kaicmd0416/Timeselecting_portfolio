from matplotlib import pyplot as plt
import global_setting.global_dic as glv
import pandas as pd
import os
import sys
path = os.getenv('GLOBAL_TOOLSFUNC_new')
sys.path.append(path)
import global_tools as gt
import os
import yaml
from datetime import datetime, timedelta
import calendar
import numpy as np
config_path=glv.get('config_path')
class portfolio_construction:
    def __init__(self):
        target_date=datetime.today()
        target_date=gt.strdate_transfer(target_date)
        self.target_date=target_date
        self.now = datetime.now().replace(tzinfo=None)  # 当前时间
    def sql_path_withdraw(self):
        workspace_path = os.path.abspath(os.path.dirname(__file__))
        config_path = os.path.join(workspace_path, 'global_setting', 'timeselecting_portfolio_sql.yaml')
        return config_path
    def decision_30050(self, rolling_window):
        available_date = gt.last_workday_calculate(self.target_date)
        # 将available_date转换为datetime对象，减去一年，再转换回字符串格式
        available_dt = datetime.strptime(available_date, '%Y-%m-%d')
        start_dt = available_dt - timedelta(days=400)
        start_date = start_dt.strftime('%Y-%m-%d')
        df_index = gt.indexData_withdraw(None, start_date, available_date, ['pct_chg'], False)
        df_index = gt.sql_to_timeseries(df_index)
        df_index = df_index[['valuation_date', '000016.SH', '000300.SH']]
        df_index_today=gt.indexData_withdraw(None, self.target_date, self.target_date, ['pct_chg'], True)
        df_index_today = gt.sql_to_timeseries(df_index_today)
        df_index_today = df_index_today[['valuation_date', '000016.SH', '000300.SH']]
        df_index=pd.concat([df_index,df_index_today])
        df_index.set_index('valuation_date', inplace=True, drop=True)
        df_return = df_index.rolling(rolling_window).sum()
        df_return.dropna(inplace=True)
        df_return['difference'] = df_return['000016.SH'] - df_return['000300.SH']
        df_return['quantile_0.1'] = df_return['difference'].rolling(252).quantile(0.1)
        df_return['quantile_0.9'] = df_return['difference'].rolling(252).quantile(0.9)
        df_return.dropna(inplace=True)
        df_return['signal_momentum'] = 0
        df_return.loc[df_return['difference'] >= 0, ['signal_momentum']] = '000016.SH'
        df_return.loc[df_return['difference'] < 0, ['signal_momentum']] = '000300.SH'
        df_return.loc[df_return['difference'] < df_return['quantile_0.1'], ['signal_momentum']] = '000016.SH'
        df_return.loc[df_return['difference'] > df_return['quantile_0.9'], ['signal_momentum']] = '000300.SH'
        df_return.reset_index(inplace=True)
        signal = df_return[df_return['valuation_date'] ==self.target_date]['signal_momentum'].tolist()[0]
        return signal
    def timeselecting_signalWithdraw(self):
        """
        提取L0信号数据，如果target_date的combine_value为0.5，则查找过去最近一天不为0.5的值

        Returns:
            float: combine_value值
        """
        inputpath_mean = glv.get('L0_signalData_prod')
        # 提取全部日期的数据
        df = gt.data_getting(inputpath_mean, config_path)

        # 确保日期格式正确
        df['valuation_date'] = pd.to_datetime(df['valuation_date'])
        df = df.sort_values(by='valuation_date')

        # 找到target_date对应的数据
        target_datetime = pd.to_datetime(self.target_date)
        target_data = df[df['valuation_date'] == target_datetime]

        if target_data.empty:
            raise ValueError(f"未找到 {self.target_date} 的数据")

        combine_value = target_data['final_value'].iloc[0]
        return combine_value

    def future_finding(self):
        """
        找到target_date所在月份的第三个星期五，并根据比较结果返回相应的月份代码

        Returns:
            str: 如果target_date小于第三个星期五，返回YYMM格式；如果大于，返回下个月MM
        """
        # 将target_date转换为datetime对象
        if isinstance(self.target_date, str):
            target_dt = datetime.strptime(self.target_date, '%Y-%m-%d')
        else:
            target_dt = self.target_date

        year = target_dt.year
        month = target_dt.month

        # 找到该月第一个星期五
        first_day = datetime(year, month, 1)
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)

        # 计算第三个星期五
        third_friday = first_friday + timedelta(days=14)

        # 检查第三个星期五是否为工作日
        if not gt.is_workday(third_friday.strftime('%Y-%m-%d')):
            # 如果不是工作日，找到下一个工作日
            third_friday = gt.next_workday_calculate(third_friday.strftime('%Y-%m-%d'))
            third_friday = datetime.strptime(third_friday, '%Y-%m-%d')

        # 比较target_date和第三个星期五
        if target_dt < third_friday:
            # 返回当前年份的后两位 + 当月的月份 (YYMM)
            return f"{str(year)[-2:]}{month:02d}"
        else:
            # 返回下个月的月份 (MM)
            if month < 12:
                next_month = month + 1
                next_year = year
            else:
                next_month = 1
                next_year = year + 1
            return f"{str(next_year)[-2:]}{next_month:02d}"
    def signal_generator(self,index_type):
        available_date = gt.last_workday_calculate(self.target_date)
        start_date=pd.to_datetime(available_date) - timedelta(days=10)
        start_date=gt.strdate_transfer(start_date)
        df_index = gt.indexData_withdraw(index_type, start_date, available_date, ['close'], False)
        df_index_today=gt.indexData_withdraw(index_type, self.target_date, self.target_date, ['close'], True)
        df_index=pd.concat([df_index,df_index_today])
        mean = np.mean(df_index['close'].tolist()[-5:])
        last_index = df_index['close'].tolist()[-1]
        print(f"{index_type}当前点位为{last_index},五日线为{mean}")
        if mean <= last_index:
            return True
        else:
            return False
    def future_portfolio_construction_pro(self):
        combine_value = self.timeselecting_signalWithdraw()
        future_num=self.future_finding()
        df_hszz = pd.DataFrame()
        df_szzz = pd.DataFrame()
        code_list_hszz = ['IM' + str(future_num), 'IF' + str(future_num)]
        code_list_szzz = ['IM' + str(future_num), 'IH' + str(future_num)]
        if combine_value > 0.5:
            signal=self.signal_generator('中证1000')
            if signal==True:
                weight_list_hszz = [1, 0]
                weight_list_szzz = [1, 0]
            else:
                weight_list_hszz = [1, -1]
                weight_list_szzz = [1, -1]
        elif combine_value ==0.5:
            signal=self.signal_generator('中证1000')
            signal1 = self.signal_generator('沪深300')
            signal2 = self.signal_generator('上证50')
            if signal==True and signal1==True:
                weight_list_hszz = [0.5,0.5]
            if signal==True and signal2==True:
                weight_list_szzz = [0.5,0.5]
            if signal==True and signal2==False:
                weight_list_szzz = [0.5, 0]
            if signal==True and signal1==False:
                weight_list_hszz = [0.5, 0]
            if signal==False and signal1==True:
                weight_list_hszz = [0, 0.5]
            if signal==False and signal2==True:
                weight_list_szzz = [0, 0.5]
            if signal==False and signal2==False:
                weight_list_szzz = [0, 0]
            if signal == False and signal1 == False:
                weight_list_hszz = [0, 0]
            else:
                print(signal,signal1,signal2)
        else:
            signal1 = self.signal_generator('沪深300')
            signal2=self.signal_generator('上证50')
            if signal1==True:
                weight_list_hszz = [0, 1]
            else:
                weight_list_hszz=[-1,1]
            if signal2==True:
               weight_list_szzz = [0, 1]
            else:
                weight_list_szzz=[-1,1]
        df_hszz['code'] = code_list_hszz
        df_szzz['code'] = code_list_szzz
        df_hszz['weight'] = weight_list_hszz
        df_szzz['weight'] = weight_list_szzz
        df_hszz['portfolio_name'] = 'Timeselecting_future_hs300_pro'
        df_szzz['portfolio_name'] = 'Timeselecting_future_sz50_pro'
        df_hszz['valuation_date'] = self.target_date
        df_szzz['valuation_date'] = self.target_date
        return df_hszz, df_szzz
    def future_portfolio_construction_mix(self):
        combine_value = self.timeselecting_signalWithdraw()
        future_num=self.future_finding()
        signal_300=self.decision_30050(5)
        df_final = pd.DataFrame()
        if combine_value > 0.5:
            code_list = ['IM' + str(future_num), 'IH' + str(future_num)]
            signal=self.signal_generator('中证1000')
            if signal==True:
                weight_list = [1, 0]
            else:
                weight_list = [1, -1]
        elif combine_value ==0.5:
            signal=self.signal_generator('中证1000')
            signal1 = self.signal_generator('上证50')
            code_list = ['IM' + str(future_num), 'IH' + str(future_num)]
            if signal==True and signal1==True:
                weight_list = [0.5,0.5]
            if signal==True and signal1==False:
                weight_list = [0.5, 0]
            if signal==False and signal1==True:
                weight_list = [0, 0.5]
            if signal == False and signal1 == False:
                weight_list = [0, 0]
            else:
                print(signal,signal1)
        else:
            if signal_300 == '000300.SH':
                code_list = ['IM' + str(future_num), 'IF' + str(future_num)]
            else:
                code_list = ['IM' + str(future_num), 'IH' + str(future_num)]
            chi_name = gt.index_mapping(signal_300, 'chi_name')
            signal1 = self.signal_generator(chi_name)
            if signal1==True:
                weight_list = [0, 1]
            else:
                weight_list=[-1,1]
        df_final['code'] = code_list
        df_final['weight'] = weight_list
        df_final['portfolio_name'] = 'Timeselecting_future'
        df_final['valuation_date'] = self.target_date
        return df_final
    def portfolio_to_holding(self,df,df_stock, df_hstock, df_etf, df_option, df_future, df_convertible_bond, df_index):
        df_info, df_detail = gt.portfolio_analyse_manual(df, df_stock, df_hstock, df_etf, df_option, df_future, df_convertible_bond, df_index,account_money=2800000, cost_stock=0, cost_etf=0,
                                                         cost_future=0, cost_option=0, cost_convertiblebond=0,
                                                         realtime=True)
        df_detail=df_detail[['valuation_date','code','quantity','portfolio_name']]
        return df_detail
    def portfolio_saving_main(self):
        df_stock, df_hstock, df_etf, df_option, df_future, df_convertible_bond, df_index = gt.mktData_withdraw(
            self.target_date, self.target_date, True)
        df_future_mix=self.future_portfolio_construction_mix()
        df_futurehs_pro, df_futuresz_pro = self.future_portfolio_construction_pro()
        inputpath_sql=self.sql_path_withdraw()
        sm=gt.sqlSaving_main(inputpath_sql, 'Portfolio', delete=True)
        for df in [df_futurehs_pro, df_futuresz_pro,df_future_mix]:
            df=self.portfolio_to_holding(df,df_stock, df_hstock, df_etf, df_option, df_future, df_convertible_bond, df_index)
            portfolio_name=df['portfolio_name'].tolist()[0]
            df['valuation_date']=self.target_date
            df['update_time']=self.now
            sm.df_to_sql(df,'portfolio_name',portfolio_name)
def running_main():
    time = datetime.now()
    if time.hour == 14 and time.minute < 30:
       gt.table_manager2(config_path, 'portfolio_new', 'portfolio_timeselecting')
    pc=portfolio_construction()
    pc.portfolio_saving_main()
