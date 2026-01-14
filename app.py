import sys
import ctypes
import signal
import time
import os
import shutil
import json
import pyperclip
import keyboard
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QSystemTrayIcon, QMenu, QMessageBox, QAbstractItemView,
                             QCheckBox, QGroupBox, QFileDialog, QListWidget, 
                             QTabWidget, QComboBox, QSplitter, QDoubleSpinBox, QListWidgetItem)
from PyQt6.QtGui import QIcon, QAction, QImage
from PyQt6.QtCore import Qt, QTimer, QSize, QEventLoop, QObject, pyqtSignal, QEvent

# Allow Ctrl+C to kill the app
signal.signal(signal.SIGINT, signal.SIG_DFL)

CONFIG_FILE = "config.json"

class HotkeyService(QObject):
    # Signal now emits a list of actions: [{'type': '...', 'value': '...'}, ...]
    paste_requested = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.hotkeys = {}
        self.load_config()
        self.is_listening = False

    def normalize_key(self, key_combo):
        if not key_combo:
            return ""
        return key_combo.lower().replace(" ", "")

    def load_config(self):
        """Load hotkeys, supporting migration to v4 (dict with tag and actions)."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    
                    self.hotkeys = {}
                    for k, v in raw_data.items():
                        norm_k = self.normalize_key(k)
                        final_data = {'tag': '', 'actions': []}

                        if isinstance(v, dict) and 'actions' in v:
                            final_data = v
                        elif isinstance(v, list):
                            final_data['actions'] = v
                        elif isinstance(v, dict) and 'type' in v:
                            final_data['actions'] = [v]
                        elif isinstance(v, str):
                            final_data['actions'] = [{'type': 'text', 'value': v}]
                            
                        self.hotkeys[norm_k] = final_data
            except Exception as e:
                print(f"Error loading config: {e}")
                self.hotkeys = {}
        else:
            self.hotkeys = {}

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.hotkeys, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def add_hotkey(self, key_combo, actions, tag=""):
        key = self.normalize_key(key_combo)
        self.hotkeys[key] = {'tag': tag, 'actions': actions}
        self.save_config()
        self.restart_listening()

    def remove_hotkey(self, key_combo):
        key = self.normalize_key(key_combo)
        if key in self.hotkeys:
            del self.hotkeys[key]
            self.save_config()
            self.restart_listening()

    def trigger_sequence(self, actions):
        self.paste_requested.emit(actions)

    def start_listening(self):
        try:
            keyboard.unhook_all()
        except:
            pass

        for key, data in self.hotkeys.items():
            if not key or key.strip() == "":
                continue
            try:
                actions = data.get('actions', [])
                if actions:
                    keyboard.add_hotkey(key, lambda a=actions: self.trigger_sequence(a), suppress=True)
            except Exception as e:
                print(f"Failed to register hotkey '{key}': {e}")
        
        self.is_listening = True

    def stop_listening(self):
        try:
            keyboard.unhook_all()
        except:
            pass
        self.is_listening = False

    def restart_listening(self):
        self.start_listening()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuickPaste v3.1 - 可自訂延遲版")
        self.resize(1000, 700)
        self.is_quitting = False

        # Initialize Service
        self.service = HotkeyService()
        self.service.paste_requested.connect(self.handle_sequence_request)
        self.service.start_listening()

        # UI Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Panel ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_list = QLabel("已設定的快捷鍵 (💡 雙擊「備註」欄位可直接修改)")
        lbl_list.setStyleSheet("font-weight: bold; color: #555;")
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["快捷鍵", "備註", "動作數"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.table.itemClicked.connect(self.on_table_click)
        self.table.itemChanged.connect(self.on_table_item_changed)
        
        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("✨ 新增")
        self.btn_new.clicked.connect(self.reset_editor)
        self.btn_del = QPushButton("🗑️ 刪除")
        self.btn_del.clicked.connect(self.delete_hotkey)
        self.btn_del.setStyleSheet("color: red;")
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_del)

        left_layout.addWidget(lbl_list)
        left_layout.addWidget(self.table)
        left_layout.addLayout(btn_layout)

        # --- Right Panel ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        key_group = QGroupBox("1. 設定觸發快捷鍵")
        key_layout = QVBoxLayout()
        k_row = QHBoxLayout()
        self.chk_ctrl = QCheckBox("Ctrl")
        self.chk_shift = QCheckBox("Shift")
        self.chk_alt = QCheckBox("Alt")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("主按鍵 (如: 1, a)")
        self.key_input.setFixedWidth(80)
        self.key_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        k_row.addWidget(self.chk_ctrl)
        k_row.addWidget(self.chk_shift)
        k_row.addWidget(self.chk_alt)
        k_row.addWidget(QLabel("+"))
        k_row.addWidget(self.key_input)
        k_row.addStretch()
        key_layout.addLayout(k_row)
        key_group.setLayout(key_layout)

        seq_group = QGroupBox("2. 編輯動作序列")
        seq_layout = QHBoxLayout()
        self.seq_list = QListWidget()
        self.seq_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        ctrl_layout = QVBoxLayout()
        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedWidth(30)
        self.btn_up.clicked.connect(self.move_step_up)
        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedWidth(30)
        self.btn_down.clicked.connect(self.move_step_down)
        self.btn_remove = QPushButton("✖")
        self.btn_remove.setFixedWidth(30)
        self.btn_remove.setStyleSheet("color: red;")
        self.btn_remove.clicked.connect(self.remove_step)
        ctrl_layout.addWidget(self.btn_up)
        ctrl_layout.addWidget(self.btn_down)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_remove)
        seq_layout.addWidget(self.seq_list)
        seq_layout.addLayout(ctrl_layout)
        seq_group.setLayout(seq_layout)

        add_group = QGroupBox("3. 加入新動作")
        add_layout = QVBoxLayout()
        delay_layout = QHBoxLayout()
        self.spin_delay = QDoubleSpinBox()
        self.spin_delay.setRange(0.0, 10.0)
        self.spin_delay.setSingleStep(0.1)
        self.spin_delay.setValue(0.3)
        self.spin_delay.setSuffix(" 秒")
        delay_layout.addWidget(QLabel("此步驟執行後等待:"))
        delay_layout.addWidget(self.spin_delay)
        delay_layout.addStretch()
        
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        tab_text = QWidget()
        t_layout = QHBoxLayout(tab_text)
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("輸入文字...")
        btn_add_t = QPushButton("加入文字")
        btn_add_t.clicked.connect(self.add_text_step)
        t_layout.addWidget(self.txt_input)
        t_layout.addWidget(btn_add_t)
        
        tab_key = QWidget()
        k_layout = QHBoxLayout(tab_key)
        self.cmb_keys = QComboBox()
        self.cmb_keys.addItems(["enter", "tab", "backspace", "space", "esc"])
        self.cmb_keys.setEditable(True)
        btn_add_k = QPushButton("加入按鍵")
        btn_add_k.clicked.connect(self.add_key_step)
        k_layout.addWidget(self.cmb_keys)
        k_layout.addWidget(btn_add_k)
        
        tab_img = QWidget()
        i_layout = QHBoxLayout(tab_img)
        self.lbl_img = QLineEdit()
        self.lbl_img.setReadOnly(True)
        btn_brow = QPushButton("瀏覽...")
        btn_brow.clicked.connect(self.browse_image)
        btn_add_i = QPushButton("加入圖片")
        btn_add_i.clicked.connect(self.add_img_step)
        i_layout.addWidget(self.lbl_img)
        i_layout.addWidget(btn_brow)
        i_layout.addWidget(btn_add_i)

        self.tab_widget.addTab(tab_text, "📝 文字")
        self.tab_widget.addTab(tab_key, "⌨️ 按鍵")
        self.tab_widget.addTab(tab_img, "🖼️ 圖片")
        
        add_layout.addLayout(delay_layout)
        add_layout.addWidget(self.tab_widget)
        add_group.setLayout(add_layout)

        self.btn_save = QPushButton("💾 儲存此快捷鍵設定")
        self.btn_save.setStyleSheet("font-weight: bold; padding: 5px;")
        self.btn_save.clicked.connect(self.save_hotkey)

        right_layout.addWidget(key_group)
        right_layout.addWidget(seq_group)
        right_layout.addWidget(add_group)
        right_layout.addWidget(self.btn_save)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2)

        bottom_bar = QHBoxLayout()
        self.status_label = QLabel("就緒")
        self.status_label.setStyleSheet("color: gray;")
        
        self.btn_reload = QPushButton("🔄 重載快捷鍵")
        self.btn_reload.clicked.connect(self.on_reload_click)

        self.btn_quit = QPushButton("🔴 結束程式")
        self.btn_quit.clicked.connect(self.quit_app)
        self.btn_quit.setStyleSheet("color: red;")
        
        bottom_bar.addWidget(self.status_label)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_reload)
        bottom_bar.addWidget(self.btn_quit)

        layout_container = QVBoxLayout()
        layout_container.addWidget(splitter)
        layout_container.addLayout(bottom_bar)
        self.central_widget.setLayout(layout_container)
        
        self.setup_tray()
        self.refresh_table()

        QApplication.instance().focusChanged.connect(self.on_focus_changed)

    def on_reload_click(self):
        self.service.restart_listening()
        self.status_label.setText("快捷鍵已重載 ✓")
        QTimer.singleShot(2000, lambda: self.status_label.setText("就緒"))

    def on_focus_changed(self, old, new):
        if new and (isinstance(new, QLineEdit) or isinstance(new, QDoubleSpinBox) or isinstance(new, QComboBox)):
            if self.service.is_listening:
                self.service.stop_listening()
                self.status_label.setText("輸入模式 (快捷鍵暫停)")
        else:
            if not self.service.is_listening:
                self.service.restart_listening()
                self.status_label.setText("就緒")

    def on_tab_changed(self, index):
        if index == 0: self.spin_delay.setValue(0.3)
        elif index == 1: self.spin_delay.setValue(0.1)
        elif index == 2: self.spin_delay.setValue(1.5)

    def add_step_to_list(self, a_type, value, display, delay):
        item_text = f"[{a_type.upper()}] {display} (wait {delay}s)"
        l_item = QListWidgetItem(item_text)
        l_item.setData(Qt.ItemDataRole.UserRole, {'type': a_type, 'value': value, 'delay': delay})
        self.seq_list.addItem(l_item)
        self.seq_list.scrollToBottom()

    def add_text_step(self):
        val = self.txt_input.text()
        if val:
            self.add_step_to_list('text', val, val, self.spin_delay.value())
            self.txt_input.clear()

    def add_key_step(self):
        val = self.cmb_keys.currentText()
        if val: self.add_step_to_list('key', val, val, self.spin_delay.value())

    def add_img_step(self):
        path = self.lbl_img.text()
        if path:
            self.add_step_to_list('image', path, os.path.basename(path), self.spin_delay.value())
            self.lbl_img.clear()

    def browse_image(self):
        fname, _ = QFileDialog.getOpenFileName(self, "選圖", "", "Images (*.png *.jpg *.jpeg)")
        if fname: self.lbl_img.setText(fname)

    def remove_step(self):
        row = self.seq_list.currentRow()
        if row >= 0: self.seq_list.takeItem(row)

    def move_step_up(self):
        row = self.seq_list.currentRow()
        if row > 0:
            item = self.seq_list.takeItem(row)
            self.seq_list.insertItem(row-1, item)
            self.seq_list.setCurrentRow(row-1)

    def move_step_down(self):
        row = self.seq_list.currentRow()
        if row < self.seq_list.count()-1 and row >= 0:
            item = self.seq_list.takeItem(row)
            self.seq_list.insertItem(row+1, item)
            self.seq_list.setCurrentRow(row+1)

    def get_key_string(self):
        parts = []
        if self.chk_ctrl.isChecked(): parts.append("ctrl")
        if self.chk_shift.isChecked(): parts.append("shift")
        if self.chk_alt.isChecked(): parts.append("alt")
        k = self.key_input.text().strip().lower()
        if not k: return None
        parts.append(k)
        return "+".join(parts)

    def save_hotkey(self):
        key = self.get_key_string()
        if not key or self.seq_list.count() == 0: return
        actions = []
        for i in range(self.seq_list.count()):
            data = self.seq_list.item(i).data(Qt.ItemDataRole.UserRole)
            if data['type'] == 'image':
                src = data['value']
                if "images" not in src and os.path.exists(src):
                    try:
                        if not os.path.exists("images"): os.makedirs("images")
                        dest = os.path.join("images", f"{int(time.time())}_{os.path.basename(src)}")
                        shutil.copy2(src, dest)
                        data['value'] = dest
                    except: pass
            actions.append(data)
        
        # Smart Tag Generation
        current_tag = self.service.hotkeys.get(key, {}).get('tag', '')
        
        # Only auto-generate if tag is empty
        if not current_tag.strip():
            summary_parts = []
            for act in actions:
                if act['type'] == 'text':
                    # Truncate text to 6 chars
                    t_val = act['value']
                    if len(t_val) > 6: t_val = t_val[:6] + ".."
                    summary_parts.append(f"文[{t_val}]")
                elif act['type'] == 'key':
                    summary_parts.append(f"按[{act['value']}]")
                elif act['type'] == 'image':
                    summary_parts.append("圖")
            
            # Limit total summary length
            full_summary = "+".join(summary_parts)
            if len(full_summary) > 40: full_summary = full_summary[:40] + "..."
            current_tag = full_summary
        
        self.service.add_hotkey(key, actions, current_tag)
        self.refresh_table()
        self.reset_editor()
        self.status_label.setText(f"已儲存: {key}")

    def delete_hotkey(self):
        row = self.table.currentRow()
        if row >= 0:
            key = self.table.item(row, 0).text()
            if QMessageBox.question(self, "刪除", f"確認刪除 {key}?") == QMessageBox.StandardButton.Yes:
                self.service.remove_hotkey(key)
                self.refresh_table()
                self.reset_editor()

    def on_table_click(self, item):
        key = self.table.item(item.row(), 0).text()
        data = self.service.hotkeys.get(key, {'tag': '', 'actions': []})
        self.reset_editor()
        parts = key.split('+')
        self.chk_ctrl.setChecked('ctrl' in parts)
        self.chk_shift.setChecked('shift' in parts)
        self.chk_alt.setChecked('alt' in parts)
        mods = ['ctrl','shift','alt']
        main = [p for p in parts if p not in mods]
        if main: self.key_input.setText(main[0])
        for act in data.get('actions', []):
            delay = act.get('delay', 0.5 if act['type']=='image' else 0.1)
            self.add_step_to_list(act['type'], act['value'], act['value'], delay)

    def on_table_item_changed(self, item):
        if item.column() == 1:
            row = item.row()
            key_item = self.table.item(row, 0)
            if key_item:
                key = key_item.text()
                if key in self.service.hotkeys:
                    self.service.hotkeys[key]['tag'] = item.text()
                    self.service.save_config()

    def reset_editor(self):
        self.chk_ctrl.setChecked(False)
        self.chk_shift.setChecked(False)
        self.chk_alt.setChecked(False)
        self.key_input.clear()
        self.seq_list.clear()
        self.txt_input.clear()
        self.lbl_img.clear()

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for k, v in self.service.hotkeys.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            item_key = QTableWidgetItem(k)
            item_key.setFlags(item_key.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 0, item_key)
            self.table.setItem(r, 1, QTableWidgetItem(v.get('tag', '')))
            actions = v.get('actions', [])
            item_count = QTableWidgetItem(str(len(actions)))
            item_count.setFlags(item_count.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 2, item_count)
        self.table.blockSignals(False)

    def safe_wait(self, seconds):
        loop = QEventLoop()
        QTimer.singleShot(int(seconds * 1000), loop.quit)
        loop.exec()

    def handle_sequence_request(self, actions):
        self.status_label.setText("執行中...")
        clipboard = QApplication.clipboard()
        for act in actions:
            delay = act.get('delay', 0.5) 
            try:
                if act['type'] == 'text':
                    pyperclip.copy(act['value'])
                    self.safe_wait(0.05)
                    keyboard.send('ctrl+v')
                elif act['type'] == 'key':
                    keyboard.send(act['value'])
                elif act['type'] == 'image':
                    if os.path.exists(act['value']):
                        img = QImage(act['value'])
                        if not img.isNull():
                            clipboard.setImage(img)
                            self.safe_wait(0.1)
                            keyboard.send('ctrl+v')
            except: pass
            self.safe_wait(delay)
        self.status_label.setText("完成")

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        menu = QMenu()
        menu.addAction("顯示主視窗", self.show)
        menu.addAction("🔄 重載快捷鍵", self.service.restart_listening)
        menu.addSeparator()
        menu.addAction("結束程式", self.quit_app)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)

    def closeEvent(self, e):
        self.service.stop_listening()
        e.accept()

    def quit_app(self):
        self.is_quitting = True
        self.service.stop_listening()
        QApplication.instance().quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())