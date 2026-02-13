#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体工具模块 - 确保中文字体正确加载和应用
"""

import os
from kivy.core.text import LabelBase
from kivy.utils import platform

# 全局字体名称
CHINESE_FONT_NAME = 'ChineseFont'

# 字体文件搜索路径（按优先级排序）
FONT_SEARCH_PATHS = [
    # 打包后的路径（PyInstaller/Buildozer）
    os.path.join(os.path.dirname(__file__), 'fonts', 'SourceHanSansCN-Regular.otf'),
    os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansCJK-Regular.ttc'),
    os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansCJK-Regular.otf'),
    os.path.join(os.path.dirname(__file__), 'fonts', 'DroidSansFallbackFull.ttf'),
    os.path.join(os.path.dirname(__file__), 'fonts', 'DroidSansFallback.ttf'),
    os.path.join(os.path.dirname(__file__), 'fonts', 'msyh.ttf'),
    os.path.join(os.path.dirname(__file__), 'fonts', 'simhei.ttf'),
    # 相对路径
    'fonts/SourceHanSansCN-Regular.otf',
    'fonts/NotoSansCJK-Regular.ttc',
    'fonts/NotoSansCJK-Regular.otf',
    'fonts/DroidSansFallbackFull.ttf',
    'fonts/DroidSansFallback.ttf',
    'fonts/msyh.ttf',
    'fonts/simhei.ttf',
]

# Android 系统字体路径
ANDROID_SYSTEM_FONTS = [
    '/system/fonts/NotoSansCJK-Regular.ttc',
    '/system/fonts/NotoSansCJK-Regular.otf',
    '/system/fonts/DroidSansFallbackFull.ttf',
    '/system/fonts/DroidSansFallback.ttf',
    '/system/fonts/NotoSansSC-Regular.otf',
    '/system/fonts/Roboto-Regular.ttf',
]


def find_font_file():
    """
    查找可用的中文字体文件
    
    Returns:
        str: 字体文件的完整路径，如果找不到则返回 None
    """
    # 首先检查打包的字体
    for font_path in FONT_SEARCH_PATHS:
        if os.path.exists(font_path):
            print(f"[FONT] Found font: {font_path}")
            return os.path.abspath(font_path)
    
    # 在 Android 上检查系统字体
    if platform == 'android':
        for font_path in ANDROID_SYSTEM_FONTS:
            if os.path.exists(font_path):
                print(f"[FONT] Found system font: {font_path}")
                return font_path
    
    print("[FONT] No Chinese font found!")
    return None


def register_chinese_font():
    """
    注册中文字体到 Kivy
    
    Returns:
        str: 注册的字体名称，如果失败则返回 None
    """
    font_path = find_font_file()
    
    if font_path:
        try:
            # 注册字体
            LabelBase.register(CHINESE_FONT_NAME, font_path)
            print(f"[FONT] Registered font: {CHINESE_FONT_NAME} -> {font_path}")
            return CHINESE_FONT_NAME
        except Exception as e:
            print(f"[FONT] Failed to register font: {e}")
    
    return None


def get_font_name():
    """
    获取应该使用的字体名称
    
    Returns:
        str: 字体名称，如果没有中文字体则返回 'Roboto'（Kivy默认）
    """
    # 尝试注册字体
    registered = register_chinese_font()
    if registered:
        return registered
    
    # 回退到默认字体
    print("[FONT] Using default font (may not support Chinese)")
    return 'Roboto'


# 全局字体名称（在导入时初始化）
GLOBAL_FONT_NAME = get_font_name()


def create_label_kwargs(font_size='14sp', **kwargs):
    """
    创建带有正确字体设置的 Label 参数
    
    Args:
        font_size: 字体大小
        **kwargs: 其他参数
    
    Returns:
        dict: 可以用于 Label 构造的参数字典
    """
    label_kwargs = {
        'font_name': GLOBAL_FONT_NAME,
        'font_size': font_size,
    }
    label_kwargs.update(kwargs)
    return label_kwargs


def create_button_kwargs(font_size='14sp', **kwargs):
    """
    创建带有正确字体设置的 Button 参数
    
    Args:
        font_size: 字体大小
        **kwargs: 其他参数
    
    Returns:
        dict: 可以用于 Button 构造的参数字典
    """
    button_kwargs = {
        'font_name': GLOBAL_FONT_NAME,
        'font_size': font_size,
    }
    button_kwargs.update(kwargs)
    return button_kwargs


def create_textinput_kwargs(font_size='14sp', **kwargs):
    """
    创建带有正确字体设置的 TextInput 参数
    
    Args:
        font_size: 字体大小
        **kwargs: 其他参数
    
    Returns:
        dict: 可以用于 TextInput 构造的参数字典
    """
    textinput_kwargs = {
        'font_name': GLOBAL_FONT_NAME,
        'font_size': font_size,
    }
    textinput_kwargs.update(kwargs)
    return textinput_kwargs


def create_tabbed_panel_header_kwargs(font_size='14sp', **kwargs):
    """
    创建带有正确字体设置的 TabbedPanelHeader 参数
    
    Args:
        font_size: 字体大小
        **kwargs: 其他参数
    
    Returns:
        dict: 可以用于 TabbedPanelHeader 构造的参数字典
    """
    header_kwargs = {
        'font_name': GLOBAL_FONT_NAME,
        'font_size': font_size,
    }
    header_kwargs.update(kwargs)
    return header_kwargs
