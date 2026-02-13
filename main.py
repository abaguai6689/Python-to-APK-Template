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

# ============ 配置常量 ============
XOR_KEY = b"GameData"
BYPASS_PREFIX = "BYPASSED_HEX::"

# 数值上限
SAVE_MAX_CURRENCY = 999999999
SAVE_MAX_FLAME = 999999
SAVE_MAX_FOLLOWER = 99999
SAVE_MAX_INGREDIENT = 9999
SAVE_MAX_ITEM = 999

# 问题字段触发器
TROUBLESOME_TRIGGERS = [
    b'"FarmAnimal":[{"FarmAnimalID":11090001,"Name":"',
]
END_MARKER = b'"}],'

# 图标
ICONS = {
    'gold': '💰', 'bei': '🐚', 'flame': '🔥', 'follower': '👥',
    'fish': '🐟', 'food': '🍖', 'item': '📦', 'search': '🔍',
    'save': '💾', 'load': '📂', 'backup': '🔒', 'exit': '🚪',
    'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️',
    'star': '⭐', 'arrow': '➜', 'heart': '❤️', 'wave': '🌊',
    'diver': '🤿', 'shark': '🦈', 'octopus': '🐙', 'crab': '🦀'
}


def xor_bytes(data_bytes, key_bytes, key_start_index=0):
    """执行XOR加密/解密"""
    key_len = len(key_bytes)
    return bytes([byte ^ key_bytes[(key_start_index + i) % key_len] 
                  for i, byte in enumerate(data_bytes)])


def find_field_details(encrypted_bytes, start_pos):
    """查找问题字段的详细信息"""
    field_len = None
    
    slice_for_len_check = encrypted_bytes[start_pos:]
    for offset_pass1 in range(len(XOR_KEY)):
        temp_key_idx = (start_pos + offset_pass1) % len(XOR_KEY)
        decrypted_slice = xor_bytes(slice_for_len_check, XOR_KEY, key_start_index=temp_key_idx)
        
        try:
            end_marker_pos = decrypted_slice.index(END_MARKER)
            field_len = end_marker_pos
            break
        except ValueError:
            continue
    
    if field_len is None:
        return None, None
    
    resync_pos = start_pos + field_len
    if resync_pos >= len(encrypted_bytes):
        return None, None
    
    slice_len = min(50, len(encrypted_bytes) - resync_pos)
    slice_for_offset_check = encrypted_bytes[resync_pos:resync_pos + slice_len]
    
    for offset_pass2 in range(len(XOR_KEY)):
        temp_key_idx = (resync_pos + offset_pass2) % len(XOR_KEY)
        decrypted_slice = xor_bytes(slice_for_offset_check, XOR_KEY, key_start_index=temp_key_idx)
        
        if decrypted_slice.startswith(END_MARKER):
            return field_len, temp_key_idx
    
    return field_len, None


def decode_sav_to_json(encrypted_bytes):
    """解密.sav文件为JSON字符串"""
    output_buffer = bytearray()
    data_idx = 0
    key_idx = 0
    
    while data_idx < len(encrypted_bytes):
        decrypted_byte = encrypted_bytes[data_idx] ^ XOR_KEY[key_idx % len(XOR_KEY)]
        output_buffer.append(decrypted_byte)
        
        trigger_found = False
        for trigger in TROUBLESOME_TRIGGERS:
            if output_buffer.endswith(trigger):
                field_start_pos = data_idx + 1
                length, new_key_idx = find_field_details(encrypted_bytes, field_start_pos)
                
                if length is not None and new_key_idx is not None:
                    field_bytes = encrypted_bytes[field_start_pos:field_start_pos + length]
                    
                    output_buffer = output_buffer[:-len(trigger)]
                    output_buffer.extend(trigger)
                    bypass_string = f'{BYPASS_PREFIX}{field_bytes.hex()}:{new_key_idx}'
                    output_buffer.extend(bypass_string.encode('ascii'))
                    
                    data_idx = field_start_pos + length
                    key_idx = new_key_idx
                    trigger_found = True
                break
        
        if not trigger_found:
            data_idx += 1
            key_idx += 1
    
    return output_buffer.decode('utf-8')


