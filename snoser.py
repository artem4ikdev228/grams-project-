import smtplib
import requests
import random
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

LOG_CHANNEL_ID = -1002625395986

# Глобальный словарь для хранения статусов почт
EMAIL_STATUSES = {}

# Конфигурация почтовых сервисов
MAIL_SERVICES = {
    'gmail': {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 465,
        'senders': {
            'a9082642549.20@gmail.com': 'ujdt zume gtod yacr',
        }
    },
    'mailru': {
        'smtp_server': 'smtp.mail.ru',
        'smtp_port': 465,
        'senders': {
            'artem_filippov59@mail.ru': 'VtbThJGa9zT4WLTPWLjo',
            'artem_filamon59@mail.ru': 'U6UYwSaliXBv1MmPfggH',
            'artem_filamen59@mail.ru': 'Eu2jIzHFDeEi6cZci7RC',
            'artem_filaman59@mail.ru': 'vHrCl1hy3GxfzgxbIgfi',
            'artem_filamqn59@mail.ru': 'Lrz9dNEyihKjRDqdwIV1',
            'maksim_filamon@mail.ru': '6M2Z1BBAZTFujxcw3jQq',
            'maksim_filaman@mail.ru': '1CfeizeyjMkKT41PbxS6',
            'maksim_filamag@mail.ru': 'uIIRdCIPSAqAmkol9PxV',
            'maksim_filamen@mail.ru': '4dhWthyqqm9ixfTBiDrY',
        }
    }
}

# Инициализация статусов почт
for service_name, service_config in MAIL_SERVICES.items():
    for email in service_config['senders'].keys():
        EMAIL_STATUSES[email] = {'status': 'unknown', 'last_check': None}

phone_numbers_templates = [
    "+7917**11**2",
    "+7926**386**",
    "+7952**99*63",
    "+7903**76*82",
    "+7914**237*7*",
    "+7937**61***",
    "+7978**42***",
    "+7982**89***",
    "+7921**57***",
    "+7991**34***",
    "+7910**68***",
    "+7940**15***",
    "+7961**72***",
    "+7985**49***",
    "+7951**27***",
    "+7916**83***",
    "+7932**95***",
    "+7975**44***",
    "+7989**78***",
    "+7993**64***",
    "+7923**58***",
    "+7970**30***",
    "+7960**17***",
    "+7995**48***",
    "+7953**25***",
    "+7919**77***",
    "+7938**36***",
    "+7986**62***",
    "+7907**81*7*",
    "+7947**53*6*",
    "+7971**29***"
]

receivers = ['sms@telegram.org', 'dmca@telegram.org', 'abuse@telegram.org',
     'sticker@telegram.org', 'support@telegram.org', 'topCA@telegram.org', 'recover@telegram.org', 'ceo@telegram.org']

SEND_DELAY = 0.1
SEND_REPEATS = 1

last_update_cache = {}

class Form(StatesGroup):
    waiting_for_account_info = State()
    waiting_for_complaint_info = State()
    waiting_for_bot_username = State()
    waiting_for_method = State()

def generate_phone_number():
    template = random.choice(phone_numbers_templates)
    return ''.join(random.choice('0123456789') if char == '*' else char for char in template)

def send_web_complaint(complaint_text, phone_number):
    url = "https://telegram.org/support"
    headers = {'content-type': 'application/json'}
    data = {'complaint': complaint_text, 'phone_number': phone_number}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Web complaint error: {e}")
        return False

def method_selection_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📧 Email", callback_data='method_email'))
    builder.row(InlineKeyboardButton(text="🌐 Web", callback_data='method_web'))
    builder.row(InlineKeyboardButton(text="🔥 Все методы", callback_data='method_all'))
    return builder.as_markup()

def main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚨 Snozer", callback_data='snozer'))
    builder.row(
        InlineKeyboardButton(text="🎯 Профиль", callback_data='profile'),
        InlineKeyboardButton(text="‼️ Информация ‼️", callback_data='info')
    )
    return builder.as_markup()

