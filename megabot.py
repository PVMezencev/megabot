import asyncio
import os
import re
import sys
from datetime import datetime

import yaml
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import BotCommand, ContentType

# Специальная обёртка для исключения, чтоб завершить все асинхронные задачи.
from aiogram.utils.exceptions import RetryAfter


class CheckAccess(BaseMiddleware):
    users = []

    def __init__(self, users):
        self.users = users
        super(CheckAccess, self).__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        if f'{message.chat.id}' not in self.users:
            print(
                f'{datetime.utcnow().isoformat(sep="T")}: пресечение попытки несанкционированного доступа пользователем {message.from_user.id} из чата {message.chat.id}')
            raise CancelHandler()


class ErrorThatShouldCancelOtherTasks(Exception):
    pass


# Хендлер приёма файлов.
async def doc_handler(message: types.Message):
    doc_id = message.document.file_id
    doc_name = message.document.file_name
    ex_fn = ''
    try:
        ex_fn = doc_name.split('.')[-1].lower()
    except:
        pass
    doc_size = message.document.file_size
    doc_type = message.document.mime_type
    print(message, doc_type)
    # ВАЖНО! - если файл не текстовый, то decode упадет с исключением.
    doc_type_arr = ['text/csv', 'text/plain', 'text/x-python']
    doc_ex_arr = ['txt', 'ssim', 'py']
    if doc_type not in doc_type_arr or ex_fn not in doc_ex_arr:
        await message.answer('Неверный типчик  файла')
    else:
        # Получить файл телеграмного типа.
        file = await bot.get_file(doc_id)
        # Загрузить файл в работу (открыть для чтения).
        content_downloaded = await bot.download_file(file.file_path)
        # Получить содержимое (в виде массива байт).
        content = content_downloaded.read()
        # Закрыть файловый дескриптор.
        content_downloaded.close()
        # Вывод тех информации.
        print(f'Имя файла: {doc_name}')
        print(f'Размер файла: {doc_size}')
        print(f'Тип файла: {doc_type}')

        # Выясним наиболее приемлемое обозначение автора файла.
        author = message.from_user.full_name
        if author == '':
            author = message.from_user.first_name
        if author == '':
            author = message.from_user.username
        if author == '':
            author = f'не определён, но его чат: {message.from_user.id}'

        # Вывод тех информации.
        print(f'Отправитель: {author}')

        # Удалить сообщение с файлом из чата.
        # await message.delete()
        # await message.answer('Файл удален')

        # Что-то ответить пользователю.
        await message.answer(f'Имя файла: {doc_name}\n'
                             f'Размер файла: {doc_size / 1000} kB\n'
                             f'Тип файла: {doc_type}\n'
                             f'Отправитель: {author}\n'
                             f'Ом-ном-ном-ном... спасибо, файл съеден!')

        if ex_fn == 'py':
            wc = os.getcwd()
            exec_script_path_dir = os.path.join(wc, 'scripts', f'{message.from_user.id}')
            if not os.path.exists(exec_script_path_dir):
                try:
                    os.makedirs(name=exec_script_path_dir, mode=0o775)
                except Exception as e:
                    await message.answer(f'!!!Ошибка: {e}')
                    return
            exec_script_path = os.path.join(exec_script_path_dir, 'entry-point.py')
            try:
                with open(exec_script_path, 'wb') as fn:
                    fn.write(content)
            except Exception as e:
                await message.answer(f'!!!Ошибка: {e}')
                return
        else:
            await message.answer(f'меня не учили обрабатывать файлы {doc_name}')


async def cmd_me_handler(message: types.Message):
    await message.answer(f'Мой TelegramID: `{message.from_user.id}`\nTelegramID чата: `{message.chat.id}`',
                         parse_mode=types.ParseMode.MARKDOWN_V2)


async def main_handler(message: types.Message):
    result = await exec_cmd(message.text, message.from_user.id)

    await message.answer(result)


async def exec_cmd(data, user_id) -> str:
    exec_script_path = os.path.join('scripts', f'{user_id}', 'entry-point.py')
    if not os.path.exists(exec_script_path):
        exec_script_path = os.path.join('examples', 'entry-point-example.py')
    python_interpreter = 'python'

    cwd = os.path.dirname(exec_script_path)
    script_name = os.path.basename(exec_script_path)

    proc = await asyncio.create_subprocess_exec(
        python_interpreter, '-u', script_name, data,
        limit=1024 * 512,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    result = ''
    while True:
        data = await proc.stdout.readline()
        if not data:
            err = await proc.stderr.readline()
            if err:
                result += err.decode() + '\n'
                continue
            break
        result += data.decode() + '\n'

    await proc.wait()

    return result


# Регистрация команд, отображаемых в интерфейсе Telegram
async def set_commands(b: Bot):
    commands = [
        BotCommand(command="/me", description="Показать информацию обо мне"),
    ]
    await b.set_my_commands(commands)


def register_handlers(d: Dispatcher):
    d.register_message_handler(cmd_me_handler, commands=['me'])
    d.register_message_handler(doc_handler, content_types=ContentType.DOCUMENT)
    d.register_message_handler(main_handler)


async def bot_command_handler(d: Dispatcher, users: list):
    register_handlers(d)
    d.middleware.setup(CheckAccess(users))

    await set_commands(d.bot)

    while True:
        try:
            await d.start_polling()
        except (KeyboardInterrupt, SystemExit, RuntimeError) as e:
            break
        except RetryAfter as e:
            print(f'{datetime.utcnow().isoformat(sep="T")}: disp.start_polling() RetryAfter {e}')
            to_sleeps = re.findall(r'(\d+)', f'{e}')
            if len(to_sleeps) != 0:
                to_sleep = to_sleeps[0]
                await asyncio.sleep(int(to_sleep))
        except Exception as e:
            print(f'{datetime.utcnow().isoformat(sep="T")}: disp.start_polling(): {e}')
            await asyncio.sleep(2)
        raise ErrorThatShouldCancelOtherTasks


# Главная функция.
async def main(users_list: list, d: Dispatcher = None, cycle=False):
    tasks = []
    if d is not None:
        tasks.append(asyncio.create_task(bot_command_handler(d, users_list)))

    try:
        await asyncio.gather(*tasks)
    except ErrorThatShouldCancelOtherTasks:
        for t in tasks:
            t.cancel()
    finally:
        if d is not None:
            s = await d.bot.get_session()
            await s.close()


# Константы.
CFG_PATH = 'config-megabot.yml'

# Начало выполнения.
if __name__ == '__main__':
    try:
        with open(CFG_PATH, 'r') as yml_file:
            CFG = yaml.load(yml_file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        sys.exit(f'Укажите файл конфигурации {CFG_PATH}')

    bot = Bot(token=CFG.get('bot'))
    disp = Dispatcher(bot)

    users_list = [u.strip() for u in CFG.get('users') if u.strip() != ""]

    try:
        asyncio.run(main(users_list, disp))
    except KeyboardInterrupt:
        sys.exit(0)
