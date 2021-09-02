import os
import re
import json
import shutil
from PyQt5 import QtCore, QtGui, QtWidgets
from methods.windows.settings import *


# Окно с настройками клиента
class SettingPanel(QtWidgets.QWidget):
    def __init__(self, parent=None, signal=None):
        super().__init__(parent, QtCore.Qt.Window)
        self.setting = Ui_Form()
        self.setting.setupUi(self)
        self.setWindowModality(2)

        # Сигнал для возврата в интерфейс
        self.signal = signal

        # Отключаем стандартные границы окна программы
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.center()

        # Растягиваем таблицу на всю ширину окна и скрываем нумерацию
        header = self.setting.tableWidget.horizontalHeader()
        for position in range(3):
            header.setSectionResizeMode(position, QtWidgets.QHeaderView.Stretch)
        self.setting.tableWidget.verticalHeader().setVisible(False)

        # Инициализируем все параметры окна
        self.init_data()

        # Обработчики кнопок
        self.setting.pushButton_7.clicked.connect(lambda: self.close())
        self.setting.pushButton_6.clicked.connect(self.save_config)
        self.setting.pushButton_8.clicked.connect(self.load_image)
        self.setting.pushButton_9.clicked.connect(self.delete_image)
        self.setting.pushButton_12.clicked.connect(self.add_item)
        self.setting.pushButton_10.clicked.connect(self.apply_data)
        self.setting.pushButton_11.clicked.connect(self.del_row)

        # Подгружаем настройки если они уже имеются
        if os.path.exists(os.path.join("data", "config.json")):
            with open(os.path.join("data", "config.json")) as file:
                data = json.load(file)
                self.setting.lineEdit_4.setText(data['nick'])
                self.setting.lineEdit_2.setText(data['server_ip'])
                self.setting.lineEdit_3.setText(data['server_port'])


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


    # Загрузить изображение в качестве аватарки пользователя
    def load_image(self):
        image_path = QtWidgets.QFileDialog.getOpenFileName(filter="*.png\n*.jpg")

        if image_path[0]: # Если пользователь выбрал изображение
            if os.path.getsize(image_path[0]) < 5120:
                # В зависимости от формата изображения задаем имя
                image_format = "png" if "png" in image_path[1] else "jpg"
                shutil.copy(image_path[0], os.path.join("data", f"custom.{image_format}"))

                # Обновляем Label который отвечает за изображение
                image_pixmap = QtGui.QPixmap(os.path.join("data", f"custom.{image_format}"))
                self.setting.label.setPixmap(image_pixmap)
            else:
                message = "Изображение не должно быть больше 5кб"
                QtWidgets.QMessageBox.about(self, "Ошибка", message)


    # Инициализация параметров при загрузке окна с настройками
    def init_data(self):
        # Если установлена аватарка - добавляем в Label
        for filename in os.listdir("data"):
            if "custom" in filename:
                image_pixmap = QtGui.QPixmap(os.path.join("data", filename))
                self.setting.label.setPixmap(image_pixmap)

        # Обновляем список серверов
        with open(os.path.join("data", "servers.json")) as file:
            server_list = json.load(file)

        # Бежим по ключам сервера, которые являются именем и заполняем таблицу
        for server in server_list:
            # Добавляем новую пустую строку
            rowPosition = self.setting.tableWidget.rowCount()
            self.setting.tableWidget.insertRow(rowPosition)

            # Заполняем её данными из конфига (имя, адрес, порт)
            self.setting.tableWidget.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem(server))
            self.setting.tableWidget.setItem(rowPosition, 1, QtWidgets.QTableWidgetItem(server_list[server]["ip"]))
            self.setting.tableWidget.setItem(rowPosition, 2, QtWidgets.QTableWidgetItem(server_list[server]["port"]))


    # Удалить аватарку
    def delete_image(self):
        for filename in os.listdir("data"):
            if "custom" in filename:
                os.remove(os.path.join("data", filename))
                self.setting.label.setText("64x64")


    # Добавить новую строку в список с серверами
    def add_item(self):
        dataline = self.setting.lineEdit_5.text()

        # Если строка не пустая и содержит 3 элемента
        if dataline and len(dataline.split(":")) == 3:
            parsed = dataline.split(":") # [name, ip, port]

            # Проверяем данные на валидность
            if not (self.check_ip(parsed[1]) and self.check_port(parsed[2])):
                QtWidgets.QMessageBox.about(self, "Ошибка", "Проверьте правильность ввода данных!")
                return

            # Проверяем нет ли таких значений в таблице
            # Бежим по всем строкам таблицы
            for row in range(self.setting.tableWidget.rowCount()):
                name = self.setting.tableWidget.item(row, 0).text()
                ip = self.setting.tableWidget.item(row, 1).text()
                port = self.setting.tableWidget.item(row, 2).text()

                # Проверяем уникальность имени и связки ip & port
                if (parsed[0] == name) or (parsed[1] == ip and parsed[2] == port):
                    QtWidgets.QMessageBox.about(self, "Ошибка", "Такие данные уже существуют!")
                    return

            # Если совпадение не найдено добавляем в таблицу пустую строку
            rowPosition = self.setting.tableWidget.rowCount()
            self.setting.tableWidget.insertRow(rowPosition)

            # Заполняем пустую строку значениями
            for num, text in enumerate(parsed):
                self.setting.tableWidget.setItem(rowPosition, num, QtWidgets.QTableWidgetItem(text))


    # Проверяем валидность ip адреса
    def check_ip(self, ip_line):
        regular_ip = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        if not re.match(regular_ip, ip_line) is None:
            return True
        else:
            return False


    # Проверяем валидность порта
    def check_port(self, port_line):
        if port_line.isdecimal() and int(port_line) <= 65535:
            return True
        else:
            return False


    # Применить настройки из таблицы серверов
    def apply_data(self):
        row_index = self.setting.tableWidget.currentRow() # Индекс строки

        # Заменяем основные настройки на выбранные
        if row_index != -1:
            ip = self.setting.tableWidget.item(row_index, 1).text()
            port = self.setting.tableWidget.item(row_index, 2).text()
            self.setting.lineEdit_2.setText(ip)
            self.setting.lineEdit_3.setText(port)


    # Удалить строку из таблицы
    def del_row(self):
        row_index = self.setting.tableWidget.currentRow() # Индекс строки
        if row_index != -1:
            self.setting.tableWidget.removeRow(row_index)


    # Сохранить настройки пользователя
    def save_config(self):
        nick = self.setting.lineEdit_4.text()
        server_ip = self.setting.lineEdit_2.text()
        server_port = self.setting.lineEdit_3.text()

        # Обновляем датчики, для того чтобы пользователь видел какие поля правильные
        self.setting.lineEdit_2.setStyleSheet("border-radius: 7px;")
        self.setting.lineEdit_3.setStyleSheet("border-radius: 7px;")
        self.setting.lineEdit_4.setStyleSheet("border-radius: 7px;")

        # Проверяем корректность ввода пользователя
        if len(nick) >= 3 and len(nick) <= 20:
            if self.check_ip(server_ip):
                if self.check_port(server_port):
                    # Перезаписываем конфиг с настройками пользователя
                    with open(os.path.join("data", "config.json"), "w") as file:
                        data = {"nick": nick, "server_ip": server_ip, "server_port": server_port}
                        json.dump(data, file, indent=6)

                    # Перезаписываем конфиг с настройками серверов
                    all_server = {}
                    for row in range(self.setting.tableWidget.rowCount()):
                        name = self.setting.tableWidget.item(row, 0).text()
                        ip = self.setting.tableWidget.item(row, 1).text()
                        port = self.setting.tableWidget.item(row, 2).text()

                        all_server[name] = {
                            "ip": ip,
                            "port": port
                        }

                    with open(os.path.join("data", "servers.json"), "w") as file:
                        json.dump(all_server, file, indent=6)

                    # Закрываем окно с настройками
                    self.close()
                    self.signal.emit(['update_config'])
                else:
                    self.setting.lineEdit_3.setStyleSheet("border: 2px solid red; border-radius: 7px;")
                    self.setting.lineEdit_3.setText("Проверьте правильность ввода SERVER_PORT")
            else:
                self.setting.lineEdit_2.setStyleSheet("border: 2px solid red; border-radius: 7px;")
                self.setting.lineEdit_2.setText("Проверьте правильность ввода SERVER_IP")
        else:
            self.setting.lineEdit_4.setStyleSheet("border: 2px solid red; border-radius: 7px;")
            self.setting.lineEdit_4.setText("Слишком длинный либо слишком короткий ник")