def account_types_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚮 Спам", callback_data='spam'))
    builder.row(InlineKeyboardButton(text="📊 Личные данные", callback_data='personal_data'))
    builder.row(InlineKeyboardButton(text="🤬 Оскорбления", callback_data='abuse'))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data='back'))
    return builder.as_markup()

def channel_types_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Личные данные", callback_data='channel_personal'))
    builder.row(InlineKeyboardButton(text="🔞 Живодерство", callback_data='channel_illegal'))
    builder.row(InlineKeyboardButton(text="🔞 Порнография", callback_data='channel_cp'))
    builder.row(InlineKeyboardButton(text="🛍 Прайсы", callback_data='channel_price'))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data='back'))
    return builder.as_markup()

async def update_progress_message(bot: Bot, chat_id: int, message_id: int, target: str, current: int, total: int, method: str):
    progress = min(int((current / total) * 10), 10)
    progress_bar = '🟢' * progress + '⚪' * (10 - progress)
    percentage = min(int((current / total) * 100), 100)

    new_text = f"Отправка жалоб на {target} ({method})...\n\nПроцесс: {progress_bar} {percentage}%{'​' if current % 2 else ''}"

    cache_key = f"{chat_id}_{message_id}"

    if last_update_cache.get(cache_key) != new_text:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=new_text
            )
            last_update_cache[cache_key] = new_text
        except Exception as e:
            if "message is not modified" not in str(e):
                print(f"Ошибка при обновлении прогресса: {e}")

    if len(last_update_cache) > 100:
        oldest_key = next(iter(last_update_cache))
        last_update_cache.pop(oldest_key)

