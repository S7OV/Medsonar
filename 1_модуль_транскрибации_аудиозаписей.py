# -*- coding: utf-8 -*-
"""1. Модуль транскрибации аудиозаписей

# Модуль загрузки и транскрибации файлов (первый этап)

Данный модуль загружает и обрабатывает {MAX_RECORDS} аудио файлов от каждого менеджера из общей папки.

На входе нужно указать настройки на листе Конфигурация в рабочей таблице.

На выходе транскрибации будут сохранены в рабочую таблицу в лист Транскрибации RAW.

### ======== Служебные функции ========
"""

# @title Разное

import re

# Функция для загрузки MP3 файла с Google Drive
def load_mp3_from_google_drive(file_id: str, file_name: str) -> bytes:
    try:
        # Определение URL для загрузки файла
        download_url = f'https://drive.google.com/uc?id={file_id}&export=download'

        # Загрузка файла
        response = requests.get(download_url)
        response.raise_for_status()  # Проверка на успешность ответа

        # Сохранение MP3 файла во временный файл
        with open(file_name, "wb") as f:
            f.write(response.content)

        return response.content

    except requests.RequestException as e:
        print(f"Ошибка при загрузке файла: {e}")
        return None

    except IOError as e:
        print(f"Ошибка при сохранении файла: {e}")
        return None

# Функция для форматирования текста
def format_transcript(text):
    # Добавляем пробелы после знаков препинания, если их нет
    text = re.sub(r'([.!?])([^\s])', r'\1 \2', text)

    # Разделяем текст по знакам препинания, сохраняя сами знаки
    sentences = re.split(r'([.!?])', text)

    formatted_text = ''

    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i].strip()
        punctuation = sentences[i + 1].strip()
        formatted_text += sentence + punctuation + '\n'

    # Добавляем последнюю часть текста, если она существует
    if len(sentences) % 2 != 0:
        formatted_text += sentences[-1].strip()

    return formatted_text

# Функция для расчета стоимости транскрибации
def calculate_cost(duration_seconds):
    # Стоимость транскрибации Whisper на момент написания (уточните стоимость у OpenAI)
    cost_per_minute = 0.006  # Долларов за минуту
    cost = (duration_seconds / 60) * cost_per_minute
    return cost

# Функция для извлечения дополнительных данных из имени файла
def get_audio_info(filename):
    # Шаблон регулярного выражения для извлечения информации
    pattern = r'.*(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.\d+_from_(\d+)_to_(\d+)_session_(\d+)_\w+'

    # Применяем регулярное выражение к имени файла
    match = re.match(pattern, filename)

    if match:
        # Извлекаем данные из групп регулярного выражения
        date_time = match.group(1)  # Дата-время
        from_number = match.group(2)  # От кого звонок
        to_number = match.group(3)  # Кому звонок
        session_id = match.group(4)  # Номер сессии

        audio_info = {
            "filename": filename,
            "date_time": date_time,
            "from_number": from_number,
            "to_number": to_number,
            "session_id": session_id,
        }

    else:
        # В случае ошибки возвращаем словарь с именем файла и прочерками
        audio_info = {
            "filename": filename,
            "date_time": "---",
            "from_number": "---",
            "to_number": "---",
            "session_id": "---",
        }

    return audio_info


# Проверка функции и вывод результата
filename = "2024-06-24_12-15-45.096841_from_79615079433_to_049360_session_4109971104_talk.mp3"
audio_info = get_audio_info(filename)
print(audio_info)

# @title Получаем список файлов датасета
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials
from googleapiclient.errors import HttpError


