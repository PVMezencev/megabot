## Бот Телеграм, который будет выполнять задачи из вашего собственного файла entry-point.py.

#### Описание:
```text
За основу можно взять файл examples/entry-point-example.py. 
Бот принимает любой текст, в качестве аргументов передаёт его в entry-point.py, 
полученный результат возвращает пользователю.
Опишите свою логику на Python по шаблону examples/entry-point-example.py и отправьте этот файл боту, 
он примет его и будет выполнять команды только для вас.
```

#### Требования:
```text
python > 3.10
aiogram ~ 2.25.1
```

#### Установка:
 ```bash
 # Клонируем репозиторий себе инструментами git, либо скачиваем ZIP:
 git clone git@github.com:PVMezencev/megabot.git && cd megabot/
 # Создаем файл конфигурации на основе шаблона, заполняем своими данными.
 cp examples/config-megabot.example.yml config-megabot.yml
 ```


#### Настройки:
* bot - `строка` укажите токен бота 
* users - `список строк` список TelegramID пользователей