async def check_email_status(email: str, password: str, smtp_server: str, smtp_port: int):
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email, password)
            EMAIL_STATUSES[email] = {'status': 'active', 'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            return True
    except smtplib.SMTPAuthenticationError:
        EMAIL_STATUSES[email] = {'status': 'dead', 'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        return False
    except Exception as e:
        EMAIL_STATUSES[email] = {'status': 'error', 'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        print(f"Error checking email {email}: {e}")
        return False

async def start_command(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в Grams Project\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard()
    )

async def email_status_command(message: types.Message):
    # Проверяем статусы всех почт
    checking_msg = await message.answer("🔍 Проверяю статусы почтовых аккаунтов...")

    active_count = 0
    dead_count = 0
    error_count = 0

    for service_name, service_config in MAIL_SERVICES.items():
        for email, password in service_config['senders'].items():
            await check_email_status(email, password, service_config['smtp_server'], service_config['smtp_port'])
            status = EMAIL_STATUSES[email]['status']

            if status == 'active':
                active_count += 1
            elif status == 'dead':
                dead_count += 1
            else:
                error_count += 1

    status_text = (
        "📧 Статус почтовых аккаунтов:\n\n"
        f"✅ Активных: {active_count}\n"
        f"❌ Мёртвых: {dead_count}\n"
        f"⚠️ С ошибками: {error_count}\n\n"
        "Для просмотра деталей используйте /email_list"
    )

    await checking_msg.edit_text(status_text)

async def email_list_command(message: types.Message):
    active_emails = []
    dead_emails = []
    error_emails = []

    for email, data in EMAIL_STATUSES.items():
        if data['status'] == 'active':
            active_emails.append(email)
        elif data['status'] == 'dead':
            dead_emails.append(email)
        else:
            error_emails.append(email)

    response = "📧 Список почтовых аккаунтов:\n\n"

    if active_emails:
        response += "✅ Активные:\n" + "\n".join(active_emails) + "\n\n"

    if dead_emails:
        response += "❌ Мёртвые:\n" + "\n".join(dead_emails) + "\n\n"

    if error_emails:
        response += "⚠️ С ошибками:\n" + "\n".join(error_emails)

    await message.answer(response[:4096])  # Ограничение длины сообщения в Telegram

async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'snozer':
        await callback.message.edit_text(
            "🔨 Выберите тип жалобы:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👮‍♂️ Жалоба на аккаунт", callback_data='account'),
                ],
                [
                    InlineKeyboardButton(text="👮‍♂️ Жалоба на канал", callback_data='channel'),
                    InlineKeyboardButton(text="🤖 Жалоба на бота", callback_data='bot'),
                ],
                [
                    InlineKeyboardButton(text="🔙 Назад", callback_data='back_to_main')
                ]
            ])
        )
    elif callback.data == 'profile':
        user_id = callback.from_user.id
        await callback.message.edit_text(
            f"👤 Ваш профиль:\n\n"
            f"ID: {user_id}\n",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data='back_to_main')]
                ])
        )
    elif callback.data == 'info':
        await callback.message.edit_text(
            "ℹ️ Информация о проекте:\n\n"
            "Grams Project - инструмент для очистки Telegram от нарушителей\n"
            "Версия: 1.0\n"
            "Разработчик: (хз)"
        )
    elif callback.data == 'back_to_main':
        await callback.message.edit_text(
            "👋 Добро пожаловать в Grams Project\n\n"
            "Выберите действие:",
            reply_markup=main_menu_keyboard()
        )
    elif callback.data == 'account':
        await callback.message.edit_text(
            "Выберите причину жалобы:",
            reply_markup=account_types_keyboard()
        )
    elif callback.data == 'channel':
        await callback.message.edit_text(
            "Выберите причину жалобы:",
            reply_markup=channel_types_keyboard()
        )
    elif callback.data == 'back':
        await callback.message.edit_text(
            "🔨 Выберите тип жалобы:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👮‍♂️ Жалоба на аккаунт", callback_data='account'),
                    InlineKeyboardButton(text="👮‍♂️ Жалоба на канал", callback_data='channel'),
                    InlineKeyboardButton(text="🤖 Жалоба на бота", callback_data='bot')
                ],
                [
                    InlineKeyboardButton(text="🔙 Назад", callback_data='back_to_main')
                ]
            ])
        )
    elif callback.data in ['spam', 'personal_data', 'abuse']:
        await state.update_data(complaint_type=callback.data)
        await state.set_state(Form.waiting_for_account_info)
        await callback.message.edit_text(
            "Введите username и ID аккаунта через пробел\n"
            "Пример: @username 123456789\n\n"
            "ID можно получить через бота @username_to_id_bot"
        )
    elif callback.data in ['channel_personal', 'channel_illegal', 'channel_cp','channel_price']:
        await state.update_data(complaint_type=callback.data)
        await state.set_state(Form.waiting_for_complaint_info)
        await callback.message.edit_text(
            "Введите ссылку на канал и на нарушение\n"
            "Пример: https://t.me/channel https://t.me/channel/123\n\nТОЛЬКО ПУБЛИЧНЫЕ ССЫЛКИ!!"
        )
    elif callback.data == 'bot':
        await state.set_state(Form.waiting_for_bot_username)
        await callback.message.edit_text(
            "Введите username бота (например @spambot):"
        )
    elif callback.data in ['method_email', 'method_web', 'method_all']:
        await state.update_data(method=callback.data)
        user_data = await state.get_data()

        if 'complaint_type' in user_data:
            # Это жалоба на аккаунт
            if await state.get_state() == Form.waiting_for_method:
                username = user_data['username']
                user_id = user_data['user_id']
                message_link = user_data['message_link']
                complaint_type = user_data['complaint_type']

                subjects = {
                    'spam': "HELP TELEGRAM!",
                    'personal_data': "HELP TELEGRAM!",
                    'abuse': "HELP TELEGRAM!"
                }

                bodies = {
                    'spam': f"Hello, dear support. I found a user on your platform who sends a lot of unnecessary SPAM messages. His username is {username}, his ID is {user_id}, and the link to the violation is {message_link}. Please take action against this user.",
                    'personal_data': f"Hello, dear support, I have found a user on your platform who distributes other people's data without their consent. His username is {username}, his ID is {user_id}, and the link to the violation is {message_link}. Please take action against this user by blocking his account.",
                    'abuse': f"Hello, dear telegram support. I found a user who openly uses obscene language and spams in chat rooms. His username is {username}, his ID is {user_id}, and the link to the violation is {message_link}. Please take action against this user by blocking his account."
                }

                subject = subjects[complaint_type]
                body = bodies[complaint_type]

                sent_count = await send_complaint(
                    subject=subject,
                    body=body,
                    bot=callback.bot,
                    chat_id=callback.message.chat.id,
                    target=username,
                    method=callback.data
                )

                await state.clear()
        elif 'channel_link' in user_data:
            # Это жалоба на канал
            channel_link = user_data['channel_link']
            violation_link = user_data['violation_link']
            complaint_type = user_data['complaint_type']

            subjects = {
                'channel_personal': "HELP TELEGRAM!",
                'channel_illegal': "HELP TELEGRAM!",
                'channel_cp': "HELP TELEGRAM!",
                'channel_price': "HELP TELEGRAM!",
            }

            bodies = {
                'channel_personal': f"Hello, dear telegram support. I found a channel on your platform that distributes the personal data of innocent people. The link to the channel is {channel_link}, and the links to violations are {violation_link}. Please block this channel.",
                'channel_illegal': f"Hello, dear Telegram support. I found a channel on your platform that promotes animal cruelty. The link to the channel is {channel_link}, and the links to violations are {violation_link}. Please block this channel.",
                'channel_cp': f"Hello, dear Telegram support. I found a channel on your platform that distributes pornography involving minors. The link to the channel is {channel_link}, and the links to violations are {violation_link}. Please block this channel.",
                'channel_price': f"Hello, dear telegram moderator, I want to complain to you about a channel that sells doxing and swatting services. Link to the telegram channel:{channel_link} Link to the violation: {violation_link}. Please block this channel."
            }

            subject = subjects[complaint_type]
            body = bodies[complaint_type]

            sent_count = await send_complaint(
                subject=subject,
                body=body,
                bot=callback.bot,
                chat_id=callback.message.chat.id,
                target=channel_link,
                method=callback.data
            )

            await state.clear()
        elif 'bot_username' in user_data:
            # Это жалоба на бота
            bot_username = user_data['bot_username']

            subject = "HELP TELEGRAM!"
            body = f"Hello, dear telegram support. I found a bot on your platform that searches through your users' personal data. The link to the bot is {bot_username}. Please figure it out and block this bot."

            sent_count = await send_complaint(
                subject=subject,
                body=body,
                bot=callback.bot,
                chat_id=callback.message.chat.id,
                target=bot_username,
                method=callback.data
            )

            await state.clear()