def get_audio_list(folder_id_url, status_widget):
    # Начинаем с пустого списка статусов
    status_log = []

    # Функция для обновления статуса и отображения в `status_widget`
    def update_status(new_status, is_temporary=False):
        nonlocal status_log
        if is_temporary:
            # Удаляем старый временный статус и добавляем новый
            status_log = [status for status in status_log if not status.startswith('🕑 Обработка файлов')]
            status_log.append(new_status)
        else:
            # Добавляем новый статус и удаляем все временные статусы с часами
            status_log = [status for status in status_log if '🕑' not in status]
            status_log.append(new_status)

        # Обновляем `status_widget` значением, состоящим из всех статусов, соединенных через <br>
        status_widget.value = "<br>".join(status_log)


    progress.value = 10  # Обновляем прогресс
    # Статус: Аутентификация
    update_status('🕑 Аутентификация Google...', is_temporary=True)
    sleep(0.5)  # Симуляция длительной операции
    # Проверяем значение stopLoop из JavaScript
    if check_stop_loop():
        return

    # Аутентификация
    auth.authenticate_user()
    gauth = GoogleAuth()
    gauth.credentials = GoogleCredentials.get_application_default()
    drive = GoogleDrive(gauth)

    # Статус: Аутентификация завершена
    update_status('✅ Аутентификация Google завершена.')
    sleep(0.5)
    # Проверяем значение stopLoop из JavaScript
    if check_stop_loop():
        return

    # Статус: Извлечение ID из ссылки
    update_status('🕑 Извлечение ID папки из ссылки...', is_temporary=True)
    sleep(0.5)
    # Проверяем значение stopLoop из JavaScript
    if check_stop_loop():
        return
    progress.value = 15  # Обновляем прогресс

    pattern = r'folders/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, folder_id_url)
    if not match:
        raise ValueError("Неверный формат ссылки. Убедитесь, что ссылка содержит 'folders/<folder_id>'.")

    folder_id = match.group(1)
    update_status('✅ ID папки успешно извлечен.')

    # Статус: Проверка существования папки
    update_status('🕑 Проверка существования папки...', is_temporary=True)
    try:
        for i in range(20, 30, 2):
            progress.value = i
            sleep(0.1)  # Задержка для более плавного обновления прогресса
            # Проверяем значение stopLoop из JavaScript
            if check_stop_loop():
                return
        drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
        update_status('✅ Папка найдена.')
    except HttpError as e:
        if e.resp.status == 404:
            update_status('❌ Папка не найдена.')
            raise ValueError(f"Папка {folder_id_url} не найдена.")
        else:
            update_status('❌ Ошибка при проверке папки.')
            raise



    # Статус: Получение списка файлов
    update_status('🕑 Получение списка файлов из папки...', is_temporary=True)
    for i in range(30, 50, 4):
        progress.value = i
        sleep(0.01)  # Задержка для более плавного обновления прогресса


    audio_list = []
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
    total_files = len(file_list)
    update_status(f'✅ Список файлов получен. Всего файлов: {total_files}.')


    # Статус: Обработка файлов
    update_status(f'🕑 Обработка файлов... (0 из {total_files})', is_temporary=True)
    for idx, file in enumerate(file_list):
        file_size = int(file.get('fileSize', 0))  # Получение размера файла и преобразование в int
        FILTER = int(config['FILTER_AUDIO_SIZE'])
        if FILTER == 0 or file_size > FILTER:
            audio_info = get_audio_info(file['title'])
            audio_info['id'] = file['id']
            audio_list.append(audio_info)
    # Проверяем значение stopLoop из JavaScript
    if check_stop_loop():
        return

        # Обновление прогресса от 60 до 80 в зависимости от обработки файлов
        sleep(0.01)  # Задержка для более плавного обновления прогресса
        progress.value = 55 + int(20 * (idx + 1) / total_files)  # Прогресс от 60 до 80

        # Обновление статуса с указанием количества обработанных файлов
        if (idx + 1) % 100 == 0 or (idx + 1) == total_files:
            update_status(f'🕑 Обработка файлов... ({idx + 1} из {total_files})', is_temporary=True)
    # Проверяем значение stopLoop из JavaScript
    if check_stop_loop():
        return

    progress.value = 75  # Обновляем прогресс
    # Явное удаление временного статуса перед добавлением финального сообщения
    status_log = [status for status in status_log if not status.startswith('🕑 Обработка файлов')]
    update_status(f'✅ Обработка завершена. Всего обработано файлов: {len(audio_list)}.')

    return audio_list

# @title Получаем краткий список файлов по операторам
from collections import defaultdict

