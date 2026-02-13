#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🌊 Dave the Diver 存档修改器 Android版 🌊                                   ║
║   DiveSaveEd for Android - Kivy GUI Edition                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import re
import shutil
import time
import random
import traceback
from datetime import datetime
from pathlib import Path

# Kivy 导入
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.core.window import Window
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.text import LabelBase
from kivy.metrics import dp

# 导入字体工具模块
from font_utils import (
    GLOBAL_FONT_NAME, 
    create_label_kwargs, 
    create_button_kwargs,
    create_textinput_kwargs,
    create_tabbed_panel_header_kwargs
)

# ============ 日志配置 ============
LOG_FILE = None

def init_logging():
    """初始化日志记录"""
    global LOG_FILE
    try:
        if platform == 'android':
            log_dir = '/sdcard/DaveSaveEd/logs'
        else:
            log_dir = os.path.expanduser('~/DaveSaveEd/logs')
        
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        LOG_FILE = os.path.join(log_dir, f'app_{timestamp}.log')
        log_message(f"=== DaveSaveEd 启动 ===")
        log_message(f"日志文件: {LOG_FILE}")
        log_message(f"平台: {platform}")
        return True
    except Exception as e:
        print(f"初始化日志失败: {e}")
        return False

def log_message(msg):
    """记录日志到文件和控制台"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    
    if LOG_FILE:
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except:
            pass

# ============ 配置常量 ============
XOR_KEY = b"GameData"
BYPASS_PREFIX = "BYPASSED_HEX::"

# 数值上限
SAVE_MAX_CURRENCY = 999999999
SAVE_MAX_FLAME = 999999
SAVE_MAX_FOLLOWER = 99999
SAVE_MAX_INGREDIENT = 9999
SAVE_MAX_ITEM = 999


def xor_bytes(data_bytes, key_bytes, key_start_index=0):
    """执行XOR加密/解密"""
    key_len = len(key_bytes)
    return bytes([byte ^ key_bytes[(key_start_index + i) % key_len] 
                  for i, byte in enumerate(data_bytes)])


def decode_sav_to_json(encrypted_bytes):
    """
    解密.sav文件为JSON字符串
    这是修复后的版本，更健壮地处理各种情况
    """
    try:
        log_message(f"开始解密，数据大小: {len(encrypted_bytes)} 字节")
        
        # 简单XOR解密
        decrypted = xor_bytes(encrypted_bytes, XOR_KEY)
        
        # 尝试直接解码为UTF-8
        try:
            json_str = decrypted.decode('utf-8')
            log_message(f"UTF-8 解码成功，长度: {len(json_str)}")
            
            # 验证JSON是否有效
            json.loads(json_str)
            log_message("JSON 验证成功")
            return json_str
            
        except UnicodeDecodeError as e:
            log_message(f"UTF-8 解码失败: {e}，尝试其他方法")
            
            # 尝试使用 'utf-8-sig' 或忽略错误
            json_str = decrypted.decode('utf-8', errors='ignore')
            log_message(f"使用 errors='ignore' 解码，长度: {len(json_str)}")
            return json_str
            
    except Exception as e:
        log_message(f"解密失败: {e}")
        log_message(traceback.format_exc())
        raise


def encode_json_to_sav(json_string):
    """加密JSON字符串为.sav格式"""
    try:
        # 简单XOR加密
        json_bytes = json_string.encode('utf-8')
        encrypted = xor_bytes(json_bytes, XOR_KEY)
        return bytes(encrypted)
    except Exception as e:
        log_message(f"加密失败: {e}")
        log_message(traceback.format_exc())
        raise


class ItemDatabase:
    """物品数据库类"""
    
    def __init__(self, json_path):
        self.items = {}
        self.name_to_id = {}
        self.load_database(json_path)
    
    def load_database(self, json_path):
        """加载物品数据库"""
        try:
            log_message(f"尝试加载数据库: {json_path}")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                log_message(f"数据库文件大小: {len(content)} 字符")
                
                # 尝试解析JSON
                try:
                    data = json.loads(content)
                    
                    # 处理不同的JSON结构
                    if isinstance(data, dict):
                        self.items = {int(k): v for k, v in data.items() if k.isdigit()}
                    elif isinstance(data, list):
                        self.items = {int(item['id']): item['name'] for item in data if 'id' in item and 'name' in item}
                    
                    self.name_to_id = {v: k for k, v in self.items.items()}
                    log_message(f"数据库加载成功: {len(self.items)} 个物品")
                    return True
                    
                except json.JSONDecodeError as e:
                    log_message(f"JSON 解析失败: {e}")
                    # 尝试修复可能的格式问题
                    try:
                        # 尝试读取第一行看看是什么格式
                        first_line = content.split('\n')[0] if '\n' in content else content[:100]
                        log_message(f"文件内容前100字符: {first_line}")
                    except:
                        pass
                    return False
            else:
                log_message(f"数据库文件不存在: {json_path}")
            return False
            
        except Exception as e:
            log_message(f"加载物品数据库失败: {e}")
            log_message(traceback.format_exc())
            return False
    
    def search(self, keyword):
        """综合搜索（ID或名称）"""
        try:
            item_id = int(keyword)
            if item_id in self.items:
                return [(item_id, self.items[item_id])]
        except ValueError:
            pass
        
        keyword = keyword.lower()
        results = []
        for item_id, item_name in self.items.items():
            if keyword in item_name.lower():
                results.append((item_id, item_name))
        return results
    
    def get_name(self, item_id):
        """获取物品名称"""
        return self.items.get(item_id, f"未知物品({item_id})")


class DaveSaveEditor:
    """存档编辑器主类"""
    
    def __init__(self):
        self.save_data = None
        self.file_path = None
        self.backup_path = None
        self.item_db = None
        self.last_error = None
    
    def load_item_database(self, json_path):
        """加载物品数据库"""
        self.item_db = ItemDatabase(json_path)
        return len(self.item_db.items) > 0
    
    def load_save_file(self, filepath):
        """加载存档文件"""
        self.last_error = None
        try:
            log_message(f"尝试加载存档: {filepath}")
            
            # 检查文件是否存在
            if not os.path.exists(filepath):
                self.last_error = f"文件不存在: {filepath}"
                log_message(self.last_error)
                return False
            
            # 检查文件大小
            file_size = os.path.getsize(filepath)
            log_message(f"文件大小: {file_size} 字节")
            
            if file_size == 0:
                self.last_error = "文件为空"
                log_message(self.last_error)
                return False
            
            # 读取文件
            with open(filepath, 'rb') as f:
                encrypted_bytes = f.read()
            
            log_message(f"读取到 {len(encrypted_bytes)} 字节数据")
            
            # 解密
            json_str = decode_sav_to_json(encrypted_bytes)
            log_message(f"解密成功，JSON 长度: {len(json_str)}")
            
            # 尝试修复可能的JSON格式问题
            json_str = self._fix_json(json_str)
            
            # 解析 JSON
            self.save_data = json.loads(json_str)
            self.file_path = filepath
            
            log_message(f"存档加载成功")
            return True
            
        except json.JSONDecodeError as e:
            self.last_error = f"JSON 解析失败: {e}"
            log_message(self.last_error)
            # 尝试保存解密后的内容以便调试
            try:
                debug_path = '/sdcard/DaveSaveEd/debug_decrypted.json'
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(json_str if 'json_str' in locals() else "解密失败")
                log_message(f"调试文件已保存: {debug_path}")
            except:
                pass
            return False
        except Exception as e:
            self.last_error = f"加载存档失败: {str(e)}"
            log_message(self.last_error)
            log_message(traceback.format_exc())
            return False
    
    def _fix_json(self, json_str):
        """尝试修复可能的JSON格式问题"""
        original = json_str
        
        # 移除可能的BOM
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
            log_message("移除了 BOM")
        
        # 移除尾部多余的字符
        json_str = json_str.rstrip('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
        
        # 尝试找到最后一个有效的JSON字符
        # 从后往前找，找到匹配的括号
        brace_count = 0
        bracket_count = 0
        last_valid_pos = len(json_str) - 1
        
        for i, char in enumerate(json_str):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
            
            # 记录最后一个平衡的位置
            if brace_count == 0 and bracket_count == 0 and i > 0:
                last_valid_pos = i
        
        if last_valid_pos < len(json_str) - 1:
            log_message(f"截断到位置 {last_valid_pos}，原长度 {len(json_str)}")
            json_str = json_str[:last_valid_pos + 1]
        
        if len(json_str) != len(original):
            log_message(f"JSON 已修复，新长度: {len(json_str)}")
        
        return json_str
    
    def create_backup(self):
        """创建备份"""
        if not self.file_path:
            return False
        
        try:
            backup_dir = os.path.join(os.path.dirname(self.file_path), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(self.file_path)
            backup_name = f"{filename}_{timestamp}.bak"
            self.backup_path = os.path.join(backup_dir, backup_name)
            
            shutil.copy2(self.file_path, self.backup_path)
            log_message(f"备份创建成功: {self.backup_path}")
            return True
        except Exception as e:
            log_message(f"创建备份失败: {e}")
            return False
    
    def save_save_file(self):
        """保存存档文件"""
        if not self.save_data or not self.file_path:
            return False
        
        try:
            self.create_backup()
            json_str = json.dumps(self.save_data, separators=(',', ':'), ensure_ascii=False)
            encrypted_bytes = encode_json_to_sav(json_str)
            
            with open(self.file_path, 'wb') as f:
                f.write(encrypted_bytes)
            
            log_message(f"存档保存成功: {self.file_path}")
            return True
        except Exception as e:
            log_message(f"保存失败: {e}")
            log_message(traceback.format_exc())
            return False
    
    def get_current_values(self):
        """获取当前数值"""
        if not self.save_data:
            return None
        
        player_info = self.save_data.get("PlayerInfo", {})
        sns_info = self.save_data.get("SNSInfo", {})
        
        return {
            'gold': player_info.get("m_Gold", 0),
            'bei': player_info.get("m_Bei", 0),
            'flame': player_info.get("m_ChefFlame", 0),
            'follower': sns_info.get("m_Follow_Count", 0)
        }
    
    def set_gold(self, value):
        """设置金币"""
        if not self.save_data:
            return False
        
        if "PlayerInfo" not in self.save_data:
            self.save_data["PlayerInfo"] = {}
        
        value = min(value, SAVE_MAX_CURRENCY)
        self.save_data["PlayerInfo"]["m_Gold"] = value
        return True
    
    def set_bei(self, value):
        """设置贝币"""
        if not self.save_data:
            return False
        
        if "PlayerInfo" not in self.save_data:
            self.save_data["PlayerInfo"] = {}
        
        value = min(value, SAVE_MAX_CURRENCY)
        self.save_data["PlayerInfo"]["m_Bei"] = value
        return True
    
    def set_flame(self, value):
        """设置工匠之火"""
        if not self.save_data:
            return False
        
        if "PlayerInfo" not in self.save_data:
            self.save_data["PlayerInfo"] = {}
        
        value = min(value, SAVE_MAX_FLAME)
        self.save_data["PlayerInfo"]["m_ChefFlame"] = value
        return True
    
    def set_follower(self, value):
        """设置粉丝数"""
        if not self.save_data:
            return False
        
        if "SNSInfo" not in self.save_data:
            self.save_data["SNSInfo"] = {}
        
        value = min(value, SAVE_MAX_FOLLOWER)
        self.save_data["SNSInfo"]["m_Follow_Count"] = value
        return True
    
    def list_ingredients(self):
        """列出当前所有食材"""
        if not self.save_data or "Ingredients" not in self.save_data:
            return []
        
        ingredients = []
        for key, item in self.save_data["Ingredients"].items():
            if "ingredientsID" in item:
                ing_id = item["ingredientsID"]
                count = item.get("count", 0)
                name = self.item_db.get_name(ing_id) if self.item_db else f"食材{ing_id}"
                ingredients.append({
                    'id': ing_id,
                    'name': name,
                    'count': count,
                    'key': key
                })
        
        return ingredients
    
    def set_all_ingredients(self, value):
        """设置所有食材的数量"""
        if not self.save_data or "Ingredients" not in self.save_data:
            return False
        
        value = min(value, SAVE_MAX_INGREDIENT)
        count = 0
        
        for key, item in self.save_data["Ingredients"].items():
            if "ingredientsID" in item:
                self.save_data["Ingredients"][key]["count"] = value
                count += 1
        
        return count
    
    def search_and_modify_item(self, keyword, new_value):
        """搜索并修改物品"""
        if not self.save_data or not self.item_db:
            return False, "未加载存档或数据库"
        
        results = self.item_db.search(keyword)
        
        if not results:
            return False, f"未找到 '{keyword}'"
        
        if len(results) == 1:
            item_id, item_name = results[0]
            return self._modify_item_by_id(item_id, item_name, new_value)
        else:
            return "multiple", results
    
    def _modify_item_by_id(self, item_id, item_name, new_value):
        """根据ID修改物品数量"""
        modified = False
        
        if "Ingredients" in self.save_data:
            for key, item in self.save_data["Ingredients"].items():
                if item.get("ingredientsID") == item_id:
                    item["count"] = min(new_value, SAVE_MAX_INGREDIENT)
                    modified = True
                    break
        
        if not modified:
            if "Ingredients" not in self.save_data:
                self.save_data["Ingredients"] = {}
            
            key = str(item_id)
            self.save_data["Ingredients"][key] = {
                "ingredientsID": item_id,
                "parentID": item_id,
                "count": min(new_value, SAVE_MAX_INGREDIENT),
                "level": 1,
                "branchCount": 0,
                "isNew": True,
                "placeTagMask": 1,
                "lastGainTime": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
                "lastGainGameTime": "10/03/2022 08:30:52"
            }
            modified = True
        
        return True, item_name if modified else False
    
    def set_ingredient_count(self, ingredient_key, value):
        """设置指定食材的数量"""
        if not self.save_data or "Ingredients" not in self.save_data:
            return False
        
        if ingredient_key in self.save_data["Ingredients"]:
            value = min(value, SAVE_MAX_INGREDIENT)
            self.save_data["Ingredients"][ingredient_key]["count"] = value
            return True
        return False


class FileChooserPopup(Popup):
    """文件选择弹窗"""
    
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = '选择存档文件 (.sav)'
        self.title_font = GLOBAL_FONT_NAME
        self.size_hint = (0.9, 0.9)
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        if platform == 'android':
            from android.storage import primary_external_storage_path
            initial_path = primary_external_storage_path()
        else:
            initial_path = os.path.expanduser('~')
        
        self.filechooser = FileChooserListView(
            path=initial_path,
            filters=['*.sav'],
            dirselect=False
        )
        layout.add_widget(self.filechooser)
        
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        
        btn_cancel = Button(text='取消', font_name=GLOBAL_FONT_NAME)
        btn_cancel.bind(on_press=self.dismiss)
        
        btn_select = Button(text='选择', font_name=GLOBAL_FONT_NAME, background_color=(0.2, 0.8, 0.2, 1))
        btn_select.bind(on_press=self.on_select)
        
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_select)
        
        layout.add_widget(btn_layout)
        self.add_widget(layout)
    
    def on_select(self, instance):
        if self.filechooser.selection:
            selected_path = self.filechooser.selection[0]
            log_message(f"用户选择文件: {selected_path}")
            self.callback(selected_path)
            self.dismiss()


class MessagePopup(Popup):
    """消息提示弹窗"""
    
    def __init__(self, title, message, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.title_font = GLOBAL_FONT_NAME
        self.size_hint = (0.8, 0.4)
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(
            text=message,
            font_name=GLOBAL_FONT_NAME,
            font_size='16sp',
            text_size=(None, None),
            halign='center'
        ))
        
        btn_ok = Button(text='确定', font_name=GLOBAL_FONT_NAME, size_hint_y=0.3)
        btn_ok.bind(on_press=self.dismiss)
        layout.add_widget(btn_ok)
        
        self.add_widget(layout)


class NumberInputPopup(Popup):
    """数字输入弹窗"""
    
    def __init__(self, title, hint, max_val, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.title_font = GLOBAL_FONT_NAME
        self.size_hint = (0.8, 0.4)
        self.callback = callback
        self.max_val = max_val
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.text_input = TextInput(
            hint_text=hint,
            font_name=GLOBAL_FONT_NAME,
            input_filter='int',
            multiline=False,
            font_size='18sp'
        )
        layout.add_widget(self.text_input)
        
        btn_layout = BoxLayout(size_hint_y=0.4, spacing=10)
        
        btn_cancel = Button(text='取消', font_name=GLOBAL_FONT_NAME)
        btn_cancel.bind(on_press=self.dismiss)
        
        btn_ok = Button(text='确定', font_name=GLOBAL_FONT_NAME, background_color=(0.2, 0.8, 0.2, 1))
        btn_ok.bind(on_press=self.on_confirm)
        
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_ok)
        
        layout.add_widget(btn_layout)
        self.add_widget(layout)
    
    def on_confirm(self, instance):
        try:
            value = int(self.text_input.text)
            if value < 0:
                value = 0
            if value > self.max_val:
                value = self.max_val
            self.callback(value)
            self.dismiss()
        except ValueError:
            pass


class SearchPopup(Popup):
    """搜索物品弹窗"""
    
    def __init__(self, editor, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = '搜索物品'
        self.title_font = GLOBAL_FONT_NAME
        self.size_hint = (0.9, 0.8)
        self.editor = editor
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        search_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        self.search_input = TextInput(
            hint_text='输入物品ID或名称',
            font_name=GLOBAL_FONT_NAME,
            multiline=False,
            font_size='16sp'
        )
        search_btn = Button(text='搜索', font_name=GLOBAL_FONT_NAME, size_hint_x=0.2)
        search_btn.bind(on_press=self.do_search)
        
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)
        layout.add_widget(search_layout)
        
        self.results_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.results_layout.bind(minimum_height=self.results_layout.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.results_layout)
        layout.add_widget(scroll)
        
        btn_close = Button(text='关闭', font_name=GLOBAL_FONT_NAME, size_hint_y=0.1)
        btn_close.bind(on_press=self.dismiss)
        layout.add_widget(btn_close)
        
        self.add_widget(layout)
        self.search_results = []
    
    def do_search(self, instance):
        keyword = self.search_input.text.strip()
        if not keyword:
            return
        
        self.results_layout.clear_widgets()
        results = self.editor.item_db.search(keyword)
        
        if not results:
            self.results_layout.add_widget(Label(
                text='未找到相关物品',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=40
            ))
            return
        
        self.search_results = results
        
        for idx, (item_id, item_name) in enumerate(results[:20]):
            btn = Button(
                text=f'{item_name} (ID: {item_id})',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=50
            )
            btn.bind(on_press=lambda inst, i=idx: self.on_select(i))
            self.results_layout.add_widget(btn)
        
        if len(results) > 20:
            self.results_layout.add_widget(Label(
                text=f'...还有 {len(results)-20} 个结果',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=30
            ))
    
    def on_select(self, index):
        item_id, item_name = self.search_results[index]
        
        def set_value(value):
            success, msg = self.editor._modify_item_by_id(item_id, item_name, value)
            if success:
                self.callback(f'已修改 {item_name} 数量为 {value}')
            else:
                self.callback(f'修改失败')
        
        popup = NumberInputPopup(
            title=f'修改 {item_name}',
            hint=f'输入数量 (0-{SAVE_MAX_ITEM})',
            max_val=SAVE_MAX_ITEM,
            callback=set_value
        )
        popup.open()
        self.dismiss()


class MainScreen(BoxLayout):
    """主界面"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        
        self.editor = DaveSaveEditor()
        
        # 提前创建 log_label
        self.log_label = Label(
            text='就绪',
            font_name=GLOBAL_FONT_NAME,
            font_size='12sp',
            size_hint_y=0.08,
            color=(0.6, 0.6, 0.6, 1),
            text_size=(None, None),
            halign='left'
        )
        
        # 标题
        self.add_widget(Label(
            text='🌊 Dave the Diver 存档修改器',
            font_name=GLOBAL_FONT_NAME,
            font_size='24sp',
            size_hint_y=0.08,
            bold=True
        ))
        
        # 状态栏
        self.status_label = Label(
            text='未加载存档',
            font_name=GLOBAL_FONT_NAME,
            font_size='14sp',
            size_hint_y=0.06,
            color=(0.8, 0.8, 0.8, 1)
        )
        self.add_widget(self.status_label)
        
        # 加载数据库
        self.load_item_database()
        
        # 标签页
        self.tabs = TabbedPanel(do_default_tab=False, size_hint_y=0.86)
        
        tab_file = TabbedPanelHeader(text='📂 存档')
        tab_file.font_name = GLOBAL_FONT_NAME
        tab_file.content = self.create_file_tab()
        self.tabs.add_widget(tab_file)
        
        tab_currency = TabbedPanelHeader(text='💰 货币')
        tab_currency.font_name = GLOBAL_FONT_NAME
        tab_currency.content = self.create_currency_tab()
        self.tabs.add_widget(tab_currency)
        
        tab_ingredients = TabbedPanelHeader(text='🍖 食材')
        tab_ingredients.font_name = GLOBAL_FONT_NAME
        tab_ingredients.content = self.create_ingredients_tab()
        self.tabs.add_widget(tab_ingredients)
        
        tab_items = TabbedPanelHeader(text='📦 物品')
        tab_items.font_name = GLOBAL_FONT_NAME
        tab_items.content = self.create_items_tab()
        self.tabs.add_widget(tab_items)
        
        self.add_widget(self.tabs)
        self.add_widget(self.log_label)
    
    def load_item_database(self):
        """加载物品数据库"""
        possible_paths = []
        
        if platform == 'android':
            from android.storage import primary_external_storage_path
            storage = primary_external_storage_path()
            possible_paths = [
                os.path.join(storage, 'Download', 'items_id_map.json'),
                os.path.join(os.path.dirname(__file__), 'items_id_map.json'),
                '/sdcard/Download/items_id_map.json',
                '/storage/emulated/0/Download/items_id_map.json',
            ]
        else:
            possible_paths = [
                os.path.join(os.path.dirname(__file__), 'items_id_map.json'),
                'items_id_map.json',
            ]
        
        log_message(f"搜索数据库路径: {possible_paths}")
        
        loaded = False
        for path in possible_paths:
            log_message(f"检查路径: {path} -> 存在: {os.path.exists(path)}")
            if os.path.exists(path):
                if self.editor.load_item_database(path):
                    self.log(f'已加载物品数据库: {os.path.basename(path)}')
                    loaded = True
                    break
        
        if not loaded:
            self.log('警告: 未找到物品数据库')
            log_message('所有数据库路径都不存在')
    
    def log(self, message):
        """添加日志"""
        if hasattr(self, 'log_label') and self.log_label is not None:
            self.log_label.text = message
        else:
            print(f"[LOG] {message}")
    
    def show_message(self, title, message):
        """显示消息弹窗"""
        popup = MessagePopup(title, message)
        popup.open()
    
    def create_file_tab(self):
        """创建存档管理标签"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.file_info_label = Label(
            text='请选择存档文件',
            font_name=GLOBAL_FONT_NAME,
            font_size='16sp',
            size_hint_y=0.3
        )
        layout.add_widget(self.file_info_label)
        
        btn_load = Button(text='📂 选择存档文件', font_name=GLOBAL_FONT_NAME, font_size='18sp', size_hint_y=0.2)
        btn_load.bind(on_press=self.show_file_chooser)
        layout.add_widget(btn_load)
        
        btn_save = Button(
            text='💾 保存修改',
            font_name=GLOBAL_FONT_NAME,
            font_size='18sp',
            size_hint_y=0.2,
            background_color=(0.2, 0.7, 0.3, 1)
        )
        btn_save.bind(on_press=self.save_file)
        layout.add_widget(btn_save)
        
        btn_export = Button(text='📤 导出JSON', font_name=GLOBAL_FONT_NAME, font_size='16sp', size_hint_y=0.15)
        btn_export.bind(on_press=self.export_json)
        layout.add_widget(btn_export)
        
        return layout
    
    def create_currency_tab(self):
        """创建货币修改标签"""
        layout = GridLayout(cols=2, padding=20, spacing=15)
        
        self.currency_labels = {}
        currencies = [
            ('gold', '💰 金币', SAVE_MAX_CURRENCY),
            ('bei', '🐚 贝币', SAVE_MAX_CURRENCY),
            ('flame', '🔥 工匠之火', SAVE_MAX_FLAME),
            ('follower', '👥 粉丝数', SAVE_MAX_FOLLOWER)
        ]
        
        for key, name, max_val in currencies:
            label = Label(
                text=f'{name}: 0',
                font_name=GLOBAL_FONT_NAME,
                font_size='16sp',
                size_hint_y=None,
                height=50
            )
            self.currency_labels[key] = label
            layout.add_widget(label)
            
            btn = Button(text='修改', font_name=GLOBAL_FONT_NAME, size_hint_y=None, height=50)
            btn.bind(on_press=lambda inst, k=key, n=name, m=max_val: self.modify_currency(k, n, m))
            layout.add_widget(btn)
        
        return layout
    
    def create_ingredients_tab(self):
        """创建食材管理标签"""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        
        btn_refresh = Button(text='🔄 刷新列表', font_name=GLOBAL_FONT_NAME)
        btn_refresh.bind(on_press=self.refresh_ingredients)
        
        btn_set_all = Button(text='⚡ 统一设置数量', font_name=GLOBAL_FONT_NAME)
        btn_set_all.bind(on_press=self.set_all_ingredients)
        
        btn_layout.add_widget(btn_refresh)
        btn_layout.add_widget(btn_set_all)
        layout.add_widget(btn_layout)
        
        self.ingredients_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.ingredients_layout.bind(minimum_height=self.ingredients_layout.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.ingredients_layout)
        layout.add_widget(scroll)
        
        return layout
    
    def create_items_tab(self):
        """创建物品搜索标签"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        btn_search = Button(text='🔍 搜索并修改物品', font_name=GLOBAL_FONT_NAME, font_size='20sp', size_hint_y=0.3)
        btn_search.bind(on_press=self.show_search_popup)
        layout.add_widget(btn_search)
        
        layout.add_widget(Label(
            text='支持按物品ID或名称搜索\n可添加新物品到存档',
            font_name=GLOBAL_FONT_NAME,
            font_size='14sp',
            color=(0.6, 0.6, 0.6, 1)
        ))
        
        return layout
    
    def show_file_chooser(self, instance):
        """显示文件选择器"""
        def on_select(path):
            log_message(f"选择的文件路径: {path}")
            
            if self.editor.load_save_file(path):
                self.file_info_label.text = f'已加载: {os.path.basename(path)}'
                self.status_label.text = f'当前存档: {os.path.basename(path)}'
                self.status_label.color = (0.2, 0.8, 0.2, 1)
                self.update_currency_display()
                self.refresh_ingredients()
                self.log('存档加载成功')
            else:
                error_msg = self.editor.last_error or '未知错误'
                log_message(f"加载失败: {error_msg}")
                self.show_message('错误', f'加载存档失败\n{error_msg}')
        
        popup = FileChooserPopup(on_select)
        popup.open()
    
    def update_currency_display(self):
        """更新货币显示"""
        values = self.editor.get_current_values()
        if values:
            self.currency_labels['gold'].text = f'💰 金币: {values["gold"]}'
            self.currency_labels['bei'].text = f'🐚 贝币: {values["bei"]}'
            self.currency_labels['flame'].text = f'🔥 工匠之火: {values["flame"]}'
            self.currency_labels['follower'].text = f'👥 粉丝数: {values["follower"]}'
    
    def modify_currency(self, key, name, max_val):
        """修改货币"""
        if not self.editor.save_data:
            self.show_message('错误', '请先加载存档')
            return
        
        def do_modify(value):
            if key == 'gold':
                success = self.editor.set_gold(value)
            elif key == 'bei':
                success = self.editor.set_bei(value)
            elif key == 'flame':
                success = self.editor.set_flame(value)
            elif key == 'follower':
                success = self.editor.set_follower(value)
            
            if success:
                self.update_currency_display()
                self.log(f'{name} 已修改为 {value}')
        
        popup = NumberInputPopup(
            title=f'修改 {name}',
            hint=f'输入数值 (0-{max_val})',
            max_val=max_val,
            callback=do_modify
        )
        popup.open()
    
    def refresh_ingredients(self, instance=None):
        """刷新食材列表"""
        self.ingredients_layout.clear_widgets()
        
        if not self.editor.save_data:
            self.ingredients_layout.add_widget(Label(
                text='请先加载存档',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=40
            ))
            return
        
        ingredients = self.editor.list_ingredients()
        if not ingredients:
            self.ingredients_layout.add_widget(Label(
                text='暂无食材数据',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=40
            ))
            return
        
        ingredients.sort(key=lambda x: x['count'], reverse=True)
        
        for ing in ingredients[:50]:
            btn = Button(
                text=f'{ing["name"]} x{ing["count"]}',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=45
            )
            btn.bind(on_press=lambda inst, k=ing['key'], n=ing['name']: self.modify_ingredient(k, n))
            self.ingredients_layout.add_widget(btn)
    
    def modify_ingredient(self, key, name):
        """修改单个食材"""
        def do_modify(value):
            if self.editor.set_ingredient_count(key, value):
                self.log(f'{name} 数量已修改为 {value}')
                self.refresh_ingredients()
        
        popup = NumberInputPopup(
            title=f'修改 {name}',
            hint=f'输入数量 (0-{SAVE_MAX_INGREDIENT})',
            max_val=SAVE_MAX_INGREDIENT,
            callback=do_modify
        )
        popup.open()
    
    def set_all_ingredients(self, instance):
        """统一设置所有食材"""
        if not self.editor.save_data:
            self.show_message('错误', '请先加载存档')
            return
        
        def do_modify(value):
            count = self.editor.set_all_ingredients(value)
            self.log(f'已将 {count} 个食材设置为 {value}')
            self.refresh_ingredients()
        
        popup = NumberInputPopup(
            title='统一设置食材数量',
            hint=f'输入数量 (0-{SAVE_MAX_INGREDIENT})',
            max_val=SAVE_MAX_INGREDIENT,
            callback=do_modify
        )
        popup.open()
    
    def show_search_popup(self, instance):
        """显示搜索弹窗"""
        if not self.editor.save_data:
            self.show_message('错误', '请先加载存档')
            return
        
        def on_result(message):
            self.log(message)
        
        popup = SearchPopup(self.editor, on_result)
        popup.open()
    
    def save_file(self, instance):
        """保存存档"""
        if not self.editor.save_data:
            self.show_message('错误', '请先加载存档')
            return
        
        if self.editor.save_save_file():
            self.show_message('成功', '存档已保存\n备份文件已创建')
            self.log('存档保存成功')
        else:
            self.show_message('错误', '保存失败')
    
    def export_json(self, instance):
        """导出JSON"""
        if not self.editor.save_data:
            self.show_message('错误', '请先加载存档')
            return
        
        try:
            base_name = os.path.splitext(os.path.basename(self.editor.file_path))[0]
            
            if platform == 'android':
                from android.storage import primary_external_storage_path
                output_dir = primary_external_storage_path()
            else:
                output_dir = os.path.dirname(self.editor.file_path)
            
            output_path = os.path.join(output_dir, f'{base_name}_导出.json')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.editor.save_data, f, ensure_ascii=False, indent=2)
            
            self.show_message('成功', f'JSON已导出到:\n{output_path}')
            self.log('JSON导出成功')
        except Exception as e:
            self.show_message('错误', f'导出失败: {str(e)}')


