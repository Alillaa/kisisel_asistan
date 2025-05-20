import sys
import sqlite3
import hashlib
import datetime
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox, QComboBox,
                             QGroupBox, QRadioButton, QDialog, QProgressBar, QSlider, QTableWidget, QTableWidgetItem, QMenuBar, QAction,
                             QInputDialog, QDial, QToolBox, QListWidget, QLabel, QPushButton, QTabWidget, QSpinBox, QDoubleSpinBox,
                             QFormLayout, QTextEdit, QMessageBox, QCalendarWidget, QDesktopWidget, QHeaderView, QSizePolicy,
                             QStyle, QGridLayout)
from PyQt5.QtCore import Qt, QDate, QTimer, QSize, QFile
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap
import traceback

DATABASE_NAME = 'personal_diary_app_v2.db'
WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"

ICON_PATHS = {
    "app_icon": "icons/app_icon.png",
    "home": "icons/home.png",
    "new_entry": "icons/new_entry.png",
    "my_entries": "icons/my_entries.png",
    "health": "icons/health.png",
    "weather": "icons/weather.png",
    "save": "icons/save.png",
    "delete": "icons/delete.png",
    "view": "icons/view.png",
    "settings": "icons/settings.png",
    "theme": "icons/theme.png",
    "city_settings": "icons/city_settings.png",
    "exit": "icons/exit.png",
    "about": "icons/about.png",
    "change_user": "icons/change_user.png",
    "fetch_weather": "icons/fetch_weather.png",
    "welcome_flower": "icons/welcome_flower.png",
    "important_star": "icons/important_star.png",
    "health_save": "icons/health_save.png",
    "calendar": "icons/calendar.png",
    "quote": "icons/quote.png",
    "quick_actions": "icons/quick_actions.png",
    "diary_title_icon": "icons/diary_title_icon.png",
    "user": "icons/user.png",
    "password": "icons/password.png",
    "register": "icons/register.png",
    "login": "icons/login.png",
    "api_key_icon": "icons/api_key_icon.png"
}

def get_icon(icon_key, fallback_style_enum=None):
    icon_path = ICON_PATHS.get(icon_key)
    if icon_path and QFile.exists(icon_path):
        return QIcon(icon_path)
    elif fallback_style_enum and QApplication.instance():
        try:
            return QApplication.instance().style().standardIcon(fallback_style_enum)
        except Exception:
            pass
    if icon_key == "exit" and QApplication.instance():
        return QApplication.instance().style().standardIcon(QStyle.SP_DialogCancelButton)
    if icon_key == "save" and QApplication.instance():
        return QApplication.instance().style().standardIcon(QStyle.SP_DialogSaveButton)
    if icon_key == "delete" and QApplication.instance():
        return QApplication.instance().style().standardIcon(QStyle.SP_TrashIcon)
    if icon_key == "view" and QApplication.instance():
        return QApplication.instance().style().standardIcon(QStyle.SP_FileIcon)
    return QIcon()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT,
        surname TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS diary_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        entry_date TEXT NOT NULL,
        title TEXT,
        content TEXT NOT NULL,
        mood TEXT,
        is_important INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS health_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        water_ml INTEGER DEFAULT 0,
        exercise_km REAL DEFAULT 0.0,
        sleep_hours REAL DEFAULT 0.0,
        UNIQUE(user_id, log_date),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        theme_color TEXT,
        city TEXT,
        api_key TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    try:
        cursor.execute("SELECT api_key FROM user_preferences LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE user_preferences ADD COLUMN api_key TEXT")

    conn.commit()
    conn.close()

def add_user(username, password, name, surname):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash, name, surname) VALUES (?, ?, ?, ?)",
                       (username, hash_password(password), name, surname))
        user_id = cursor.lastrowid
        if user_id:
            cursor.execute("INSERT OR IGNORE INTO user_preferences (user_id, theme_color, city, api_key) VALUES (?, ?, ?, ?)",
                           (user_id, "Mavi", "Istanbul", None))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_user(username, password):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, name, surname FROM users WHERE username = ?", (username,))
    user_record = cursor.fetchone()
    conn.close()
    if user_record and user_record[1] == hash_password(password):
        user_name = user_record[2] if user_record[2] is not None else ""
        user_surname = user_record[3] if user_record[3] is not None else ""
        return {"id": user_record[0], "name": user_name, "surname": user_surname, "username": username}
    return None

def save_user_preference(user_id, key, value):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO user_preferences (user_id, theme_color, city, api_key) VALUES (?, ?, ?, ?)",
                   (user_id, "Mavi", "Istanbul", None))

    valid_keys = ["theme_color", "city", "api_key"]
    if key in valid_keys:
        cursor.execute(f"UPDATE user_preferences SET {key} = ? WHERE user_id = ?", (value, user_id))
    else:
        conn.close()
        return
    conn.commit()
    conn.close()

def get_user_preference(user_id, key):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    valid_keys = ["theme_color", "city", "api_key"]
    if key not in valid_keys:
        conn.close()
        return None
    try:
        cursor.execute(f"SELECT {key} FROM user_preferences WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.OperationalError as e:
        return None
    finally:
        conn.close()

def add_diary_entry(user_id, title, content, mood, is_important):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    entry_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO diary_entries (user_id, entry_date, title, content, mood, is_important) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, entry_date, title, content, mood, 1 if is_important else 0))
    conn.commit()
    conn.close()

