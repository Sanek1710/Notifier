import requests
import vk_api
import sys
from threading import Thread, Lock
import os
import time
import datetime
import traceback
from vk_api.longpoll import VkLongPoll, VkEventType
import pymysql.cursors
import argparse
def exceptionDecorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print_tb(e)
            raise (e)
    return wrapper
@exceptionDecorator
def sendNotifies(events):
    for event in events:
        write_msg(event["userId"],event["randomId"],"Напоминаю: сегодня -" + event["message"])

def notifierThread(nextTimeNotify,sqlClient,lock):
    while True:
        lock.acquire()
        if datetime.datetime.now().timestamp() >= nextTimeNotify[0]:
            try:
                events = sqlClient.getEventsByTimestamp(nextTimeNotify[0])
                sendNotifies(events)
                sqlClient.clearEventsByEvents(events)
                nextTimeNotify[0] = sqlClient.getMinTimestamp()
            except Exception as e:
                print_tb(e)
                pass
        lock.release()
        time.sleep(1)

class SqlClient:
    def __init__(self,configFile):
        with open(configFile,'r') as file:
            content = file.read().split(" ")
            host = content[0]
            user = content[1]
            password = content[2]
            db = content[3]
        self.connection = pymysql.connect(host=host,
                             user=user,
                             password=password,
                             db=db,
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
    @exceptionDecorator
    def addUser(self,userId):
        with self.connection.cursor() as cursor:
            sql = "INSERT INTO `users` (`userId`) VALUES (%s)"
            cursor.execute(sql, (userId)) 
        self.connection.commit()
    @exceptionDecorator
    def addEvent(self,event):
        with self.connection.cursor() as cursor:
            sql = "INSERT INTO `events` (`userId`, `randomId`, `timestamp`,`message`,`everyYear`) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql, (event['userId'],event['randomId'],event['timestamp'],event['message'],event['everyYear'])) 
        self.connection.commit()
    @exceptionDecorator
    def getUsers(self):
        result = []
        with self.connection.cursor() as cursor:
            sql = "SELECT `userId` FROM `users`"
            cursor.execute(sql)
            result = [x['userId'] for x in cursor.fetchall()]
        return result
    @exceptionDecorator
    def getEventByUserId(self, userId):
        result = []
        with self.connection.cursor() as cursor:
            sql = "SELECT * FROM `events` WHERE userID=%s"
            cursor.execute(sql,(str(userId)))
            result = cursor.fetchall()
        return result  
    @exceptionDecorator      
    def getEventsByTimestamp(self,timestamp):   
        result = []
        with self.connection.cursor() as cursor:
            sql = "SELECT * FROM `events` WHERE timestamp=%s"
            cursor.execute(sql,(str(timestamp)))
            result = cursor.fetchall()
        return result 
    @exceptionDecorator
    def clearEventsByEvents(self,events):
        with self.connection.cursor() as cursor:
            sqlDel = "DELETE FROM `events` WHERE id=%s"
            sqlUpdate = "UPDATE `events` SET timestamp = %s WHERE id=%s"
            for event in events:
                if event["everyYear"] == False:
                    cursor.execute(sqlDel, (event["id"])) 
                else:
                    startDate =  datetime.datetime.fromtimestamp(event["timestamp"])
                    newDate = startDate.replace(startDate.year + 1)
                    newTimestamp =newDate.timestamp()
                    cursor.execute(sqlUpdate, (newTimestamp,event["id"])) 
        self.connection.commit()
    @exceptionDecorator
    def clearEventsByTimestamp(self,timestamp,userId):
        with self.connection.cursor() as cursor:
            sqlDel = "DELETE FROM `events` WHERE id=%s and timestamp=%s"
            cursor.execute(sqlDel, (userId,timestamp)) 
        self.connection.commit()
    @exceptionDecorator
    def clearAllEvents(self,userId):
        with self.connection.cursor() as cursor:
            sqlDel = "DELETE FROM `events` WHERE id=%s"
            cursor.execute(sqlDel, (userId)) 
        self.connection.commit()
    @exceptionDecorator
    def getMinTimestamp(self):
        with self.connection.cursor() as cursor:
            sql = "SELECT MIN(timestamp) as min_timestamp FROM `events`"
            cursor.execute(sql)
            result = cursor.fetchone()
            return result['min_timestamp']
        self.connection.commit()   
def write_msg(user_id,random_id, message):
    vk.messages.send(user_id=user_id,random_id=random_id,message=message)
    print("Sending to user=" + str(user_id) + " message " + message)
def print_tb(e):
    print (''.join(traceback.TracebackException.from_exception(e).format()))
def getHelpMessage():
    msg =  'Со мной ты никогда не забудешь поздравить друга с днем рождения или про годовщину свадьбы своих родителей!'
    msg+= '\nЯ понимаю сообщения в следующем формате:\n1)add <date> <message> - Добавить напоминание с сообщением <message> в день <date>'
    msg+= '\n2)delete <date> - Удалить напоминание для дня <date>\n3)delete all - Удалить все напоминания\n4)print - Вывести список всех напоминаний'
    msg+= '\n5)help - вывести это сообщение'
    msg+= '\nФормат даты: DD.MM.YYYY HH:MM или DD.MM HH:MM. В первом случае напоминание сработает только один раз, во втором будет работать каждый год. Указывайте московское время.'
    msg+= '\nПримеры:\nadd 05.02.2021 12:00 День рождения Юли\n25 февраля в 12 часов дня по мск в 2021 году тебе придет напоминание от меня с текстом "Напоминаю: сегодня - День рождения Юли"'
    msg+= '\nadd 29.11 10:00 День матери\nКаждый год 29 ноября в 10 часов дня по мск тебе будет приходить напоминание от меня с текстом "Напоминаю: сегодня - День матери"'
    return msg
def userInputToTimestamp(dateStr,timeStr):
    now = datetime.datetime.now()
    formatString = "%d.%m.%Y %H:%M"
    datetimeStr = dateStr+ ' ' + timeStr
    if len(dateStr) > 5:
        newEvent['everyYear'] = False
        timestamp = dateToTimestamp(datetimeStr,formatString)
    else:
        newEvent['everyYear'] = True
        checkDateTimeStr = dateStr + '.' + str(now.year) + ' ' + timeStr
        checkTimestamp = dateToTimestamp(checkDateTimeStr,formatString)
        if checkTimestamp > now.timestamp():
            timestamp = checkTimestamp
        else:
            checkDateTimeStr = dateStr + '.' + str(now.year + 1) + ' ' + timeStr
            timestamp =dateToTimestamp(checkDateTimeStr,formatString)
    return timestamp                                                    
def formatEvents(events):
    resStr = ""
    index = 1
    for event in events:
        resStr += (str(index) + ") " + timestampToDate(event["timestamp"]) + " " + event["message"] + '\n')
        index += 1
    return resStr
def timestampToDate(timestamp):
    return str(datetime.datetime.fromtimestamp(timestamp))
def dateToTimestamp(dateTimeStr,formatString):
    try:
        return time.mktime(datetime.datetime.strptime(dateTimeStr,formatString).timetuple())
    except ValueError as e:
        print_tb(e)
        raise ValueError("Неверный формат даты")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', type=str,
                        help='your vk group token')
    parser.add_argument('--dbConfig',
                        help='path to config db file')
    args = parser.parse_args()
    vk_session = vk_api.VkApi(token=args.token)
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()
    sqlClient = SqlClient(args.dbConfig)
    usersList = sqlClient.getUsers()
    lock = Lock()
    nextTime =[]
    minTime = int(sqlClient.getMinTimestamp())
    nextTime.append(minTime)
    notifierWorker = Thread(target=notifierThread,args=(nextTime,sqlClient,lock,))
    notifierWorker.start()
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if str(event.user_id) in usersList:
                        try:
                            request = event.text.split()
                            if request[0] == "help":
                                write_msg(event.user_id,event.random_id,getHelpMessage())
                            elif request[0] == "add":
                                newEvent = {}
                                dateStr = request[1]
                                timeStr = request[2]
                                timestamp = userInputToTimestamp(dateStr,timeStr)
                                del request[0:3]
                                message = (''.join(x + ' ' for x in request))
                                newEvent['userId'] = event.user_id
                                newEvent['randomId'] = event.random_id
                                newEvent['timestamp'] = timestamp
                                newEvent['message'] = message[:-1]
                                sqlClient.addEvent(newEvent)
                                lock.acquire()
                                nextTime[0] = sqlClient.getMinTimestamp()
                                lock.release()             
                                write_msg(event.user_id, event.random_id,'Событие зарегистрировано!')
                            elif request[0] == "print":
                                write_msg(event.user_id,event.random_id,"Зарегистрированные события:\n" + formatEvents(sqlClient.getEventByUserId(event.user_id)))
                            elif request[0] == "delete":
                                if request[1] == "all":
                                    sqlClient.clearAllEvents(event.user_id)
                                    write_msg(event.user_id,event.random_id, "Все события удалены!")
                                else:
                                    dateStr = request[1]
                                    timeStr = request[2]
                                    timestamp = userInputToTimestamp(dateStr,timeStr)
                                    sqlClient.clearEventsByTimestamp(timestamp,event.user_id)
                                    write_msg(event.user_id,event.random_id, "Событие удалено!")                                                          
                            else:
                                write_msg(event.user_id,event.random_id, "Неизвестный формат сообщения")
                        except ValueError as e:
                            write_msg(event.user_id,event.random_id,str(e))
                        except Exception as e:
                            print_tb(e)
                            write_msg(event.user_id,event.random_id,'Что-то пошло не так')
                    else:
                        write_msg(event.user_id,event.random_id,'И тебе привет! '+ getHelpMessage())
                        sqlClient.addUser(event.user_id)
                        usersList.append(str(event.user_id))
        except Exception as e:
            print_tb(e)