class DaveSaveEdApp(App):
    """Kivy应用主类"""
    
    def build(self):
        # 初始化日志
        init_logging()
        
        # 延迟导入 Android 库，防止启动闪退
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                
                # Android 11+ 需要所有文件访问权限
                permissions = [
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
                
                log_message(f"请求权限: {permissions}")
                request_permissions(permissions)
                
                # 尝试请求 MANAGE_EXTERNAL_STORAGE (Android 11+)
                try:
                    from android import autoclass
                    from android import activity
                    
                    # 检查是否需要特殊权限
                    Environment = autoclass('android.os.Environment')
                    if not Environment.isExternalStorageManager():
                        log_message("需要 MANAGE_EXTERNAL_STORAGE 权限")
                        
                        # 打开设置页面让用户手动授权
                        Intent = autoclass('android.content.Intent')
                        Settings = autoclass('android.provider.Settings')
                        intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                        activity.startActivity(intent)
                except Exception as e:
                    log_message(f"检查存储管理权限失败: {e}")
                    
            except ImportError as e:
                log_message(f"导入权限模块失败: {e}")
        
        Window.clearcolor = (0.12, 0.14, 0.18, 1)
        self.title = 'Dave the Diver 存档修改器'
        return MainScreen()


if __name__ == '__main__':
    DaveSaveEdApp().run()
