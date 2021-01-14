import os
import sys
import unittest
sys.path.append(os.path.join('..'))
from server import proccess_agent
from common.vars import ACTION, PRESENCE, USER, USERNAME, RESPONSE, ERROR, TIME


class TestProccessAgent(unittest.TestCase):
    def setUp(self):
        # словарь с опрделенным ответом функции (200)
        self.ok_dict = {RESPONSE: 200}
        # словарь с опрделенным ответом функции (400)
        self.fail_dict = {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        }
        self.wrong_action = 'wrong_action'
        self.time = '1.1'
        self.username = 'Guest'
        self.wrong_username = 'WrongGuest'

    def test_without_action(self):
        self.assertEqual(proccess_agent({TIME: self.time, USER: {USERNAME: self.username}}), self.fail_dict)

    def test_error_action(self):
        self.assertEqual(proccess_agent({ACTION: self.wrong_action, TIME: self.time,\
                                         USER: {USERNAME: self.username}}), self.fail_dict)

    def test_without_time(self):
        self.assertEqual(proccess_agent({ACTION: PRESENCE, USER: {USERNAME: self.username}}), self.fail_dict)

    def test_without_user(self):
        self.assertEqual(proccess_agent({ACTION: PRESENCE, TIME: self.time}), self.fail_dict)

    def test_error_username(self):
        self.assertEqual(proccess_agent({ACTION: PRESENCE, TIME: self.time,\
                                         USER: {USERNAME: self.wrong_username}}), self.fail_dict)

    def test_ok_proccess_agent(self):
        self.assertEqual(proccess_agent({ACTION: PRESENCE, TIME: self.time,\
                                         USER: {USERNAME: self.username}}), self.ok_dict)


if __name__ == "__main__":
    unittest.main()