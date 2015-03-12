#!/usr/bin/env python3

import init
import datetime
from datetime import timedelta
import re
import imaplib
from email.mime.text import MIMEText
import time

########################################################################################################################
def get_id(data):
    return re.search('Message-ID: <(.*?)>', data[0][1].decode('utf-8'), re.IGNORECASE).group(1)

def get_sender(data):
    return get_mail_entry('From', data[0][1].decode('utf-8'))
    
def get_receiver(data):
    return get_mail_entry('To', data[0][1].decode('utf-8'))
	
def get_subject(data):
    return re.search('Subject: ([^\n\r]*)', data[0][1].decode('utf-8'), re.IGNORECASE).group(1)
    
def get_in_reply_to(data):
    in_reply_to_tmp = re.search('In-Reply-To: <(.*?)>', data[0][1].decode('utf-8'), re.IGNORECASE)
    if in_reply_to_tmp != None:
        return in_reply_to_tmp.group(1)
    else:
        return None

def get_sent_on(data):
    return datetime.datetime(*imaplib.Internaldate2tuple(re.search('INTERNALDATE ".*?"', data[0][0].decode('utf-8'))
                                                            .group(0).encode('utf-8'))[:6])
                                                            
def get_mail_entry(name, data):
	# matches the name followed by a colon, then some stuff until the email starts with either
	# a space or a smaller than the group mail is called mail the string ends with a greater than if there 
	# was a smaller, otherwise with nothing
	return re.search('%s:(?:.|\s)*?(?:(?P<gt><)| )(?P<mail>[^\s<]+@[^\s>]+)(?(gt)>)' % name, data, re.IGNORECASE).group('mail')

	
########################################################################################################################
def get_params(data, command):
    res = re.search('^%s: (.*)$' % command, data)
    if res == None:
        return []
    
    return re.split(',\s*', res.group(1))
    
	
########################################################################################################################                                                            
def execute_command(command):
    if command == 'UPDATEIGNORE':
        debug_msg = MIMEText('')
        debug_msg['Subject'] = init.config.get('Ignore', 'ignore_update_subject')
        debug_msg['From'] = '<' + init.config.get('Smtp', 'self_mail') + '>'
        debug_msg['To'] = '<' + init.config.get('Ignore', 'ignore_update_mail') + '>'
        init.conn_smtp.sendmail(init.config.get('Smtp', 'self_mail'), init.config.get('Ignore', 'ignore_update_mail'), debug_msg.as_string())
        time.sleep(30)
        
        ret, mails = init.conn_imap.search(None, 'UNSEEN', 'FROM '+init.config.get('Smtp', 'mailinglist_owner'), 'TO '+init.config.get('Smtp', 'self_mail'))
        print (mails)
        if len(mails[0]) == 0:
            print ('DID NOT RECEIVE IGNORE')
            
        mails = mails[0].decode('utf-8').split(' ')[0]
        
        text = init.conn_imap.fetch(mails, 'BODY.PEEK[TEXT]')
        init.conn_imap.uid('store', mails, '+FLAGS', '\Seen')

        res = re.search('((?:[^\s]+@[^\s]+\s+)+)', text[1][0][1].decode('utf-8')).group(0) 

        init.config.set('Ignore', 'ignore_auto', re.sub('\s+', ' ', res))
        
        print(re.sub('\s+', ' ', res))
        init.save_config()
        
    elif command.startswith('DELETE: '):
        res = get_params(command, 'DELETE')
        for id in res:
            del_mail_from_db(id)
    elif command.startswith('ADDIGNORE: '):
        res = get_params(command, 'ADDIGNORE')
         
        for id in res:
            init.config.set('Ignore', 'ignore_manual', init.config.get('Ignore', 'ignore_manual') + ' ' + id)
            init.save_config()

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
    test = init.session.query(init.Question).get(question.id)
    if  test == None:
        init.session.add(question)
        init.session.commit()
    else:
        print ('Attention: %s already in db as %s' % (question, test))
    
    
########################################################################################################################
def del_mail_from_db(mail_id):
    init.session.execute("DELETE FROM questions WHERE id='%s'" % mail_id)


########################################################################################################################
def mail_answered(id, answer): # message_id of mail that was answered, answer as Question object
    init.session.execute("UPDATE questions SET is_answered=1, answered_on='%s', answered_by='%s' WHERE id='%s'"
                         % (answer.sent_on, answer.sender, id))