def encode_json_to_sav(json_string):
    """加密JSON字符串为.sav格式"""
    pattern = re.compile(rf'{BYPASS_PREFIX}([a-fA-F0-9]+):(\d+)')
    output_bytes = bytearray()
    last_end = 0
    key_idx = 0
    
    for match in pattern.finditer(json_string):
        start, end = match.span()
        
        clean_part_str = json_string[last_end:start]
        clean_part_bytes = clean_part_str.encode('utf-8')
        output_bytes.extend(xor_bytes(clean_part_bytes, XOR_KEY, key_start_index=key_idx))
        key_idx = (key_idx + len(clean_part_bytes)) % len(XOR_KEY)
        
        hex_data = match.group(1)
        new_key_idx = int(match.group(2))
        
        raw_field_bytes = bytes.fromhex(hex_data)
        output_bytes.extend(raw_field_bytes)
        key_idx = new_key_idx
        
        last_end = end
    
    remaining_part_str = json_string[last_end:]
    remaining_part_bytes = remaining_part_str.encode('utf-8')
    output_bytes.extend(xor_bytes(remaining_part_bytes, XOR_KEY, key_start_index=key_idx))
    
    return bytes(output_bytes)


class ItemDatabase:
    """物品数据库类"""
    
    def __init__(self, json_path):
        self.items = {}
        self.name_to_id = {}
        self.load_database(json_path)
    
    def load_database(self, json_path):
        """加载物品数据库"""
        try:
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.items = {int(k): v for k, v in json.load(f).items()}
                self.name_to_id = {v: k for k, v in self.items.items()}
                return True
            return False
        except Exception as e:
            print(f"加载物品数据库失败: {e}")
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
    
    def load_item_database(self, json_path):
        """加载物品数据库"""
        self.item_db = ItemDatabase(json_path)
        return len(self.item_db.items) > 0
    
    def load_save_file(self, filepath):
        """加载存档文件"""
        try:
            with open(filepath, 'rb') as f:
                encrypted_bytes = f.read()
            
            json_str = decode_sav_to_json(encrypted_bytes)
            self.save_data = json.loads(json_str)
            self.file_path = filepath
            return True
        except Exception as e:
            return False
    
    def create_backup(self):
        """创建备份"""
        if not self.file_path:
            return False
        
        backup_dir = os.path.join(os.path.dirname(self.file_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(self.file_path)
        backup_name = f"{filename}_{timestamp}.bak"
        self.backup_path = os.path.join(backup_dir, backup_name)
        
        shutil.copy2(self.file_path, self.backup_path)
        return True
    
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
            
            return True
        except Exception as e:
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
        self.size_hint = (0.9, 0.9)
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 获取存储路径
        if platform == 'android':
            # 延迟导入，避免在类定义时导入
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
        
        # 按钮区域
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        
        btn_cancel = Button(text='取消')
        btn_cancel.bind(on_press=self.dismiss)
        
        btn_select = Button(text='选择', background_color=(0.2, 0.8, 0.2, 1))
        btn_select.bind(on_press=self.on_select)
        
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_select)
        
        layout.add_widget(btn_layout)
        self.add_widget(layout)
    
    def on_select(self, instance):
        if self.filechooser.selection:
            self.callback(self.filechooser.selection[0])
            self.dismiss()


class MessagePopup(Popup):
    """消息提示弹窗"""
    
    def __init__(self, title, message, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.8, 0.4)
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(
            text=message,
            font_size='16sp',
            text_size=(None, None),
            halign='center'
        ))
        
        btn_ok = Button(text='确定', size_hint_y=0.3)
        btn_ok.bind(on_press=self.dismiss)
        layout.add_widget(btn_ok)
        
        self.add_widget(layout)