async def send_complaint(subject: str, body: str, bot: Bot, chat_id: int, target: str, method: str):
    try:
        user = await bot.get_chat(chat_id)
        username = f"@{user.username}" if user.username else f"ID: {user.id}"

        # Логирование начала сноса
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_msg = (
            f"🚀 Начат снос цели:\n"
            f"👤 Пользователь: {username}\n"
            f"🎯 Цель: {target}\n"
            f"🛠 Метод: {'email' if method == 'method_email' else 'web' if method == 'method_web' else 'все методы'}\n"
            f"⏱ Время начала: {start_time}"
        )
        await bot.send_message(LOG_CHANNEL_ID, start_msg)

        if method == 'method_email':
            # Только email - используем только активные почты
            active_senders = sum(
                1 for service in MAIL_SERVICES.values() 
                for email in service['senders'] 
                if EMAIL_STATUSES.get(email, {}).get('status') == 'active'
            )

            total_sends = active_senders * len(receivers) * SEND_REPEATS
            progress_msg = await bot.send_message(chat_id, f"Отправка email жалоб на {target}...\n\nПроцесс: ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪ 0%")

            sent_count = 0
            for service_name, service_config in MAIL_SERVICES.items():
                for sender_email, sender_password in service_config['senders'].items():
                    # Пропускаем мертвые почты
                    if EMAIL_STATUSES.get(sender_email, {}).get('status') != 'active':
                        continue

                    for receiver in receivers:
                        for attempt in range(SEND_REPEATS):
                            if send_email(
                                receiver=receiver,
                                sender_email=sender_email,
                                sender_password=sender_password,
                                subject=subject,
                                body=body,
                                smtp_server=service_config['smtp_server'],
                                smtp_port=service_config['smtp_port']
                            ):
                                sent_count += 1
                                await update_progress_message(
                                    bot, 
                                    chat_id, 
                                    progress_msg.message_id,
                                    target, 
                                    sent_count, 
                                    total_sends,
                                    "email"
                                )
                                time.sleep(SEND_DELAY)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text=f"‼️ Отправка email жалоб на {target} завершена\n\n✅ Отправлено {sent_count} репортов\n"
                     f"📧 Использовано почт: {active_senders}"
            )

        elif method == 'method_web':
            # Только веб
            total_sends = len(phone_numbers_templates) * 5
            progress_msg = await bot.send_message(chat_id, f"Отправка web жалоб на {target}...\n\nПроцесс: ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪ 0%")

            sent_count = 0
            for template in phone_numbers_templates:
                for attempt in range(5):
                    phone_number = generate_phone_number()
                    if send_web_complaint(body, phone_number):
                        sent_count += 1
                        await update_progress_message(
                            bot,
                            chat_id,
                            progress_msg.message_id,
                            target,
                            sent_count,
                            total_sends,
                            "web"
                        )
                        time.sleep(0.5)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text=f"‼️ Отправка web жалоб на {target} завершена\n\n✅ Отправлено {sent_count} репортов"
            )

        else:
            # Все методы (email + web)
            active_senders = sum(
                1 for service in MAIL_SERVICES.values() 
                for email in service['senders'] 
                if EMAIL_STATUSES.get(email, {}).get('status') == 'active'
            )

            email_total = active_senders * len(receivers) * SEND_REPEATS
            web_total = len(phone_numbers_templates) * 5
            total_sends = email_total + web_total
            progress_msg = await bot.send_message(chat_id, f"Отправка жалоб на {target}...\n\nПроцесс: ⚪⚪⚪⚪⚪⚪⚪⚪⚪⚪ 0%")

            sent_count = 0

            # Отправка email жалоб (только активные)
            for service_name, service_config in MAIL_SERVICES.items():
                for sender_email, sender_password in service_config['senders'].items():
                    # Пропускаем мертвые почты
                    if EMAIL_STATUSES.get(sender_email, {}).get('status') != 'active':
                        continue

                    for receiver in receivers:
                        for attempt in range(SEND_REPEATS):
                            if send_email(
                                receiver=receiver,
                                sender_email=sender_email,
                                sender_password=sender_password,
                                subject=subject,
                                body=body,
                                smtp_server=service_config['smtp_server'],
                                smtp_port=service_config['smtp_port']
                            ):
                                sent_count += 1
                                await update_progress_message(
                                    bot, 
                                    chat_id, 
                                    progress_msg.message_id,
                                    target, 
                                    sent_count, 
                                    total_sends,
                                    "email"
                                )
                                time.sleep(SEND_DELAY)

            # Отправка веб жалоб
            for template in phone_numbers_templates:
                for attempt in range(5):
                    phone_number = generate_phone_number()
                    if send_web_complaint(body, phone_number):
                        sent_count += 1
                        await update_progress_message(
                            bot,
                            chat_id,
                            progress_msg.message_id,
                            target,
                            sent_count,
                            total_sends,
                            "web"
                        )
                        time.sleep(0.5)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text=f"‼️ Отправка жалоб на {target} завершена\n\n"
                     f"✅ Отправлено {sent_count} репортов\n"
                     f"📧 Email: {email_total} (использовано почт: {active_senders})\n"
                     f"🌐 Web: {web_total}"
            )

        # Логирование завершения сноса
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        end_msg = (
            f"✅ Снос завершен:\n"
            f"👤 Пользователь: {username}\n"
            f"🎯 Цель: {target}\n"
            f"📊 Результат: {sent_count} репортов\n"
            f"⏱ Время завершения: {end_time}"
        )
        await bot.send_message(LOG_CHANNEL_ID, end_msg)
        return sent_count

    except Exception as e:
        error_msg = f"❌ Ошибка при отправке жалоб:\n{str(e)}"
        await bot.send_message(chat_id, error_msg)
        await bot.send_message(LOG_CHANNEL_ID, error_msg)
        return 0

