#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dave the Diver Save Editor for Android
Kivy GUI Edition
"""

import os
import sys
import json
import re
import shutil
import time
import traceback
from datetime import datetime
from pathlib import Path

# Kivy imports
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
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp

# Import font utilities
from font_utils import GLOBAL_FONT_NAME

# ============ Logging Configuration ============
LOG_FILE = None

def init_logging():
    """Initialize logging"""
    global LOG_FILE
    try:
        if platform == 'android':
            log_dir = '/sdcard/DaveSaveEd/logs'
        else:
            log_dir = os.path.expanduser('~/DaveSaveEd/logs')
        
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        LOG_FILE = os.path.join(log_dir, f'app_{timestamp}.log')
        log_message("=== DaveSaveEd Started ===")
        log_message(f"Log file: {LOG_FILE}")
        log_message(f"Platform: {platform}")
        return True
    except Exception as e:
        print(f"Failed to initialize logging: {e}")
        return False

def log_message(msg):
    """Log message to file and console"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    
    if LOG_FILE:
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except:
            pass

# ============ Configuration Constants ============
XOR_KEY = b"GameData"
BYPASS_PREFIX = "BYPASSED_HEX::"

# Value limits
SAVE_MAX_CURRENCY = 999999999
SAVE_MAX_FLAME = 999999
SAVE_MAX_FOLLOWER = 99999
SAVE_MAX_INGREDIENT = 9999
SAVE_MAX_ITEM = 999

# Problem field triggers (for special handling)
TROUBLESOME_TRIGGERS = [
    b'"FarmAnimal":[{"FarmAnimalID":11090001,"Name":"',
]
END_MARKER = b'"],'


def xor_bytes(data_bytes, key_bytes, key_start_index=0):
    """Perform XOR encryption/decryption"""
    key_len = len(key_bytes)
    return bytes([byte ^ key_bytes[(key_start_index + i) % key_len] 
                  for i, byte in enumerate(data_bytes)])


def find_field_details(encrypted_bytes, start_pos):
    """Find details of problematic field"""
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
    """Decrypt .sav file to JSON string"""
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
    
    return output_buffer.decode('utf-8', errors='ignore')


def encode_json_to_sav(json_string):
    """Encrypt JSON string to .sav format"""
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


def clean_json_string(json_str):
    """Clean JSON string by removing invalid characters"""
    # Remove BOM if present
    if json_str.startswith('\ufeff'):
        json_str = json_str[1:]
    
    # Remove control characters except common whitespace
    result = []
    for char in json_str:
        code = ord(char)
        # Allow: printable chars, tab(9), newline(10), carriage return(13)
        if code >= 32 or code in (9, 10, 13):
            result.append(char)
    
    cleaned = ''.join(result)
    
    # Try to fix truncated JSON
    # Count braces and brackets
    brace_count = 0
    bracket_count = 0
    last_valid_pos = len(cleaned) - 1
    
    for i, char in enumerate(cleaned):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        elif char == '[':
            bracket_count += 1
        elif char == ']':
            bracket_count -= 1
        
        # Record last balanced position
        if brace_count == 0 and bracket_count == 0 and i > 0:
            last_valid_pos = i
    
    if last_valid_pos < len(cleaned) - 1:
        log_message(f"Truncated JSON at position {last_valid_pos}")
        cleaned = cleaned[:last_valid_pos + 1]
    
    return cleaned


class ItemDatabase:
    """Item database class"""
    
    def __init__(self, json_path):
        self.items = {}
        self.name_to_id = {}
        self.load_database(json_path)
    
    def load_database(self, json_path):
        """Load item database"""
        try:
            log_message(f"Loading database: {json_path}")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                log_message(f"Database file size: {len(content)} characters")
                
                # Clean and parse JSON
                content = clean_json_string(content)
                
                try:
                    data = json.loads(content)
                    
                    # Handle different JSON structures
                    if isinstance(data, dict):
                        self.items = {int(k): v for k, v in data.items() if str(k).isdigit()}
                    elif isinstance(data, list):
                        self.items = {int(item['id']): item['name'] for item in data if 'id' in item and 'name' in item}
                    
                    self.name_to_id = {v: k for k, v in self.items.items()}
                    log_message(f"Database loaded: {len(self.items)} items")
                    return True
                    
                except json.JSONDecodeError as e:
                    log_message(f"JSON parse failed: {e}")
                    return False
            else:
                log_message(f"Database file not found: {json_path}")
            return False
            
        except Exception as e:
            log_message(f"Failed to load database: {e}")
            log_message(traceback.format_exc())
            return False
    
    def search(self, keyword):
        """Search by ID or name"""
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
        """Get item name"""
        return self.items.get(item_id, f"Unknown({item_id})")


