from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Text
from sqlalchemy.orm import mapper, sessionmaker
from common.vars import *
import datetime


class Client_DB:
    class KnownUsers:
        def __init__(self, user):
            self.id = None
            self.username = user

    class HistoryMessage:
        def __init__(self, from_user, to_user, msg):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.msg = msg
            self.date = datetime.datetime.now()

    class Contacts:
        def __init__(self, contact):
            self.id = None
            self.name = contact

    def __init__(self, name):
        self.engine_db = create_engine(f'sqlite:///client_{name}db.db3', echo=False, pool_recycle=7200,
                                       connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        known_users = Table('Known_Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String)
                            )

        history_msg = Table('History_Message', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('from_user', String),
                            Column('to_user', String),
                            Column('msg', Text),
                            Column('date', DateTime)
                            )

        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('name', String, unique=True)
                         )

        self.metadata.create_all(self.engine_db)

        mapper(self.KnownUsers, known_users)
        mapper(self.HistoryMessage, history_msg)
        mapper(self.Contacts, contacts)

        session_ = sessionmaker(bind=self.engine_db)
        self.session = session_()

        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, contact):
        if not self.session.query(self.Contacts).filter_by(name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def remove_contact(self, contact):
        self.session.query(self.Contacts).filter_by(name=contact).delete()

    def add_users(self, users_list):
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_msg(self, from_user, to_user, msg):
        msg_row = self.HistoryMessage(from_user, to_user, msg)
        self.session.add(msg_row)
        self.session.commit()

    # Функция возвращающяя контакты
    def get_contacts(self):
        return [contact[0] for contact in self.session.query(self.Contacts.name).all()]

    # Функция возвращающяя список известных пользователей
    def get_known_users(self):
        return [user[0] for user in self.session.query(self.KnownUsers.username).all()]

    # Функция проверяющяя наличие пользователя в известных
    def check_user(self, user):
        if self.session.query(self.KnownUsers).filter_by(username=user).count():
            return True
        else:
            return False

    # Функция проверяющяя наличие пользователя контактах
    def check_contact(self, contact):
        if self.session.query(self.Contacts).filter_by(contact_name=contact).count():
            return True
        else:
            return False

    # Функция возвращающая историю переписки
    def get_history_msg(self, sender=None, receiver=None):
        query = self.session.query(self.HistoryMessage)
        if sender:
            query = query.filter_by(from_user=sender)
        if receiver:
            query = query.filter_by(to_user=receiver)
        return [(history_row.from_user, history_row.to_user, history_row.msg, history_row.date)
                for history_row in query.all()]


if __name__ == '__main__':
    test_db = Client_DB('test1')
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    test_db.save_msg('test1', 'test2', f'Привет! я тестовое сообщение от {datetime.datetime.now()}!')
    test_db.save_msg('test2', 'test1', f'Привет! я другое тестовое сообщение от {datetime.datetime.now()}!')
    print(test_db.get_contacts())
    print(test_db.get_known_users())
    print(test_db.check_user('test1'))
    print(test_db.check_user('test10'))
    print(test_db.get_history_msg('test2'))
    print(test_db.get_history_msg(receiver='test2'))
    print(test_db.get_history_msg('test3'))
    test_db.remove_contact('test4')
    print(test_db.get_contacts())


