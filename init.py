import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
import datetime
import configparser
import imaplib
import smtplib
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
    subject = Column(String)
    is_answered = Column(Boolean)
    sent_on = Column(DateTime)
    answered_by = Column(String)
    answered_on = Column(DateTime)

    def __repr__(self):
        return "<Question(id='%s', sender='%s', subject='%s', is_answered='%i', sent_on='%s', answered_by='%s', " \
               "answered_on='%s')>" % (self.id, self.sender, self.subject, self.is_answered, self.sent_on,
                                       self.answered_by, self.answered_on)

    def __init__(self, id = '-1', sender = '', subject = '', is_answered = 0, sent_on = datetime.datetime(1990, 1, 1),
                 answered_by = 'NO ONE', answered_on = datetime.datetime(1990, 1, 1)):
        self.id = id
        self.sender = sender
        self.subject = subject
        self.is_answered = is_answered
        self.sent_on = sent_on
        self.answered_by = answered_by
        self.answered_on = answered_on


if not os.path.isfile(config.get('DB', 'file')):
    base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


conn_imap = imaplib.IMAP4_SSL(config.get('Imap', 'hostname'))
conn_imap.login(config.get('Imap', 'username'), config.get('Imap', 'password'))
conn_imap.select(config.get('Imap', 'mailbox'))

conn_smtp = smtplib.SMTP_SSL(config.get('Smtp', 'hostname'))
conn_smtp.esmtp_features["auth"] = "LOGIN PLAIN"
conn_smtp.login(config.get('Smtp', 'username'), config.get('Smtp', 'password'))



########################################################################################################################
def reset_today(): # for testing purposes, resets all mails received today to unseen
    # DOING THIS AND NOT CHANGING DATABASE CAN CAUSE UNTESTED BEHAVIOUR
    ret, data = conn_imap.search(None, "(ON {0})".format(time.strftime("%d-%b-%Y")))
    list = data[0].decode('utf-8').split(' ')

    for mail in list:
        conn_imap.store(mail, '-FLAGS', '\Seen')

