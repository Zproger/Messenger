import os
import sys
import time
import pickle
import socket
import threading
from loguru import logger
from cryptography.fernet import Fernet


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
    sink=os.path.join("logs", "server_log.txt"),
    format="{time:HH:mm:ss} - {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="100 MB",
    compression="zip",
    enqueue=True # Делаем логгер потокобезопасным
)
# ============================================================================================================


class Server:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.all_client = []
        self.symmetric_key = None

        # Запускаем прослушивание соединений
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.ip, self.port))
        self.server.listen(0)
        threading.Thread(target=self.connect_handler).start()
        logger.debug(f"Сервер запущен ({self.ip}:{self.port})")


    # Обрабатываем входящие соединения
    def connect_handler(self):
        logger.debug("Запущен обработчик входящих соединений")
        while True:
            client, address = self.server.accept()
            if client not in self.all_client:
                self.all_client.append(client)

                # Отправляем запрос на успешное подключение + раздаем симметричные ключи
                self.get_key()
                payload = ['SERVER_OK', "Успешное подключение к чату!", self.symmetric_key]
                client.send(pickle.dumps(payload))
                logger.info(f'{address} - Успешное подключение к чату!')
                threading.Thread(target=self.message_handler, args=(client,)).start()
            time.sleep(2)


    # Отправляем сообщение всем клиентам кроме текущего
    # Принимает client_socket и сообщение для рассылки
    def sendall(self, current_socket, message):
        for client in self.all_client:
            if client != current_socket:
                client.send(message)


    # Обрабатываем отправленный текст
    def message_handler(self, client_socket):
        while True:
            try:
                message = client_socket.recv(7168)
                pickle_dec = pickle.loads(message)
                logger.debug(pickle_dec)
            except Exception as err:
                logger.exception(f"message_handler error:")
                self.all_client.remove(client_socket)
                logger.error(f"Неизвестный клиент удален с сервера из-за ошибки")
                break

            # Отправляем зашифрованное сообщение всем клиентам
            if pickle_dec[0] == "ENCRYPT_MESSAGE":
                self.sendall(client_socket, message)

            # Уведомление всем пользователям
            elif pickle_dec[0] == "USERS_NOTIFY":
                client_msg = pickle.dumps(["USERS_NOTIFY", pickle_dec[1]])
                self.sendall(client_socket, client_msg)

            # Если клиент отправил запрос на дисконнект
            elif pickle_dec[0] == "EXIT":
                logger.debug(f'{pickle_dec[1]} - разорвал соединение!')
                logger.debug("=" * 50)

                # Отправляем уведомление всех клиентам
                client_msg = pickle.dumps(["USERS_NOTIFY", f"{pickle_dec[1]} - Покинул чат"])
                self.sendall(client_socket, client_msg)
                self.all_client.remove(client_socket)
                break
            time.sleep(1)


    # Генератор сессионного симметричного ключа
    def get_key(self) -> None:
        if self.symmetric_key is None:
            logger.debug("Сгенерирован симметричный ключ шифрования")
            self.symmetric_key = Fernet.generate_key()


if __name__ == "__main__":
    myserver = Server('127.0.0.1', 5555)
