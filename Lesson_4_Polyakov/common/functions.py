import json
import sys
from common.vars import MAX_PACKAGE_SIZE, ENCODING
from errors import IncorrectDataRecivedError, NonDictInputError
sys.path.append('../')


# получить сообщение
def get_message(client):
    """
    Утилита приёма и декодирования сообщения принимает байты выдаёт словарь,
    если приняточто-то другое отдаёт ошибку значения
    :param client:
    :return:
    """
    encoded_response = client.recv(MAX_PACKAGE_SIZE)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        else:
            raise IncorrectDataRecivedError
    else:
        raise IncorrectDataRecivedError


# отправить сообщение
def send_message(sock, msg):
    '''
    :param sock: сокет
    :param msg: сообщение
    :return:
    '''
    if not isinstance(msg, dict):
        raise NonDictInputError
    message = json.dumps(msg)
    encoded_msg = message.encode(ENCODING)
    sock.send(encoded_msg)