class DaveSaveEditor:
    """Save editor main class"""
    
    def __init__(self):
        self.save_data = None
        self.file_path = None
        self.backup_path = None
        self.item_db = None
        self.last_error = None
    
    def load_item_database(self, json_path):
        """Load item database"""
        self.item_db = ItemDatabase(json_path)
        return len(self.item_db.items) > 0
    
    def load_save_file(self, filepath):
        """Load save file"""
        self.last_error = None
        try:
            log_message(f"Loading save: {filepath}")
            
            # Check if file exists
            if not os.path.exists(filepath):
                self.last_error = f"File not found: {filepath}"
                log_message(self.last_error)
                return False
            
            # Check file size
            file_size = os.path.getsize(filepath)
            log_message(f"File size: {file_size} bytes")
            
            if file_size == 0:
                self.last_error = "File is empty"
                log_message(self.last_error)
                return False
            
            # Read file
            with open(filepath, 'rb') as f:
                encrypted_bytes = f.read()
            
            log_message(f"Read {len(encrypted_bytes)} bytes")
            
            # Decrypt
            json_str = decode_sav_to_json(encrypted_bytes)
            log_message(f"Decrypted, JSON length: {len(json_str)}")
            
            # Clean JSON
            json_str = clean_json_string(json_str)
            log_message(f"Cleaned JSON length: {len(json_str)}")
            
            # Parse JSON
            self.save_data = json.loads(json_str)
            self.file_path = filepath
            
            log_message("Save loaded successfully")
            return True
            
        except json.JSONDecodeError as e:
            self.last_error = f"JSON parse error: {e}"
            log_message(self.last_error)
            # Save debug file
            try:
                debug_path = '/sdcard/DaveSaveEd/debug_decrypted.json'
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(json_str if 'json_str' in locals() else "Decryption failed")
                log_message(f"Debug file saved: {debug_path}")
            except:
                pass
            return False
        except Exception as e:
            self.last_error = f"Load failed: {str(e)}"
            log_message(self.last_error)
            log_message(traceback.format_exc())
            return False
    
    def create_backup(self):
        """Create backup"""
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
            log_message(f"Backup created: {self.backup_path}")
            return True
        except Exception as e:
            log_message(f"Backup failed: {e}")
            return False
    
    def save_save_file(self):
        """Save save file"""
        if not self.save_data or not self.file_path:
            return False
        
        try:
            self.create_backup()
            json_str = json.dumps(self.save_data, separators=(',', ':'), ensure_ascii=False)
            encrypted_bytes = encode_json_to_sav(json_str)
            
            with open(self.file_path, 'wb') as f:
                f.write(encrypted_bytes)
            
            log_message(f"Save saved: {self.file_path}")
            return True
        except Exception as e:
            log_message(f"Save failed: {e}")
            log_message(traceback.format_exc())
            return False
    
    def get_current_values(self):
        """Get current values"""
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
        """Set gold"""
        if not self.save_data:
            return False
        
        if "PlayerInfo" not in self.save_data:
            self.save_data["PlayerInfo"] = {}
        
        value = min(value, SAVE_MAX_CURRENCY)
        self.save_data["PlayerInfo"]["m_Gold"] = value
        return True
    
    def set_bei(self, value):
        """Set bei currency"""
        if not self.save_data:
            return False
        
        if "PlayerInfo" not in self.save_data:
            self.save_data["PlayerInfo"] = {}
        
        value = min(value, SAVE_MAX_CURRENCY)
        self.save_data["PlayerInfo"]["m_Bei"] = value
        return True
    
    def set_flame(self, value):
        """Set flame"""
        if not self.save_data:
            return False
        
        if "PlayerInfo" not in self.save_data:
            self.save_data["PlayerInfo"] = {}
        
        value = min(value, SAVE_MAX_FLAME)
        self.save_data["PlayerInfo"]["m_ChefFlame"] = value
        return True
    
    def set_follower(self, value):
        """Set follower count"""
        if not self.save_data:
            return False
        
        if "SNSInfo" not in self.save_data:
            self.save_data["SNSInfo"] = {}
        
        value = min(value, SAVE_MAX_FOLLOWER)
        self.save_data["SNSInfo"]["m_Follow_Count"] = value
        return True
    
    def list_ingredients(self):
        """List all ingredients"""
        if not self.save_data or "Ingredients" not in self.save_data:
            return []
        
        ingredients = []
        for key, item in self.save_data["Ingredients"].items():
            if "ingredientsID" in item:
                ing_id = item["ingredientsID"]
                count = item.get("count", 0)
                name = self.item_db.get_name(ing_id) if self.item_db else f"Item{ing_id}"
                ingredients.append({
                    'id': ing_id,
                    'name': name,
                    'count': count,
                    'key': key
                })
        
        return ingredients
    
    def set_all_ingredients(self, value):
        """Set all ingredient quantities"""
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
        """Search and modify item"""
        if not self.save_data or not self.item_db:
            return False, "Save or database not loaded"
        
        results = self.item_db.search(keyword)
        
        if not results:
            return False, f"'{keyword}' not found"
        
        if len(results) == 1:
            item_id, item_name = results[0]
            return self._modify_item_by_id(item_id, item_name, new_value)
        else:
            return "multiple", results
    
    def _modify_item_by_id(self, item_id, item_name, new_value):
        """Modify item quantity by ID"""
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
        """Set specific ingredient quantity"""
        if not self.save_data or "Ingredients" not in self.save_data:
            return False
        
        if ingredient_key in self.save_data["Ingredients"]:
            value = min(value, SAVE_MAX_INGREDIENT)
            self.save_data["Ingredients"][ingredient_key]["count"] = value
            return True
        return False


