import sys
import os
import logging
import inspect
sys.path.append(os.path.join(os.getcwd(), '..'))
sys.path.append(os.path.join('/log/config'))
import log.config.client_log_config
import log.config.server_log_config


if sys.argv[0].find('client') == -1:
    LOGGER = logging.getLogger('server.app')
else:
    LOGGER = logging.getLogger('client.app')


# функция декоратор
def log(func):
    def wrapper(*args, **kwargs):
        wrap = func(*args, **kwargs)
        LOGGER.debug(f'Была вызвана функция {func.__name__} с параметрами {args}, {kwargs}. '
                     f'Вызов из модуля {func.__module__}. Вызов из функции {inspect.stack()[1][3]}', stacklevel=2)
        return wrap
    return wrapper


# класс декоратор
class Log:
    def __call__(self, func):
        def decorated(*args, **kwargs):
            wrap = func(*args, **kwargs)
            LOGGER.debug(f'Была вызвана функция {func.__name__} с параметрами {args}, {kwargs}. '
                         f'Вызов из модуля {func.__module__}. Вызов из функции {inspect.stack()[1][3]}', stacklevel=2)
            return wrap
        return decorated