def get_diary_entries(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, entry_date, title, mood, is_important, SUBSTR(content, 1, 50) FROM diary_entries WHERE user_id = ? ORDER BY entry_date DESC", (user_id,))
    entries = cursor.fetchall()
    conn.close()
    return entries

def get_diary_entry_by_id(entry_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, mood, is_important FROM diary_entries WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()
    conn.close()
    return entry

def delete_diary_entry(entry_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

def update_health_log(user_id, date_str, water_ml, exercise_km, sleep_hours):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO health_data (user_id, log_date, water_ml, exercise_km, sleep_hours) VALUES (?, ?, ?, ?, ?)",
                   (user_id, date_str, water_ml, exercise_km, sleep_hours))
    conn.commit()
    conn.close()

def get_health_log(user_id, date_str):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT water_ml, exercise_km, sleep_hours FROM health_data WHERE user_id = ? AND log_date = ?", (user_id, date_str))
    log = cursor.fetchone()
    conn.close()
    return log if log else (0, 0.0, 0.0)

init_db()

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kullanıcı Girişi")
        self.setWindowIcon(get_icon("app_icon"))
        self.setModal(True)
        self.setFixedSize(400, 250)
        self.setStyleSheet("""
            QDialog { background-color: #E8F0FE; }
            QLabel { font-size: 12pt; color: #333; }
            QLineEdit { padding: 8px; border: 1px solid #B0C4DE; border-radius: 4px; font-size: 11pt; background-color: white; }
            QPushButton {
                background-color: #4A90E2; color: white; padding: 10px 15px;
                font-size: 11pt; border: none; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #357ABD; }
            QPushButton#registerBtn { background-color: #50C878; }
            QPushButton#registerBtn:hover { background-color: #3A9D59; }
        """)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 10)

        self.username_edit = QLineEdit(self)
        self.username_edit.setPlaceholderText("Kullanıcı Adı")
        form_layout.addRow(QLabel("Kullanıcı Adı:"), self.username_edit)

        self.password_edit = QLineEdit(self)
        self.password_edit.setPlaceholderText("Parola")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow(QLabel("Parola:"), self.password_edit)

        layout.addLayout(form_layout)
        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 0, 20, 20)
        self.login_btn = QPushButton("Giriş Yap", self)
        self.login_btn.setIcon(get_icon("login"))
        self.login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(self.login_btn)

        self.register_btn = QPushButton("Kayıt Ol", self)
        self.register_btn.setObjectName("registerBtn")
        self.register_btn.setIcon(get_icon("register"))
        self.register_btn.clicked.connect(self.handle_register_dialog)
        button_layout.addWidget(self.register_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.user_data = None

    def handle_register_dialog(self):
        register_dialog = RegisterDialog(self)
        if register_dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Kayıt Başarılı", "Yeni kullanıcı başarıyla oluşturuldu. Lütfen giriş yapın.")

    def handle_login(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        user = check_user(username, password)
        if user:
            self.user_data = user
            self.accept()
        else:
            QMessageBox.warning(self, "Giriş Hatası", "Kullanıcı adı veya parola hatalı!")
            self.user_data = None

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Kullanıcı Kaydı")
        self.setWindowIcon(get_icon("app_icon"))
        self.setFixedSize(450, 380)
        self.setStyleSheet("""
            QDialog { background-color: #E8F0FE; }
            QLabel { font-size: 12pt; color: #333; }
            QLineEdit { padding: 8px; border: 1px solid #B0C4DE; border-radius: 4px; font-size: 11pt; background-color: white;}
            QPushButton {
                background-color: #50C878; color: white; padding: 10px 15px;
                font-size: 11pt; border: none; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3A9D59; }
        """)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(20,20,20,10)

        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("Adınız")
        form_layout.addRow(QLabel("Ad:"), self.name_edit)

        self.surname_edit = QLineEdit(self)
        self.surname_edit.setPlaceholderText("Soyadınız")
        form_layout.addRow(QLabel("Soyad:"), self.surname_edit)

        self.username_edit = QLineEdit(self)
        self.username_edit.setPlaceholderText("Kullanıcı Adı Seçin")
        form_layout.addRow(QLabel("Kullanıcı Adı:"), self.username_edit)

        self.password_edit = QLineEdit(self)
        self.password_edit.setPlaceholderText("Parola Oluşturun")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow(QLabel("Parola:"), self.password_edit)

        self.confirm_password_edit = QLineEdit(self)
        self.confirm_password_edit.setPlaceholderText("Parolayı Doğrulayın")
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow(QLabel("Parola Tekrar:"), self.confirm_password_edit)

        layout.addLayout(form_layout)
        layout.addStretch()

        self.register_btn = QPushButton("Kayıt Ol", self)
        self.register_btn.setIcon(get_icon("register"))
        self.register_btn.setFixedHeight(40)
        self.register_btn.clicked.connect(self.handle_registration)

        button_container = QWidget()
        button_h_layout = QHBoxLayout(button_container)
        button_h_layout.addStretch()
        button_h_layout.addWidget(self.register_btn)
        button_h_layout.addStretch()
        button_h_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(button_container)
        layout.setContentsMargins(20,20,20,20)
        self.setLayout(layout)

    def handle_registration(self):
        name = self.name_edit.text()
        surname = self.surname_edit.text()
        username = self.username_edit.text()
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()

        if not (name.strip() and surname.strip() and username.strip() and password and confirm_password):
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen tüm alanları doldurun.")
            return
        if len(password) < 6:
            QMessageBox.warning(self, "Parola Zayıf", "Parola en az 6 karakter olmalıdır.")
            return
        if password != confirm_password:
            QMessageBox.warning(self, "Parola Hatası", "Parolalar eşleşmiyor.")
            return

        if add_user(username, password, name, surname):
            self.accept()
        else:
            QMessageBox.warning(self, "Kayıt Hatası", "Bu kullanıcı adı zaten alınmış veya bir veritabanı hatası oluştu.")


class App(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.user_id = self.user_data["id"]
        self.username = self.user_data["username"]
        self.user_name_str = str(self.user_data.get("name", ""))
        self.user_surname_str = str(self.user_data.get("surname", ""))

        global WEATHER_API_KEY
        saved_api_key = get_user_preference(self.user_id, "api_key")
        if saved_api_key:
            WEATHER_API_KEY = saved_api_key
        
        self.setWindowIcon(get_icon("app_icon"))
        self.setWindowTitle(f"Kişisel Asistanım - Hoş Geldin {self.user_name_str}!")
        self.setGeometry(0, 0, 1200, 850)
        self.center_window()

        self.current_theme_color_name = get_user_preference(self.user_id, "theme_color") or "Mavi"
        self.apply_theme_color(self.current_theme_color_name)

        self._create_menu_bar()
        self.init_ui()

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.auto_fetch_weather)
        self.weather_timer.start(1800000)


    def apply_theme_color(self, color_name_key):
        self.current_theme_color_name = color_name_key
        self.color_map_themes = {
            "Mavi": ("#E0F2F7", "#B3E5FC", "#81D4FA", "#29B6F6", "#FFFFFF", "#222222"),
            "Yeşil": ("#E8F5E9", "#C8E6C9", "#A5D6A7", "#66BB6A", "#FFFFFF", "#1B5E20"),
            "Sarı": ("#FFFDE7", "#FFF9C4", "#FFF59D", "#FFEE58", "#424242", "#795548"),
            "Kırmızı": ("#FFEBEE", "#FFCDD2", "#EF9A9A", "#EF5350", "#FFFFFF", "#B71C1C"),
            "Mor": ("#F3E5F5", "#E1BEE7", "#CE93D8", "#AB47BC", "#FFFFFF", "#4A148C"),
            "Turuncu": ("#FFF3E0", "#FFE0B2", "#FFCC80", "#FFA726", "#FFFFFF", "#E65100"),
            "Koyu Gri": ("#ECEFF1", "#CFD8DC", "#B0BEC5", "#78909C", "#FFFFFF", "#263238"),
            "Pembe": ("#FCE4EC", "#F8BBD0", "#F48FB1", "#F06292", "#FFFFFF", "#880E4F"),
            "Doğa Yeşili": ("#D1E8D1", "#A3D1A3", "#7CC07C", "#5EAE5E", "#FFFFFF", "#104510"),
            "Gökyüzü Mavisi": ("#D6EEF7", "#AEDBF0", "#8AC9E9", "#6AB7E2", "#FFFFFF", "#1A3A4A")
        }
        current_palette = self.color_map_themes.get(color_name_key, self.color_map_themes["Mavi"])
        main_bg, widget_bg, tab_bg, accent_color, text_color_on_accent, main_text_color = current_palette
        self.setStyleSheet(f"""
            QMainWindow, QDialog {{ background-color: {main_bg}; font-size: 10pt; color: {main_text_color}; }}
            QTabWidget::pane {{ border: 1px solid {self.adjust_color(accent_color, -30)}; background-color: {widget_bg}; border-radius: 0 0 6px 6px;}}
            QTabBar::tab {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.adjust_color(tab_bg, 20)}, stop:1 {tab_bg});
                border: 1px solid {self.adjust_color(accent_color, -30)};
                border-bottom: none; /* Seçili olmayan tabın alt kenarını kaldır */
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 100px; padding: 8px 15px; margin-right: 2px; color: {main_text_color}; font-weight: bold;
            }}
            QTabBar::tab:selected {{ background: {accent_color}; color: {text_color_on_accent}; border-color: {accent_color}; }}
            QTabBar::tab:hover {{ background: {self.adjust_color(accent_color, 15)}; color: {text_color_on_accent if self.is_light_color(accent_color) else main_text_color };}}
            QWidget {{ background-color: transparent; color: {main_text_color}; }}
            QTabWidget QWidget {{ background-color: {widget_bg}; }}
            QLabel, QCheckBox, QRadioButton {{ font-size: 10pt; background-color: transparent; color: {main_text_color}; }}
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                padding: 7px; border: 1px solid {self.adjust_color(accent_color, -50)}; border-radius: 5px;
                background-color: #FFFFFF; font-size: 10pt; color: #333333;
            }}
            QComboBox QAbstractItemView {{ background-color: #FFFFFF; color: #333333; selection-background-color: {accent_color}; selection-color: {text_color_on_accent}; }}
            QPushButton {{
                background-color: {accent_color}; color: {text_color_on_accent}; padding: 8px 15px;
                font-size: 10pt; border: 1px solid {self.adjust_color(accent_color, -20)}; border-radius: 5px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.adjust_color(accent_color, -20)}; border: 1px solid {self.adjust_color(accent_color, -40)};}}
            QPushButton:pressed {{ background-color: {self.adjust_color(accent_color, -40)}; }}
            QPushButton:disabled {{ background-color: {self.adjust_color(accent_color, 50)}; color: {self.adjust_color(text_color_on_accent, 50)}; border-color: {self.adjust_color(accent_color, 30)};}}
            QGroupBox {{
                font-weight: bold; border: 1px solid {accent_color}; border-radius: 6px;
                margin-top: 1em; padding: 1em 0.5em 0.5em 0.5em; background-color: {self.adjust_color(widget_bg, 5)};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 7px; left: 10px; color: {accent_color}; background-color: {widget_bg}; border-radius: 3px; }}
            QTableWidget {{ gridline-color: {self.adjust_color(accent_color, -40)}; background-color: #FFFFFF; color: #333333; alternate-background-color: {self.adjust_color(widget_bg, 10)};}}
            QHeaderView::section {{ background-color: {tab_bg}; padding: 5px; border: 1px solid {self.adjust_color(accent_color, -30)}; font-size: 10pt; font-weight: bold; color: {main_text_color};}}
            QProgressBar {{ border: 1px solid {accent_color}; border-radius: 5px; text-align: center; background-color: #FFFFFF; color: {main_text_color};}}
            QProgressBar::chunk {{ background-color: {accent_color}; border-radius: 4px;}}
            QSlider::groove:horizontal {{ border: 1px solid {self.adjust_color(accent_color, -50)}; background: #FFFFFF; height: 8px; border-radius: 4px; }}
            QSlider::handle:horizontal {{ background: {accent_color}; border: 1px solid {accent_color}; width: 16px; margin: -4px 0; border-radius: 8px;}}
            QListWidget {{ background-color: #FFFFFF; border: 1px solid {self.adjust_color(accent_color, -30)}; color: #333333; }}
            QListWidget::item:selected {{ background-color: {accent_color}; color: {text_color_on_accent}; }}
            QMenuBar {{ background-color: {main_bg}; color: {main_text_color}; border-bottom: 1px solid {self.adjust_color(accent_color, -30)};}}
            QMenuBar::item {{ background: transparent; padding: 5px 10px; }}
            QMenuBar::item:selected {{ background: {accent_color}; color: {text_color_on_accent}; }}
            QMenu {{ background-color: {widget_bg}; border: 1px solid {self.adjust_color(accent_color, -20)}; color: {main_text_color}; }}
            QMenu::item:selected {{ background-color: {accent_color}; color: {text_color_on_accent}; }}
            QCalendarWidget QWidget {{ alternate-background-color: {accent_color}; selection-background-color: {self.adjust_color(accent_color, -30)}; }}
            QCalendarWidget QToolButton {{ color: {main_text_color}; background-color: {tab_bg}; border: none; padding: 5px; }}
            QCalendarWidget QToolButton:hover {{ background-color: {accent_color}; color: {text_color_on_accent}; }}
            QCalendarWidget QMenu {{ background-color: {widget_bg}; }}
            QCalendarWidget QSpinBox {{ background-color: white; color: black; }}
            QCalendarWidget #qt_calendar_navigationbar {{ background-color: {tab_bg}; }}
            QToolBox::tab {{ background: {tab_bg}; border-radius: 4px; padding: 8px; color: {main_text_color}; font-weight:bold; border: 1px solid {self.adjust_color(accent_color, -30)}; }}
            QToolBox::tab:selected {{ background: {accent_color}; color: {text_color_on_accent}; border: 1px solid {accent_color};}}
            QToolBox QWidget {{ background-color: {self.adjust_color(widget_bg, 5)}; }}
        """)
        save_user_preference(self.user_id, "theme_color", color_name_key)

    def is_light_color(self, hex_color):
        color = QColor(hex_color)
        return color.lightnessF() > 0.6

    def adjust_color(self, hex_color, amount):
        try:
            color = QColor(hex_color)
            h, s, l_val, a = color.getHslF()
            
            l_val = max(0.0, min(1.0, l_val + amount / 255.0))
            
            return QColor.fromHslF(h, s, l_val, a).name()
        except Exception:
            return hex_color

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Dosya")
        file_menu.setIcon(get_icon("settings"))
        change_user_action = QAction(get_icon("change_user"), "Kullanıcı Değiştir", self)
        change_user_action.triggered.connect(self.logout_and_restart)
        file_menu.addAction(change_user_action)
        exit_action = QAction(get_icon("exit", QStyle.SP_DialogCancelButton), "Çıkış", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = menu_bar.addMenu("Ayarlar")
        settings_menu.setIcon(get_icon("settings"))
        theme_menu = settings_menu.addMenu(get_icon("theme"),"Tema Rengi Seç")
        for color_name_key in self.color_map_themes.keys():
            action = QAction(color_name_key, self)
            action.triggered.connect(lambda checked, c=color_name_key: self.apply_theme_color(c))
            theme_menu.addAction(action)
        set_city_action = QAction(get_icon("city_settings"), "Varsayılan Şehri Ayarla", self)
        set_city_action.triggered.connect(self.set_default_city)
        settings_menu.addAction(set_city_action)

        set_api_key_action = QAction(get_icon("api_key_icon", QStyle.SP_ComputerIcon),"API Anahtarını Ayarla", self)
        set_api_key_action.triggered.connect(self.set_user_api_key)
        settings_menu.addAction(set_api_key_action)


        help_menu = menu_bar.addMenu("Yardım")
        about_action = QAction(get_icon("about", QStyle.SP_MessageBoxInformation), "Hakkında", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def set_user_api_key(self):
        global WEATHER_API_KEY
        current_key = get_user_preference(self.user_id, "api_key") or ""
        
        instructions_text = (
            "OpenWeatherMap API Anahtarı Nasıl Alınır:\n"
            "1. https://openweathermap.org/free adresine gidin.\n"
            "2. \"Current Weather Data\" altındaki \"Get API key\" butonuna tıklayın.\n"
            "3. Ücretsiz bir hesap oluşturun veya giriş yapın.\n"
            "4. Giriş yaptıktan sonra \"My API keys\" bölümünden anahtarınızı kopyalayın."
        )
        
        new_key, ok = QInputDialog.getText(self, "API Anahtarı Ayarı",
                                           f"{instructions_text}\n\nLütfen OpenWeatherMap API anahtarınızı girin:",
                                           QLineEdit.Normal, current_key)
        if ok:
            if new_key.strip():
                WEATHER_API_KEY = new_key.strip()
                save_user_preference(self.user_id, "api_key", WEATHER_API_KEY)
                QMessageBox.information(self, "API Anahtarı Güncellendi", "API anahtarınız güncellendi ve kaydedildi.")
                self.auto_fetch_weather()
            else:
                WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
                save_user_preference(self.user_id, "api_key", None)
                QMessageBox.information(self, "API Anahtarı Temizlendi", "Kaydedilmiş API anahtarınız temizlendi.")
                if hasattr(self, 'temp_label'):
                    self._reset_weather_labels_on_error(api_key_cleared=True)


    def set_default_city(self):
        current_city = get_user_preference(self.user_id, 'city') or "Istanbul"
        new_city, ok = QInputDialog.getText(self, "Varsayılan Şehir", "Hava durumu için varsayılan şehri girin:", QLineEdit.Normal, current_city)
        if ok and new_city.strip():
            save_user_preference(self.user_id, "city", new_city.strip())
            QMessageBox.information(self, "Şehir Güncellendi", f"Varsayılan şehir '{new_city.strip()}' olarak ayarlandı.")
            if hasattr(self, 'city_input'): self.city_input.setText(new_city.strip())
            self.auto_fetch_weather()

    def logout_and_restart(self):
        self.close()
        QApplication.instance().setProperty("restart", True)
        QApplication.instance().quit()

    def show_about_dialog(self):
        QMessageBox.about(self, "Hakkında", "Kişisel Asistanım v1.5\n\nPyQt5 ile geliştirilmiştir.\n\nÖzellikler: Günlük, Sağlık Takibi, Hava Durumu, API Kaydı.")

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tab_ana_sayfa = QWidget()
        self.tab_gunluk_yaz = QWidget()
        self.tab_gunluklerim = QWidget()
        self.tab_saglik = QWidget()
        self.tab_hava_durumu = QWidget()
        self.tabs.addTab(self.tab_ana_sayfa, get_icon("home"), "Ana Sayfa")
        self.tabs.addTab(self.tab_gunluk_yaz, get_icon("new_entry"), "Yeni Günlük")
        self.tabs.addTab(self.tab_gunluklerim, get_icon("my_entries"), "Günlüklerim")
        self.tabs.addTab(self.tab_saglik, get_icon("health"), "Sağlık Takip")
        self.tabs.addTab(self.tab_hava_durumu, get_icon("weather"), "Hava Durumu")
        self.tabs.setIconSize(QSize(20, 20))
        self.create_ana_sayfa_tab(self.tab_ana_sayfa)
        self.create_gunluk_yaz_tab(self.tab_gunluk_yaz)
        self.create_gunluklerim_tab(self.tab_gunluklerim)
        self.create_saglik_tab(self.tab_saglik)
        self.create_hava_durumu_tab(self.tab_hava_durumu)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.on_tab_changed(self.tabs.currentIndex())

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def on_tab_changed(self, index):
        current_tab_widget = self.tabs.widget(index)
        if current_tab_widget == self.tab_gunluklerim:
            self.load_diary_entries()
        elif current_tab_widget == self.tab_saglik:
            if hasattr(self, 'health_calendar'):
                self.health_calendar.setSelectedDate(QDate.currentDate())
                self.load_health_data_for_date(QDate.currentDate())
        elif current_tab_widget == self.tab_hava_durumu:
            self.auto_fetch_weather()

    def create_ana_sayfa_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30,25,30,25)
        layout.setSpacing(20)

        welcome_layout = QHBoxLayout()
        welcome_label = QLabel(f"Merhaba, {self.user_name_str}!", self)
        welcome_label.setFont(QFont("Arial", 26, QFont.Bold))
        welcome_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        welcome_layout.addWidget(welcome_label)
        welcome_layout.addStretch()
        self.decorative_image_label = QLabel(self)
        pixmap = QPixmap(ICON_PATHS.get("welcome_flower", ""))
        if not pixmap.isNull():
            self.decorative_image_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.decorative_image_label.setText("🌸")
            self.decorative_image_label.setFont(QFont("Arial", 30))
        self.decorative_image_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        welcome_layout.addWidget(self.decorative_image_label)
        layout.addLayout(welcome_layout)

        date_label = QLabel(QDate.currentDate().toString("d MMMM yy, dddd"), self)
        date_label.setFont(QFont("Arial", 14, QFont.StyleItalic))
        date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(date_label)

        quote_group = QGroupBox("Günün İlhamı", self)
        quote_layout = QVBoxLayout(quote_group)
        self.quote_label = QLabel("Her yeni gün, hayatınızı değiştirmek için bir şanstır. Kelebekler gibi kanatlanın! 🦋", self)
        self.quote_label.setFont(QFont("Georgia", 13, QFont.StyleItalic))
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignCenter)
        quote_layout.addWidget(self.quote_label)
        layout.addWidget(quote_group)

        quick_actions_group = QGroupBox("Hızlı Erişim", self)
        actions_layout = QGridLayout(quick_actions_group)
        actions_layout.setSpacing(15)

        btn_new_entry = QPushButton(get_icon("new_entry"), " Yeni Günlük Yaz", self)
        btn_new_entry.setFixedHeight(45)
        btn_new_entry.setIconSize(QSize(20,20))
        btn_new_entry.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_gunluk_yaz))
        actions_layout.addWidget(btn_new_entry, 0, 0)

        btn_view_entries = QPushButton(get_icon("my_entries"), " Günlüklerimi Gör", self)
        btn_view_entries.setFixedHeight(45)
        btn_view_entries.setIconSize(QSize(20,20))
        btn_view_entries.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_gunluklerim))
        actions_layout.addWidget(btn_view_entries, 0, 1)

        btn_health_tracker = QPushButton(get_icon("health"), " Sağlık Takibim", self)
        btn_health_tracker.setFixedHeight(45)
        btn_health_tracker.setIconSize(QSize(20,20))
        btn_health_tracker.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_saglik))
        actions_layout.addWidget(btn_health_tracker, 1, 0)

        btn_weather = QPushButton(get_icon("weather"), " Hava Durumu", self)
        btn_weather.setFixedHeight(45)
        btn_weather.setIconSize(QSize(20,20))
        btn_weather.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_hava_durumu))
        actions_layout.addWidget(btn_weather, 1, 1)
        layout.addWidget(quick_actions_group)
        layout.addStretch()

    def create_gunluk_yaz_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        self.diary_title_edit = QLineEdit(self)
        self.diary_title_edit.setPlaceholderText("Günlüğüne bir başlık ver...")
        form_layout.addRow(QLabel("Başlık:"), self.diary_title_edit)

        self.diary_text_area = QTextEdit(self)
        self.diary_text_area.setPlaceholderText("Bugün neler oldu, neler hissettin? Özgürce yaz...")
        self.diary_text_area.setMinimumHeight(250)
        form_layout.addRow(QLabel("İçerik:"), self.diary_text_area)

        mood_widget = QWidget()
        mood_h_layout = QHBoxLayout(mood_widget)
        mood_h_layout.setContentsMargins(0,0,0,0)

        mood_label = QLabel("Ruh Hali:")
        self.mood_combobox = QComboBox(self)
        self.mood_combobox.addItems(["Harika! ✨", "Mutlu 😊", "Normal 😐", "Biraz Üzgün 😟", "Kötü 😔", "Karışık 🤯", "Belirtmek İstemiyorum"])
        mood_h_layout.addWidget(mood_label)
        mood_h_layout.addWidget(self.mood_combobox, 1)

        self.important_checkbox = QCheckBox("Önemli", self)
        self.important_checkbox.setIcon(get_icon("important_star"))
        mood_h_layout.addWidget(self.important_checkbox)
        mood_h_layout.addStretch(0)
        form_layout.addRow(mood_widget)

        layout.addLayout(form_layout)

        self.save_diary_button = QPushButton(get_icon("save", QStyle.SP_DialogSaveButton), " Günlüğü Kaydet", self)
        self.save_diary_button.setFixedHeight(40)
        self.save_diary_button.setIconSize(QSize(18,18))
        self.save_diary_button.clicked.connect(self.save_diary_entry)
        
        button_container = QWidget()
        button_h_layout = QHBoxLayout(button_container)
        button_h_layout.addStretch()
        button_h_layout.addWidget(self.save_diary_button)
        button_h_layout.addStretch()
        layout.addWidget(button_container)
        layout.addStretch()

    def save_diary_entry(self):
        title = self.diary_title_edit.text()
        content = self.diary_text_area.toPlainText()
        mood = self.mood_combobox.currentText()
        is_important = self.important_checkbox.isChecked()

        if not content.strip():
            QMessageBox.warning(self, "Eksik Bilgi", "Günlük içeriği boş olamaz.")
            return

        add_diary_entry(self.user_id, title, content, mood, is_important)
        QMessageBox.information(self, "Kaydedildi", "Günlüğün başarıyla kaydedildi.")
        self.diary_title_edit.clear()
        self.diary_text_area.clear()
        self.mood_combobox.setCurrentIndex(0)
        self.important_checkbox.setChecked(False)
        if self.tabs.currentWidget() == self.tab_gunluklerim:
            self.load_diary_entries()

    def create_gunluklerim_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15,15,15,15)
        self.diary_table = QTableWidget(self)
        self.diary_table.setAlternatingRowColors(True)
        self.diary_table.setColumnCount(6)
        self.diary_table.setHorizontalHeaderLabels(["ID", "Tarih", "Başlık", "Ruh Hali", "Önemli", "Önizleme"])
        self.diary_table.setColumnHidden(0, True)
        self.diary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.diary_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.diary_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.diary_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.diary_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.diary_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.diary_table.setSelectionMode(QTableWidget.SingleSelection)
        self.diary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.diary_table.doubleClicked.connect(self.view_diary_entry_detail)
        layout.addWidget(self.diary_table)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        view_button = QPushButton(get_icon("view", QStyle.SP_FileIcon), " Seçili Günlüğü Görüntüle", self)
        view_button.setIconSize(QSize(16,16))
        view_button.clicked.connect(self.view_diary_entry_detail)
        buttons_layout.addWidget(view_button)

        delete_button = QPushButton(get_icon("delete", QStyle.SP_TrashIcon), " Seçili Günlüğü Sil", self)
        delete_button.setIconSize(QSize(16,16))
        delete_button.clicked.connect(self.delete_selected_diary_entry)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

    def load_diary_entries(self):
        self.diary_table.setRowCount(0)
        entries = get_diary_entries(self.user_id)
        for row_num, entry_data in enumerate(entries):
            self.diary_table.insertRow(row_num)
            self.diary_table.setItem(row_num, 0, QTableWidgetItem(str(entry_data[0])))
            try:
                dt_obj = datetime.datetime.strptime(entry_data[1], "%Y-%m-%d %H:%M:%S")
                formatted_date = dt_obj.strftime("%d.%m.%Y %H:%M")
            except ValueError:
                formatted_date = entry_data[1]
            self.diary_table.setItem(row_num, 1, QTableWidgetItem(formatted_date))
            self.diary_table.setItem(row_num, 2, QTableWidgetItem(entry_data[2] if entry_data[2] else ""))
            self.diary_table.setItem(row_num, 3, QTableWidgetItem(entry_data[3] if entry_data[3] else ""))
            
            important_item = QTableWidgetItem()
            if entry_data[4]:
                important_item.setIcon(get_icon("important_star"))
                important_item.setText(" Evet")
            else:
                important_item.setText("Hayır")
            important_item.setTextAlignment(Qt.AlignCenter)
            self.diary_table.setItem(row_num, 4, important_item)
            
            preview_text = (entry_data[5] if entry_data[5] else "")
            if len(preview_text) == 50:
                preview_text += "..."
            self.diary_table.setItem(row_num, 5, QTableWidgetItem(preview_text))

        self.diary_table.resizeColumnsToContents()
        self.diary_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.diary_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

    def view_diary_entry_detail(self):
        selected_rows = self.diary_table.selectionModel().selectedRows()
        current_row = self.diary_table.currentRow()

        if not selected_rows and current_row < 0 :
            QMessageBox.warning(self, "Seçim Yok", "Lütfen görüntülemek için bir günlük seçin.")
            return
        
        actual_row_index = selected_rows[0].row() if selected_rows else current_row

        entry_id_item = self.diary_table.item(actual_row_index, 0)
        if not entry_id_item:
            QMessageBox.critical(self, "Hata", "Günlük ID'si alınamadı.")
            return
        entry_id = int(entry_id_item.text())
        entry = get_diary_entry_by_id(entry_id)

        if entry:
            dialog = QDialog(self)
            dialog.setWindowIcon(get_icon("view", QStyle.SP_FileIcon))
            dialog_title_text = entry[0] if entry[0] else "Başlıksız Günlük"
            dialog.setWindowTitle(f"Günlük Detayı: {dialog_title_text}")
            dialog.setMinimumSize(550,450)
            dialog.setStyleSheet(self.styleSheet())

            layout = QVBoxLayout(dialog)
            layout.setSpacing(10)

            title_label = QLabel(f"<b>Başlık:</b> {dialog_title_text}")
            title_label.setWordWrap(True)
            layout.addWidget(title_label)

            content_area = QTextEdit()
            content_area.setPlainText(entry[1])
            content_area.setReadOnly(True)
            layout.addWidget(content_area)

            info_layout = QHBoxLayout()
            mood_label = QLabel(f"<b>Ruh Hali:</b> {entry[2]}")
            info_layout.addWidget(mood_label)
            important_label = QLabel(f"<b>Önemli:</b> {'Evet ✅' if entry[3] else 'Hayır ❌'}")
            info_layout.addWidget(important_label)
            layout.addLayout(info_layout)

            close_button = QPushButton(get_icon("exit", QStyle.SP_DialogCloseButton), " Kapat")
            button_bar_layout = QHBoxLayout()
            button_bar_layout.addStretch()
            button_bar_layout.addWidget(close_button)
            layout.addLayout(button_bar_layout)

            close_button.clicked.connect(dialog.accept)
            dialog.exec_()

    def delete_selected_diary_entry(self):
        selected_rows = self.diary_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Seçim Yok", "Lütfen silmek için bir günlük seçin.")
            return

        reply = QMessageBox.question(self, "Silme Onayı", "Bu günlüğü kalıcı olarak silmek istediğinizden emin misiniz?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            entry_id = int(self.diary_table.item(selected_rows[0].row(), 0).text())
            delete_diary_entry(entry_id)
            self.load_diary_entries()
            QMessageBox.information(self, "Silindi", "Günlük başarıyla silindi.")

    def create_saglik_tab(self, tab):
        main_layout = QHBoxLayout(tab)
        main_layout.setContentsMargins(15,15,15,15)
        main_layout.setSpacing(15)

        calendar_group = QGroupBox("Tarih Seçimi", self)
        calendar_layout = QVBoxLayout(calendar_group)
        self.health_calendar = QCalendarWidget(self)
        self.health_calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.health_calendar.clicked[QDate].connect(self.load_health_data_for_date)
        calendar_layout.addWidget(self.health_calendar)
        main_layout.addWidget(calendar_group, 1)

        data_entry_group = QGroupBox("Günlük Sağlık Verileri", self)
        data_layout = QVBoxLayout(data_entry_group)
        data_layout.setSpacing(10)

        self.health_toolbox = QToolBox()

        daily_log_page = QWidget()
        daily_log_form = QFormLayout(daily_log_page)
        daily_log_form.setSpacing(12)

        self.water_spinbox = QSpinBox(self)
        self.water_spinbox.setRange(0, 10000); self.water_spinbox.setSuffix(" ml"); self.water_spinbox.setSingleStep(250)
        daily_log_form.addRow(QLabel("💧 Su Tüketimi:"), self.water_spinbox)

        self.exercise_spinbox = QDoubleSpinBox(self)
        self.exercise_spinbox.setRange(0, 100); self.exercise_spinbox.setSuffix(" km"); self.exercise_spinbox.setSingleStep(0.5)
        daily_log_form.addRow(QLabel("🏃 Egzersiz:"), self.exercise_spinbox)

        self.sleep_spinbox = QDoubleSpinBox(self)
        self.sleep_spinbox.setRange(0, 24); self.sleep_spinbox.setSuffix(" saat"); self.sleep_spinbox.setSingleStep(0.5)
        daily_log_form.addRow(QLabel("😴 Uyku Süresi:"), self.sleep_spinbox)

        self.save_health_button = QPushButton(get_icon("health_save", QStyle.SP_DialogSaveButton), " Sağlık Verilerini Kaydet", self)
        self.save_health_button.setFixedHeight(35)
        self.save_health_button.setIconSize(QSize(16,16))
        self.save_health_button.clicked.connect(self.save_health_data)
        daily_log_form.addRow(self.save_health_button)
        self.health_toolbox.addItem(daily_log_page, get_icon("new_entry"),"Günlük Kayıt")

        goals_page = QWidget()
        goals_layout = QFormLayout(goals_page)
        goals_layout.setSpacing(12)

        self.water_goal_slider = QSlider(Qt.Horizontal)
        self.water_goal_slider.setRange(1000, 5000); self.water_goal_slider.setSingleStep(250); self.water_goal_slider.setValue(2500)
        self.water_goal_label = QLabel(f"Günlük Su Hedefi: {self.water_goal_slider.value()} ml")
        self.water_goal_slider.valueChanged.connect(lambda val: self.water_goal_label.setText(f"Günlük Su Hedefi: {val} ml"))
        self.water_goal_slider.valueChanged.connect(self.update_health_progress)
        goals_layout.addRow(self.water_goal_label, self.water_goal_slider)

        self.water_progress = QProgressBar(self)
        self.water_progress.setTextVisible(True)
        goals_layout.addRow(QLabel("Su İlerlemesi:"), self.water_progress)
        self.health_toolbox.addItem(goals_page, get_icon("important_star"),"Hedefler ve İlerleme")

        data_layout.addWidget(self.health_toolbox)
        main_layout.addWidget(data_entry_group, 2)

        self.health_calendar.setSelectedDate(QDate.currentDate())
        self.load_health_data_for_date(QDate.currentDate())

    def load_health_data_for_date(self, q_date):
        date_str = q_date.toString("yyyy-MM-dd")
        water, exercise, sleep = get_health_log(self.user_id, date_str)
        self.water_spinbox.setValue(water)
        self.exercise_spinbox.setValue(exercise)
        self.sleep_spinbox.setValue(sleep)
        self.update_health_progress()

    def save_health_data(self):
        selected_date = self.health_calendar.selectedDate().toString("yyyy-MM-dd")
        water = self.water_spinbox.value()
        exercise = self.exercise_spinbox.value()
        sleep = self.sleep_spinbox.value()
        update_health_log(self.user_id, selected_date, water, exercise, sleep)
        QMessageBox.information(self, "Kaydedildi", f"{selected_date} için sağlık verileri kaydedildi.")
        self.update_health_progress()

    def update_health_progress(self):
        current_water = self.water_spinbox.value()
        water_goal = self.water_goal_slider.value()
        if water_goal > 0:
            progress_percent = min(100, int((current_water / water_goal) * 100))
            self.water_progress.setValue(progress_percent)
            self.water_progress.setFormat(f"%p ({current_water}/{water_goal} ml)")
        else:
            self.water_progress.setValue(0)
            self.water_progress.setFormat("Hedef Belirlenmedi")

    def create_hava_durumu_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(15)

        input_layout = QHBoxLayout()
        self.city_input = QLineEdit(self)
        default_city = get_user_preference(self.user_id, "city") or "Istanbul"
        self.city_input.setText(default_city)
        self.city_input.setPlaceholderText("Şehir adı girin (örn: London, TR)...")
        input_layout.addWidget(self.city_input, 1)

        fetch_button = QPushButton(get_icon("fetch_weather"), " Hava Durumunu Getir", self)
        fetch_button.setIconSize(QSize(16,16))
        fetch_button.clicked.connect(self.fetch_weather_manually)
        input_layout.addWidget(fetch_button)
        layout.addLayout(input_layout)

        self.weather_info_group = QGroupBox("Hava Durumu Bilgileri", self)
        weather_layout = QGridLayout(self.weather_info_group)
        weather_layout.setSpacing(10)

        self.weather_icon_label = QLabel(self)
        self.weather_icon_label.setFixedSize(100,100)
        self.weather_icon_label.setAlignment(Qt.AlignCenter)
        self.weather_icon_label.setStyleSheet("border: 1px solid lightgray; border-radius: 50px; background-color: rgba(255,255,255,0.3);")
        weather_layout.addWidget(self.weather_icon_label, 0, 0, 3, 1, Qt.AlignCenter)

        self.temp_label = QLabel("Sıcaklık: -", self)
        self.temp_label.setFont(QFont("Arial", 18, QFont.Bold))
        weather_layout.addWidget(self.temp_label, 0, 1)

        self.feels_like_label = QLabel("Hissedilen: -", self)
        self.feels_like_label.setFont(QFont("Arial", 11))
        weather_layout.addWidget(self.feels_like_label, 1, 1)

        self.condition_label = QLabel("Durum: -", self)
        self.condition_label.setFont(QFont("Arial", 11))
        self.condition_label.setWordWrap(True)
        weather_layout.addWidget(self.condition_label, 2, 1)

        self.humidity_label = QLabel("Nem: -", self)
        self.humidity_label.setFont(QFont("Arial", 11))
        weather_layout.addWidget(self.humidity_label, 0, 2)

        self.wind_label = QLabel("Rüzgar: -", self)
        self.wind_label.setFont(QFont("Arial", 11))
        weather_layout.addWidget(self.wind_label, 1, 2)
        
        self.city_name_label = QLabel("Şehir: -", self)
        self.city_name_label.setFont(QFont("Arial", 12, QFont.Bold))
        weather_layout.addWidget(self.city_name_label, 2, 2)
        
        weather_layout.setColumnStretch(1,1)
        weather_layout.setColumnStretch(2,1)
        self.weather_info_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.weather_info_group)

        self.clothing_suggestion_group = QGroupBox("Giyim Önerisi", self)
        suggestion_layout = QVBoxLayout(self.clothing_suggestion_group)
        self.suggestion_label = QLabel("Hava durumu bilgisi bekleniyor...", self)
        self.suggestion_label.setFont(QFont("Arial", 11, QFont.StyleItalic))
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setAlignment(Qt.AlignCenter)
        suggestion_layout.addWidget(self.suggestion_label)
        layout.addWidget(self.clothing_suggestion_group)
        

        self.last_fetch_label = QLabel("Son Güncelleme: Henüz Yok", self)
        self.last_fetch_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.last_fetch_label.setStyleSheet("font-size: 9pt; color: gray;")
        layout.addWidget(self.last_fetch_label)
        layout.addStretch()

    def auto_fetch_weather(self):
        city = get_user_preference(self.user_id, "city") or "Istanbul"
        if hasattr(self, 'city_input') and self.tabs.currentWidget() == self.tab_hava_durumu:
            input_city = self.city_input.text().strip()
            if input_city:
                city = input_city
        if city:
            self.get_weather(city)

    def fetch_weather_manually(self):
        city = self.city_input.text().strip()
        if not city:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir şehir adı girin.")
            return
        self.get_weather(city)

    def get_weather(self, city_name):
        global WEATHER_API_KEY
        
        user_specific_api_key = get_user_preference(self.user_id, "api_key")

        if not user_specific_api_key and (not WEATHER_API_KEY or WEATHER_API_KEY == "YOUR_OPENWEATHERMAP_API_KEY"):
            instructions_text = (
                "OpenWeatherMap API Anahtarı Nasıl Alınır?\n\n"
                "1. Web Sitesi: Tarayıcınızdan https://openweathermap.org/ adresine gidin.\n"
                "2. Kayıt Olun (Sign Up): Sağ üst köşedeki \"Sign Up\" linkinden ücretsiz bir hesap oluşturun.\n"
                "3. Giriş Yapın (Sign In): Hesabınızla giriş yapın.\n"
                "4. API Keys Bölümü: Giriş yaptıktan sonra, kullanıcı adınıza tıklayarak açılan menüden \"My API keys\" sekmesine gidin.\n"
                "5. API Anahtarı Oluşturun/Görüntüleyin: Genellikle \"default\" (varsayılan) bir API anahtarı zaten üretilmiş olur. "
                "Yoksa, \"Create key\" butonu ile yeni bir anahtar oluşturun (bir isim vermeniz istenebilir, örn: \"KisiselAsistanimAnahtari\").\n"
                "6. Anahtarı Kopyalayın: API anahtarınız, genellikle uzun bir harf ve rakam dizisidir. Bu anahtarı tamamen kopyalayın.\n\n"
                "Lütfen edindiğiniz OpenWeatherMap API anahtarınızı aşağıdaki alana girin.\n\n"
                "Eğer hemen kayıt olmakla uğraşmak istemiyorsanız, geçici olarak aşağıdaki örnek anahtarı kullanabilirsiniz:\n"
                "7278da4b07af6e74ba7456cb79b95585\n"
                "(Not: Bu örnek anahtarın gelecekte de çalışacağı garanti edilmez ve kendi ücretsiz anahtarınızı almanız önemle tavsiye edilir.)"
            )
            
            formatted_instructions_text = instructions_text.replace('\n', '<br>')
            instructions_html = f"<p style='color:white;'>{formatted_instructions_text}</p>"
            
            suggested_key_for_dialog = user_specific_api_key if user_specific_api_key else "7278da4b07af6e74ba7456cb79b95585"

            new_key, ok = QInputDialog.getText(self, "OpenWeatherMap API Anahtarı Gerekli",
                                               instructions_html,
                                               QLineEdit.Normal, suggested_key_for_dialog)
            if ok and new_key.strip():
                WEATHER_API_KEY = new_key.strip()
                save_user_preference(self.user_id, "api_key", WEATHER_API_KEY)
                QMessageBox.information(self, "API Anahtarı Kaydedildi", "API anahtarınız bu kullanıcı için kaydedildi ve kullanılacak.")
            elif ok and not new_key.strip():
                WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
                save_user_preference(self.user_id, "api_key", None)
                QMessageBox.warning(self, "API Anahtarı Temizlendi", "API anahtarı alanı boş bırakıldığı için kaydedilmiş anahtar temizlendi. Hava durumu bilgisi alınamayacak.")
                self._reset_weather_labels_on_error(api_key_cleared=True)
                return
            else:
                self._reset_weather_labels_on_error(api_key_missing=True)
                QMessageBox.warning(self, "API Anahtarı Girilmedi", "API anahtarı girilmediği için hava durumu bilgisi alınamıyor.")
                return
        elif user_specific_api_key and WEATHER_API_KEY != user_specific_api_key:
            WEATHER_API_KEY = user_specific_api_key
        elif not WEATHER_API_KEY or WEATHER_API_KEY == "YOUR_OPENWEATHERMAP_API_KEY":
            QMessageBox.critical(self, "API Anahtarı Sorunu", "API anahtarı bulunamadı. Lütfen Ayarlar menüsünden API anahtarınızı girin.")
            self._reset_weather_labels_on_error(api_key_missing=True)
            return


        params = {"q": city_name, "appid": WEATHER_API_KEY, "units": "metric", "lang": "tr"}
        try:
            response = requests.get(WEATHER_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            self.city_name_label.setText(f"Şehir: {data['name']}, {data['sys']['country']}")
            self.temp_label.setText(f"Sıcaklık: {data['main']['temp']:.1f}°C")
            self.feels_like_label.setText(f"Hissedilen: {data['main']['feels_like']:.1f}°C")
            self.condition_label.setText(f"Durum: {data['weather'][0]['description'].capitalize()}")
            self.humidity_label.setText(f"Nem: %{data['main']['humidity']}")
            self.wind_label.setText(f"Rüzgar: {data['wind']['speed']:.1f} m/s")
            self.last_fetch_label.setText(f"Son Güncelleme: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            
            icon_code = data['weather'][0]['icon']
            icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
            try:
                icon_data_response = requests.get(icon_url, timeout=5)
                icon_data_response.raise_for_status()
                icon_data = icon_data_response.content
                pixmap = QPixmap()
                if pixmap.loadFromData(icon_data):
                    self.weather_icon_label.setPixmap(pixmap.scaled(self.weather_icon_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.weather_icon_label.setText("İkon Yüklenemedi")
            except requests.exceptions.RequestException as icon_err:
                self.weather_icon_label.setText("İkon Alınamadı")
            
            self.generate_clothing_suggestion(data['main']['temp'], data['weather'][0]['main'], data['wind']['speed'])

        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 401:
                QMessageBox.critical(self, "API Hatası", "API Anahtarı geçersiz veya hatalı. Lütfen Ayarlar menüsünden veya bir sonraki denemede geçerli bir anahtar girin.")
                self._reset_weather_labels_on_error(api_key_invalid=True)
            elif http_err.response.status_code == 404:
                QMessageBox.warning(self, "Bulunamadı", f"Şehir '{city_name}' bulunamadı. Lütfen şehir adını kontrol edin.")
                self._reset_weather_labels_on_error()
            else:
                QMessageBox.critical(self, "HTTP Hatası", f"Hava durumu alınırken bir HTTP hatası oluştu: {http_err}")
                self._reset_weather_labels_on_error()
        except requests.exceptions.RequestException as e:
            self._reset_weather_labels_on_error(connection_error=True)
            QMessageBox.warning(self, "Bağlantı Sorunu", f"Hava durumu bilgisi alınamadı. İnternet bağlantınızı kontrol edin veya API sunucusunda bir sorun olabilir.\nDetay: {e}")
        except Exception as e:
            detailed_traceback = traceback.format_exc()
            QMessageBox.critical(self, "Beklenmedik Hata", f"Hava durumu işlenirken bir hata oluştu: {e}")
            self._reset_weather_labels_on_error()


    def _reset_weather_labels_on_error(self, connection_error=False, api_key_missing=False, api_key_invalid=False, api_key_cleared=False):
        if api_key_missing or api_key_cleared:
            self.temp_label.setText("Sıcaklık: API Anahtarı Eksik")
            self.suggestion_label.setText("API anahtarı olmadan hava durumu alınamıyor.")
            self.weather_icon_label.setText("🔑")
        elif api_key_invalid:
            self.temp_label.setText("Sıcaklık: API Anahtarı Geçersiz")
            self.suggestion_label.setText("Lütfen geçerli bir API anahtarı girin.")
            self.weather_icon_label.setText("🚫")
        elif connection_error:
            self.temp_label.setText("Sıcaklık: Bağlantı Hatası")
            self.suggestion_label.setText("Hava durumu sunucusuna bağlanılamadı.")
            self.weather_icon_label.setText("🔌")
        else:
            self.temp_label.setText("Sıcaklık: Hata")
            self.suggestion_label.setText("Hava durumu bilgisi alınamadı.")
            self.weather_icon_label.setText("⚠")

        self.feels_like_label.setText("Hissedilen: -")
        self.condition_label.setText("Durum: -")
        self.humidity_label.setText("Nem: -")
        self.wind_label.setText("Rüzgar: -")
        self.city_name_label.setText("Şehir: -")
        self.last_fetch_label.setText(f"Son Güncelleme: Başarısız")
        if not api_key_missing and not api_key_invalid and not api_key_cleared : self.weather_icon_label.clear()


    def generate_clothing_suggestion(self, temp, condition_main, wind_speed):
        suggestion = ""
        if temp > 28:
            suggestion = "Çok sıcak! ☀ İnce ve açık renkli kıyafetler, şort, tişört, sandalet. Bol su için ve güneşten korunun."
        elif temp > 20:
            suggestion = "Sıcak ve güzel bir hava. Tişört, ince pantolon/etek. Akşam için ince bir hırka gerekebilir."
        elif temp > 15:
            suggestion = "Ilık bir hava. Uzun kollu tişört, gömlek veya ince bir kazak. Kot pantolon veya benzeri."
        elif temp > 10:
            suggestion = "Serin. Kazak veya sweatshirt, hafif bir ceket veya mont. 🧥"
        elif temp > 5:
            suggestion = "Soğuk. Kalın kazak, mont, atkı ve bere düşünebilirsiniz. 🧣"
        else:
            suggestion = "Çok soğuk! 🥶 Kat kat giyinin. Kalın mont, termal içlik, atkı, bere ve eldiven şart."

        if "Rain" in condition_main or "Drizzle" in condition_main:
            suggestion += " Yağmurluk veya şemsiye almayı unutmayın. ☔"
        elif "Snow" in condition_main:
            suggestion += " Kar montu, su geçirmez botlar ve eldivenler iyi olur. 🧤❄"
        elif "Clear" in condition_main and temp > 15:
            suggestion += " Güneşli bir gün, güneş gözlüğü iyi bir fikir. 😎"
        
        if wind_speed > 7:
            suggestion += f" Rüzgarlı ({wind_speed:.1f} m/s)! Rüzgar kesen bir giysi faydalı olacaktır. 🌬"
        elif "Wind" in condition_main and temp < 15 :
            suggestion += " Hafif rüzgarlı olabilir."
            
        self.suggestion_label.setText(suggestion if suggestion else "Hava durumuna göre giyinin.")


def main():
    app = QApplication(sys.argv)
    app.setProperty("restart", False)

    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted and login_dialog.user_data:
        user_data = login_dialog.user_data
        try:
            window = App(user_data)
            window.show()
            exit_code = app.exec_()

            if app.property("restart"):
                main()
            else:
                sys.exit(exit_code)
        except Exception as e:
            detailed_traceback = traceback.format_exc()

            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setText("Uygulama başlatılırken kritik bir hata oluştu!")
            error_dialog.setInformativeText(str(e))
            error_dialog.setWindowTitle("Kritik Hata")
            error_dialog.setDetailedText(detailed_traceback)
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.exec_()
            sys.exit(1)
    else:
        sys.exit()

if __name__ == "__main__":
    main()