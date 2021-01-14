import sys
import os
import json
import unittest
sys.path.append(os.path.join('../common'))
sys.path.append(os.path.join('../new'))
from vars import ACTION, PRESENCE, USER, USERNAME, RESPONSE, ERROR, TIME, ENCODING
from functions import get_message, send_message



class TestSocketClass:
    def __init__(self, init_dict):
        self.init_dict = init_dict
        self.encoded_msg = None
        self.received_msg = None

    def send(self, msg_to_send):
        json_msg_to_send = json.dumps(self.init_dict)
        self.encoded_msg = json_msg_to_send.encode(ENCODING)
        self.received_msg = msg_to_send


    def recv(self, max_size):
        json_msg = json.dumps(self.init_dict)
        return json_msg.encode(ENCODING)


class TestFuncs(unittest.TestCase):

    def setUp(self):
        # словарь с опрделенным ответом функции (200)
        self.good_dict = {RESPONSE: 200}
        # словарь с опрделенным ответом функции (400)
        self.fail_dict = {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        }
        # словарь для отправки
        self.dict_to_send = {
            ACTION: PRESENCE,
            TIME: 1.1,
            USER: {
                USERNAME: 'user_test'
            }
        }
        self.test_sock = TestSocketClass(self.dict_to_send)
        self.test_sock_ok_recv = TestSocketClass(self.good_dict)
        self.test_sock_ok_err = TestSocketClass(self.fail_dict)


    def test_send_msg(self):

        send_message(self.test_sock, self.dict_to_send)
        self.assertEqual(self.test_sock.encoded_msg, self.test_sock.received_msg)
        with self.assertRaises(Exception):
            send_message(self.test_sock, self.test_sock)

    def test_get_msg(self):
        self.assertEqual(get_message(self.test_sock_ok_recv), self.good_dict)
        self.assertEqual(get_message(self.test_sock_ok_err), self.fail_dict)


if __name__ == "__main__":
    unittest.main()
