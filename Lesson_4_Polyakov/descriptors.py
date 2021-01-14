import logging
import sys
from log.config.server_log_config import *
LOGGER = logging.getLogger('server.app')


class Port:
    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if value < 1025 or value > 65535:
            LOGGER.critical(f'Запуск сервера с недопустимым значением порта = {value}.'
                            f' Допустимые значения от 1024 до 65535')
            sys.exit(1)
            # raise ValueError(f'Запуск сервера с недопустимым значением порта = {value}.'
            #       f' Допустимые значения от 1024 до 65535')
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name

# для примера
class ServerEx:
    port = Port()

    def __init__(self, addr, port=7777):
        self.addr = addr
        self.port = port

    def print_host(self):
        return f'address - {self.addr}, port - {self.port}'


# пример
if __name__ == '__main__':
    OBJ = ServerEx('192.168.1.1', 9999)
    print(OBJ.print_host())
    print('*'*10)
    OBJ1 = ServerEx('192.168.1.2')
    print(OBJ1.print_host())
