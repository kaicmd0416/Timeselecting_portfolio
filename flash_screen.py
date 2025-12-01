# -*- coding: utf-8 -*-
"""独立的闪烁测试脚本"""
import tkinter as tk
import ctypes
import time
import sys

def set_window_topmost(hwnd):
    """设置窗口置顶"""
    try:
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        user32 = ctypes.windll.user32
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        return True
    except:
        return False

def flash_screen(duration=3):
    """闪烁屏幕"""
    try:
        root = tk.Tk()
        
        # 先设置窗口大小和位置，再设置其他属性
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        
        # 先设置全屏和置顶
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

if __name__ == '__main__':
    duration = 3
    if len(sys.argv) > 1:
        try:
            duration = float(sys.argv[1])
        except:
            pass
    flash_screen(duration)

