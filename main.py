import init
import datetime
from datetime import timedelta
import re
import imaplib


########################################################################################################################
def get_new_mails():
    ret, tmp_mails = init.conn_imap.search(None, 'UNSEEN')
    mails = tmp_mails[0].decode('utf-8').split(' ')

    print('Mails:')
    for mail in mails:
        print('%s' % mail)

    return mails


########################################################################################################################
def add_mail_to_db(question):
    init.session.add(question)
    init.session.commit()


########################################################################################################################
def mail_answered(id, answer): # message_id of mail that was answered, answer as Question object
    init.session.execute("UPDATE questions SET is_answered=1, answered_on='%s', answered_by='%s' WHERE id='%s'"
                         % (answer.sent_on, answer.sender, id))


########################################################################################################################
def create_question_from_mail(mail):
    """

    :rtype : init.Question
    """
    ret, data = init.conn_imap.fetch(mail, '(INTERNALDATE BODY[HEADER.FIELDS (MESSAGE-ID FROM SUBJECT)])')

    id = re.search('Message-ID: <(.*?)>', data[0][1].decode('utf-8'), re.IGNORECASE).group(1)
    sender = re.search('From: .*? <(.*?)>', data[0][1].decode('utf-8'), re.IGNORECASE).group(1)
    subject = re.search('Subject: ([^\n\r]*)', data[0][1].decode('utf-8'), re.IGNORECASE).group(1)
    is_answered = False
    sent_on = datetime.datetime(*imaplib.Internaldate2tuple(re.search('INTERNALDATE ".*?"', data[0][0].decode('utf-8'))
                                                            .group(0).encode('utf-8'))[:6])
    answered_by = 'NO-ONE'
    answered_on = datetime.datetime(1990, 1, 1)

    return init.Question(id=id, sender=sender, subject = subject, is_answered=is_answered, sent_on=sent_on,
                         answered_by=answered_by, answered_on=answered_on)


########################################################################################################################
def get_all_unanswered():
    return init.session.query(init.Question).filter_by(is_answered=0).all()


########################################################################################################################
def get_all_unanswered_long():
    date = datetime.datetime.now() - timedelta(days = 2)
    return init.session.query(init.Question).filter(init.Question.is_answered == 0, init.Question.sent_on > date).all()



# d = init.connection.uid('fetch', '4019', 'BODY[HEADER.FIELDS (date)]')
# d[1][0][1].decode('utf-8')
# re.search('(?<=Date: \w{3}, ).*\d(?=\s*)', d[1][0][1].decode('utf-8')).group(0)
# re.sub('(?P<g1>\d{2}) (?P<g2>\w{3}) (?P<g3>\d{4})', r'\g<g1>-\g<g2>-\g<g3>', date)
# .encode('utf-8')

#d = init.connection.uid('fetch', '4019', 'INTERNALDATE')
# d[1][0]
# re.search('INTERNALDATE.*(?=\)$)', a)
#init.connection.uid('store', '4032', '+FLAGS', '\Seen')



########################################################################################################################
def main():
    mails = get_new_mails()
    ignore = init.config.get('Ignore', 'ignore').split('\n')


    for mail in mails:
        if len(mail) == 0:
            continue

        print ('Mail: %s' % mail)

        ret, data = init.conn_imap.fetch(mail, 'BODY[HEADER.FIELDS (FROM IN-REPLY-TO)]')
        sender_tmp = re.search('From: .*? <(.*?)>', data[0][1].decode('utf-8'), re.IGNORECASE)
        if sender_tmp != None:
            sender = sender_tmp.group(1)
        else:
            sender = None

        in_reply_to_tmp = re.search('In-Reply-To: <(.*?)>', data[0][1].decode('utf-8'), re.IGNORECASE)
        if in_reply_to_tmp != None:
            in_reply_to = in_reply_to_tmp.group(1)
        else:
            in_reply_to = None
        print('Mail: %s; Sender: %s; IN-REPLY-TO: %s' % (mail, sender, in_reply_to))

        if sender in ignore:
            if in_reply_to != None:
                # case: intern -> extern answer
                question = create_question_from_mail(mail)
                mail_answered(in_reply_to, question)
                print('Answered: %s; Answerer: %s, %s' % (in_reply_to, question.sender, question.id))

        else:
            question = create_question_from_mail(mail)
            add_mail_to_db(question)
            print('Added to DB: %s, %s' % (question.sender, question.id))

        init.conn_imap.uid('store', mail, '+FLAGS', '\Seen')



if __name__ == "__main__":
    main()