def get_records_by_list(audio_list, max_records=5):

    unique_to_numbers = defaultdict(list)
    original_counts = defaultdict(int)

    # Заполняем словари
    for record in audio_list:
        unique_to_numbers[record['to_number']].append(record)
        original_counts[record['to_number']] += 1

    # Фильтруем номера, у которых меньше max_records записей
    max_records = int(max_records)
    filtered_to_numbers = {to_number: records for to_number, records in unique_to_numbers.items() if len(records) >= max_records}

    # Составляем результат, включая не более max_records записей для каждого номера
    result = [rec for to_number in filtered_to_numbers for rec in filtered_to_numbers[to_number][:max_records]]

    return result, original_counts

# @title Работа с WHISPER API

def run_transcript(record, file_name):
    if not 'text' in record:
        # Создание клиента OpenAI
        client = openai.OpenAI()

        # Указываем слова в параметре prompt МОЖНО ДОПОЛНЯТЬ ДЛЯ ЛУЧШЕЙ ТРАНСКРИБАЦИИ:
        prompt = "клиника Медсонар, оператор, Петра Метальникова, Бочарникова"

        # Получение длительности аудиофайла
        audio_segment = AudioSegment.from_file(file_name, format="mp3")
        audio_duration = audio_segment.duration_seconds

        if audio_duration > 1:
            # Выполнение транскрибации с параметром prompt и замер времени выполнения
            start_time = time.time()
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=open(file_name, "rb"),
                prompt=prompt
            )
            end_time = time.time()
            elapsed_time = end_time - start_time

            # Обработка и форматирование текста
            text = transcript.text
            formatted_text = format_transcript(text)
            cost = calculate_cost(audio_duration)
        else:
            formatted_text = 'error'
            cost = 0
            elapsed_time = 0

        return {
            "text": formatted_text,
            "duration": round(audio_duration, 2),
            "elapsed_time": round(elapsed_time, 2),
            "cost": round(cost, 4)
        }

# @title Функции взаимодействия с кнопкой "Отмена"
# Функция для проверки значения stopLoop из JavaScript
from google.colab import output
def check_stop_loop():
    return output.eval_js('stopLoop')

# Функция для сброса флага остановки stopLoop из JavaScript
def reset_stop_loop():
    return output.eval_js('resetStopLoop()')

# Функция для установки флага остановки stopLoop из JavaScript
def set_stop_loop():
    return output.eval_js('setStopLoop()')

# @title Вывод информации по выбранным записям

