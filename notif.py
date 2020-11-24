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
#fileStructure - savedData_timestampMs_.json
#events:[userId:str,randomId:str,timestamp:str,message:str,everyYear:bool]
class DataStructure:
    def __init__(self):
        self.filepath = 'savedData.json'
        self.usersListPath = 'users.txt'
        self.usersList = self.readUsers(self.usersListPath)
        self.events = self.fromJson(self.filepath)
    def fromJson(self,pathToJson):
        events = []
        try:
            with open(pathToJson,"r",encoding="utf-8") as f:
                for line in [x.strip('\n') for x in f.readlines() if len(x.strip('\n'))>0]:
                    print(len(line))
                #lines = f.readlines()
                #for line in [x[:-1] for x in lines if len(x) > 0]:
                    print("%" + line + "%" )                    
                    jDict =json.loads(line)                    
                    events.append(jDict)
            pass
        except Exception as e:
            print_tb(e)
        return events
    def readUsers(self,path):
        res = []
        try:
            with open(path,'r',encoding="utf-8") as f:
                res = [int(x) for x in f.read().split(',') if x]
                print(res)
        except Exception as e:
            print_tb(e)
        return res
    def update(self,event):
        with open(self.filepath,"a",encoding="utf-8") as f:
            f.write(json.dumps(event,ensure_ascii=False))
            f.write("\n")
    def updateUsers(self,user_id):
        with open(self.usersListPath,"a",encoding="utf-8") as f:
            f.write(str(user_id) + ',')
        self.usersList.append(user_id)
    def getUsers(self):
        return self.usersList
    def getEventsByUser(self,user_id):

def write_msg(user_id,random_id, message):
    vk.messages.send(user_id=user_id,random_id=random_id,message=message)
def print_tb(e):
    print (''.join(traceback.TracebackException.from_exception(e).format()))
def getHelpMessage():
    msg =  'Со мной ты никогда не забудешь поздравить друга с днем рождения или про годовщину свадьбы своих родителей!'
    msg+= '\nЯ понимаю сообщения в следующем формате:\n1)add <date> <message> - Добавить напоминание с сообщением <message> в день <date>'
    msg+= '\n2)delete <date> - Удалить напоминание для дня <date>\n3)delete all - Удалить все напоминания\n4)print - Вывести список всех напоминаний'
    msg+= '\n5)help - вывести это сообщение'
    msg+= '\nФормат даты: DD-MM-YYYY HH:MM или DD-MM HH:MM. В первом случае напоминание сработает только один раз, во втором будет работать каждый год. Указывайте московское время.'
    msg+= '\nПримеры:\nadd 05.02.2021 12:00 День рождения Юли\n25 февраля в 12 часов дня по мск в 2021 году тебе придет напоминание от меня с текстом "Напоминаю: сегодня - День рождения Юли"'
    msg+= '\nadd 29.11 10:00 День матери\nКаждый год 29 ноября в 10 часов дня по мск тебе будет приходить напоминание от меня с текстом "Напоминаю: сегодня - День матери"'
    return msg
token='9ff67bec81a05eded4e87077f09ec65399d330a0a78e39bba9596c0295ba4c3c757a0ce6004d44f8b3664'

vk_session = vk_api.VkApi(token=token)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()
data = DataStructure()
usersList = data.getUsers()
#my_thread = threading.Thread(target=dateChecking)
#my_thread.start()
# Основной цикл
for event in longpoll.listen():
    # Если пришло новое сообщение
    print (event.type)
    if event.type == VkEventType.MESSAGE_NEW:
    
        # Если оно имеет метку для меня( то есть бота)
        if event.to_me:
            if event.user_id in usersList:
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
                        newEvent['user_id'] = event.user_id
                        newEvent['random_id'] = event.random_id
                        newEvent['timestamp'] = timestamp
                        newEvent['message'] = message[:-1]
                        data.update(newEvent)             
                        print("MESSAGE BEFORE")           
                        write_msg(event.user_id, event.random_id,'Событие зарегистрировано!')
                        print("MESSAGE AFTER")           
                    elif request[0] == "print":
                        pass
                    else:
                        write_msg(event.user_id,event.random_id, "Неизвестный формат сообщения")
                except Exception as e:
                    print_tb(e)
                    write_msg(event.user_id,event.random_id,'Что-то пошло не так')
            else:
                write_msg(event.user_id,event.random_id,'И тебе привет! '+ getHelpMessage())
                data.updateUsers(event.user_id)

