# Программа-клиент

import socket
import json
import sys
import time
import logging
import argparse
import threading
import log.config.client_log_config
from errors import ReqFieldMissingError, ServerError, IncorrectDataRecivedError
from decos import log, Log
from common.vars import *
from common.functions import get_message, send_message
from metas import ClientMaker
from client_database import Client_DB

LOG_CLIENT = logging.getLogger('client.app')

# Объект блокировки сокета и работы с базой данных
sock_lock = threading.Lock()
database_lock = threading.Lock()


class ClientSender(threading.Thread, metaclass=ClientMaker):
    @Log()
    def __init__(self, username, sock, database):
        self.username = username
        self.sock = sock
        self.client_db = database
        super().__init__()


    # функция созадния сообщения-словаря для выхода клиента
    @Log()
    def create_exit_msg(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            USERNAME: self.username
        }

    # @Log()
    def create_message(self):
        to_user = input('Введите получателя сообщения: ')
        msg = input('Введите сообщение: ')

        # Проверим, что получатель существует
        with database_lock:
            if not self.client_db.check_user(to_user):
                LOG_CLIENT.error(f'Попытка отправить сообщение незарегистрированому получателю: {to_user}')
                return

        msg_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: msg
        }
        LOG_CLIENT.info(f'Сфомирован словарь сообщения {msg_dict}')

        with database_lock:
            self.client_db.save_msg(self.username, to_user, msg)

        with sock_lock:
            try:
                send_message(self.sock, msg_dict)
                LOG_CLIENT.info(f'Сообщение отпрвлено пользователю {to_user}')
            except OSError as error:
                if error.errno:
                    LOG_CLIENT.critical(f'Потеряно соединение с сервером.')
                    exit(1)
                else:
                    LOG_CLIENT.error('Не удалось передать сообщение. Таймаут сообщения')
                # sys.exit(1)

    # @Log()
    def run(self):
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()

            elif command == 'help':
                self.print_help()

            # exit
            elif command == 'exit':
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_msg())
                    except:
                        pass
                    print('Завершение работы мессенжера')
                    LOG_CLIENT.info(f'Завершение работы по команде пользователя')
                time.sleep(1)
                break

            # Список контактов
            elif command == 'contacts':
                with database_lock:
                    contact_list = self.client_db.get_contacts()
                for contact in contact_list:
                    print(contact)

            # Редактирование контактов
            elif command == 'edit':
                self.edit_contacts()

            # история сообщений.
            elif command == 'history':
                self.print_history()

            else:
                print('Неизвестная команда, попробуйте снова, ну или наберите help =)')

    # help функция
    # @staticmethod
    @Log()
    def print_help(self):
        print(f'Поддерживаются команды: \n'
              f'message - отпрвить сообщение. Адресат и текст вводится далее\n'
              f'help - справка по командам\n'
              f'exit - выход из программы\n'
              f'history - история сообщений\n'
              f'contacts - список контактов\n'
              f'edit - редактирование списка контактов')

    def print_history(self):
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.client_db.get_history_msg(sender=self.username)
                for msg in history_list:
                    print(f'\nСообщение от пользователя: {msg[0]} от {msg[3]}:\n{msg[2]}')
            elif ask == 'out':
                history_list = self.client_db.get_history_msg(receiver=self.username)
                for msg in history_list:
                    print(f'\nСообщение от пользователя: {msg[1]} от {msg[3]}:\n{msg[2]}')
            else:
                history_list = self.client_db.get_history_msg()
                for msg in history_list:
                    print(f'\nСообщение от пользователя: {msg[0]}, пользователю {msg[1]} от {msg[3]}\n{msg[2]}')

    def edit_contacts(self):
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемного контакта: ')
            with database_lock:
                if self.client_db.check_contact(edit):
                    self.client_db.remove_contact(edit)
                else:
                    LOG_CLIENT.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            edit = input('Введите имя создаваемого контакта: ')
            if self.client_db.check_user(edit):
                with database_lock:
                    self.client_db.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.username, edit)
                    except:
                        LOG_CLIENT.error('Не удалось отправить информацию на сервер.')


class ClientReader(threading.Thread, metaclass=ClientMaker):
    # @Log()
    def __init__(self, username, sock, database):
        self.username = username
        self.sock = sock
        self.client_db = database
        super().__init__()

    # @Log()
    def run(self):
        while True:
            time.sleep(1)
            with sock_lock:
                try:
                    msg = get_message(self.sock)
                # Принято некорректное сообщение
                except IncorrectDataRecivedError:
                    LOG_CLIENT.error(f'Неудалось декодировать сообщение')
                except OSError as error:
                    if error.errno:
                        LOG_CLIENT.critical(f'Потеряно соединение с сервером')
                        break
                # Проблемы с соединением Вышел таймаут соединения или Обрыв соединения
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    LOG_CLIENT.critical(f'Потеряно соединение с сервером')
                    break
                else:
                    if ACTION in msg and msg[ACTION] == MESSAGE and SENDER in msg and \
                            DESTINATION in msg and MESSAGE_TEXT in msg and msg[DESTINATION] == self.username:
                        print(f'\nПолучено сообщение от пользователя {msg[SENDER]}:\n {msg[MESSAGE_TEXT]}')

                        with database_lock:
                            try:
                                self.client_db.save_msg(msg[SENDER], self.username, msg[MESSAGE_TEXT])
                            except:
                                LOG_CLIENT.error(f'Ошибка взаимодействия с базой данных')

                        LOG_CLIENT.info(f'Получено сообщение от пользователя {msg[SENDER]}: {msg[MESSAGE_TEXT]}')
                    else:
                        LOG_CLIENT.error(f'Получено некорректное сообщение с сервера: {msg}')


