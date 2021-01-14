import sys
import os
import unittest
sys.path.append(os.path.join(os.getcwd(), '..'))
from common.vars import ACTION, PRESENCE, USER, USERNAME, RESPONSE, ERROR, TIME
from client import create_msg, parsing_ans


class TestClient(unittest.TestCase):
    def setUp(self):
        # создадим словарь для тестирования функции create_msg
        self.test = create_msg()
        self.time = 1.1
        self.test[TIME] = self.time
        # зададим верное и не правильное имя пользователя
        self.accountname = 'Guest'
        self.wrong_accountname = 'Wrong Guest'
        # словари для проверки выдачи определенного ответа функции parsing_ans
        self.full_ok_dict = {ACTION: PRESENCE, TIME: self.time, USER: {USERNAME: self.accountname}}
        self.ok_dict = {RESPONSE: 200}
        # словари для проверки выдачи определенного ответа функции parsing_ans
        self.full_fail_dict = {RESPONSE: 400, ERROR: 'Bad Request'}
        self.fail_dict = {ERROR: 'Bad Request'}
        # строковые представления ответов функции parsing_ans
        self.fail_str = f'400: Bad Request'
        self.ok_str = f'200: OK'



    def test_create_message(self):
        self.assertEqual(self.test, self.full_ok_dict)

    def test_parsing_ans_wrong_response(self):
        self.assertEqual(parsing_ans(self.full_fail_dict), self.fail_str)

    def test_parsing_ans_ok_response(self):
        self.assertEqual(parsing_ans(self.ok_dict), self.ok_str)

    def test_parsing_ans_value_error(self):
        self.assertRaises(ValueError, parsing_ans, self.fail_dict)


if __name__=='__main__':
    unittest.main()
