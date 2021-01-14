from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.vars import *
import datetime


class Server_DB:
    # класс-отображение таблицы всех пользователей
    class Users:
        def __init__(self, username):
            self.id = None
            self.username = username
            self.last_login = datetime.datetime.now()

    # класс-отображение таблицы активных пользователей
    class ActiveUsers:
        def __init__(self, user_id, login_time, ip_address, port):
            self.id = None
            self.user_id = user_id
            self.login_time = login_time
            self.ip_address = ip_address
            self.port = port

    # класс-отображение таблицы учета входа пользователей
    class LoginHistory:
        def __init__(self, user_id, date_time, ip_address, port):
            self.id = None
            self.user_id = user_id
            self.date_time = date_time
            self.ip_address = ip_address
            self.port = port

    # класс-отображение таблицы контактов пользователей
    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # класс-отображение таблицы истории действий пользователя
    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent_msg = 0
            self.get_msg = 0

    def __init__(self, path):
        # self.engine_db = create_engine('sqlite:///server_db.db3', echo=False, pool_recycle=7200)
        self.engine_db = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                       connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users_tbl = Table('Users', self.metadata,
                          Column('id', Integer, primary_key=True),
                          Column('username', String(128), unique=True),
                          Column('last_login', DateTime)
                          )
        # таблица истории входов пользователй
        users_history_tbl = Table('Login_history', self.metadata,
                                  Column('id', Integer, primary_key=True),
                                  Column('user_id', ForeignKey('Users.id')),
                                  Column('date_time', DateTime),
                                  Column('ip_address', String(16)),
                                  Column('port', String(10))
                                  )
        # таблица активных пользователей
        active_users_tbl = Table('Active_users', self.metadata,
                                 Column('id', Integer, primary_key=True),
                                 Column('user_id', ForeignKey('Users.id'), unique=True),
                                 Column('login_time', DateTime),
                                 Column('ip_address', String(16)),
                                 Column('port', String(10))
                                 )

        # таблица контактов пользователей
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('user', ForeignKey('Users.id')),
                         Column('contact', ForeignKey('Users.id'))
                         )

        users_history_actions_tbl = Table('ActionHistory', self.metadata,
                                          Column('id', Integer, primary_key=True),
                                          Column('user', ForeignKey('Users.id')),
                                          Column('sent_msg', Integer),
                                          Column('get_msg', Integer)
                                          )

        self.metadata.create_all(self.engine_db)

        mapper(self.Users, users_tbl)
        mapper(self.ActiveUsers, active_users_tbl)
        mapper(self.LoginHistory, users_history_tbl)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistory, users_history_actions_tbl)

        # создаем сессию
        session_ = sessionmaker(bind=self.engine_db)
        self.session = session_()

        # при подключении бд очищаем таблицу активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username, ip_address, port):
        # print(username, ip_address, port)
        result = self.session.query(self.Users).filter_by(username=username)
        if result.count():
            user = result.first()
            user.last_login = datetime.datetime.now()
        else:
            user = self.Users(username)
            self.session.add(user)
            self.session.commit()
            # пишем в таблицу истории пользователей
            user_to_history = self.UsersHistory(user.id)
            self.session.add(user_to_history)

        active_user = self.ActiveUsers(user.id, user.last_login, ip_address, port)
        self.session.add(active_user)

        history = self.LoginHistory(user.id, user.last_login, ip_address, port)
        self.session.add(history)

        self.session.commit()

    def user_logout(self, username):
        # print(username)
        result = self.session.query(self.Users).filter_by(username=username).first()

        self.session.query(self.ActiveUsers).filter_by(user_id=result.id).delete()

        self.session.commit()

    def process_msg(self, sender, recipient):
        # id отправителя и получателя
        sender = self.session.query(self.Users).filter_by(username=sender).first().id
        recipient = self.session.query(self.Users).filter_by(username=recipient).first().id
        # счетчки отправленных и принятых сообщений
        sender_count_msg = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        recipient_count_msg = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        # print(sender)
        # print(recipient)
        # print(sender_count_msg.sent_msg)
        # print(recipient_count_msg.get_msg)
        sender_count_msg.sent_msg += 1
        recipient_count_msg.get_msg += 1

        self.session.commit()

    def add_contact(self, user, contact):
        # id пользователей
        user = self.session.query(self.Users).filter_by(username=user).first()
        contact = self.session.query(self.Users).filter_by(username=contact).first()

        # проверка на то, что контакта существует и еще нет у пользователя
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user, contact):
        # id пользователей
        user = self.session.query(self.Users).filter_by(username=user).first()
        contact = self.session.query(self.Users).filter_by(username=contact).first()

        # существует контакт?
        if not contact:
            return

        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()

    def all_users(self):
        users = self.session.query(self.Users.username, self.Users.last_login)
        return users.all()

    def active_users(self):
        active_users = self.session.query(self.Users.username,
                                          self.ActiveUsers.ip_address,
                                          self.ActiveUsers.port,
                                          self.ActiveUsers.login_time,).join(self.Users)
        return active_users.all()

    def login_history(self, username=None):
        history = self.session.query(self.Users.username,
                                     self.LoginHistory.ip_address,
                                     self.LoginHistory.port,
                                     self.LoginHistory.date_time).join(self.Users)
        if username:
            history = history.filter(self.Users.username == username)
        return history.all()

    def get_contacts(self, username):
        user = self.session.query(self.Users).filter_by(username=username).one()
        query = self.session.query(self.UsersContacts, self.Users.username).filter_by(user=user.id). \
            join(self.Users, self.UsersContacts.contact == self.Users.id)
        # print(query)
        return [contact[1] for contact in query.all()]

    def msg_history(self):
        query = self.session.query(
            self.Users.username,
            self.Users.last_login,
            self.UsersHistory.sent_msg,
            self.UsersHistory.get_msg
        ).join(self.Users)
        return query.all()


if __name__ == '__main__':
    test_db = Server_DB()

    test_db.user_login('client1', '192.168.1.6', '5555')
    test_db.user_login('client2', '192.168.1.100', '9999')
    test_db.user_login('client3', '192.168.1.88', '5565')
    test_db.user_login('client4', '192.168.1.33', '9252')
    test_db.user_login('client6', '192.168.1.23', '5533')
    # print(test_db.all_users())
    # print(test_db.active_users())
    # test_db.user_logout('client1')
    # print(test_db.all_users())
    # print(test_db.active_users())
    # print('*'*20)
    # print(test_db.login_history('client1'))
    # print('*'*20)
    # print(test_db.all_users())
    # print(test_db.active_users())
    test_db.add_contact('client1', 'client2')
    test_db.add_contact('client1', 'client3')
    test_db.add_contact('client3', 'client2')
    print(test_db.get_contacts('client1'))
    test_db.remove_contact('client1', 'client2')
    print(test_db.get_contacts('client1'))
    print(test_db.msg_history())
    test_db.process_msg('client1', 'client3')
    print(test_db.msg_history())
