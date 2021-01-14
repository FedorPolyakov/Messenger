# Программа-сервер

import os
import socket
import select
import json
import sys
import logging
import argparse
import time
import threading
import configparser
from decos import log, Log
from common.vars import *
from common.functions import get_message, send_message
import log.config.server_log_config
from descriptors import Port
from metas import ServerMaker
from server_database import Server_DB
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem


LOG_SERVER = logging.getLogger('server.app')

new_conn = False
conflag_lock = threading.Lock()


# парсинг запуска скрипта
@Log()
def parse_args(default_port, default_address):
    parser = argparse.ArgumentParser()
    # проверяем порт
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    # проверяем адрес
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    port_listen = namespace.p
    address_listen = namespace.a
    return address_listen, port_listen


class Server(threading.Thread, metaclass=ServerMaker):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        # параметры подключения
        self.address = listen_address
        self.port = listen_port

        # бд сервера
        self.database = database

        # список постучавшихся клиентов
        self.clients = []
        # список сообщений от клиентов серверу
        self.msgs = []
        # словарь имен клиентов
        self.names = dict()
        super().__init__()

    # @Log()
    def init_socket(self):
        LOG_SERVER.info(f'Запущен сервер, порт для подключений "{self.port}", адрес '
                        f'с которого принимается сообщение "{self.address}", '
                        f'если адрес не указан, принимаются сообщения с любых адресов.')

        # создаем сокет
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        my_socket.bind((self.address, self.port))
        my_socket.settimeout(0.5)

        # слушаем сокет
        self.sock = my_socket
        self.sock.listen()

    def run(self):
        # сокет
        self.init_socket()

        while True:
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                LOG_SERVER.info(f'Установлено соедиение с адресом {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []

            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError as err:
                LOG_SERVER.error(f'Ошибка работы с сокетами: {err}')

            # принимаем сообщения, но если происходит ошибка - исключаем клиента
            if recv_data_lst:
                for clint_with_msg in recv_data_lst:
                    try:
                        self.process_agent(get_message(clint_with_msg), clint_with_msg)
                    except:
                        LOG_SERVER.info(f'Клиент {clint_with_msg.getpeername()} '
                                        f'отключился от сервера.')
                        for name in self.names:
                            self.database.user_logout(name)
                            del self.names[name]
                            break
                        self.clients.remove(clint_with_msg)

            # обрабатываем каждое полученное сообщение, если оно конечно есть
            for i in self.msgs:
                try:
                    self.process_p2p_message(i, send_data_lst)
                except (ConnectionAbortedError, ConnectionError, ConnectionResetError, ConnectionRefusedError):
                    LOG_SERVER.info(f'Связь с клиентом по имени {i[DESTINATION]} была разорвна')
                    self.clients.remove(self.names[i[DESTINATION]])
                    self.database.user_logout(i[DESTINATION])
                    del self.names[i[DESTINATION]]
            self.msgs.clear()

    @Log()
    def process_p2p_message(self, msg, listen_socks):
        if msg[DESTINATION] in self.names and self.names[msg[DESTINATION]] in listen_socks:
            send_message(self.names[msg[DESTINATION]], msg)
            LOG_SERVER.info(f'Отпрвлено сообщение пользователю {self.names[msg[DESTINATION]]}'
                            f' от пользователя {self.names[msg[SENDER]]}.')
        elif msg[DESTINATION] in self.names and self.names[msg[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            LOG_SERVER.error(f'Пользователь {msg[DESTINATION]} не зарегестрирован на сервере,'
                             f' отправка сообщений от этого пользователя не возможна.')

    # функция парсинга сообщений в режиме клиент - сервер
    @Log()
    def process_agent(self, msg, client):
        global new_conn
        LOG_SERVER.debug(f'Разбор сообщения от клиента : {msg}')

        # если принятое сообщение - сообщение о присутствии клиента, то принимаем и отвечаем
        if ACTION in msg and msg[ACTION] == PRESENCE and TIME in msg and USER in msg:
            # если пользователя еще не знаем, то регестрируем его в списке клиентов,
            # иначе отправляем ответ и заверщаем
            if msg[USER][USERNAME] not in self.names.keys():
                self.names[msg[USER][USERNAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(msg[USER][USERNAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                with conflag_lock:
                    new_conn = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return

        # Если это сообщение, то добавляем его в очередь сообщений. Ответа не надо
        elif ACTION in msg and msg[ACTION] == MESSAGE and TIME in msg and MESSAGE_TEXT in msg and \
                DESTINATION in msg and SENDER in msg and self.names[msg[SENDER]] == client:
            self.msgs.append(msg)
            self.database.process_msg(msg[SENDER], msg[DESTINATION])
            return

        # Если клиент выходит
        elif ACTION in msg and msg[ACTION] == EXIT and USERNAME in msg and self.names[msg[USERNAME]] == client:
            self.database.user_logout(msg[USERNAME])
            LOG_SERVER.info(f'Клиент {msg[USERNAME]} корректно отключился от сервера')
            self.clients.remove(self.names[msg[USERNAME]])
            self.names[msg[USERNAME]].close()
            del self.names[msg[USERNAME]]
            with conflag_lock:
                new_conn = True
            return

        # Если это запрос контакт-листа
        elif ACTION in msg and msg[ACTION] == GET_CONTACTS and USER in msg and self.names[msg[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(msg[USER])
            send_message(client, response)

        # Если это добавление контакта
        elif ACTION in msg and msg[ACTION] == ADD_CONTACT and USERNAME in msg and USER in msg \
                and self.names[msg[USER]] == client:
            self.database.add_contact(msg[USER], msg[USERNAME])
            send_message(client, RESPONSE_200)

        # Если это удаление контакта
        elif ACTION in msg and msg[ACTION] == REMOVE_CONTACT and USERNAME in msg \
                and self.names[msg[USERNAME]] == client:
            self.database.remove_contact(msg[USER], msg[USERNAME])
            send_message(client, RESPONSE_200)

        # Если это запрос Известных пользователей
        elif ACTION in msg and msg[ACTION] == USERS_REQUEST and USERNAME in msg \
                and self.names[msg[USERNAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0]
                                   for user in self.database.all_users()]
            send_message(client, response)

        # в иных случаях выдаем bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Некорректный запрос'
            send_message(client, response)
            return


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключенных пользователей')
    print('loglist - история входов пользователя')
    print('get_contacts - контакты выбранного пользователя')
    print('add_contact - добавление контактов')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    # Загрузка файла конфигурации сервера
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")

    # Загрузка параметров командной строки, если нет параметров, то задаём
    # значения по умоланию.
    listen_address, listen_port = parse_args(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])
    path = os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file'])
    print(path)

    server_db = Server_DB(path)

    # создаем экземпляр класса сервреа
    server = Server(listen_address, listen_port, server_db)
    server.daemon = True
    server.start()

    # Создаём графическое окуружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(server_db))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Функция обновляющяя список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update():
        global new_conn
        if new_conn:
            main_window.active_clients_table.setModel(
                gui_create_model(server_db))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_conn = False

    # Функция создающяя окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(server_db))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    # Функция сохранения настроек
    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()
    '''
    listen_address, listen_port = parse_args()
    # дб сервера
    server_db = Server_DB()

    # создаем экземпляр класса сервреа
    server = Server(listen_address, listen_port, server_db)
    server.daemon = True
    server.start()

    # help
    print_help()

    # server.main_func()
    # Основной цикл сервера:
    while True:
        command = input('Введите комманду: ')
        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'users':
            for user in sorted(server_db.all_users()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(server_db.active_users()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loglist':
            name = input('Введите имя пользователя для просмотра истории. Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(server_db.login_history(name)):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        elif command == 'get_contacts':
            name = input('Введите имя пользователя для просмотра его контактов: ')
            print(f'Контакты пользователя {name}: {server_db.get_contacts(name)}')
        elif command == 'add_contact':
            name = input(f'Введите имя пользователя, которому хотите добавит контакт: ')
            friend = input(f'Введите имя пользователя, которого хотите добавить пользователю {name}: ')
            server_db.add_contact(name, friend)
            print(f'Контакты пользователя {name}: {server_db.get_contacts(name)}')
        else:
            print('Команда не распознана.')
    '''


if __name__ == '__main__':
    main()
