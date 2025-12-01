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
import ctypes
import time
import threading
import multiprocessing

# Windows上multiprocessing需要设置启动方法
if sys.platform == 'win32':
    multiprocessing.set_start_method('spawn', force=True)

config_path=glv.get('config_path')

def _flash_screen_process(duration):
    """在独立进程中运行的闪烁函数"""
    try:
        import tkinter as tk
        import ctypes
        
        # 确保窗口始终置顶
        def set_window_topmost(hwnd):
            try:
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                user32 = ctypes.windll.user32
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
            except:
                pass
        
        root = tk.Tk()
        
        # 先设置窗口大小和位置，再设置其他属性
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        
        # 先设置置顶和透明度
        root.attributes('-topmost', True)
        root.attributes('-alpha', 0.0)
        root.configure(bg='red')
        
        # 设置窗口大小和位置为全屏
        root.geometry(f'{width}x{height}+0+0')
        
        # 最后设置无边框（必须在geometry之后）
        root.overrideredirect(True)
        
        # 获取窗口句柄并强制置顶
        try:
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            if hwnd == 0:
                hwnd = root.winfo_id()
            set_window_topmost(hwnd)
        except:
            pass
        
        flash_count = int(duration * 2)
        
        def flash_loop(count=0):
            if count < flash_count:
                if count % 2 == 0:
                    root.attributes('-alpha', 0.5)
                    root.lift()
                    root.focus_force()
                    # 每次闪烁时重新设置置顶
                    try:
                        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
                        if hwnd == 0:
                            hwnd = root.winfo_id()
                        set_window_topmost(hwnd)
                    except:
                        pass
                else:
                    root.attributes('-alpha', 0.0)
                root.update()
                root.after(500, lambda: flash_loop(count + 1))
            else:
                root.attributes('-alpha', 0.0)
                root.update()
                root.destroy()
                root.quit()
        
        root.after(100, lambda: flash_loop(0))
        root.mainloop()
        
    except Exception as e:
        # 静默处理错误
        pass

def flash_window(duration=3):
    """闪烁整个屏幕，持续指定秒数 - 支持PyCharm和控制台运行"""
    try:
        # 方法1: 尝试使用subprocess调用测试脚本（更可靠）
        test_script = os.path.join(os.path.dirname(__file__), 'flash_screen.py')
        if os.path.exists(test_script):
            import subprocess
            if sys.platform == 'win32':
                # Windows系统 - 使用pythonw.exe避免显示控制台
                python_exe = sys.executable
                pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
                if os.path.exists(pythonw_exe):
                    python_exe = pythonw_exe
                subprocess.Popen([python_exe, test_script, str(duration)], 
                               creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            else:
                subprocess.Popen([sys.executable, test_script, str(duration)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            return
        
        # 方法2: 使用multiprocessing（备选方案）
        process = multiprocessing.Process(target=_flash_screen_process, args=(duration,))
        process.daemon = True
        process.start()
    except Exception:
        # 静默处理错误
        pass
def index_decision(x):
    if 'IH' in x:
        return '000016.SH'
    if 'IM' in x:
        return '000852.SH'
    if 'IF' in x:
        return '000300.SH'
def portfolio_withdraw():
    target_date = datetime.today()
    target_date = gt.strdate_transfer(target_date)
    inputpath=glv.get('portfolio')
    inputpath=str(inputpath)+f" Where portfolio_name='Timeselecting_future_sz50_pro' and valuation_date='{target_date}'"
    df=gt.data_getting(inputpath,config_path)
    df['index_type']=df['code'].apply(lambda x: index_decision(x))
    
    # 检查weight列是否均大于等于0
    if df['weight'].ge(0).all():
        # 如果均大于等于0，输出weight大于0的index_type列表
        result = df[df['weight'] > 0]['index_type'].unique().tolist()
    else:
        # 否则输出空列表
        result = []
    
    return result
    
def indexdata_withdraw(zhi_sun,valid_code):
    target_date = datetime.today()
    target_date = gt.strdate_transfer(target_date)
    available_date = gt.last_workday_calculate(target_date)
    start_date = pd.to_datetime(available_date) - timedelta(days=10)
    start_date = gt.strdate_transfer(start_date)
    df_index = gt.indexData_withdraw(None, start_date, available_date, ['close'], False)
    df_index_today = gt.indexData_withdraw(None, target_date, target_date, ['close'], True)
    df_index = df_index[df_index['code'].isin(valid_code)]
    df_index_today = df_index_today[df_index_today['code'].isin(valid_code)]
    df_index = pd.concat([df_index, df_index_today])
    # 按code分组处理
    results = {}
    for code in valid_code:
        df_code = df_index[df_index['code'] == code].copy()
        if len(df_code) == 0:
            continue

        # 按日期排序，确保数据顺序正确
        df_code = df_code.sort_values('valuation_date')

        # 计算过去5日的平均值
        if len(df_code) >= 5:
            mean = df_code['close'].tail(5).mean()
        else:
            # 如果数据不足5日，使用所有可用数据
            mean = df_code['close'].mean()

        # 获取现价（最后一个值）
        last_index = df_code['close'].iloc[-1]
        proportion = (last_index - mean) / mean
        proportion = proportion * 100
        if last_index < mean * (1 - zhi_sun):
            flash_window(5)  # 闪烁3秒
            print('请尽快平仓止损,请尽快平仓止损,请尽快平仓止损,请尽快平仓止损')
            print(f"{code} 当前点位为{last_index:.2f}, 五日线为{mean:.2f}, 比例为{proportion:.2f}%")

        else:
            print(f"{code} 当前点位为{last_index:.2f}, 五日线为{mean:.2f}, 比例为{proportion:.2f}%")
    return results
def monitor_main(activate=True):
    if activate==True:
        valid_code = portfolio_withdraw()
        if len(valid_code) > 0:
            print(f"目前多头为{valid_code}")
            indexdata_withdraw(0.005, valid_code)
if __name__ == '__main__':
    monitor_main()
    # # 取消下面的注释来测试闪烁功能
    # # test_flash()
    #
    # # 正常运行主程序
    # indexdata_withdraw(-0.05)