from datetime import datetime
def on_upload_button_click(b):
    upload_button.disabled = True
    transcription_button.disabled = True
    cancel_button.disabled = False

    progress.value = 0

    with output_area:
        clear_output()

        # Перезагрузка основной Конфигурации из Google Spreadsheets
        # Создаем виджет для отображения текста
        config_widget = widgets.HTML('<h2>🕑 Загрузка основной Конфигурации из рабочей таблицы...</h2>')
        config_widget.add_class('config-widget')
        display(config_widget)

        global config  # Указываем, что будем использовать глобальную переменную
        config = re_config(gs_client, colab_id, spreadsheet_url)

        sleep(1)
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return
        # Обновляем текст в виджете
        progress.value = 5  # Обновляем прогресс
        config_widget.value = '<h2>✅ Конфигурация успешно загружена.</h2>'

        # Создаем виджет для отображения текста
        audio_widget = widgets.HTML('<h2>🕑 Получаю список аудиозаписей...</h2>')
        audio_widget.add_class('audio-widget')
        status_widget = widgets.HTML('')
        status_widget.add_class('status-widget')

        display(audio_widget)
        sleep(1)
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return
        display(status_widget)

        sleep(.5)
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        global records_list  # Указываем, что будем использовать глобальную переменную

        # Загружаем список файлов из расшаренной папки на Google Drive
        audio_list = get_audio_list(config['GOOGLE_DRIVE_AUDIO_URL'], status_widget)

        # Обновляем текст в виджете
        progress.value = 80  # Обновляем прогресс
        audio_widget.value = '<h2>✅ Аудиозаписи успешно загружены.</h2>'

        sleep(.3)
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return
        #clear_output()

        # Назначаем класс для первого виджета
        status_widget.add_class('hidden')
        sleep(.1)
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        # Назначаем класс для второго виджета
        config_widget.add_class('hidden')
        sleep(.3)
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return


        # Сортируем audio_list по возрастанию даты и времени
        audio_list = sorted(audio_list, key=lambda x: datetime.strptime(x['date_time'], '%Y-%m-%d_%H-%M-%S') if x['date_time'] != "---" else datetime.min)
        progress.value = 85  # Обновляем прогресс
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        # Фильтруем список по операторам и получаем статистику
        records_list, call_stats = get_records_by_list(audio_list, max_records=config['MAX_RECORDS'])
        progress.value = 90  # Обновляем прогресс
        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        # clear_output()
        # Статистика всех записей по операторам
        print(f"Всего записей: {len(audio_list)}\n-----------------------------------")
        for operator, num_calls in call_stats.items():
            # Фильтруем записи по оператору
            filtered_records = [record for record in audio_list if record['to_number'] == operator]

            if filtered_records:
                # Определяем минимальную и максимальную дату для каждого оператора
                min_date = min(datetime.strptime(record['date_time'], '%Y-%m-%d_%H-%M-%S') for record in filtered_records)
                max_date = max(datetime.strptime(record['date_time'], '%Y-%m-%d_%H-%M-%S') for record in filtered_records)

                # Выводим статистику с периодом звонков
                print(f"Оператор: \033[1;36m{operator:<12}\033[0m "
                      f"Записей: \033[1;34m{num_calls:<5}\033[0m "
                      f"Период звонков: с \033[1;32m{min_date.strftime('%Y-%m-%d %H:%M:%S')}\033[0m "
                      f"по \033[1;32m{max_date.strftime('%Y-%m-%d %H:%M:%S')}\033[0m")
        progress.value = 95  # Обновляем прогресс

        # Получаем список операторов и приводим их к единому формату
        operator_list = [operator.strip() for operator in config['OPERATOR_LIST'].split(',')] if config['OPERATOR_LIST'] else []

        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        if operator_list:
            print(f"\nСписок операторов (OPERATOR_LIST): \033[1;34m{', '.join(operator_list)}\033[0m\n-----------------------------------")
            # Приводим операторы к единому формату, удаляя ведущие нули
            normalized_operator_list = [operator.lstrip('0') for operator in operator_list]

            # Фильтруем records_list по операторам из operator_list
            records_list = [record for record in records_list if record['to_number'].lstrip('0') in normalized_operator_list]
        else:
            print(f"\nСписок операторов для анализа (OPERATOR_LIST): \033[1;34mВсе операторы\033[0m\n-----------------------------------")

        print(f"\nВыбрано записей для транскрибации: \033[1;34m{len(records_list)}\033[0m\n-----------------------------------")

        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        # Вывод информации по операторам
        for operator, num_calls in call_stats.items():
            # Фильтруем записи по оператору 'to_number' с учетом фильтрации по operator_list
            filtered_records = [record for record in records_list if record['to_number'] == operator]

            if filtered_records:
                # Получаем минимальную и максимальную дату
                min_date = min(datetime.strptime(record['date_time'], '%Y-%m-%d_%H-%M-%S') for record in filtered_records)
                max_date = max(datetime.strptime(record['date_time'], '%Y-%m-%d_%H-%M-%S') for record in filtered_records)

                # Форматируем вывод для второго блока
                print(f"Оператор: \033[1;36m{operator:<12}\033[0m "
                      f"Записей: \033[1;34m{len(filtered_records):<5}\033[0m "
                      f"Период звонков: с \033[1;32m{min_date.strftime('%Y-%m-%d %H:%M:%S')}\033[0m "
                      f"по \033[1;32m{max_date.strftime('%Y-%m-%d %H:%M:%S')}\033[0m")

        progress.value = 100  # Завершаем прогресс

    upload_button.disabled = False
    transcription_button.disabled = False
    cancel_button.disabled = True

# @title ====> **КНОПКА 3 - "ОТМЕНА".** Отмена обработки <====

