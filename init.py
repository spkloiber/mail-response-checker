import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
import datetime
import configparser
import imaplib
import os.path
import time

config = configparser.ConfigParser()
config.read('config.cfg')

engine = create_engine('sqlite:///' + config.get('DB', 'file'))
base = declarative_base(bind=engine)

class Question(base):
    __tablename__ = 'questions'

    id = Column(String, primary_key = True)
    sender = Column(String)
    is_answered = Column(Boolean)
    sent_on = Column(DateTime)
    answered_by = Column(String)
    answered_on = Column(DateTime)

    def __repr__(self):
        return "<Question(id='%i', reply_id='%s', sender='%s', is_answered='%i', sent_on='%s', answered_by='%s', " \
               "answered_on='%s')>" % (self.id, self.sender, self.is_answered, self.sent_on,
                                       self.answered_by, self.answered_on)

    def __init__(self, id = None, sender = None, is_answered = None,
                 sent_on = None, answered_by = None, answered_on = None):
        self.id = '-1' if id is None else id
        self.sender = '' if sender is None else sender
        self.is_answered = 0 if is_answered is None else is_answered
        self.sent_on = datetime.datetime(1990, 1, 1) if sent_on is None else sent_on
        self.answered_by = 'NO ONE' if answered_by is None else answered_by
        self.answered_on = datetime.datetime(1990, 1, 1) if answered_on is None else answered_on


if not os.path.isfile(config.get('DB', 'file')):
    base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


connection = imaplib.IMAP4_SSL(config.get('Imap', 'hostname'))
connection.login(config.get('Imap', 'username'), config.get('Imap', 'password'))
connection.select(config.get('Imap', 'mailbox'))


########################################################################################################################
def reset_today(): # for testing purposes, resets all mails received today to unseen
    ret, data = connection.search(None, "(ON {0})".format(time.strftime("%d-%b-%Y")))
    list = data[0].decode('utf-8').split(' ')

    for mail in list:
        connection.store(mail, '-FLAGS', '\Seen')

