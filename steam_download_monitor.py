import psutil
import time
import os
import winreg
import re
from datetime import datetime

#  НАСТРОЙКИ

# Интервал между измерениями (в секундах)
# 60 секунд = 1 минута
CHECK_INTERVAL = 60

# Сколько раз измерять скорость (5 минут = 5 измерений)
TOTAL_CHECKS = 5


#  ФУНКЦИИ 

def get_steam_path():
    """
    Получаем путь установки Steam из реестра Windows.
    Благодаря этому скрипт не зависит от того,
    куда пользователь установил Steam.
    """
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
    steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
    return steam_path.replace("/", "\\")


def get_current_game(steam_path):
    """
    Определяем, какая игра сейчас скачивается.

    В папке steamapps Steam хранит файлы:
    appmanifest_<appid>.acf

    Внутри каждого файла есть параметр StateFlags:
    - 1024 или 1026 -> активная загрузка
    - другие значения -> нет загрузки

    Если найден файл с нужным StateFlags,
    извлекаем название игры ("name").
    """
    steamapps = os.path.join(steam_path, "steamapps")

    # Если папка steamapps не найдена, выходим
    if not os.path.exists(steamapps):
        return None

    # Перебираем все appmanifest-файлы
    for file in os.listdir(steamapps):
        if file.startswith("appmanifest_") and file.endswith(".acf"):
            path = os.path.join(steamapps, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

                # Ищем StateFlags
                state_match = re.search(r'"StateFlags"\s+"(\d+)"', content)
                if state_match and state_match.group(1) in ("1024", "1026"):
                    # Если StateFlags подходит, ищем название игры
                    name_match = re.search(r'"name"\s+"(.+?)"', content)
                    if name_match:
                        return name_match.group(1)

    # Если активной загрузки нет
    return None


def get_download_speed(interval):
    """
    Считаем среднюю скорость загрузки за interval секунд.

    Берём:
    1. Общее количество принятых байт в начале
    2. Ждём interval секунд
    3. Берём общее количество байт в конце
    4. Разницу делим на время -> получаем байты/сек
    """
    net1 = psutil.net_io_counters()
    time.sleep(interval)
    net2 = psutil.net_io_counters()

    return (net2.bytes_recv - net1.bytes_recv) / interval


def format_speed(bytes_per_sec):
    """
    Преобразуем байты в секунду в читаемый формат:
    B/s, KB/s или MB/s
    """
    if bytes_per_sec > 1024 ** 2:
        return f"{bytes_per_sec / 1024 ** 2:.2f} MB/s"
    elif bytes_per_sec > 1024:
        return f"{bytes_per_sec / 1024:.2f} KB/s"
    else:
        return f"{bytes_per_sec:.0f} B/s"


def is_steam_running():
    """
    Проверяем, запущен ли процесс Steam.
    Если Steam не запущен – нет смысла продолжать работу.
    """
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and "steam" in proc.info['name'].lower():
            return True
    return False


def print_status(game, status, speed=None):
    """
    Унифицированный вывод информации в консоль.
    Если скорость ещё не измерена, выводим 'измеряется...'
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}]")
    print(f"Игра: {game}")
    print(f"Статус: {status}")

    if speed is None:
        print("Скорость: измеряется...")
    else:
        print(f"Скорость: {format_speed(speed)}")

    print("-" * 50)


# ОСНОВНАЯ ЛОГИКА 

def main():
    # Проверяем, запущен ли Steam
    if not is_steam_running():
        print("Steam не запущен. Запусти Steam и попробуй снова.")
        return

    # Получаем путь к Steam
    steam_path = get_steam_path()
    print(f"Steam найден по пути: {steam_path}")
    print("Мониторинг загрузки Steam (вывод сразу, затем каждую минуту в течение 5 минут):\n")

    # Первый мгновенный вывод 
    # Здесь мы не считаем скорость, а просто показываем статус
    game = get_current_game(steam_path)

    if game:
        status = "Загружается"
        game_name = game
    else:
        status = "Пауза"
        game_name = "Нет активной загрузки"

    print_status(game_name, status)

    # Основные 5 измерений 
    # Каждую минуту измеряем скорость и выводим результат
    for _ in range(TOTAL_CHECKS):
        speed = get_download_speed(CHECK_INTERVAL)
        game = get_current_game(steam_path)

        if game:
            status = "Загружается"
            game_name = game
        else:
            status = "Пауза"
            game_name = "Нет активной загрузки"

        print_status(game_name, status, speed)


# Точка входа в программу
if __name__ == "__main__":
    main()
