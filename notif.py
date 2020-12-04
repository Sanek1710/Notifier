import requests
import vk_api
import sys
import threading
import os
import json
import time
import datetime
import traceback
from vk_api.longpoll import VkLongPoll, VkEventType
import pymysql.cursors
#events:[userId:str,randomId:str,timestamp:str,message:str,everyYear:bool]
class SqlClient:
    def __init__(self,configFile):
        with open(configFile,'r') as file:
            content = file.read().split(" ")
            host = content[0]
            user = content[1]
            password = content[2]
            db = content[3]
        print (host)
        print(user)
        print(password)
        print (db)
        self.connection = pymysql.connect(host=host,
                             user=user,
                             password=password,
                             db=db,
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
    def addUser(self,userId):
        try:
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO `users` (`userId`) VALUES (%s)"
                cursor.execute(sql, (userId)) 
            self.connection.commit()
        except Exception as e:
            print_tb(e)
            raise(e)
    def addEvent(self,event):
        try:
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO `events` (`userId`, `randomId`, `timestamp`,`message`,`everyYear`) VALUES (%s,%s,%s,%s,%s)"
                cursor.execute(sql, (event['userId'],event['randomId'],event['timestamp'],event['message'],event['everyYear'])) 
            self.connection.commit()
        except Exception as e:
            print_tb(e)
            raise(e)
    def getUsers(self):
        result = []
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT `userId` FROM `users`"
                cursor.execute(sql)
                result = [x['userId'] for x in cursor.fetchall()]
        except Exception as e:
            print_tb(e)
            raise(e)
        return result
def write_msg(user_id,random_id, message):
    vk.messages.send(user_id=user_id,random_id=random_id,message=message)
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
token='9ff67bec81a05eded4e87077f09ec65399d330a0a78e39bba9596c0295ba4c3c757a0ce6004d44f8b3664'

vk_session = vk_api.VkApi(token=token)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()
sqlClient = SqlClient("db.txt")
usersList = sqlClient.getUsers()
print(usersList)

#my_thread = threading.Thread(target=dateChecking)
#my_thread.start()
# Основной цикл
for event in longpoll.listen():
    # Если пришло новое сообщение
    print (event.type)
    if event.type == VkEventType.MESSAGE_NEW:
    
        # Если оно имеет метку для меня( то есть бота)
        if event.to_me:
            if str(event.user_id) in usersList:
                try:
                    request = event.text.split()

                    print(event.user_id,event.random_id)
                    if request[0] == "help":
                        write_msg(event.user_id,event.random_id,getHelpMessage())
                    elif request[0] == "add":
                        dateStr = request[1]
                        timeStr = request[2]
                        newEvent = {}
                        now = datetime.datetime.now()
                        print(now.year)
                        formatString = "%d.%m.%Y %H:%M"
                        datetimeStr = dateStr+ ' ' + timeStr
                        if len(dateStr) > 5:
                            newEvent['everyYear'] = False
                            timestamp = time.mktime(datetime.datetime.strptime(datetimeStr,formatString ).timetuple())
                        else:
                            newEvent['everyYear'] = True
                            checkDateTimeStr = dateStr + '.' + str(now.year) + ' ' + timeStr
                            checkTimestamp = time.mktime(datetime.datetime.strptime(checkDateTimeStr,formatString ).timetuple())
                            if checkTimestamp > now.timestamp():
                                timestamp = checkTimestamp
                            else:
                                checkDateTimeStr = dateStr + '.' + str(now.year + 1) + ' ' + timeStr
                                timestamp = time.mktime(datetime.datetime.strptime(checkDateTimeStr,formatString ).timetuple())                        
                                               
                        del request[0:3]
                        message = (''.join(x + ' ' for x in request))
                        #events:[user_id:str,random_id:str,timestamp:str,message:str,everyYear:bool]
                        newEvent['userId'] = event.user_id
                        newEvent['randomId'] = event.random_id
                        newEvent['timestamp'] = timestamp
                        newEvent['message'] = message[:-1]
                        sqlClient.addEvent(newEvent)             
                        write_msg(event.user_id, event.random_id,'Событие зарегистрировано!')
                    elif request[0] == "print":
                        print(sqlClient.getEventById(event.user_id))
                        write_msg(event.user_id,event.random_id, "Неизвестный формат сообщения")
                    else:
                        write_msg(event.user_id,event.random_id, "Неизвестный формат сообщения")
                except Exception as e:
                    print_tb(e)
                    write_msg(event.user_id,event.random_id,'Что-то пошло не так')
            else:
                write_msg(event.user_id,event.random_id,'И тебе привет! '+ getHelpMessage())
                sqlClient.addUser(event.user_id)
                usersList.append(event.user_id)