def send_email(receiver: str, sender_email: str, sender_password: str, 
              subject: str, body: str, smtp_server: str, smtp_port: int):
    try:
        # Проверяем статус почты перед отправкой
        if EMAIL_STATUSES.get(sender_email, {}).get('status') != 'active':
            return False

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print(f"Email sent from {sender_email} to {receiver} via {smtp_server}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"Authentication failed for {sender_email}: {e}")
        EMAIL_STATUSES[sender_email] = {'status': 'dead', 'last_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        return False
    except Exception as e:
        print(f"Email sending error ({smtp_server}): {str(e)}")
        return False

async def process_account_info(message: types.Message, state: FSMContext):
    try:
        if len(message.text.split()) == 2:
            username, user_id = message.text.split()
            if not username.startswith('@') or not user_id.isdigit():
                raise ValueError

            await state.update_data(username=username, user_id=user_id)
            await message.answer("Теперь введите ссылку на сообщение с нарушением (например, https://t.me/chat/123)\n\nТОЛЬКО ПУБЛИЧНУЮ ССЫЛКУ!!")
            return

        elif await state.get_state() == Form.waiting_for_account_info:
            message_link = message.text
            if not message_link.startswith('https://t.me/'):
                await message.answer("❌ Ссылка должна начинаться с https://t.me/")
                return

            await state.update_data(message_link=message_link)
            await state.set_state(Form.waiting_for_method)
            await message.answer(
                "Выберите метод отправки жалоб:",
                reply_markup=method_selection_keyboard()
            )

    except Exception as e:
        await message.answer("❌ Ошибка формата. Введите username и ID через пробел\nПример: @username 123456789")
        print(f"Error: {e}")

async def process_complaint_info(message: types.Message, state: FSMContext):
    try:
        channel_link, violation_link = message.text.split()
        await state.update_data(channel_link=channel_link, violation_link=violation_link)
        await state.set_state(Form.waiting_for_method)
        await message.answer(
            "Выберите метод отправки жалоб:",
            reply_markup=method_selection_keyboard()
        )

    except Exception as e:
        await message.answer("❌ Ошибка формата. Введите 2 ссылки через пробел")
        print(f"Error: {e}")

async def process_bot_username(message: types.Message, state: FSMContext):
    try:
        bot_username = message.text.strip()
        if not bot_username.startswith('@'):
            await message.answer("❌ Username должен начинаться с @")
            return

        await state.update_data(bot_username=bot_username)
        await state.set_state(Form.waiting_for_method)
        await message.answer(
            "Выберите метод отправки жалоб:",
            reply_markup=method_selection_keyboard()
        )

    except Exception as e:
        await message.answer("❌ Произошла ошибка при обработке запроса")
        print(f"Error: {e}")

async def main():
    
    bot = Bot(token="8120819650:AAEbxgE5CfMjXo6AzZAgZ_gSIhUU2hzWnGg")
    dp = Dispatcher()

    dp.message.register(start_command, Command(commands=["start"]))
    dp.message.register(email_status_command, Command(commands=["email"]))
    dp.message.register(email_list_command, Command(commands=["email_list"]))
    dp.callback_query.register(handle_callback)
    dp.message.register(process_account_info, Form.waiting_for_account_info)
    dp.message.register(process_complaint_info, Form.waiting_for_complaint_info)
    dp.message.register(process_bot_username, Form.waiting_for_bot_username)

    # Проверяем статусы почт при старте
    for service_name, service_config in MAIL_SERVICES.items():
        for email, password in service_config['senders'].items():
            await check_email_status(email, password, service_config['smtp_server'], service_config['smtp_port'])

    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