########################################################################################################################
def create_question_from_mail(mail):
    """

    :rtype : init.Question
    """
    ret, data = init.conn_imap.fetch(mail, '(INTERNALDATE BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM SUBJECT)])')

    id = get_id(data)
    sender = get_sender(data)
    subject = get_subject(data)
    is_answered = False
    sent_on = get_sent_on(data)
    
    answered_by = 'NO-ONE'
    answered_on = datetime.datetime(1990, 1, 1)

    return init.Question(id=id, sender=sender, subject = subject, is_answered=is_answered, sent_on=sent_on,
                         answered_by=answered_by, answered_on=answered_on)


########################################################################################################################
def get_all_unanswered():
    return init.session.query(init.Question).filter_by(is_answered=0).all()


########################################################################################################################
def get_all_unanswered_long():
    """

    :rtype : list
    """
    date = datetime.datetime.now() - timedelta(days = 2)
    return init.session.query(init.Question).filter(init.Question.is_answered == 0, init.Question.sent_on < date).all()



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
    ignore = init.config.get('Ignore', 'ignore_auto').split(' ')
    ignore.extend(init.config.get('Ignore', 'ignore_manual').split(' '))

    debug = ('Time: %s, Mails: %s' % (datetime.datetime.now(), mails))

    for mail in mails:
        print ('Mail: %s, %d' % (mail, len(mail)))
        if len(mail) == 0:
            continue

        debug += ('Mail: %s\n' % mail)

        ret, data = init.conn_imap.fetch(mail, 'BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT IN-REPLY-TO)]')
        sender = get_sender(data)
        in_reply_to = get_in_reply_to(data)
        receiver = get_receiver(data)
        subject = get_subject(data)

        debug += ('Mail: %s; Sender: %s; IN-REPLY-TO: %s\n' % (mail, sender, in_reply_to))

        if sender in ignore:
            if in_reply_to != None:
                # case: intern -> extern answer
                question = create_question_from_mail(mail)
                mail_answered(in_reply_to, question)
                debug += ('Answered: %s; Answerer: %s, %s\n' % (in_reply_to, question.sender, question.id))
            elif receiver == init.config.get('Smtp', 'self_mail'):
                debug += ('Command: %s' % subject)
                execute_command(subject)
                
        else:
            question = create_question_from_mail(mail)
            add_mail_to_db(question)
            debug += ('Added to DB: %s, %s\n' % (question.sender, question.id))

        print ('Setting seen flag of %s' % mail)
        init.conn_imap.uid('store', mail, '+FLAGS', '\Seen')

    debug_msg = MIMEText(debug)
    debug_msg['Subject'] = 'MAILCHECKER DEBUG'
    debug_msg['From'] = '<' + init.config.get('Smtp', 'self_mail') + '>'
    debug_msg['To'] = '<' + init.config.get('Smtp', 'debug_mail') + '>'
    init.conn_smtp.sendmail(init.config.get('Smtp', 'self_mail'), init.config.get('Smtp', 'debug_mail'), debug_msg.as_string())


    unanswered = get_all_unanswered()
    master_txt = 'List of unanswered messages:\n'
    for question in unanswered:
        master_txt += question.__repr__() + '\n'

    master_msg = MIMEText(master_txt)
    master_msg['Subject'] = '[Bits] DAILY ANSWER STATUS'
    master_msg['From'] = '<' + init.config.get('Smtp', 'self_mail') + '>'
    master_msg['To'] = '<' + init.config.get('Smtp', 'master_mail') + '>'
    init.conn_smtp.sendmail(init.config.get('Smtp', 'self_mail'), [init.config.get('Smtp', 'debug_mail'),init.config.get('Smtp', 'debug_mail')] , master_msg.as_string())


    unanswered_long = get_all_unanswered_long()
    if len(unanswered_long) > 0:
        mailinglist_txt = 'List of messages not answered for more than 2 days:\n'
        for question in unanswered:
            mailinglist_txt += question.__repr__() + '\n'

        mailinglist_msg = MIMEText(mailinglist_txt)
        mailinglist_msg['Subject'] = '[Bits] ANSWER!'
        mailinglist_msg['From'] = '<' + init.config.get('Smtp', 'self_mail') + '>'
        mailinglist_msg['To'] = '<' + init.config.get('Smtp', 'mailinglist') + '>'
        init.conn_smtp.sendmail(init.config.get('Smtp', 'self_mail'), init.config.get('Smtp', 'debug_mail'), mailinglist_msg.as_string())

    init.conn_imap.logout()
    init.conn_smtp.close()
    init.session.close()


# from email.mime.text import MIMEText
# msg = MIMEText(CONTENT)
# msg['Subject'] = SUBJECT
# init.conn_smtp.sendmail('kloiber@htu.tugraz.at', 'kloiber@htu.tugraz.at', msg.as_string())
if __name__ == "__main__":
    main()
