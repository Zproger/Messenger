import os
import sys
import time
import json
import socket
from loguru import logger
from PyQt5 import QtCore, QtGui, QtWidgets
from des import *

from methods.SettingsPanel import *
from methods.ConnectThreadMonitor import *


# Настраиваем глобальный логгер для вывода в stdout
# ============================================================================================================
logger.remove()
logger.add(
    sink=sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> - <cyan>{name}:{function}:{line}</cyan> - <blue>{message}</blue>",
    level="DEBUG"
)

# Конфигурация логгера, который работает с журналом
logger.add(
    sink=os.path.join("logs", "client_log.txt"),
    format="{time:HH:mm:ss} - {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="100 MB",
    compression="zip",
    enqueue=True # Делаем логгер потокобезопасным
)
# ============================================================================================================


# Интерфейс программы и обработчик событий внутри него
class Client(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Данные из конфига (симметричный ключ получаем в ответе от сервера)
        self.nick = None
        self.ip = None
        self.port = None
        self.smile_type = None
        self.connect_status = False

        # Экземпляр класса для обработки соединений и сигналов
        self.connect_monitor = message_monitor()
        self.connect_monitor.mysignal.connect(self.signal_handler)

        # Отключаем стандартные границы окна программы
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.center()

        # Блокируем кнопку "Выйти из чата"
        self.btn_locker(self.ui.pushButton_19, True)

        # Обработчики основных кнопок + кнопок с панели
        self.ui.pushButton.clicked.connect(self.send_message)
        self.ui.lineEdit.returnPressed.connect(self.send_message)
        self.ui.pushButton_2.clicked.connect(self.connect_to_server)
        self.ui.pushButton_3.clicked.connect(lambda: self.close())
        self.ui.pushButton_4.clicked.connect(lambda: self.ui.listWidget.clear())
        self.ui.pushButton_5.clicked.connect(lambda: self.showMinimized())
        self.ui.pushButton_7.clicked.connect(self.setting_panel)
        self.ui.pushButton_19.clicked.connect(self.server_disconnect)

        # Обработчик смайликов
        self.ui.pushButton_10.clicked.connect(lambda: self.smile_send('1'))
        self.ui.pushButton_11.clicked.connect(lambda: self.smile_send('2'))
        self.ui.pushButton_12.clicked.connect(lambda: self.smile_send('3'))
        self.ui.pushButton_6.clicked.connect(lambda: self.smile_send('4'))
        self.ui.pushButton_8.clicked.connect(lambda: self.smile_send('5'))
        self.ui.pushButton_9.clicked.connect(lambda: self.smile_send('6'))
        self.ui.pushButton_13.clicked.connect(lambda: self.smile_send('7'))
        self.ui.pushButton_17.clicked.connect(lambda: self.smile_send('8'))
        self.ui.pushButton_16.clicked.connect(lambda: self.smile_send('9'))
        self.ui.pushButton_14.clicked.connect(lambda: self.smile_send('10'))
        self.ui.pushButton_15.clicked.connect(lambda: self.smile_send('11'))
        self.ui.pushButton_18.clicked.connect(lambda: self.smile_send('12'))
        self.ui.pushButton_21.clicked.connect(lambda: self.smile_send('13'))
        self.ui.pushButton_22.clicked.connect(lambda: self.smile_send('14'))
        self.ui.pushButton_24.clicked.connect(lambda: self.smile_send('15'))


    # Перетаскивание безрамочного окна
    # ==================================================================
    def center(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        try:
            delta = QtCore.QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()
        except AttributeError:
            pass
    # ==================================================================


    # Отправить смайлик
    def smile_send(self, smile_number: str):
        btn_base = {'1': self.ui.pushButton_10,
                    '2': self.ui.pushButton_11,
                    '3': self.ui.pushButton_12,
                    '4': self.ui.pushButton_6,
                    '5': self.ui.pushButton_8,
                    '6': self.ui.pushButton_9,
                    '7': self.ui.pushButton_13,
                    '8': self.ui.pushButton_17,
                    '9': self.ui.pushButton_16,
                    '10': self.ui.pushButton_14,
                    '11': self.ui.pushButton_15,
                    '12': self.ui.pushButton_18,
                    '13': self.ui.pushButton_21,
                    '14': self.ui.pushButton_22,
                    '15': self.ui.pushButton_24}

        change_style = """
        border-radius: 35px;
        border: 2px solid white;
        """

        default_style = """
        border: none;
        """

        if self.smile_type == None:
            btn_base[smile_number].setStyleSheet(change_style)
            self.smile_type = smile_number

        elif self.smile_type != None and self.smile_type != smile_number:
            btn_base[self.smile_type].setStyleSheet(default_style)
            btn_base[smile_number].setStyleSheet(change_style)
            self.smile_type = smile_number

        elif self.smile_type != None and self.smile_type == smile_number:
            btn_base[smile_number].setStyleSheet(default_style)
            self.smile_type = None

        logger.debug(f"SELF.SMILE_TYPE: {self.smile_type}")


    # Открыть окно для настройки клиента
    def setting_panel(self):
        setting_win = SettingPanel(self, self.connect_monitor.mysignal)
        setting_win.show()


    # Обновление конфигов клиента
    def update_config(self):
        """
        Используется для обновления значений на лету, без необходимости
        перезапускать клиент (В случае если пользователь отредактировал настройки
        либо же запустил софт и необходимо проинициализировать значения)
        """
        # Если конфиг уже был создан
        if os.path.exists(os.path.join("data", "config.json")):
            with open(os.path.join("data", "config.json")) as file:
                data = json.load(file)
                self.nick = data['nick']
                self.ip = data['server_ip']
                self.port = int(data['server_port'])


    # Обработчик сигналов из потока
    def signal_handler(self, value: list):
        # Обновление параметров конфига
        if value[0] == "update_config":
            self.update_config()

        # Обновление симметричного ключа
        elif value[0] == "SERVER_OK":
            self.connect_status = True
            item = QtWidgets.QListWidgetItem()
            item.setTextAlignment(QtCore.Qt.AlignHCenter)
            item.setText(f"SERVER: {value[1]}\n")
            self.ui.listWidget.addItem(item)
            logger.info(value)

            # Отправляем уведомление о том, что мы вступили в чат
            payload = ['USERS_NOTIFY', f"{self.nick} - Вступил в чат"]
            self.connect_monitor.send_encrypt(payload)

        # Если пользователь вступил или вышел из чата
        elif value[0] == "USERS_NOTIFY":
            item = QtWidgets.QListWidgetItem()
            item.setTextAlignment(QtCore.Qt.AlignHCenter)
            item.setText(f"SERVER: {value[1]}\n")
            self.ui.listWidget.addItem(item)
            logger.info(value)

        # Обработка сообщений других пользователей
        # ['ENCRYPT_MESSAGE', self.nick, avatar, message_text.encode()]
        elif value[0] == "ENCRYPT_MESSAGE":
            item = QtWidgets.QListWidgetItem()
            item.setTextAlignment(QtCore.Qt.AlignLeft)

            # Используем аватарку пользователя
            size = QtCore.QSize(45, 45)

            # Если отправили смайлик вместо аватарки
            if str(value[2]).isdecimal():
                icon = QtGui.QIcon(os.path.join("icons", f"smile{value[2]}.png"))

            # Если отправлена аватарка
            elif isinstance(value[2], bytes):
                pixmap_obj = QtGui.QPixmap()
                pixmap_obj.loadFromData(value[2])
                icon = QtGui.QIcon(pixmap_obj)

            # Если нет аватарки и не выбран смайлик
            else:
                icon = QtGui.QIcon(os.path.join("icons", "user.png"))

            # Задаем иконку в строку
            item.setIcon(icon)
            self.ui.listWidget.setIconSize(size)
            self.ui.listWidget.addItem(item)
            item.setText(f"{value[1]}:\n{value[-1]}")
            logger.info(value)

        elif value[0] == "CONNECTION_ERROR":
            message = "Сервер разорвал соединение\nповторите попытку через несколько минут"
            QtWidgets.QMessageBox.about(self, "Ошибка Соединения", message)
            self.btn_locker(self.ui.pushButton_2, False)
            self.btn_locker(self.ui.pushButton_7, False)
            self.btn_locker(self.ui.pushButton_19, True)
            self.connect_status = False
            logger.info(value)


    # Отправить сообщение на сервер
    def send_message(self):
        if self.connect_status:
            message_text = self.ui.lineEdit.text()
            profile_photo = None # Путь к фото пользователя

            # Если пользователь выбрал смайлик
            if self.smile_type:
                profile_photo = self.smile_type

            # Если не выбрал смайлик но есть аватарка
            elif os.path.exists(os.path.join("data", "custom.png")):
                with open(os.path.join("data", "custom.png"), "rb") as photo:
                    profile_photo = photo.read()

            # Если нет аватарки и нет смайлика
            else:
                profile_photo = None

            # Если поле с текстом не пустое - шифруем сообщение и передаем на сервер
            if len(message_text) > 0:
                payload = ['ENCRYPT_MESSAGE', self.nick, profile_photo, message_text.encode()]
                self.connect_monitor.send_encrypt(payload)

                # Добавляем свое сообщение в ListWidget
                item = QtWidgets.QListWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignLeft)
                size = QtCore.QSize(45, 45)

                # Прикрепляем к нему нашу аватарку
                if self.smile_type:
                    icon = QtGui.QIcon(os.path.join("icons", f"smile{self.smile_type}.png"))

                elif os.path.exists(os.path.join("data", "custom.png")):
                    icon = QtGui.QIcon(os.path.join("data", "custom.png"))

                else:
                    icon = QtGui.QIcon(os.path.join("icons", "user.png"))
                self.ui.listWidget.setIconSize(size)
                item.setIcon(icon)

                # Выводим свое сообщение в панель и удаляем с поля воода
                item.setText(f"{self.nick} (ВЫ):\n{message_text}")
                self.ui.listWidget.addItem(item)
                self.ui.lineEdit.clear()
        else:
            message = "Проверьте соединение с сервером"
            QtWidgets.QMessageBox.about(self, "Оповещение", message)


    # Покдлючаемся к общему серверу
    def connect_to_server(self):
        self.update_config()    # Обновляем данные пользователя

        if self.nick != None:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect((self.ip, self.port))

                # Запускаем мониторинг входящих сообщений
                self.connect_monitor.server_socket = self.client
                self.connect_monitor.start()

                # Блокируем кнопки и разблокируем кнопку "Выйти из чата"
                self.btn_locker(self.ui.pushButton_2, True)
                self.btn_locker(self.ui.pushButton_7, True)
                self.btn_locker(self.ui.pushButton_19, False)
            except Exception as err:
                message = "Ошибка соединения с сервером.\nПроверьте правильность ввода данных"
                QtWidgets.QMessageBox.about(self, "Оповещение", message)
        else:   # Если пользователь не заполнил данные
            message = "Для начала заполните данные во вкладке 'Настройки'"
            QtWidgets.QMessageBox.about(self, "Оповещение", message)


    # Отключиться от сервера
    def server_disconnect(self):
        payload = ['EXIT', f'{self.nick}']
        self.connect_monitor.send_encrypt(payload)
        self.client.close()
        self.ui.listWidget.clear()

        # Снимаем блокировку с основных кнопок и блокируем кнопку для отключения
        self.btn_locker(self.ui.pushButton_19, True)
        self.btn_locker(self.ui.pushButton_2, False)
        self.btn_locker(self.ui.pushButton_7, False)


    # Блокировщик кнопок
    def btn_locker(self, btn: object, lock_status: bool) -> None:
        default_style = """
        QPushButton{
            color: white;
            border-radius: 7px;
            background-color: #595F76;
        }
        QPushButton:hover{
            background-color: #50566E;
        }      
        QPushButton:pressed{
            background-color: #434965;
        }
        """

        lock_style = """
        color: #9EA2AB;
        border-radius: 7px;
        background-color: #2C313C;
        """

        if lock_status:
            btn.setDisabled(True)
            btn.setStyleSheet(lock_style)
        else:
            btn.setDisabled(False)
            btn.setStyleSheet(default_style)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myapp = Client()
    myapp.show()
    sys.exit(app.exec_())