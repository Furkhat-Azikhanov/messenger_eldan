import webbrowser
import random
import string
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy_garden.mapview import MapView, MapMarker
import sqlite3
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM
from plyer import gps
import platform
from kivy.uix.anchorlayout import AnchorLayout
from socket import socket, AF_INET, SOCK_STREAM


# Подключение к базе данных
conn = sqlite3.connect('messenger.db')
cursor = conn.cursor()

# Создание таблицы с проверкой, существует ли она уже
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE,
                    country TEXT,
                    city TEXT,
                    role TEXT,
                    language TEXT,
                    password TEXT,
                    latitude REAL,
                    longitude REAL
                    )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    receiver TEXT,
                    message TEXT
                    )''')

conn.commit()

# Экран для регистрации
class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super(RegisterScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')

        self.phone_input = TextInput(hint_text="Введите номер телефона", multiline=False)
        self.country_input = TextInput(hint_text="Введите страну", multiline=False)
        self.city_input = TextInput(hint_text="Введите город", multiline=False)
        
        self.role_spinner = Spinner(
            text="Выберите роль",
            values=["Работник", "Работодатель"],
            size_hint=(None, None),
            size=(200, 44)
        )

        self.language_spinner = Spinner(
            text="Выберите язык",
            values=["Английский", "Русский"],
            size_hint=(None, None),
            size=(200, 44)
        )

        self.password_input = TextInput(hint_text="Введите пароль", password=True, multiline=False)
        register_button = Button(text="Зарегистрироваться")
        register_button.bind(on_press=self.register_user)

        layout.add_widget(self.phone_input)
        layout.add_widget(self.country_input)
        layout.add_widget(self.city_input)
        layout.add_widget(self.role_spinner)
        layout.add_widget(self.language_spinner)
        layout.add_widget(self.password_input)
        layout.add_widget(register_button)

        self.add_widget(layout)

    def register_user(self, instance):
        phone = self.phone_input.text
        country = self.country_input.text
        city = self.city_input.text
        role = self.role_spinner.text
        language = self.language_spinner.text
        password = self.password_input.text

        def on_location(lat, lon):
            cursor.execute("INSERT INTO users (phone, country, city, role, language, password, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (phone, country, city, role, language, password, lat, lon))
            conn.commit()
            self.manager.current = 'login'

        if platform.system() == 'Darwin':
            lat, lon = 43.238949, 76.889709
            on_location(lat, lon)
        else:
            gps.configure(on_location=on_location)
            gps.start(minTime=1000, minDistance=0)

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        self.phone_input = TextInput(hint_text="Введите номер телефона", multiline=False)
        self.password_input = TextInput(hint_text="Введите пароль", password=True, multiline=False)
        login_button = Button(text="Войти")
        login_button.bind(on_press=self.login_user)
        layout.add_widget(self.phone_input)
        layout.add_widget(self.password_input)
        layout.add_widget(login_button)
        self.add_widget(layout)

    def login_user(self, instance):
        phone = self.phone_input.text
        password = self.password_input.text
        cursor.execute("SELECT * FROM users WHERE phone = ? AND password = ?", (phone, password))
        user = cursor.fetchone()
        if user:
            self.manager.get_screen('user_list').set_current_user(phone, user[4])
            self.manager.current = 'user_list'

class UserListScreen(Screen):
    def __init__(self, **kwargs):
        super(UserListScreen, self).__init__(**kwargs)
        self.current_user = None
        self.current_role = None

    def set_current_user(self, phone, role):
        self.current_user = phone
        self.current_role = role
        self.show_home()

    def show_home(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical')
        label = Label(text=f"Вы вошли как {self.current_user} ({self.current_role})")
        layout.add_widget(label)

        button_layout = BoxLayout(size_hint=(1, 0.2))

        home_button = Button(text="Home")
        button_layout.add_widget(home_button)

        chat_button = Button(text="Chat")
        chat_button.bind(on_press=self.go_to_chat)
        button_layout.add_widget(chat_button)

        map_button = Button(text="Map")
        map_button.bind(on_press=self.go_to_map)
        button_layout.add_widget(map_button)

        layout.add_widget(button_layout)
        self.add_widget(layout)

    def go_to_chat(self, instance):
        self.manager.get_screen('chat_list').set_current_user(self.current_user, self.current_role)
        self.manager.current = 'chat_list'

    def go_to_map(self, instance):
        self.manager.current = 'map'

class MapScreen(Screen):
    def __init__(self, **kwargs):
        super(MapScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        self.mapview = MapView(zoom=10, lat=43.238949, lon=76.889709)
        layout.add_widget(self.mapview)

        back_button = Button(text="Назад", size_hint=(1, 0.1))
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)

        self.add_widget(layout)

    def on_enter(self):
        self.add_markers()

    def add_markers(self):
        cursor.execute("SELECT phone, role, latitude, longitude FROM users WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        users = cursor.fetchall()

        for user in users:
            phone, role, latitude, longitude = user
            marker_image = "blue.png" if role == "Работник" else "red.png"
            marker = MapMarker(lat=latitude, lon=longitude, source=marker_image)
            self.mapview.add_widget(marker)

    def go_back(self, instance):
        self.manager.current = 'user_list'

class ChatListScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatListScreen, self).__init__(**kwargs)
        self.current_user = None
        self.current_role = None

    def set_current_user(self, phone, role):
        self.current_user = phone
        self.current_role = role
        self.update_user_list()

    def update_user_list(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical')
        users_label = Label(text="Выберите пользователя для чата")
        layout.add_widget(users_label)

        opposite_role = "Работодатель" if self.current_role == "Работник" else "Работник"

        cursor.execute("SELECT phone FROM users WHERE phone != ? AND role = ? AND phone IS NOT NULL AND phone != ''",
                       (self.current_user, opposite_role))
        users = cursor.fetchall()

        for user in users:
            if user[0]:
                user_button = Button(text=user[0])
                user_button.bind(on_press=lambda instance, u=user[0]: self.open_chat(u))
                layout.add_widget(user_button)

        back_button = Button(text="Назад", size_hint=(1, 0.2))
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)

        self.add_widget(layout)

    def open_chat(self, user):
        self.manager.get_screen('messenger').set_receiver(user, self.current_user)
        self.manager.current = 'messenger'

    def go_back(self, instance):
        self.manager.current = 'user_list'

class MessengerScreen(Screen):
    def __init__(self, **kwargs):
        super(MessengerScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')

        self.scroll = ScrollView(size_hint=(1, 0.7))
        self.message_list = BoxLayout(orientation='vertical', size_hint_y=None)
        self.message_list.bind(minimum_height=self.message_list.setter('height'))
        self.scroll.add_widget(self.message_list)
        layout.add_widget(self.scroll)

        self.input_box = BoxLayout(size_hint=(1, 0.1))
        self.message_input = TextInput(hint_text="Введите сообщение", multiline=False)
        self.send_button = Button(text="Отправить", size_hint=(0.2, 1))
        self.send_button.bind(on_press=self.send_message)
        self.input_box.add_widget(self.message_input)
        self.input_box.add_widget(self.send_button)
        layout.add_widget(self.input_box)

        video_call_button = Button(text="Видеозвонок", size_hint=(1, 0.1))
        video_call_button.bind(on_press=self.start_video_call)
        layout.add_widget(video_call_button)

        back_button = Button(text="Назад", size_hint=(1, 0.1))
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)

        self.add_widget(layout)

        # Добавляем инициализацию сокета
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect(('localhost', 33001))  # Замените на нужные хост и порт
        self.BUFSIZ = 1024
        self.receiver = None
        self.sender = None

    def set_receiver(self, receiver, sender):
        """Сохраняет информацию о текущем пользователе и получателе."""
        self.receiver = receiver
        self.sender = sender
        self.update_chat()

    def update_chat(self):
        """Обновляет экран чата, загружая сообщения между sender и receiver."""
        self.message_list.clear_widgets()
        cursor.execute("SELECT sender, message FROM messages WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)",
                       (self.sender, self.receiver, self.receiver, self.sender))
        messages = cursor.fetchall()
        for message in messages:
            if "https://meet.jit.si/" in message[1]:
                anchor = AnchorLayout(size_hint_y=None, height=40)
                link_button = Button(text=f"{message[0]} отправил ссылку для звонка", size_hint=(None, None), height=30)
                link_button.bind(on_press=lambda instance, link=message[1]: webbrowser.open(link))
                anchor.add_widget(link_button)
                self.message_list.add_widget(anchor)
            else:
                message_label = Label(text=f"{message[0]}: {message[1]}", size_hint_y=None, height=30)
                self.message_list.add_widget(message_label)

    def send_message(self, instance):
        message = self.message_input.text
        if message and self.receiver:
            cursor.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)",
                           (self.sender, self.receiver, message))
            conn.commit()
            self.update_chat()
            self.message_input.text = ""
            # Отправляем сообщение серверу
            self.client_socket.send(bytes(f"{self.sender}:{message}", "utf8"))

    def start_video_call(self, instance):
        unique_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        meet_link = f"https://meet.jit.si/{unique_id}"
        
        if self.receiver and self.sender:
            cursor.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)",
                           (self.sender, self.receiver, meet_link))
            conn.commit()
            self.update_chat()

        webbrowser.open(meet_link)
        print("Ссылка на звонок:", meet_link)

    def go_back(self, instance):
        self.manager.current = 'chat_list'


class StartScreen(Screen):
    def __init__(self, **kwargs):
        super(StartScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        register_button = Button(text="Зарегистрироваться")
        register_button.bind(on_press=self.go_to_register)
        login_button = Button(text="Войти")
        login_button.bind(on_press=self.go_to_login)
        layout.add_widget(register_button)
        layout.add_widget(login_button)
        self.add_widget(layout)

    def go_to_register(self, instance):
        self.manager.current = 'register'

    def go_to_login(self, instance):
        self.manager.current = 'login'

class MessengerApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(StartScreen(name='start'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(UserListScreen(name='user_list'))
        sm.add_widget(ChatListScreen(name='chat_list'))
        sm.add_widget(MessengerScreen(name='messenger'))
        sm.add_widget(MapScreen(name='map'))
        sm.current = 'start'
        return sm

    def on_stop(self):
        conn.close()

if __name__ == '__main__':
    MessengerApp().run()