def canсel_operation(event, client=None, verbose_level=1):
    #global is_running
    if not cancel_button.disabled:
        upload_button.disabled = False  # Устанавливаем флаг в False для отмены операции
        transcription_button.disabled = False  # Активируем кнопку транскрибации
        cancel_button.disabled = True
        reset_stop_loop()
        with output_area:
            #print("❌ Операция отменена")
            transcript_widget = widgets.HTML('<h2>❌ Операция отменена</h2>')
            display(transcript_widget)
        progress.value = 0

# @title Распознаем все файлы из списка и сохраняем их в Google Spreadsheets
# ВНИМАНИЕ!! Данный блок съедает много денег!
# Если records_list уже содержит поле 'text', то он пропускается

# Функция для сохранения records_list в Google Spreadsheet
def save_records_to_google_sheets(records_list, spreadsheet_url):

    # Открываем нужный лист на основе режима
    spreadsheet_id = parse_spreadsheet_id_by_url(spreadsheet_url)
    spreadsheet = gs_client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(config['TRANSCRIPTS_RAW_WORKSHEET'])

    # Преобразуем список records_list в формат для записи в таблицу
    rows = []
    headers = ['Ссылка на файл', 'Имя файла', 'Оператор', 'Диалог', 'Длительность', 'Время обработки', 'Стоимость']  # Заголовки столбцов
    rows.append(headers)

    for record in records_list:
        # Формируем ссылку на файл по id
        file_link = f"https://drive.google.com/file/d/{record.get('id', '')}/view" if record.get('id', '') else 'Unknown'

        # Добавляем строку с данными в порядке, соответствующем заголовкам
        rows.append([
            file_link,                       # Ссылка на файл
            record.get('filename', ''),     # Имя файла
            record.get('to_number', ''),     # Оператор
            record.get('text', ''),          # Диалог
            record.get('duration', ''),      # Длительность
            record.get('elapsed_time', ''),  # Время обработки
            record.get('cost', '')           # Стоимость
        ])

    # Очистим лист перед записью
    worksheet.clear()

    # Записываем данные в таблицу
    worksheet.update(rows)
    print("Данные успешно записаны в Google Spreadsheet!")

# Основная функция с модификацией
def get_transcript_list(b):
    upload_button.disabled = True
    transcription_button.disabled = True
    cancel_button.disabled = False
    tmp_file = 'temp.mp3'
    with output_area:
        clear_output()

        # Устанавливаем начальное значение прогресс-бара
        progress.value = 0
        progress.max = len(records_list)

        # Создаем виджет для отображения текста
        transcript_widget = widgets.HTML('<h2>🕑 Идет транскрибация аудиозаписей...</h2>')
        display(transcript_widget)



        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        for index, record in enumerate(records_list):
            if load_mp3_from_google_drive(record['id'], tmp_file) is not None:

                # Проверяем значение stopLoop из JavaScript
                if check_stop_loop():
                    return

                transcript = run_transcript(record, tmp_file)

                if transcript is not None:
                    # Дополняем данные
                    records_list[index]['text'] = transcript['text']
                    records_list[index]['duration'] = transcript['duration']
                    records_list[index]['elapsed_time'] = transcript['elapsed_time']
                    records_list[index]['cost'] = transcript['cost']

                # Удаление временного файла
                os.remove(tmp_file)

            # Выводим только имя файла
            print(f'Файл {index + 1} / {len(records_list)} : {record["filename"]} обработан')
            # Обновляем значение прогресс-бара
            progress.value += 1

        print('Все файлы распознаны')

        # Чекпоинт. Сохраняем результат в Google Spreadsheet
        save_records_to_google_sheets(records_list, config['CURRENT_SPREADSHEET_URL'])

        transcript_widget.value = '<h2>✅ Транскрибация успешно завершена.</h2>'
        progress.value = 100

    upload_button.disabled = False
    transcription_button.disabled = False
    cancel_button.disabled = True

"""### ======== Безусловно исполняемый код ========"""

# @title Системная конфигурация, ID рабочей таблицы.

# Таблица для работы
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1OO5uLqbgG0AeIOue-cilsHhUuEcvxA_ymov0HXp1NvQ/edit' # URL рабочей таблицы
worksheet_name = 'Конфигурация' # Имя листа с конфигурацией
colab_id = 1 # ID данного ноутбука

# @title Подготовка. Загрузка основной Конфигурации из Google Spreadsheets

