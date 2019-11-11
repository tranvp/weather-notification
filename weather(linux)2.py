#coding: utf-8
from cStringIO import StringIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email import Charset
from email.generator import Generator
import smtplib
import urllib2
import string
import MySQLdb
from bs4 import BeautifulSoup
import csv
import datetime

#Read csv file to create a list of email to send notification
emaillist = []
with open('/home/pi/weatheremail.csv', 'r') as f:
    csv_reader = csv.reader(f)
    for row in csv_reader:
        emaillist.append(row[0])

emaillist2 = []
with open('/home/pi/receive_all_weather_email.csv', 'r') as f:
    csv_reader = csv.reader(f)
    for row in csv_reader:
        emaillist2.append(row[0])

#User, password to send mail
emailuser = "weather.hanoi.noc@gmail.com"
emailpassword = "password"
subject = u'NOC Weather Notification'
adminemail = 'phuong.tran@ericsson.com'

#User, password and details to connect to MySQL database
con = MySQLdb.connect(host='localhost', user='prtg', passwd='prtg', db='weatherdata')
cur = con.cursor()
con.set_character_set('utf8')
cur.execute('SET NAMES utf8;')
cur.execute('SET CHARACTER SET utf8;')
cur.execute('SET character_set_connection=utf8;')

def send_html_email(user, pwd, recipient, subject, emailmsg):
    # Example address data
    global sendtoall
    from_address = [u'Weather Information', user]
    TO = recipient if type(recipient) is list else [recipient]

    # Example body
    html = u'Weather Notification :<br><br>'+ emailmsg
    text = u'Weather Notification'
 
    # Default encoding mode set to Quoted Printable. Acts globally!
    Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
 
    # 'alternative’ MIME type – HTML and plain text bundled in one e-mail message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "%s" % Header(subject, 'utf-8')
    # Only descriptive part of recipient and sender shall be encoded, not the email address
    msg['From'] = "\"%s\" <%s>" % (Header(from_address[0], 'utf-8'), from_address[1])
    #msg['To'] = "\"%s\" <%s>" % (Header(recipient[0], 'utf-8'), recipient[1])
    msg['To'] = ""
    if sendtoall == 1:
        for i in xrange(len(recipient)):
            msg['To'] = msg['To'] + str(recipient[i]) +";"
    else:
        msg['To'] = adminemail
        
    # Attach both parts
    htmlpart = MIMEText(html, 'html', 'UTF-8')
    textpart = MIMEText(text, 'plain', 'UTF-8')
    msg.attach(htmlpart)
    msg.attach(textpart)
 
    # Create a generator and flatten message object to 'file’
    str_io = StringIO()
    g = Generator(str_io, False)
    g.flatten(msg)
    # str_io.getvalue() contains ready to sent message
 
    #  Send it – using python's smtplib
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(user,pwd)
    s.sendmail(user, TO, str_io.getvalue())

##### MAIN PROGRAM
# Fetch URL
url = 'http://www.nchmf.gov.vn/web/vi-VN/43/Default.aspx'
request = urllib2.Request(url)
request.add_header('Accept-Encoding', 'utf-8')

# Response has UTF-8 charset header,
# and HTML body which is UTF-8 encoded
try:
    response = urllib2.urlopen(request)
except urllib2.URLError:
    response = ""

    # Parse weather website with BeautifulSoup
soup = BeautifulSoup(response.read().decode('utf-8', 'ignore'),"html.parser")
s = (soup.find('a', class_='tieude_tintuc')).encode('utf-8')
s = string.replace(s,"/web","http://www.nchmf.gov.vn/web")
s = string.replace(s,"/Web","http://www.nchmf.gov.vn/web")
emailmsg = unicode(s, "utf-8")

checkword = u'BÃO'
#checkword = u'MƯA'
if checkword in emailmsg :
    sendtoall = 1
else :
    sendtoall = 0

#Put debug values to database
query = "INSERT INTO debugtable(dateandtime,debugresulttext) VALUES(NOW(),%s)"
args = (s)
cur.execute(query, args)
con.commit()

#Take last time data from database
query = "SELECT dateandtime,weatherresulttext from weatherresult ORDER BY dateandtime DESC LIMIT 1"
lasttext = ""
lastdatetime = datetime.datetime.now()
cur.execute(query)
for row in cur.fetchall():
    lasttext = row[1]
    lastdatetime = row[0]

#If nothing in database or last result is different with current result, send mail and update database
if (lasttext == "") or (response <> "" and lasttext <> s) :
    currenttime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emailmsg = emailmsg + "<br><br>" +"Data updated: " +str(currenttime)
    if sendtoall == 1 :
        send_html_email(emailuser, emailpassword, emaillist, subject, emailmsg)
    else:
        send_html_email(emailuser, emailpassword, emaillist2, subject, emailmsg)
    query = "INSERT INTO weatherresult(dateandtime,weatherresulttext) VALUES(NOW(),%s)"
    args = (s)
    cur.execute(query, args)
    con.commit()
    
#If no data for 24 hour, send Heartbeat email and insert record to database
if (lasttext == s or response == "") and (abs(datetime.datetime.now() - lastdatetime) > datetime.timedelta(hours=24)):
    currenttime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emailmsg = "Information: No data in last 24 hours" + "<br><br>" +str(currenttime)
    send_html_email(emailuser, emailpassword, adminemail, subject, emailmsg)
    query = "INSERT INTO weatherresult(dateandtime,weatherresulttext) VALUES(NOW(),%s)"
    args = ("Heartbeat")
    cur.execute(query, args)
    con.commit()
