"""Homework Bot."""
import json
import logging
import os
import sys
import time
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv

from exceptions import (
    EndpointErrorException,
    JsonErrorException,
    MissingEnvoirmentVariablesException,
    TelegramErrorException,
    RequestErrorException,
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIME_DELTA = 160000
RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS: dict[str, str] = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS: dict[str, str] = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens() -> bool:
    """Check the availability of environment variables."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message) -> None:
    """Send the message to Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{message}")
    except telegram.TelegramError as telegram_error:
        logging.error(f"Не удается отправить сообщение: {telegram_error}")
        raise TelegramErrorException from telegram_error
    logging.debug(f"Отправлено сообщение в чат: {message}")


def get_api_answer(timestamp):
    """Make a request to the endpoint of the APi-service."""
    if not ENDPOINT:
        raise EndpointErrorException(
            "Отсутствует доступ к сервису Яндекс.Домашка!"
        )

    try:
        homework_statuses = requests.get(
            url=ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
        )
    except requests.RequestException as request_error:
        logging.error(f"Ошибка в запросе, адрес неверен! {request_error}")
        raise RequestErrorException(
            f"Ошибка в запросе, адрес неверен!"
        ) from request_error

    if homework_statuses.status_code != HTTPStatus.OK:
        raise ValueError(
            f"Ответ страницы: {homework_statuses.status_code},"
            "проверьте параметры запроса."
        )
    try:
        return homework_statuses.json()
    except json.JSONDecodeError as json_error:
        logging.error("Сервер вернул невалидный json")
        raise JsonErrorException(
            f"Сервер вернул невалидный json"
        ) from json_error


def check_response(response):
    """Check the response to the APi-service."""
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


def parse_status(homework) -> str:
    """Extract the status from homework information."""
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
    """Bot work base logic."""
    if not check_tokens():
        logging.critical("Отсутствует переменная окружения")
        sys.exit(MissingEnvoirmentVariablesException(
            "Отсутствует переменная окружения"
        ))

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - TIME_DELTA
    response_current_time = int(time.time())

    message = ""

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            old_homework = homework[0]
            new_message = parse_status(old_homework)
            if homework and (message != new_message):
                message = new_message
                send_message(bot, message)
            response_current_time = response.get("cuurent_date")

        except (
            TelegramErrorException,
            EndpointErrorException,
            RequestErrorException,
            JsonErrorException,
        ):
            pass

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)
            timestamp = response_current_time


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        stream=logging.StreamHandler(sys.stdout),
        format="%(asctime)s, %(levelname)s, %(message)s",
    )
    main()
