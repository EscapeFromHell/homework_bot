import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        chat_id = TELEGRAM_CHAT_ID
        text = message
        bot.send_message(chat_id, text)
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Получение ответа от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    hw_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    response = hw_statuses.json()
    if hw_statuses.status_code != 200:
        raise logging.error('Ошибка при обращении к API Практикум.Домашка')
    return response


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка типа данных в response')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Ошибка типа данных переменной homeworks')
    if len(homeworks) != 0:
        return homeworks
    else:
        raise IndexError('Список работ пуст')


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('Ошибка типа данных переменной homework')
    if not homework['homework_name']:
        logging.error('Отсутствие ключа homework_name в ответе API')
        raise KeyError('Отсутствие ключа homework_name в ответе API')
    if not homework['status']:
        logging.error('Отсутствие ключа status в ответе API')
        raise KeyError('Отсутствие ключа status в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
    else:
        logging.error('Недокументированный статус домашней работы')
        raise AttributeError('Недокументированный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    tokens = True
    if PRACTICUM_TOKEN is None:
        tokens = False
    if TELEGRAM_TOKEN is None:
        return False
    if TELEGRAM_CHAT_ID is None:
        return False
    return tokens


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME
    temp_error = None
    if check_tokens() is False:
        raise logging.critical('Ошибка токенов')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            current_timestamp = response.get(
                'current_date', current_timestamp
            )
            for hw in homework:
                message = parse_status(hw)
                send_message(bot, message)
            logging.info('Сообщение отправлено')
        except IndexError:
            logging.debug('Список работ пуст')
        except Exception as error:
            if temp_error is None:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                temp_error = error
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