class FileChooserPopup(Popup):
    """File chooser popup"""
    
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Select Save File (.sav)'
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
        
        btn_cancel = Button(text='Cancel', font_name=GLOBAL_FONT_NAME)
        btn_cancel.bind(on_press=self.dismiss)
        
        btn_select = Button(text='Select', font_name=GLOBAL_FONT_NAME, background_color=(0.2, 0.8, 0.2, 1))
        btn_select.bind(on_press=self.on_select)
        
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_select)
        
        layout.add_widget(btn_layout)
        self.add_widget(layout)
    
    def on_select(self, instance):
        if self.filechooser.selection:
            selected_path = self.filechooser.selection[0]
            log_message(f"User selected: {selected_path}")
            self.callback(selected_path)
            self.dismiss()


class MessagePopup(Popup):
    """Message popup"""
    
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
        
        btn_ok = Button(text='OK', font_name=GLOBAL_FONT_NAME, size_hint_y=0.3)
        btn_ok.bind(on_press=self.dismiss)
        layout.add_widget(btn_ok)
        
        self.add_widget(layout)


class NumberInputPopup(Popup):
    """Number input popup"""
    
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
        
        btn_cancel = Button(text='Cancel', font_name=GLOBAL_FONT_NAME)
        btn_cancel.bind(on_press=self.dismiss)
        
        btn_ok = Button(text='OK', font_name=GLOBAL_FONT_NAME, background_color=(0.2, 0.8, 0.2, 1))
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
    """Search item popup"""
    
    def __init__(self, editor, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Search Item'
        self.title_font = GLOBAL_FONT_NAME
        self.size_hint = (0.9, 0.8)
        self.editor = editor
        self.callback = callback
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        search_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        self.search_input = TextInput(
            hint_text='Enter item ID or name',
            font_name=GLOBAL_FONT_NAME,
            multiline=False,
            font_size='16sp'
        )
        search_btn = Button(text='Search', font_name=GLOBAL_FONT_NAME, size_hint_x=0.2)
        search_btn.bind(on_press=self.do_search)
        
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)
        layout.add_widget(search_layout)
        
        self.results_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.results_layout.bind(minimum_height=self.results_layout.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.results_layout)
        layout.add_widget(scroll)
        
        btn_close = Button(text='Close', font_name=GLOBAL_FONT_NAME, size_hint_y=0.1)
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
                text='No items found',
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
                text=f'...and {len(results)-20} more',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=30
            ))
    
    def on_select(self, index):
        item_id, item_name = self.search_results[index]
        
        def set_value(value):
            success, msg = self.editor._modify_item_by_id(item_id, item_name, value)
            if success:
                self.callback(f'Modified {item_name} to {value}')
            else:
                self.callback('Modification failed')
        
        popup = NumberInputPopup(
            title=f'Modify {item_name}',
            hint=f'Enter quantity (0-{SAVE_MAX_ITEM})',
            max_val=SAVE_MAX_ITEM,
            callback=set_value
        )
        popup.open()
        self.dismiss()