@Log()
def create_presence(username):
    msg_to_srv = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            USERNAME: username
        }
    }
    LOG_CLIENT.debug(f'Сформированно {PRESENCE} сообщение для пользователя {username}')
    return msg_to_srv


@Log()
def parsing_ans(msg):
    LOG_CLIENT.debug(f'Разбор сообщения от сервера : {msg}')
    if RESPONSE in msg:
        if msg[RESPONSE] == 200:
            return '200: OK'
        elif msg[RESPONSE] == 400:
            raise ServerError(f'400 : {msg[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


# парсинг запуска скрипта
@Log()
def parse_args():
    parser = argparse.ArgumentParser()
    # проверяем порт
    parser.add_argument('port', default=DEFAULT_PORT, type=int,  nargs='?')
    # проверяем адрес
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    # проверяем режим работы
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if server_port < 1024 or server_port > 65535:
        LOG_CLIENT.critical(f'Номер порта может быть задан только в диапазоне от 1024 до 65535',
                            f'{server_port} не входит в разрешенный диапазон')
        # sys.exit(1)
        exit(1)

    return server_address, server_port, client_name


# Функция запрос контакт листа
def contacts_list_request(sock, name):
    LOG_CLIENT.debug(f'Запрос контакт листа для пользователся {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    LOG_CLIENT.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    LOG_CLIENT.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Функция добавления пользователя в контакт лист
def add_contact(sock, username, contact):
    LOG_CLIENT.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        USERNAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


# Функция запроса списка известных пользователей
def user_list_request(sock, username):
    LOG_CLIENT.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        USERNAME: username
    }
    send_message(sock, req)
    print('*')
    ans = get_message(sock)
    print(ans)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        # (f'Ошибка запроса списка известных пользователей {username}')
        raise ServerError


# Функция удаления пользователя из контакт листа
def remove_contact(sock, username, contact):
    LOG_CLIENT.debug(f'Создание контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        USERNAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


# Функция инициализатор базы данных. Запускается при запуске, загружает данные в базу с сервера.
def database_load(sock, database, username):
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        LOG_CLIENT.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        LOG_CLIENT.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def main():
    print(f'Мессенджер. Клиентский модуль')
    server_address, server_port, client_name = parse_args()

    if not client_name:
        client_name = input(f'Введите имя пользователя: ')
    else:
        print(f'мессенджер запущен для пользователя {client_name}')

    LOG_CLIENT.info(f'Запущен клиент, адрес: {server_address},  порт: {server_port}, имя пользователя: {client_name}')

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.settimeout(1)

        sock.connect((server_address, server_port))
        send_message(sock, create_presence(client_name))

        answer_from_srv = parsing_ans(get_message(sock))
        print(f'Имя пользователя: {client_name}')
        print(f'Принят ответ от сервера: {answer_from_srv}')
        LOG_CLIENT.debug(f'Принят ответ от сервера: {answer_from_srv}')
    except json.JSONDecodeError:
        LOG_CLIENT.error(f'Не удалось декодировать полученную JSON-строку ')
        sys.exit(1)
    except (ConnectionRefusedError, ConnectionError):
        LOG_CLIENT.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}. '
                            f'Запрос на подлкючение отвергнуто')
        sys.exit(1)
    except ReqFieldMissingError as missing:
        LOG_CLIENT.error(f'В ответе отсутствуетс необходимое поле {missing.missing_field}')
        sys.exit(1)
    except ServerError as e:
        LOG_CLIENT.error(f'При установке соединения сервер вернул ошибку: {e.text}')
        sys.exit(1)
    else:

        # Инициализация БД
        database = Client_DB(client_name)
        database_load(sock, database, client_name)

        # если соединение с сервером установлено корректно, то запускаем прием сообщений от сервера клиенту
        sender_mod = ClientSender(client_name, sock, database)
        sender_mod.daemon = True
        sender_mod.start()
        # запускаем отправку сообщений и взамимодействие с пользователем

        receiver_mod = ClientReader(client_name, sock, database)
        receiver_mod.daemon = True
        receiver_mod.start()

        LOG_CLIENT.debug('Процессы запущены')

        while True:
            time.sleep(1)
            # print(f'{sender_mod.is_alive()}-----{receiver_mod.is_alive()}')
            if sender_mod.is_alive() and receiver_mod.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
