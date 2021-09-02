import os
import sys
import time
import pickle
from PyQt5 import QtCore
from loguru import logger
from cryptography.fernet import Fernet
from methods.windows.settings import *


# Мониторинг входящих сообщений
class message_monitor(QtCore.QThread):
    mysignal = QtCore.pyqtSignal(list)
    server_socket = None
    symmetric_key = None

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)

    def run(self):
        logger.info("Запущен потоковый обработчик")
        while True:
            if self.server_socket != None:
                try:
                    message = self.server_socket.recv(7168)
                except OSError:
                    return # Возникает при отключении от сервера, так как поток ожидаем данные по закрытому каналу связи

                pickle_dec = pickle.loads(message)

                # Если это запрос на заполнение ключей
                # ["SERVER_OK", "MESSAGE", "KEY"]
                if pickle_dec[0] == "SERVER_OK":
                    logger.info(f"SERVER_OK: {pickle_dec}")
                    self.symmetric_key = pickle_dec[-1]
                    self.cipher = Fernet(self.symmetric_key) # Объект шифровальщика
                    self.mysignal.emit(pickle_dec)

                # Если поступает пользовательское уведомление
                # pickle_dec[1] содержит сообщение
                elif pickle_dec[0] == "USERS_NOTIFY":
                    logger.info(f"USERS_NOTIFY: {pickle_dec}")
                    decrypted_payload = ["USERS_NOTIFY", pickle_dec[1]]
                    self.mysignal.emit(decrypted_payload)

                # Обработка сообщений от других пользователей
                # ['ENCRYPT_MESSAGE', self.nick, smile_num, message_text.encode()]
                elif pickle_dec[0] == "ENCRYPT_MESSAGE":
                    logger.info(f"ENCRYPT_MESSAGE: {pickle_dec}")
                    decrypted_text = self.cipher.decrypt(pickle_dec[-1]).decode()
                    decrypted_payload = ["ENCRYPT_MESSAGE", pickle_dec[1], pickle_dec[2], decrypted_text]
                    self.mysignal.emit(decrypted_payload)
            time.sleep(0.5)

    # Отправить зашифрованное сообщение на сервер
    def send_encrypt(self, data_list):
        # ['ENCRYPT_MESSAGE', self.nick, smile_num, message_text.encode()]
        if data_list[0] == "ENCRYPT_MESSAGE":
            encrypted_message = self.cipher.encrypt(data_list[-1])
            payload = pickle.dumps(['ENCRYPT_MESSAGE', data_list[1], data_list[2], encrypted_message])

            try:
                self.server_socket.send(payload)
            except Exception as err:
                logger.exception("ConnectionError:")
                self.mysignal.emit(["CONNECTION_ERROR"])
                return

        # Если нужно уведомить всех пользователей
        # ["USERS_NOTIFY", "message"]
        elif data_list[0] == "USERS_NOTIFY":
            payload = pickle.dumps(data_list)
            self.server_socket.send(payload)

        # Если клиент разорвал соединение
        # ['EXIT', f'{self.nick}', 'вышел из чата!']
        elif data_list[0] == "EXIT":
            try:
                payload = pickle.dumps(data_list)
                self.server_socket.send(payload)
            # Если сервер отключен и мы пытаемся в этот
            # момент из него выйти
            except:
                pass