class NumberInputPopup(Popup):
    """数字输入弹窗"""
    
    def __init__(self, title, hint, max_val, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.8, 0.4)
        self.callback = callback
        self.max_val = max_val
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.text_input = TextInput(
            hint_text=hint,
            input_filter='int',
            multiline=False,
            font_size='18sp'
        )
        layout.add_widget(self.text_input)
        
        btn_layout = BoxLayout(size_hint_y=0.4, spacing=10)
        
        btn_cancel = Button(text='取消')
        btn_cancel.bind(on_press=self.dismiss)
        
        btn_ok = Button(text='确定', background_color=(0.2, 0.8, 0.2, 1))
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
        self.size_hint = (0.9, 0.8)
        self.editor = editor
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 搜索输入
        search_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        self.search_input = TextInput(
            hint_text='输入物品ID或名称',
            multiline=False,
            font_size='16sp'
        )
        search_btn = Button(text='搜索', size_hint_x=0.2)
        search_btn.bind(on_press=self.do_search)
        
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)
        layout.add_widget(search_layout)
        
        # 结果列表
        self.results_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.results_layout.bind(minimum_height=self.results_layout.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.results_layout)
        layout.add_widget(scroll)
        
        # 关闭按钮
        btn_close = Button(text='关闭', size_hint_y=0.1)
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
                size_hint_y=None,
                height=40
            ))
            return
        
        self.search_results = results
        
        for idx, (item_id, item_name) in enumerate(results[:20]):
            btn = Button(
                text=f'{item_name} (ID: {item_id})',
                size_hint_y=None,
                height=50
            )
            btn.bind(on_press=lambda inst, i=idx: self.on_select(i))
            self.results_layout.add_widget(btn)
        
        if len(results) > 20:
            self.results_layout.add_widget(Label(
                text=f'...还有 {len(results)-20} 个结果',
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
        
        # ========== 修复1：提前创建 log_label（在调用 log() 之前）==========
        self.log_label = Label(
            text='就绪',
            font_size='12sp',
            size_hint_y=0.08,
            color=(0.6, 0.6, 0.6, 1),
            text_size=(None, None),
            halign='left'
        )
        # 注意：这里先不添加到布局，只创建对象，避免显示顺序问题
        
        # 标题
        self.add_widget(Label(
            text='🌊 Dave the Diver 存档修改器',
            font_size='24sp',
            size_hint_y=0.08,
            bold=True
        ))
        
        # 状态栏
        self.status_label = Label(
            text='未加载存档',
            font_size='14sp',
            size_hint_y=0.06,
            color=(0.8, 0.8, 0.8, 1)
        )
        self.add_widget(self.status_label)
        
        # 现在可以安全调用 load_item_database() 了，因为 log_label 已创建
        self.load_item_database()
        
        # 标签页
        self.tabs = TabbedPanel(do_default_tab=False, size_hint_y=0.86)
        
        # 存档标签
        tab_file = TabbedPanelHeader(text='📂 存档')
        tab_file.content = self.create_file_tab()
        self.tabs.add_widget(tab_file)
        
        # 货币标签
        tab_currency = TabbedPanelHeader(text='💰 货币')
        tab_currency.content = self.create_currency_tab()
        self.tabs.add_widget(tab_currency)
        
        # 食材标签
        tab_ingredients = TabbedPanelHeader(text='🍖 食材')
        tab_ingredients.content = self.create_ingredients_tab()
        self.tabs.add_widget(tab_ingredients)
        
        # 物品标签
        tab_items = TabbedPanelHeader(text='📦 物品')
        tab_items.content = self.create_items_tab()
        self.tabs.add_widget(tab_items)
        
        self.add_widget(self.tabs)
        
        # 最后添加日志区域到布局
        self.add_widget(self.log_label)
    
    def load_item_database(self):
        """加载物品数据库"""
        # 尝试多个可能的路径
        possible_paths = []
        
        if platform == 'android':
            # 延迟导入
            from android.storage import primary_external_storage_path
            storage = primary_external_storage_path()
            possible_paths = [
                os.path.join(storage, 'Download', '修改器源码', 'jiaoben', 'items_id_map.json'),
                os.path.join(storage, 'Download', 'items_id_map.json'),
                os.path.join(os.path.dirname(__file__), 'items_id_map.json'),
            ]
        else:
            possible_paths = [
                os.path.join(os.path.dirname(__file__), 'items_id_map.json'),
                'items_id_map.json',
            ]
        
        loaded = False
        for path in possible_paths:
            if os.path.exists(path):
                if self.editor.load_item_database(path):
                    self.log(f'已加载物品数据库: {os.path.basename(path)}')
                    loaded = True
                    break
        
        if not loaded:
            self.log('警告: 未找到物品数据库')
    
    def log(self, message):
        """添加日志"""
        # ========== 修复2：增加安全检查，防止属性未初始化时崩溃 ==========
        if hasattr(self, 'log_label') and self.log_label is not None:
            self.log_label.text = message
        else:
            # 如果 log_label 还没创建，打印到控制台
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
            font_size='16sp',
            size_hint_y=0.3
        )
        layout.add_widget(self.file_info_label)
        
        btn_load = Button(
            text='📂 选择存档文件',
            font_size='18sp',
            size_hint_y=0.2
        )
        btn_load.bind(on_press=self.show_file_chooser)
        layout.add_widget(btn_load)
        
        btn_save = Button(
            text='💾 保存修改',
            font_size='18sp',
            size_hint_y=0.2,
            background_color=(0.2, 0.7, 0.3, 1)
        )
        btn_save.bind(on_press=self.save_file)
        layout.add_widget(btn_save)
        
        btn_export = Button(
            text='📤 导出JSON',
            font_size='16sp',
            size_hint_y=0.15
        )
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
            # 标签
            label = Label(
                text=f'{name}: 0',
                font_size='16sp',
                size_hint_y=None,
                height=50
            )
            self.currency_labels[key] = label
            layout.add_widget(label)
            
            # 修改按钮
            btn = Button(
                text='修改',
                size_hint_y=None,
                height=50
            )
            btn.bind(on_press=lambda inst, k=key, n=name, m=max_val: self.modify_currency(k, n, m))
            layout.add_widget(btn)
        
        return layout
    
    def create_ingredients_tab(self):
        """创建食材管理标签"""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        
        btn_refresh = Button(text='🔄 刷新列表')
        btn_refresh.bind(on_press=self.refresh_ingredients)
        
        btn_set_all = Button(text='⚡ 统一设置数量')
        btn_set_all.bind(on_press=self.set_all_ingredients)
        
        btn_layout.add_widget(btn_refresh)
        btn_layout.add_widget(btn_set_all)
        layout.add_widget(btn_layout)
        
        # 食材列表
        self.ingredients_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.ingredients_layout.bind(minimum_height=self.ingredients_layout.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.ingredients_layout)
        layout.add_widget(scroll)
        
        return layout
    
    def create_items_tab(self):
        """创建物品搜索标签"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        btn_search = Button(
            text='🔍 搜索并修改物品',
            font_size='20sp',
            size_hint_y=0.3
        )
        btn_search.bind(on_press=self.show_search_popup)
        layout.add_widget(btn_search)
        
        layout.add_widget(Label(
            text='支持按物品ID或名称搜索\n可添加新物品到存档',
            font_size='14sp',
            color=(0.6, 0.6, 0.6, 1)
        ))
        
        return layout
    
    def show_file_chooser(self, instance):
        """显示文件选择器"""
        def on_select(path):
            if self.editor.load_save_file(path):
                self.file_info_label.text = f'已加载: {os.path.basename(path)}'
                self.status_label.text = f'当前存档: {os.path.basename(path)}'
                self.status_label.color = (0.2, 0.8, 0.2, 1)
                self.update_currency_display()
                self.refresh_ingredients()
                self.log('存档加载成功')
            else:
                self.show_message('错误', '加载存档失败')
        
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
                size_hint_y=None,
                height=40
            ))
            return
        
        ingredients = self.editor.list_ingredients()
        if not ingredients:
            self.ingredients_layout.add_widget(Label(
                text='暂无食材数据',
                size_hint_y=None,
                height=40
            ))
            return
        
        # 按数量排序
        ingredients.sort(key=lambda x: x['count'], reverse=True)
        
        for ing in ingredients[:50]:  # 最多显示50个
            btn = Button(
                text=f'{ing["name"]} x{ing["count"]}',
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
            self.log(f'JSON导出成功')
        except Exception as e:
            self.show_message('错误', f'导出失败: {str(e)}')


class DaveSaveEdApp(App):
    """Kivy应用主类"""
    
    def build(self):
    # 测试系统字体
    if platform == 'android':
        test_fonts = [
            '/system/fonts/NotoSansCJK-Regular.ttc',
            '/system/fonts/DroidSansFallbackFull.ttf',
        ]
        for f in test_fonts:
            print(f"[TEST] Font exists: {f} -> {os.path.exists(f)}")
    
    # ... 原有代码
        # 延迟导入 Android 库，防止启动闪退
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                # 申请存储权限
                permissions = [
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
                request_permissions(permissions)
            except ImportError:
                pass
        
        Window.clearcolor = (0.12, 0.14, 0.18, 1)  # 深色背景
        self.title = 'Dave the Diver 存档修改器'
        return MainScreen()


if __name__ == '__main__':
    DaveSaveEdApp().run()