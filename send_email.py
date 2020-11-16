import datetime as dt
import time
import smtplib

def send_email():
    email_user = 'myemail@gmail.com'
    server = smtplib.SMTP ('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_user, 'email pass')

    #EMAIL
    message = 'sending this from python!'
    server.sendmail(email_user, email_user, message)
    server.quit()

send_time = dt.datetime(2018,8,26,3,0,0) # set your sending time in UTC
time.sleep(send_time.timestamp() - time.time())
send_email()
print('email sent')