import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import json
import re

from time import sleep

def parse_spreadsheet_id_by_url(url):
    # Используем регулярное выражение для извлечения spreadsheet_id из URL
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)  # Получаем сам spreadsheet_id
    else:
        raise ValueError("Некорректная ссылка на Google Таблицу")

def spreadsheets_auth():
    # Устанавливаем область видимости API
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Подключаем ключ API Google
    from google.colab import userdata
    service_account_info = userdata.get('GOOGLE_JSON')
    service_account_info_dict = json.loads(service_account_info)

    # Создаем объект учетных данных
    credentials = Credentials.from_service_account_info(service_account_info_dict, scopes=scopes)

    # Авторизуемся
    client = gspread.authorize(credentials)

    return client

def load_config(client, colab_id, spreadsheet_url):
    # Открываем нужный лист на основе режима
    spreadsheet_id = parse_spreadsheet_id_by_url(spreadsheet_url)
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    # Загружаем данные из Google Таблицы в DataFrame
    df_config = get_as_dataframe(worksheet, dtype=str, header=0)

    # Заменяем все NaN, если они есть, на пустые строки
    df_config = df_config.fillna('')

    # Фильтруем строки, где Colab_ID == 0 или Colab_ID == colab_id
    df_filtered = df_config[(df_config['Colab_ID'] == '0') | (df_config['Colab_ID'] == str(colab_id))]

    # Пробежимся по строкам отфильтрованного датафрейма и заполним словарь
    config = {}

    for index, row in df_filtered.iterrows():
        constant_name = row['Константа']
        constant_value = row['Значение']
        config[constant_name] = constant_value

    return config

# Обертка к load_config
def re_config(client, colab_id, spreadsheet_url):
    config = load_config(client, colab_id, spreadsheet_url)
    if config['SPREADSHEED_OVERRIDE']:
        config = load_config(client, colab_id, config['SPREADSHEED_OVERRIDE'])
        config['CURRENT_SPREADSHEET_URL'] = config['SPREADSHEED_OVERRIDE']
    else:
        config['CURRENT_SPREADSHEET_URL'] = spreadsheet_url

    # Режим работы (не используется)
    # config['TEST_MODE'] = True if config['TEST_MODE'] == "1" else False # True - тестовый режим, False - рабочий режим

    return config

gs_client = spreadsheets_auth()
config = re_config(gs_client, colab_id, spreadsheet_url)

display(config)

# @title Установка библиотек, импорты и подключение к OpenAI
!pip install -q --upgrade openai
!pip install -q pydub
!pip install -q mutagen

import re
import requests
import openai
import getpass
import os
import io
import time
from pydub import AudioSegment
from mutagen.mp3 import MP3
from tqdm import tqdm

from openai import OpenAI
import os
from google.colab import userdata
openai_key = userdata.get('OPENAI_API_KEY');
os.environ["OPENAI_API_KEY"] = openai_key

"""# Панель управления модулем транскрибации записей"""

# @title Панель управления модулем транскрибации записей
import ipywidgets as widgets
from IPython.display import display, clear_output, update_display
from IPython.core.display import HTML

