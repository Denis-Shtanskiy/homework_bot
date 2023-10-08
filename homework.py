import logging
import os
import sys
import time
import requests
from http import HTTPStatus

import telegram
from dotenv import load_dotenv

from exceptions import (
    EndpointErrorException,
    MissingEnvoirmentVariablesException,
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRAKTIKUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s, %(levelname)s, %(message)s",
    stream=logging.StreamHandler(sys.stdout),
)


RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS: dict[str, str] = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS: dict[str, str] = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens() -> bool:
    """This function is checking the availability of environment variables"""
    variable_data: dict[str, str] = {
        "PRACTICUM_TOKEN": PRACTICUM_TOKEN,
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }
    values_not_none: list[str] = [
        variable_name
        for variable_name, value in variable_data.items()
        if not value
    ]
    if values_not_none:
        logging.critical(
            f"Переменная окружения недоступна {values_not_none}."
            "Программа будет принудительно остановлена"
        )
        sys.exit(1)
    logging.info("переменные окружения доступны.")


def send_message(bot, message) -> None:
    """This function is sending the message to Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{message}")
    except telegram.TelegramError as error:
        logging.error(f"Не удается отправить сообщение: {error}")
        raise telegram.TelegramError from error
    logging.debug(f"Отправлено сообщение в чат: {message}")


def get_api_answer(timestamp):
    """This function makes a request to the endpoint of the APi-service."""
    try:
        homework_statuses = requests.get(
            url=ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
        )
    except requests.RequestException:
        raise ("Ошибка в запросе, адрес неверен!")
    if not ENDPOINT:
        raise EndpointErrorException(
            "Отсутствует доступ к сервису Яндекс.Домашка!"
        )
    if homework_statuses.status_code != HTTPStatus.OK:
        raise ValueError(
            f"Ответ страницы: {homework_statuses.status_code},"
            "проверьте параметры запроса."
        )
    return homework_statuses.json()


def check_response(response):
    """This function checks the response to the APi-service."""
    if not isinstance(response, dict):
        raise TypeError("Ответ сервера не является словарём!")
    if "homeworks" not in response:
        raise KeyError("Отсутствует ключ 'homeworks' в словаре 'response'.")
    if "current_date" not in response:
        raise KeyError("Отсутствует ключ 'current_date' в словаре 'response'.")
    homework_statuses = response.get("homeworks")
    if not isinstance(homework_statuses, list):
        raise TypeError("Запрошенные ключ не является списком")
    return homework_statuses


def parse_status(homework):
    """This function extracts the status from homework information"""
    if "homework_name" not in homework:
        raise KeyError("Ключа 'homework_name' не найдено.")
    homework_name = homework.get("homework_name")
    status = homework.get("status")
    if not (homework_name and status):
        raise ValueError("В запросе нет имени и статуса домашней работы")
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise ValueError(f"Такого статуса: {verdict}, нет в словаре")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """The main logic of the bot's work."""
    try:
        check_tokens()
    except MissingEnvoirmentVariablesException:
        sys.exit(1)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    response_current_time = int(time.time())

    response_current_time = timestamp

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get("homeworks")
            if homework:
                old_homework = homework[0]
                message = parse_status(old_homework)
                send_message(bot, message)
        except (
            EndpointErrorException,
            MissingEnvoirmentVariablesException,
            telegram.TelegramError,
        ):
            pass

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.critical(message)
        finally:
            time.sleep(RETRY_PERIOD)
            timestamp = response_current_time


if __name__ == "__main__":
    main()
