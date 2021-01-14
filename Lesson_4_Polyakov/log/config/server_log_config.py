from logging.handlers import TimedRotatingFileHandler
from logging import getLogger, Formatter, StreamHandler, DEBUG, INFO, WARNING, ERROR, CRITICAL
from common.vars import LOGGING_LEVEL
import os
import sys
sys.path.append(os.path.join('../'))


# настройка пути логирования
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, '../logs/server/server.log')


# создаем регистратор (логгер)
LOG_SERVER = getLogger('server.app')
# создаем обработчик

FILE_HANDLER = TimedRotatingFileHandler(PATH, encoding='utf-8', interval=1, when='D')
# создаем формттер
FORMATTER = Formatter("%(asctime)-20s %(levelname)-10s %(filename)-10s %(message)s")
# подключаем форматтер к обработчику
FILE_HANDLER.setFormatter(FORMATTER)
# добавляем обработчик регистратору
LOG_SERVER.addHandler(FILE_HANDLER)
LOG_SERVER.setLevel(LOGGING_LEVEL)

if __name__ == '__main__':
    STREAM_HANDLER = StreamHandler(sys.stderr)
    STREAM_HANDLER.setFormatter(FORMATTER)
    STREAM_HANDLER.setLevel(ERROR)
    LOG_SERVER.addHandler(STREAM_HANDLER)
    # передаем сообщение
    LOG_SERVER.info('Информационное сообщение')
    LOG_SERVER.debug('Дебаг')
    LOG_SERVER.warning('Внимание')
    LOG_SERVER.error('Ошибка')
    LOG_SERVER.critical('Критическая ошибка')