class MainScreen(BoxLayout):
    """Main screen"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        
        self.editor = DaveSaveEditor()
        
        # Log label
        self.log_label = Label(
            text='Ready',
            font_name=GLOBAL_FONT_NAME,
            font_size='12sp',
            size_hint_y=0.08,
            color=(0.6, 0.6, 0.6, 1),
            text_size=(None, None),
            halign='left'
        )
        
        # Title
        self.add_widget(Label(
            text='Dave the Diver Save Editor',
            font_name=GLOBAL_FONT_NAME,
            font_size='24sp',
            size_hint_y=0.08,
            bold=True
        ))
        
        # Status bar
        self.status_label = Label(
            text='No save loaded',
            font_name=GLOBAL_FONT_NAME,
            font_size='14sp',
            size_hint_y=0.06,
            color=(0.8, 0.8, 0.8, 1)
        )
        self.add_widget(self.status_label)
        
        # Load database
        self.load_item_database()
        
        # Tabs
        self.tabs = TabbedPanel(do_default_tab=False, size_hint_y=0.86)
        
        tab_file = TabbedPanelHeader(text='Save')
        tab_file.font_name = GLOBAL_FONT_NAME
        tab_file.content = self.create_file_tab()
        self.tabs.add_widget(tab_file)
        
        tab_currency = TabbedPanelHeader(text='Currency')
        tab_currency.font_name = GLOBAL_FONT_NAME
        tab_currency.content = self.create_currency_tab()
        self.tabs.add_widget(tab_currency)
        
        tab_ingredients = TabbedPanelHeader(text='Ingredients')
        tab_ingredients.font_name = GLOBAL_FONT_NAME
        tab_ingredients.content = self.create_ingredients_tab()
        self.tabs.add_widget(tab_ingredients)
        
        tab_items = TabbedPanelHeader(text='Items')
        tab_items.font_name = GLOBAL_FONT_NAME
        tab_items.content = self.create_items_tab()
        self.tabs.add_widget(tab_items)
        
        self.add_widget(self.tabs)
        self.add_widget(self.log_label)
    
    def load_item_database(self):
        """Load item database"""
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
        
        log_message(f"Searching database paths: {possible_paths}")
        
        loaded = False
        for path in possible_paths:
            log_message(f"Checking: {path} -> exists: {os.path.exists(path)}")
            if os.path.exists(path):
                if self.editor.load_item_database(path):
                    self.log(f'Database loaded: {os.path.basename(path)}')
                    loaded = True
                    break
        
        if not loaded:
            self.log('Warning: Database not found')
            log_message('All database paths not found')
    
    def log(self, message):
        """Add log"""
        if hasattr(self, 'log_label') and self.log_label is not None:
            self.log_label.text = message
        else:
            print(f"[LOG] {message}")
    
    def show_message(self, title, message):
        """Show message popup"""
        popup = MessagePopup(title, message)
        popup.open()
    
    def create_file_tab(self):
        """Create file management tab"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.file_info_label = Label(
            text='Please select save file',
            font_name=GLOBAL_FONT_NAME,
            font_size='16sp',
            size_hint_y=0.3
        )
        layout.add_widget(self.file_info_label)
        
        btn_load = Button(text='Select Save File', font_name=GLOBAL_FONT_NAME, font_size='18sp', size_hint_y=0.2)
        btn_load.bind(on_press=self.show_file_chooser)
        layout.add_widget(btn_load)
        
        btn_save = Button(
            text='Save Changes',
            font_name=GLOBAL_FONT_NAME,
            font_size='18sp',
            size_hint_y=0.2,
            background_color=(0.2, 0.7, 0.3, 1)
        )
        btn_save.bind(on_press=self.save_file)
        layout.add_widget(btn_save)
        
        btn_export = Button(text='Export JSON', font_name=GLOBAL_FONT_NAME, font_size='16sp', size_hint_y=0.15)
        btn_export.bind(on_press=self.export_json)
        layout.add_widget(btn_export)
        
        return layout
    
    def create_currency_tab(self):
        """Create currency modification tab"""
        layout = GridLayout(cols=2, padding=20, spacing=15)
        
        self.currency_labels = {}
        currencies = [
            ('gold', 'Gold', SAVE_MAX_CURRENCY),
            ('bei', 'Bei', SAVE_MAX_CURRENCY),
            ('flame', 'Flame', SAVE_MAX_FLAME),
            ('follower', 'Followers', SAVE_MAX_FOLLOWER)
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
            
            btn = Button(text='Modify', font_name=GLOBAL_FONT_NAME, size_hint_y=None, height=50)
            btn.bind(on_press=lambda inst, k=key, n=name, m=max_val: self.modify_currency(k, n, m))
            layout.add_widget(btn)
        
        return layout
    
    def create_ingredients_tab(self):
        """Create ingredients management tab"""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        
        btn_refresh = Button(text='Refresh List', font_name=GLOBAL_FONT_NAME)
        btn_refresh.bind(on_press=self.refresh_ingredients)
        
        btn_set_all = Button(text='Set All Quantities', font_name=GLOBAL_FONT_NAME)
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
        """Create item search tab"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        btn_search = Button(text='Search and Modify Item', font_name=GLOBAL_FONT_NAME, font_size='20sp', size_hint_y=0.3)
        btn_search.bind(on_press=self.show_search_popup)
        layout.add_widget(btn_search)
        
        layout.add_widget(Label(
            text='Search by item ID or name\nCan add new items to save',
            font_name=GLOBAL_FONT_NAME,
            font_size='14sp',
            color=(0.6, 0.6, 0.6, 1)
        ))
        
        return layout
    
    def show_file_chooser(self, instance):
        """Show file chooser"""
        def on_select(path):
            log_message(f"Selected: {path}")
            
            if self.editor.load_save_file(path):
                self.file_info_label.text = f'Loaded: {os.path.basename(path)}'
                self.status_label.text = f'Current: {os.path.basename(path)}'
                self.status_label.color = (0.2, 0.8, 0.2, 1)
                self.update_currency_display()
                self.refresh_ingredients()
                self.log('Save loaded successfully')
            else:
                error_msg = self.editor.last_error or 'Unknown error'
                log_message(f"Load failed: {error_msg}")
                self.show_message('Error', f'Failed to load save\n{error_msg}')
        
        popup = FileChooserPopup(on_select)
        popup.open()
    
    def update_currency_display(self):
        """Update currency display"""
        values = self.editor.get_current_values()
        if values:
            self.currency_labels['gold'].text = f'Gold: {values["gold"]}'
            self.currency_labels['bei'].text = f'Bei: {values["bei"]}'
            self.currency_labels['flame'].text = f'Flame: {values["flame"]}'
            self.currency_labels['follower'].text = f'Followers: {values["follower"]}'
    
    def modify_currency(self, key, name, max_val):
        """Modify currency"""
        if not self.editor.save_data:
            self.show_message('Error', 'Please load save first')
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
                self.log(f'{name} set to {value}')
        
        popup = NumberInputPopup(
            title=f'Modify {name}',
            hint=f'Enter value (0-{max_val})',
            max_val=max_val,
            callback=do_modify
        )
        popup.open()
    
    def refresh_ingredients(self, instance=None):
        """Refresh ingredients list"""
        self.ingredients_layout.clear_widgets()
        
        if not self.editor.save_data:
            self.ingredients_layout.add_widget(Label(
                text='Please load save first',
                font_name=GLOBAL_FONT_NAME,
                size_hint_y=None,
                height=40
            ))
            return
        
        ingredients = self.editor.list_ingredients()
        if not ingredients:
            self.ingredients_layout.add_widget(Label(
                text='No ingredients data',
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
        """Modify single ingredient"""
        def do_modify(value):
            if self.editor.set_ingredient_count(key, value):
                self.log(f'{name} set to {value}')
                self.refresh_ingredients()
        
        popup = NumberInputPopup(
            title=f'Modify {name}',
            hint=f'Enter quantity (0-{SAVE_MAX_INGREDIENT})',
            max_val=SAVE_MAX_INGREDIENT,
            callback=do_modify
        )
        popup.open()
    
    def set_all_ingredients(self, instance):
        """Set all ingredient quantities"""
        if not self.editor.save_data:
            self.show_message('Error', 'Please load save first')
            return
        
        def do_modify(value):
            count = self.editor.set_all_ingredients(value)
            self.log(f'Set {count} ingredients to {value}')
            self.refresh_ingredients()
        
        popup = NumberInputPopup(
            title='Set All Ingredients',
            hint=f'Enter quantity (0-{SAVE_MAX_INGREDIENT})',
            max_val=SAVE_MAX_INGREDIENT,
            callback=do_modify
        )
        popup.open()
    
    def show_search_popup(self, instance):
        """Show search popup"""
        if not self.editor.save_data:
            self.show_message('Error', 'Please load save first')
            return
        
        def on_result(message):
            self.log(message)
        
        popup = SearchPopup(self.editor, on_result)
        popup.open()
    
    def save_file(self, instance):
        """Save save file"""
        if not self.editor.save_data:
            self.show_message('Error', 'Please load save first')
            return
        
        if self.editor.save_save_file():
            self.show_message('Success', 'Save saved\nBackup created')
            self.log('Save saved successfully')
        else:
            self.show_message('Error', 'Save failed')
    
    def export_json(self, instance):
        """Export JSON"""
        if not self.editor.save_data:
            self.show_message('Error', 'Please load save first')
            return
        
        try:
            base_name = os.path.splitext(os.path.basename(self.editor.file_path))[0]
            
            if platform == 'android':
                from android.storage import primary_external_storage_path
                output_dir = primary_external_storage_path()
            else:
                output_dir = os.path.dirname(self.editor.file_path)
            
            output_path = os.path.join(output_dir, f'{base_name}_exported.json')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.editor.save_data, f, ensure_ascii=False, indent=2)
            
            self.show_message('Success', f'JSON exported to:\n{output_path}')
            self.log('JSON export successful')
        except Exception as e:
            self.show_message('Error', f'Export failed: {str(e)}')


class DaveSaveEdApp(App):
    """Kivy app main class"""
    
    def build(self):
        # Initialize logging
        init_logging()
        
        # Request permissions on Android
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                
                permissions = [
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
                
                log_message(f"Requesting permissions: {permissions}")
                request_permissions(permissions)
                
                # Try to request MANAGE_EXTERNAL_STORAGE (Android 11+)
                try:
                    from android import autoclass
                    from android import activity
                    
                    Environment = autoclass('android.os.Environment')
                    if not Environment.isExternalStorageManager():
                        log_message("Need MANAGE_EXTERNAL_STORAGE permission")
                        
                        Intent = autoclass('android.content.Intent')
                        Settings = autoclass('android.provider.Settings')
                        intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                        activity.startActivity(intent)
                except Exception as e:
                    log_message(f"Storage permission check failed: {e}")
                    
            except ImportError as e:
                log_message(f"Permission module import failed: {e}")
        
        Window.clearcolor = (0.12, 0.14, 0.18, 1)
        self.title = 'Dave the Diver Save Editor'
        return MainScreen()


if __name__ == '__main__':
    DaveSaveEdApp().run()