# CSS и HTML для кнопок
style_html = widgets.HTML("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');

.medsonar-header{
    text-align: left;
    margin-bottom: 40px;
    display: flex;
    flex-direction: column;
}

.custom-buttons{
    display: flex;
    flex-direction: column;
    margin-right:30px;
}

.custom-button {
    background-color: white;
    color: #00abb8;
    font-weight: bold;
    font-size:.95rem;
    text-transform: uppercase;
    border: #00abb8 2px solid;
    border-radius: 24px;
    padding: 10px 20px;
    margin: 0 0 10px 0;
    transition: background-color 0.3s, color 0.3s;
    font-family: 'Montserrat', sans-serif;
}
.cancel-button{
    color: #cf2d46;
    border-color: #cf2d46;
    outline: none;
}
.custom-button:hover {
    background-color: #00abb8;
    color: white;
    box-shadow: none!important;
}

.cancel-button:hover{
    background-color: #cf2d46;
    box-shadow: none;
    outline: none;
}
.custom-button:disabled {
    background-color: #e0e0e0; /* Светло-серый цвет */
    color: #aaaaaa; /* Тусклый текст */
    border-color: #cccccc; /* Светло-серый цвет границы */
}
/* Свой hover для disabled */
.custom-button:disabled:hover {
    background-color: #ddd; /* Серый цвет */
    color: #888; /* Серый текст */
    border-color: #bbb; /* Светло-серый цвет границы */
    cursor: auto;
}

.output-area{
    padding:10px;
    border-radius:3px;
}
h2 {
    font-size: 20px;
    line-height: 1;
    font-weight: bold;
}
h1, h2, h3, h4, h5 {
    font-family: 'Montserrat', sans-serif;
}


/* Начальные стили для виджетов */
.config-widget,
.status-widget {
  max-height: 150px; /* Достаточно большое значение для плавного схлопывания */
  opacity: 1;
  overflow: hidden;
  transition: max-height .3s ease, opacity .3s ease;
}

/* Стили для скрытого состояния */
.hidden {
  max-height: 0;
}
</style>
""")

# Приветственная надпись
welcome_label = widgets.HTML(
    value=f"""
    <div class='medsonar-header'>
        <span style='font-size: 2rem; font-weight:bold; color:#333;'>Система нейроконтроля качества медицинского центра Медсонар</span>
        <span style='font-size: 1rem; font-weight:bold; color:#333;'><br>Модуль 1. Cоздание транскрибаций по аудио записям</span>
    </div>
    """
)

# Форма для вывода служебной информации
output_area = widgets.Output(
    layout=widgets.Layout(
        width='1000px',
        height='400px',
        overflow='auto',
        border='1px solid #00abb8'  # Устанавливаем цвет окаймления
    )
)
with output_area:
    display(HTML("<h1 style='font-size: 20px;'><center>Вас приветствует система нейроконтроля качества! <br><br> Запустите получение списка файлов</center></h1>"))

#Виджет полосы статуса
progress = widgets.IntProgress(min=0, max=100, value=0, layout=widgets.Layout(width='1020px'))

# Кнопки
upload_button = widgets.Button(description="Получение списка файлов", layout=widgets.Layout(height='50px', width='330px'))
transcription_button = widgets.Button(description="Транскрибация", layout=widgets.Layout(height='50px', width='330px'))
cancel_button = widgets.Button(description="Отмена", layout=widgets.Layout(height='50px', width='330px'))

# Применение стиля к кнопкам
upload_button.add_class('custom-button')
transcription_button.add_class('custom-button')
cancel_button.add_class('custom-button')
cancel_button.add_class('cancel-button')
output_area.add_class('output-area')


def display_buttons():
    clear_output(wait=True)
    display(welcome_label)

    button_box = widgets.VBox([upload_button, transcription_button, cancel_button],
                              layout=widgets.Layout(width='350px'))
    # Создаем вертикальный контейнер для output_area и progress
    output_and_progress_box = widgets.VBox([output_area, progress])
    hbox = widgets.HBox([button_box, output_and_progress_box])
    display(style_html)
    display(hbox)


# Привязка кнопок к функциям
upload_button.on_click(on_upload_button_click)
transcription_button.on_click(get_transcript_list)
cancel_button.on_click(canсel_operation)

# Вывод виджетов
display(style_html)
display_buttons()

cancel_button.disabled = True

js_code = """
<script>
    // Функция для сброса флага остановки цикла
    function resetStopLoop() {
        if (stopLoop) {
            stopLoop = false;
            console.log("JavaScript: Флаг остановки сброшен, stopLoop = false");
        }
    }

    document.querySelectorAll('.cancel-button').forEach((el, index) => {
        if (el.textContent.includes('Отмена')) {
            el.setAttribute('id', 'cancelButton');
        }
    });
    var stopLoop = false;
    document.getElementById('cancelButton').onclick = function() {
        stopLoop = true;
        console.log("JavaScript: Кнопка нажата, stopLoop = true");
        this.disabled = true; // Сделать кнопку недоступной после нажатия
        this.textContent = "🕑 Операция отменяется..."; // Изменить текст кнопки
    }
</script>
"""
display(HTML(js_code))
