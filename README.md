# Notifier
Бот для vk.com позволяющий регистрировать уведомления
https://vk.com/notifier144
## Использование
Запуск скрипта notif.py:
```python
python3 notif.py --token=groupToken --config=pathToConfig
```
## Формат конифга для бд
Конфиг хранится в формате ini
В начале должна быть секция DB
```ini
[DB]
host=host
user=user
password=password
db=dbname

[Server]
maxEventsPerUser=10
maxEventsPerUser=50
maxSymbolsPerMessage=100
```
## TODO
1) Добавить команду add default для стандартных праздников
2) Описать формат базы данных
