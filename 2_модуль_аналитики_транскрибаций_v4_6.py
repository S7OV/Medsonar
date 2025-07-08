# -*- coding: utf-8 -*-
"""2. Модуль аналитики транскрибаций v4.6


# Модуль аналитики транскрибаций (второй этап + третий этап)

### ======== Служебные функции ========
"""

# @title Функции для работы с Google Spreadsheets

def parse_spreadsheet_id_by_url(url):
    # Используем регулярное выражение для извлечения spreadsheet_id из URL
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)  # Получаем сам spreadsheet_id
    else:
        raise ValueError("Некорректная ссылка на Google Таблицу")

def gs_client_auth():
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

    # Исключать ответы "B" из словарей "Почему я так решил"
    config['EXCLUDE_B'] = True if config['EXCLUDE_B'] == "1" else False # True - исключать, False - не исключать (учитывать)

    return config

# Функция загрузки **транскрибаций** из рабочей таблицы.

def load_dialogue_df(client, spreadsheet_url, config):
    # Получаем доступ к определенному листу по имени
    spreadsheet_id = parse_spreadsheet_id_by_url(spreadsheet_url)
    sheet = client.open_by_key(spreadsheet_id).worksheet(config['TRANSCRIPTS_RAW_WORKSHEET'])

    # Первая строка содержит заголовки
    data = sheet.get_all_records()

    # Сколько загружаем транскрибаций, если выбран этот метод. 0 - все.
    # Преобразуем строку в число, устанавливаем 0 по умолчанию при ошибке или если NUM_TRANSCRIPTS не задано
    NUM_TRANSCRIPTS = int(config.get('NUM_TRANSCRIPTS', 0))

    # Преобразуем данные в DataFrame
    ideal_df = pd.DataFrame(data[:NUM_TRANSCRIPTS] if NUM_TRANSCRIPTS else data)

    # Выберем только интересующие столбцы и создаем копию для безопасной модификации
    ideal_df = ideal_df[['Ссылка на файл', 'Имя файла', config['DIALOGUE_COLUMN']]].copy()

    # Извлечение номера оператора из столбца "Имя файла"
    ideal_df['Оператор'] = ideal_df['Имя файла'].str.extract(r'to_([0-9]+)_')

    # Переименовываем столбец "Идеальная транскрибация" в "Диалог"
    ideal_df.rename(columns={config['DIALOGUE_COLUMN']: 'Диалог'}, inplace=True)


    # Переупорядочиваем столбцы для добавления 'Оператор' после 'Имя файла'
    cols = ideal_df.columns.tolist()  # Получаем список всех столбцов
    new_order = cols[1:2] + ['Оператор', 'Ссылка на файл', 'Диалог']  # Вставляем 'Оператор', 'Ссылка на файл' и 'Диалог'
    dialogue_df = ideal_df[new_order]  # Применяем новый порядок столбцов

    return dialogue_df


def save_masterdata_df(client, spreadsheet_url, config, masterdata_df):
    # Открывайте нужный лист на основе режима
    spreadsheet_id = parse_spreadsheet_id_by_url(spreadsheet_url)
    spreadsheet = client.open_by_key(spreadsheet_id)

    worksheet = spreadsheet.worksheet(config['MASTERDATA_WORKSHEET'])
    worksheet_gid = worksheet.id  # Получаем gid текущего листа

    # Создание столбца со ссылками на строки Google Sheets
    base_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit#gid={worksheet_gid}"
    masterdata_df['Ссылка на строку'] = base_url + "&range=A" + (masterdata_df.index + 2).astype(str)

    # Очищаем лист перед добавлением новых данных
    worksheet.clear()

    # Выгрузите датафрейм в Google Таблицу
    set_with_dataframe(worksheet, masterdata_df, include_index=False, resize=True)


def load_masterdata_df(client, spreadsheet_url, config):
    # Открывайте нужный лист на основе режима
    spreadsheet_id = parse_spreadsheet_id_by_url(spreadsheet_url)
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Получаем доступ к определенному листу по имени
    worksheet = spreadsheet.worksheet(config['MASTERDATA_WORKSHEET'])

    # Первая строка содержит заголовки
    data = worksheet.get_all_records()

    # Преобразуем данные в DataFrame
    masterdata_df = pd.DataFrame(data)

    return masterdata_df


def save_final_reports_df(client, spreadsheet_url, config, all_operators_df):
    # Открывайте нужный лист на основе режима
    spreadsheet_id = parse_spreadsheet_id_by_url(spreadsheet_url)
    spreadsheet = client.open_by_key(spreadsheet_id)

    worksheet = spreadsheet.worksheet("Выводы RAW")  # Получаем лист по названию

    output_area.layout.overflow = 'auto'
    output_area.layout.overflowY = 'scroll'
    # Загрузка данных в Google Sheets
    set_with_dataframe(worksheet, all_operators_df, include_index=False, resize=True)

# @title Функция для подключения Google Drive (диск)

def mount_google_drive(mount_point='/content/drive'):
    # Проверяем, смонтирован ли уже Google Диск
    if not os.path.exists(mount_point):
        print("Монтирование Google Диска...")
        drive.mount(mount_point)
    else:
        print("Google Диск уже смонтирован.")

# @title Функции подсчета и вывода статистики по операторам

def extract_date_time_from_filename(filename):
    # Извлекаем дату и время в формате "YYYY-MM-DD_HH-MM-SS" из имени файла
    match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d_%H-%M-%S')
    return None

def print_operator_stats(dialogue_df):
    # Добавляем колонки с датой и ID оператора, извлечённые из имени файла
    dialogue_df['Дата звонка'] = dialogue_df['Имя файла'].apply(extract_date_time_from_filename)

    # Подсчет количества уникальных значений для каждого оператора
    operator_counts = dialogue_df['Оператор'].value_counts()

    # Вывод общей статистики
    print(f"Транскрибации, загруженные из рабочей таблицы.\n\nВсего операторов: \033[1;34m{len(operator_counts)}\033[0m\nВсего записей:    \033[1;34m{len(dialogue_df)}\033[0m\n-----------------------------------")

    # Пройдемся по каждому оператору и выведем детализированную информацию
    for operator, num_calls in operator_counts.items():
        # Фильтруем записи по ID оператора
        filtered_records = dialogue_df[dialogue_df['Оператор'] == operator]

        if not filtered_records.empty:
            # Определяем минимальную и максимальную дату для каждого оператора
            min_date = filtered_records['Дата звонка'].min()
            max_date = filtered_records['Дата звонка'].max()

            # Разделяем дату и время для вывода в разных цветах
            min_date_str = min_date.strftime('%Y-%m-%d')
            min_time_str = min_date.strftime('%H:%M:%S')
            max_date_str = max_date.strftime('%Y-%m-%d')
            max_time_str = max_date.strftime('%H:%M:%S')

            # Выводим статистику с периодом звонков
            print(f"Оператор: \033[1;36m{operator:<12}\033[0m "
                  f"Записей: \033[1;34m{num_calls:<5}\033[0m "
                  f"Период звонков: с \033[1;34m{min_date_str}\033[0m \033[0;36m{min_time_str}\033[0m "
                  f"по \033[1;34m{max_date_str}\033[0m \033[0;36m{max_time_str}\033[0m")
        else:
            print(f"Оператор: \033[1;36m{operator:<12}\033[0m Нет записей для этого оператора")

# @title Функции для работы с OpenAI + функция фильтра

# Запрос OpenAI
import json
import concurrent.futures

# Функция для запроса к OpenAI
def generate_qc_json(prompt):
    client = OpenAI()
    messages = [
        {"role": "system", "content": prompt['system']},
        {"role": "user", "content": prompt['user']},
        {'role': 'assistant', 'content': ''},
    ]
    try:
        response = client.chat.completions.create(
            model=prompt['model'],
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=messages,
            max_tokens=1500,
            top_p=0.5,
            n=1
        )
        openai_response = response.choices[0].message.content
        return json.loads(openai_response)
    except Exception as e:
        print(f"Ошибка при запросе: {e}")
        return None  # Возвращаем None для легкости обнаружения ошибок

# Функция для проверки группы фильтров
def check_filter(filter_prompt, filename, config):
    print(f"\033[1;31mПроверка фильтра:    \033[0m {filename}")

    dialogue_filter = config['DIALOGUE_FILTER'].upper()

    if not dialogue_filter:
        print(f"\033[1;31mПроверка не требуется.\033[0m config['DIALOGUE_FILTER'] == \"\" - не содержит ни одной допущенной категории.")
        return False

    if set(dialogue_filter) == {'A', 'B', 'C'}:
        print(f"\033[1;31mПроверка не требуется.\033[0m config['DIALOGUE_FILTER'] == \"ABC\" - подходят все категории.")
        return True

    try:
        response = generate_qc_json(filter_prompt)
    except Exception as e:
        print(f"\033[1;31mОшибка при запросе к модели: \033[0m {e}")
        return False

    # Получаем критерии и объяснение, если они существуют в ответе
    dialogue_ok = response.get('Критерии классификации', {}).get('Целостность диалога')
    dialogue_response = response.get('Почему я так решил', {}).get('Целостность диалога')

    dialogue_ok_add = ''
    if dialogue_ok is not None:
        if dialogue_ok == 'A':
            dialogue_ok_add = ' (Отлично)'
        if dialogue_ok == 'B':
            dialogue_ok_add = ' (Низкое качество)'
        if dialogue_ok == 'C':
            dialogue_ok_add = ' (Обрыв связи)'

    # Выводим результаты
    print(f"\033[1;31mЦелостность диалога: \033[0m {dialogue_ok}{dialogue_ok_add}")
    print(f"\033[1;31mПочему я так решил:  \033[0m {dialogue_response}")

    # Проверка на соответствие фильтру
    if dialogue_ok is not None and dialogue_ok != "":
        if dialogue_ok in dialogue_filter:
            return True
        else:
            print(f"\033[1;31mОшибка фильтрации:    \033[0m {filename}")
            return False
    else:
        print(f"\033[1;31mОшибка фильтрации, не получен ответ от модели. Файл: \033[0m {filename}")
        return False  # Если не удалось получить ответ, возвращаем False

# ======== ОСНОВНАЯ АНАЛИТИКА ========
# Функция для сбора и отображения ответов с использованием переданного исполнителя
def collect_and_display_responses(prompt_group, executor, filename, file_number):
    # Используем переданный executor для маппинга функции на данные
    results = list(executor.map(generate_qc_json, prompt_group))
    for index, (prompt, response) in enumerate(zip(prompt_group, results)):
        if response is not None:
            group_name = f'Группа {index + 1}'  # Можно настроить генерацию имен групп
            color = '32' if file_number % 2 == 0 else '34'
            print(f'Файл [\033[1;{color}m{str(file_number).zfill(3)}\033[0m]: \033[1;{color}m{filename}\033[0m успешно обработан. \033[1;36m{group_name}\033[0m.')
        else:
            print(f"Ответ не получен для промпта в файле №{file_number}, группа {index + 1}")
    return results

# Функция для обработки запросов OpenAI с фильтрацией
def process_openai_requests(prepared_prompts, config, prog_min=10, prog_max=80):
    # Инициализация исполнителя в главной части скрипта
    current_responses = {}
    total_files = len(prepared_prompts)  # Общее количество файлов
    progress_range_start = prog_min  # Начальное значение прогресса
    progress_range_end = prog_max    # Конечное значение прогресса

    # Шаг прогресса для каждого файла
    progress_step = (progress_range_end - progress_range_start) / total_files

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Проход по всем элементам словаря prepared_prompts
        for file_number, (filename, prompt_group) in enumerate(prepared_prompts.items(), start=1):

            # Проверяем значение stopLoop из JavaScript
            if check_stop_loop():
                return

            # Проверка наличия группы с фильтром
            filter_prompt = next((p for p in prompt_group if p.get('filter') == "1"), None)

            # Проверка фильтра перед обработкой других групп
            if filter_prompt and check_filter(filter_prompt, filename, config):
                # Убираем фильтр из группы, чтобы он не обрабатывался дважды
                prompt_group = [p for p in prompt_group if p != filter_prompt]
                responses = collect_and_display_responses(prompt_group, executor, filename, file_number)
            else:
                # Пропускаем обработку, если фильтр не пройден
                print(f"\033[1;31mПропуск обработки файла {filename} из-за ошибки фильтрации.\033[0m")
                responses = []

            print("--------")
            # Сохраняем собранные ответы, используя имя файла как ключ
            current_responses[filename] = responses

            # Обновляем прогресс в соответствии с шагом
            progress.value = progress_range_start + file_number * progress_step

    return current_responses


# ======== ИТОГОВЫЕ ОТЧЕТЫ ========
# Функции для формирования итоговых отчетов
def collect_and_display_responses_final(prompt_group, executor):
    results = list(executor.map(generate_qc_json, prompt_group))
    '''
    for prompt, response in zip(prompt_group, results):
        if response is not None:
            print(f"\033[1;92mSYSTEM:\033[0m\n{prompt['system']}")
            print(f"\033[1;92mUSER:\033[0m\n{prompt['user']}")
            print(response)
        else:
            print("Ответ не получен для промпта:", prompt)
            '''
    return results

# Инициализация исполнителя и сбор ответов с обновлением прогресса
def process_openai_requests_final(prepared_prompts, config, prog_min=40, prog_max=65):
    current_responses = {}
    total_files = len(prepared_prompts)  # Общее количество файлов
    progress_range_start = prog_min  # Начальное значение прогресса
    progress_range_end = prog_max    # Конечное значение прогресса

    # Шаг прогресса для каждого файла
    progress_step = (progress_range_end - progress_range_start) / total_files

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Проход по всем операторам в prepared_prompts
        for file_number, (operator, prompt_group) in enumerate(prepared_prompts.items(), start=1):

            # Проверяем значение stopLoop из JavaScript
            if check_stop_loop():
                return

            # Собираем ответы
            responses = collect_and_display_responses_final(prompt_group, executor)
            current_responses[operator] = responses

            # Обновляем прогресс в соответствии с шагом
            progress_final.value = progress_range_start + file_number * progress_step

    return current_responses

# @title Функции загрузки и разбора промптов в словарь для дальнейшей обработки

# Парсинг промпта (элемента списка)
def load_markdown_to_dict(markdown_text):
    cleaned_text = markdown_text.strip('\ufeff').strip()
    # Разделяем текст по заголовкам
    sections = re.split(r'(?m)^(?:==> ## )', cleaned_text)

    result_list = []

    for section in sections:
        if section.strip():  # Игнорируем пустые секции
            # Разделяем заголовок от содержимого
            header, *content = section.split('\n', 1)
            header_details = header.split('#', 1)  # Разделяем на основной текст и комментарий
            role = header_details[0].strip()
            comment = header_details[1].strip() if len(header_details) > 1 else None

            # Ищем параметры в заголовке
            params = {}
            match = re.search(r'\((.*?)\)', role)
            if match:
                params_str = match.group(1)
                params = {key.strip(): value.strip() for key, value in (param.split('=') for param in params_str.split(';'))}
                # Удаляем параметры из заголовка
                role = re.sub(r'\(.*?\)', '', role).strip()

            # Обрабатываем содержимое
            text = content[0].strip() if content else ''  # Обрабатываем случай без текста

            # print(role, params, comment)

            # Сохраняем информацию в словарь
            result_list.append({
                'role': role,
                'comment': comment,
                'content': text,
                'params': params,
            })

    return result_list


# Загрузка и разбивка документа на отдельные промпты
def load_prompt(prompt_url):
    if "/edit" in prompt_url:
        index_of_edit = prompt_url.find("/edit") + len("/edit")
        load_url = prompt_url[:index_of_edit]
        load_url = load_url.replace("/edit", "/export?format=txt")
    else:
        print("URL не содержит '/edit'")
        return None

    response = requests.get(load_url).text.strip('\ufeff').strip().split('==========')

    # Создание нового списка для хранения очищенных строк
    prompts_list = []
    for s in response:
        prompts_list.append(load_markdown_to_dict(s.strip().replace('\r\n', '\n')))

    return prompts_list

# @title Функции для подготовки промптов к запросу.

def process_prepared_prompts(dialogue_df, prompts):
    # Преобразуем и объединяем все промпты выбранного метода с диалогами
    prepared_prompts = {}  # Инициализируем prepared_prompts как словарь
    # Проход по всем строкам в dialogue_df
    for index, row in dialogue_df.iterrows():
        # Используем 'Имя файла' как ключ, а результат функции get_combined_prompts как значение
        prepared_prompts[row['Имя файла']] = get_combined_prompts(row['Диалог'], prompts)
    return prepared_prompts


# Вывод подговленных промптов с текстами диалогов в читаемом виде
def print_prepared_prompts(prepared_prompts):
    count = 0
    for filename, tmp_prompts in prepared_prompts.items():
        print(f'FILE: \033[1;94m{filename}\033[1;0m')    # Показывает имя файла для каждого набора промптов
        for prompt in tmp_prompts:
            print(f"\033[1;92mMODEL:\033[0m {prompt.get('model', None)}")
            print(f"\033[1;92mFILTER:\033[0m {prompt.get('filter', None)}")
            print(f"\033[1;92mSYSTEM:\033[0m\n{prompt['system']}")
            print(f"\033[1;92mUSER:\033[0m\n{prompt['user']}")
            count += 1
            if count == 5:  # Ограничиваем вывод первыми пятью промптами
                break
        if count == 5:
            break

# @title Функции для совмещения промптов с диалогами MAIN
def prepare_prompt(group):
    tmp_dict = {}
    model = None  # Инициализируем переменную для хранения модели
    filter = None  # Инициализируем переменную для хранения фильтра

    for role in group:
        if role['role'] == 'system':
            tmp_dict['system'] = role['content']
            # Извлекаем информацию о модели и фильтре, если она есть в параметрах
            model = role.get('params', {}).get('model', None)
            filter = role.get('params', {}).get('filter', None)
        elif role['role'] == 'user':
            tmp_dict['user'] = role['content']
        elif role['role'] == 'assistant':
            tmp_dict['assistant'] = role['content']

    if 'system' in tmp_dict and 'user' in tmp_dict:
        # Извлекаем блок JSON из системного промпта
        json_match = re.search(r'```json\n(.*?)\n```', tmp_dict['system'], re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
            # Преобразовываем текст JSON в словарь
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                # Print more details about the JSON error
                print(f"Error decoding JSON: {e}")
                print(f"JSON Text: {json_text}")  # Print the problematic JSON text
                return None  # Or handle the error in a way suitable for your application

        # Добавляем модель и фильтр в словарь, если они были извлечены
        if model:
            tmp_dict['model'] = model
        if filter:
            tmp_dict['filter'] = filter

        return tmp_dict
    else:
        return None

def get_combined_prompts(dialogue, prompt):
    result = []
    for group in prompt:
        current_prompt = prepare_prompt(group)
        if current_prompt is not None:
            current_prompt['user'] = current_prompt['user'].replace('{{text}}', f'\n{dialogue}')
            result.append(current_prompt)
    return result

# @title Функции для совмещения промптов с диалогами FINAL
def prepare_prompt_final(group, report):
    tmp_dict = {}
    model = None  # Инициализируем переменную для хранения модели

    for role in group:
        if role['role'] == 'system':
            tmp_dict['system'] = role['content']
            # Извлекаем информацию о модели, если она есть в параметрах
            model = role.get('params', {}).get('model', None)
        elif role['role'] == 'user':
            tmp_dict['user'] = role['content']  # Пока оставляем {{text}} для замены ниже

    if 'system' in tmp_dict and 'user' in tmp_dict:
        # Извлекаем блок JSON из системного промпта
        json_match = re.search(r'```json\n(.*?)\n```', tmp_dict['system'], re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
            # Преобразовываем текст JSON в словарь
            json_data = json.loads(json_text)

            # Подготавливаем текст для подстановки на основе словаря report и JSON формы
            text_for_replacement = ""
            if "Выводы по результатам анализа" in json_data:
                # Получаем ключи нужной секции из JSON
                criteria_keys = json_data["Выводы по результатам анализа"].keys()
                # Формируем текст по каждому ключу
                for key in criteria_keys:
                    if key in report:
                        text_for_replacement += f"\n## {key}:\n{report[key]}\n"

            # Заменяем {{text}} на сформированный текст
            tmp_dict['user'] = tmp_dict['user'].replace('{{text}}', text_for_replacement)

        # Добавляем модель в словарь, если она была извлечена
        if model:
            tmp_dict['model'] = model

        return tmp_dict
    else:
        return None

def get_prepared_prompts_final(report, prompt):
    result = []
    for group in prompt:
        current_prompt = prepare_prompt_final(group, report)
        if current_prompt is not None:
            result.append(current_prompt)
    return result

def get_prepared_prompts_final_from_results_dfs(results_dfs, prompts_final):
    # Формирование DataFrame с финальными отчетами (собираем "Почему я так решил" по критериям)
    final_reports_df = pd.DataFrame(get_final_reports(results_dfs))

    # Инициализация prepared_prompts как словаря
    prepared_prompts = {}

    # Проход по всем строкам в final_reports_df
    for _, report in final_reports_df.iterrows():
        operator = report['Оператор']  # Получаем значение оператора из строки
        if operator not in prepared_prompts:
            prepared_prompts[operator] = []  # Инициализация списка для оператора, если его еще нет

        # Добавляем сформированный промпт в список для текущего оператора
        prepared_prompts[operator].append(get_prepared_prompts_final(report['Отчет'], prompts_final))

    # Создаем DataFrame из словаря prepared_prompts
    prepared_prompts_df = pd.DataFrame.from_dict(prepared_prompts, orient='index').transpose()

    # Предпросмотр структуры промптов по операторам
    #print(prepared_prompts_df)

    # Словарь для хранения подготовленных данных
    prepared_prompts = {}

    # Перебор по всем столбцам DataFrame и формирование данных
    for col_name in prepared_prompts_df.columns:
        # Собираем все промпты для текущего оператора
        prompt_group = [item for sublist in prepared_prompts_df[col_name] for item in sublist]
        prepared_prompts[col_name] = prompt_group

    return prepared_prompts

# @title Функции для работы с файлами и обновления результатов. Чекпоинт.

# Сохранение частичных результатов (при работе по отдельным группам)
def save_responses_to_file(responses, out_path):
    with open(out_path, 'w') as f:
        json.dump(responses, f, ensure_ascii=False, indent=4)

# Сохранение результатов целиком
def save_responses_to_file_all(responses, output_path_all):
    with open(output_path_all, 'w') as f:
        json.dump(responses, f, ensure_ascii=False, indent=4)

# Загрузка предыдущих результатов
def load_responses_from_file(output_path_all):
    with open(output_path_all, 'r') as f:
        loaded_responses = json.load(f)
    print("Данные успешно загружены :)")
    return loaded_responses

def update_responses(old_responses, new_responses):
    for file_name, update_entries in new_responses.items():
        if file_name not in old_responses:
            raise ValueError(f"No entry found for key '{file_name}' in loaded responses")

        loaded_entries = old_responses[file_name]

        for update_entry in update_entries:
            update_keys = set(update_entry['Критерии классификации'].keys())  # Множество ключей из обновляемой записи
            found = False

            for idx, loaded_entry in enumerate(loaded_entries):
                loaded_keys = set(loaded_entry['Критерии классификации'].keys())  # Множество ключей из загруженной записи
                if update_keys == loaded_keys:  # Сравниваем множества ключей
                    old_responses[file_name][idx] = update_entry
                    found = True
                    break

            if not found:
                # Если совпадение ключей не найдено, выбрасываем исключение
                raise ValueError(f"No match found for keys in '{file_name}' with criteria keys {update_keys}")

    return old_responses

def process_checkpoint(responses, output_path, output_path_all, test_with_criteria_list):
    # Подключение Google Диска
    drive.mount('/content/drive')

    # Сохранение текущих ответов модели в файл в зависимости от режима работы по отдельным группам или целиком
    if test_with_criteria_list:
        save_responses_to_file(responses, output_path)
    else:
        save_responses_to_file_all(responses, output_path_all)

    # Чтение всех предыдущих ответов модели из файла
    loaded_responses = load_responses_from_file(output_path_all)

    # Обновляем и сохраняем данные, иначе вызываем исключение
    if test_with_criteria_list:
        try:
            updated_responses = update_responses(loaded_responses, responses)
            save_responses_to_file_all(updated_responses, output_path_all)
            print("Ответы успешно обновлены.")
        except ValueError as e:
            print(e)
            raise ValueError("Некорректная работа с файлом при обновлении. Возможно, файл поврежден или устарел.")

    return responses

# @title Функции для декомпозиции/композиции, если используется (экспериментальный функционал)

def process_patterns_123XF(input_dict):
    # Проверка наличия 'Паттерн X' со значением 'A'
    if input_dict.get('Паттерн X') == 'A':
        return 'B'

    # Проверка, что все ключи, содержащие цифры в названии паттернов, имеют значение 'B'
    for key, value in input_dict.items():
        if any(char.isdigit() for char in key) and value != 'B':
            return input_dict.get('Паттерн F')

    return 'B'

def process_patterns_AAA(input_dict):
    # Если все значения равны 'A', вернуть 'A', иначе вернуть 'C'
    return 'A' if all(value == 'A' for value in input_dict.values()) else 'C'

def process_composition(result_responses):
    # Применяем обработку к копии
    for key, value in result_responses.items():
        for item in value:
            for k, v in item['Критерии классификации'].items():
                if isinstance(v, dict):
                    if k == "Презентация врача, услуги":
                        # Применяем обработку для "Презентация врача, услуги"
                        item['Критерии классификации'][k] = process_patterns_123XF(v)
                    elif k == "Представление":
                        # Применяем обработку для "Представление"
                        item['Критерии классификации'][k] = process_patterns_AAA(v)
    return result_responses

# @title Функции постобработки

# Функция для преобразования словаря в читаемый текст
def format_reasoning(data):
    if isinstance(data, dict):
        # Собираем все элементы в читаемый формат
        return "\n  --------\n".join([f"{key}: {value}" for key, value in data.items() if value])
    return data

def result_df_format_reason(df):
    # Применяем функцию ко всему столбцу 'Почему я так решил'
    df['Почему я так решил'] = df['Почему я так решил'].apply(format_reasoning)
    return df

# Размечаем сомнительные оценки

# Добавляем " -" к значениям в соответствующих столбцах
def append_dash(row):
    # Проходим по каждому критерию в списке "Сомнительные критерии"
    for criterion in row['Сомнительные критерии']:
        # Проверяем, что такой столбец существует в DataFrame
        if criterion in row.index:
            # Добавляем " -" к текущему значению столбца
            row[criterion] = str(row[criterion]) + " -"
    return row

# Преобразовываем критерии классификации из словаря в столбцы, устанавливаем порядок столбцов
def result_df_format_criteria(result_df):
    criteria_df = pd.json_normalize(result_df['Критерии классификации'])
    result_df = pd.concat([result_df.drop(columns=['Критерии классификации']), criteria_df], axis=1)

    # Установка порядка столбцов
    column_order = ['Ссылка на файл', 'Имя файла', 'Оператор', 'Диалог', 'Почему я так решил'] + \
                    criteria_df.columns.tolist() + ['Мои сомнения в классификации', 'Сомнительные критерии', 'Цитаты']

    result_df = result_df[column_order]

    # Сброс индекса для добавления порядковых номеров
    result_df.reset_index(drop=True, inplace=True)

    # Сбрасываем индекс, чтобы добавить порядковые номера
    result_df.reset_index(inplace=True)

    return result_df


# Подготавливаем новую структуру данных для сохранения в таблицу и возвращаем результат
def process_responses(result_responses):
    processed_data = {}
    for filename, responses in result_responses.items():
        aggregated_data = {
            "Критерии классификации": {},
            "Почему я так решил": {},
            "Мои сомнения в классификации": "",
            "Сомнительные критерии": [],
            "Цитаты": {}
        }

        for response in responses:
            # Обновление Критерии классификации и Почему я так решил
            if "Критерии классификации" in response:
                aggregated_data["Критерии классификации"].update(response["Критерии классификации"])
            if "Почему я так решил" in response:
                aggregated_data["Почему я так решил"].update(response["Почему я так решил"])

            # Скомбинирование Мои сомнения в классификации в одну строку, разделяя новой строкой
            if "Мои сомнения в классификации" in response and response["Мои сомнения в классификации"]:
                if aggregated_data["Мои сомнения в классификации"]:
                    aggregated_data["Мои сомнения в классификации"] += "\n"
                aggregated_data["Мои сомнения в классификации"] += response["Мои сомнения в классификации"]

            # Собрать уникальные сомнительные критерии
            if "Сомнительные критерии" in response:
                aggregated_data["Сомнительные критерии"].extend(response["Сомнительные критерии"])

            # Цитаты, если присутствуют
            if "Цитаты" in response:
                aggregated_data["Цитаты"].update(response["Цитаты"])

        # Удаление дубликатов сомнительных критериев
        aggregated_data["Сомнительные критерии"] = list(set(aggregated_data["Сомнительные критерии"]))

        processed_data[filename] = aggregated_data

    return processed_data



# Готовим таблицу в DataFrame
def prepare_dataframe(result_responses, dialogue_df, backup_data=None,
                      use_decomposition=False, corr_replace_ac=False,
                      columns_to_replace=None):
    """
    Функция для подготовки и обработки таблицы данных в DataFrame.

    Аргументы:
    result_responses (dict): Обработанные результаты.
    dialogue_df (pd.DataFrame): Исходные данные с диалогами.
    backup_data (dict, optional): Оригинальные данные для сравнения (используются при декомпозиции). По умолчанию None.
    use_decomposition (bool, optional): Использовать декомпозицию/композицию данных. По умолчанию False.
    corr_replace_ac (bool, optional): Заменять значения 'A -' на 'C -' в указанных столбцах. По умолчанию False.
    columns_to_replace (list, optional): Список столбцов для замены значений 'A -' на 'C -'. По умолчанию None.

    Возвращает:
    pd.DataFrame: Итоговый DataFrame после всех преобразований.
    """

    # Декомпозиция/композиция, если используется (экспериментальный функционал)
    if use_decomposition and backup_data is not None:
        result_responses = process_composition(result_responses)
        # Теперь result_responses содержит обработанные данные, а оригинальный словарь остался нетронутым
        print("Оригинальный словарь:")
        print(backup_data)
        print("\nОбработанный словарь:")
        print(result_responses)

    # Производим подготовительную обработку полученных данных для формирования DataFrame
    processed_results = process_responses(result_responses)

    # Формируем DataFrame
    processed_results_df = pd.DataFrame(processed_results).T
    processed_results_df.reset_index(inplace=True)
    processed_results_df.rename(columns={'index': 'Имя файла'}, inplace=True)

    # Объединяем полученные обработанные результаты и исходные данные для сборки итогового результата
    result_df = pd.merge(processed_results_df, dialogue_df, on='Имя файла', how='inner')

    # Форматируем "Почему я так решил". JSON -> читаемый текст
    result_df = result_df_format_reason(result_df)

    # Преобразовываем критерии классификации из словаря в столбцы, устанавливаем порядок столбцов
    result_df = result_df_format_criteria(result_df)

    # Размечаем сомнительные оценки. Добавляем " -" к значениям в соответствующих столбцах. Применяем функцию к каждой строке
    result_df = result_df.apply(append_dash, axis=1)

    # Замена значений "A -" на "C -" в указанных столбцах, если это указано в конфигурации
    if corr_replace_ac and columns_to_replace is not None:
        result_df[columns_to_replace] = result_df[columns_to_replace].replace('A -', 'C -', regex=True)

    return result_df

# Пример вызова функции:
# result_df = prepare_dataframe(result_responses, dialogue_df, backup_data=backup_data,
#                               use_decomposition=True, corr_replace_ac=True,
#                               columns_to_replace=['column1', 'column2'])

# @title Функция восстановления текстовых данные столбца 'Почему я так решил', приведя его к словарю с данными
def parse_reasoning(text):
    # Разделяем текст по строкам, исключая пустые строки
    parts = [part.strip() for part in text.split('--------') if part.strip()]
    # Создаем словарь, где каждая часть разбивается дальше на ключ и значение
    reasoning_dict = {}
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)  # Разделяем только по первому вхождению двоеточия
            reasoning_dict[key.strip()] = value.strip()
    return reasoning_dict

# @title Функция исключающая ответы "B" из "Почему я так решил", если это указано в конфиге

def update_exclude_b(results_dfs):
    # Обработка каждого датафрейма в списке
    for df in results_dfs:
        # Проход по каждой строке датафрейма
        for index, row in df.iterrows():
            # Загрузка словаря из столбца "Почему я так решил"
            criteria_dict = row['Почему я так решил']
            # Проверка каждого ключа в словаре
            keys_to_remove = []
            for key in criteria_dict.keys():
                # Проверяем, есть ли столбец с таким именем и начинается ли его значение с "B"
                if key in df.columns and str(df.at[index, key]).startswith('B'):
                    keys_to_remove.append(key)
            # Удаление ключей, чьи значения начинаются на "B"
            for key in keys_to_remove:
                del criteria_dict[key]
            # Обновление словаря в датафрейме
            df.at[index, 'Почему я так решил'] = criteria_dict

# @title Функция для формирования DataFrame с финальными отчетами (собираем "Почему я так решил" по критериям)

def get_final_reports(results_dfs):
    final_reports = []

    # Перебор всех датафреймов в results_dfs
    for df in results_dfs:
        operator = df['Оператор'].iloc[0]  # Берем оператора из первой строки
        operator_report = {}

        # Собираем уникальные критерии из всех записей в датафрейме
        all_criterias = set()
        df['Почему я так решил'].apply(lambda x: all_criterias.update(x.keys()) if isinstance(x, dict) else None)

        # Подготовка отчета для каждого критерия
        for criteria in all_criterias:
            # Собираем все значения для данного критерия и объединяем их, если критерий присутствует
            criteria_values = df['Почему я так решил'].apply(lambda x: x.get(criteria, "") if isinstance(x, dict) else "").dropna()

            # Фильтруем пустые строки и строки, содержащие только пробелы
            filtered_criteria_values = [value for value in criteria_values if value.strip()]

            if filtered_criteria_values:
                # Объединяем значения через заданный разделитель, избегая пустых вставок
                combined_text = "\n--------\n".join(filtered_criteria_values)
                operator_report[criteria] = combined_text

        # Добавляем информацию об операторе и его отчете в итоговый список
        final_reports.append({"Оператор": operator, "Отчет": operator_report})

    return final_reports

# @title Функции для переформатирования структуры данных в соответствии с операторами в итоговых отчетах

# Функции для обработки списков в тексте ответа модели
def split_list_items(text):
    if isinstance(text, str):
        # Используем регулярное выражение для разделения текста только перед пунктами списка
        items = re.split(r'(?<=\D)\. (?=\d+\.)', text)  # Ищем точку после не-цифры, за которой следует пробел, цифра и точка
        # Соединяем пункты с переносом строки, если список содержит более одного пункта
        formatted_text = '.\n'.join(items)
        return formatted_text
    return text

def process_dataframe(df):
    # Применяем функцию обработки ко всем элементам DataFrame
    for col in df.columns:
        for index, value in df[col].items():
            if isinstance(value, dict):
                for key, subvalue in value.items():
                    # Обрабатываем каждый подсловарь
                    df.at[index, col][key] = split_list_items(subvalue)
    return df


# Функция для обработки списков в ответах модели
def get_restructured_data_df(current_responses):
    restructured_data = {}

    # Перегруппировка данных
    for operator_id, reports in current_responses.items():
        restructured_data[operator_id] = {}
        for report in reports:
            for key in ['Выводы по результатам анализа', 'Рекомендации оператору']:
                for subkey, value in report[key].items():
                    if subkey not in restructured_data[operator_id]:
                        restructured_data[operator_id][subkey] = {}
                    restructured_data[operator_id][subkey][key] = value

    # Вывод новой структуры данных
    '''
    for operator_id, data in restructured_data.items():
        print(f"Operator ID: {operator_id}")
        for key, value in data.items():
            print(f"{key}:")
            for report_type, report_value in value.items():
                print(f"  {report_type}: {report_value}")
            print()  # Для лучшей читаемости
            '''

    # Производим обработку списков в ответах модели и выводим результат
    restructured_data_df = pd.DataFrame(restructured_data)
    restructured_data_df = process_dataframe(restructured_data_df)

    return restructured_data_df

def get_operator_dataframes(restructured_data_df):
    # Создаем пустой DataFrame для каждого оператора
    columns = ['Критерий', 'Выводы', 'Рекомендации']
    operator_dataframes = {}

    # Перебираем каждый столбец (оператора)
    for operator in restructured_data_df.columns:
        data = []
        # Используем .items() для перебора пар индекс-значение в Series
        for criterion, value_dict in restructured_data_df[operator].items():


            # Распаковка данных из словаря для каждого критерия
            conclusions = value_dict.get('Выводы по результатам анализа', '')
            recommendations = value_dict.get('Рекомендации оператору', '')
            data.append([criterion, conclusions, recommendations])

        # Создаем DataFrame для текущего оператора
        operator_df = pd.DataFrame(data, columns=columns)
        operator_dataframes[operator] = operator_df

    return operator_dataframes

def get_all_operators_df(operator_dataframes):
    # Создаем большой DataFrame для всех операторов
    all_operators_df = pd.DataFrame()

    # Итерация по DataFrame каждого оператора и сбор данных в один DataFrame
    for operator, df in operator_dataframes.items():
        # Добавляем столбец с идентификатором оператора
        df['Оператор'] = operator
        # Добавляем данные в общий DataFrame
        all_operators_df = pd.concat([all_operators_df, df], ignore_index=True)

    # Определение нужных столбцов
    all_operators_df = all_operators_df[['Оператор', 'Критерий', 'Выводы', 'Рекомендации']]

    return all_operators_df

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

"""### ======== Безусловно исполняемый код ========"""

# @title Системная конфигурация, ID рабочей таблицы.

# Таблица для работы
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1OO5uLqbgG0AeIOue-cilsHhUuEcvxA_ymov0HXp1NvQ/edit' # INIT URL рабочей таблицы
worksheet_name = 'Конфигурация' # Имя листа с конфигурацией
colab_id = 2 # ID данного ноутбука

# @title Подготовка. Установка OpenAI, импорты

!pip install -q openai requests
!pip install -q --upgrade --upgrade-strategy eager "regex" "charset-normalizer<4" "idna" "urllib3<3" "certifi" "requests" "anyio<4" "distro<2" "sniffio" "h11<0.15" "httpcore==1.*" "annotated-types" "typing-extensions<5" "pydantic-core==2.27.1" "pydantic<3" "jiter<1" "tqdm" "colorama" "openai" "tiktoken" "httpx<0.28"

import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
from google.colab import drive
import json
import pickle
import copy
import re
import requests
from datetime import datetime

from openai import OpenAI
import os
from google.colab import userdata

from time import sleep

import concurrent.futures



# Клиент для работы с таблицей Google
gs_client = gs_client_auth()

# Установка ключа OpenAI
openai_key = userdata.get('OPENAI_API_KEY');
os.environ["OPENAI_API_KEY"] = openai_key

# Сюда помещаем глобальные переменные
class DataHolder:
    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.spreadsheet_id = parse_spreadsheet_id_by_url(spreadsheet_url)

        # Загрузка основной Конфигурации из Google Spreadsheets
        self.config = re_config(gs_client, colab_id, self.spreadsheet_url)
        self.dialogue_df = pd.DataFrame()
        self.prepared_prompts = {}
        self.is_running = True  # Состояние выполнения

    def start_operation(self):
        self.is_running = True  # Сбрасываем флаг перед началом выполнения

    def cancel_operation(self):
        self.is_running = False  # Устанавливаем флаг в False для отмены операции

data_holder = DataHolder(spreadsheet_url)

# @title Внутренняя служебная конфигурация системы для тестов и отладки
VERBOSE_LEVEL = 1

# Тестирование по определенным критериям. При перегруппировке промптов требуется отключить при первом запуске
test_with_criteria_list = False
criteria_list_for_test = ['Презентация врача, услуги']

# Коррекция ошибок
# Применить замену "A -" на "C -". В некоторых случаях, "A -" может означать "C"
corr_replace_ac = False
# Указание столбцов, в которых нужно заменить значения, если включен режим коррекции
columns_to_replace = ['Представление', 'Прощание', 'Возражения']

# Сохранение в промежуточный файл (требуется доступ к Google Drive)
save_responses_to_tmp = False
if save_responses_to_tmp:
    mount_google_drive()
OUTPUT_PATH =     '/content/drive/My Drive/Medsonar/responses.json'     # Для отдельных групп
OUTPUT_PATH_ALL = '/content/drive/My Drive/Medsonar/responses_all.json' # Для результатов целиком
FINAL_REPORT_PATH = '/content/drive/My Drive/Medsonar/final_report_path.json' # Для результатов целиком

# Использование декомпозиции/композиции (экспериментальный функционал)
USE_DECOMPOSITION = False

# Использование раздельных кнопок для аналитики и итоговых отчетов
USE_SEPARATE_BUTTONS = False

"""### ====> **КНОПКА 1 - "ПОЛУЧЕНИЕ ПРОМПТОВ".** Загрузка и предобработка данных <===="""

# @title Функция кнопики 1 -  Загрузка и предобработка данных
def on_upload_button_click (event, client=None, verbose_level=1):
    upload_button.disabled = True
    analytic_button.disabled = True
    final_report_button.disabled = True
    cancel_button.disabled = False
    with output_area:
        clear_output()
        # Устанавливаем начальное значение прогресс-бара
        progress.value = 0
        progress_final.value = 0

        # Перезагрузка основной Конфигурации из Google Spreadsheets
        # Создаем виджет для отображения текста
        config_widget = widgets.HTML('<h2>🕑 Загрузка основной Конфигурации из рабочей таблицы...</h2>')
        display(config_widget)

        data_holder.config = re_config(client, colab_id, spreadsheet_url)

        sleep(1)
        # Обновляем текст в виджете
        config_widget.value = '<h2>✅ Конфигурация успешно загружена.</h2>'

        if verbose_level >= 2:
            display(data_holder.config)

        progress.value = 10

        # Создаем виджет для отображения текста
        dialogue_widget = widgets.HTML('<h2>🕑 Загрузка транскрибаций из рабочей таблицы...</h2>')
        display(dialogue_widget)

        # Загружаем **транскрибации** из рабочей таблицы и выводим статистику
        data_holder.dialogue_df = load_dialogue_df(client, data_holder.config['CURRENT_SPREADSHEET_URL'], data_holder.config)

        sleep(1)
        # Обновляем текст в виджете
        dialogue_widget.value = '<h2>✅ Транскрибации успешно загружены.</h2>'

        progress.value = 20




        if verbose_level >= 1:
            display(HTML('<h2>Статистика<h2>'))
            if verbose_level >= 2:
                display(data_holder.dialogue_df)
            print_operator_stats(data_holder.dialogue_df)

        progress.value = 30


        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            return

        # Загружаем промпты по группам и совмещаем с транскрибациями
        # Создаем виджет для отображения текста
        text_widget = widgets.HTML('<h2>🕑 Загружаем промпты по группам и совмещаем с транскрибациями...</h2>')
        display(text_widget)

        # Выполняем загрузку промптов
        prompts = load_prompt(data_holder.config['PROMPTS_URL_MAIN'])


        progress.value = 70

        # Совмещаем с диалогами
        # Обновляем текст в виджете
        text_widget.value = '<h2>🕑 Совмещаем промпты с транскрибациями...</h2>'
        data_holder.prepared_prompts = process_prepared_prompts(data_holder.dialogue_df, prompts)
        if verbose_level >= 2:
            display(data_holder.prepared_prompts)

        # Сохраняем prepared_prompts в data_holder
        # data_holder.prepared_prompts = prepared_prompts

        progress.value = 90

        # ПРОСТАЯ ПРОВЕРКА. Вывод подговленных промптов с текстами диалогов в читаемом виде
        if verbose_level >= 2:
            display(HTML('<h2>Подговленные промпты с текстами диалогов<h2>'))
            print_prepared_prompts(data_holder.prepared_prompts)

        sleep(1)
        # Обновляем текст в виджете
        text_widget.value = '<h2>✅ Промпты подготовлены к работе. Можно приступать к аналитике.</h2>'

        progress.value = 100

        upload_button.disabled = False
        analytic_button.disabled = False
        final_report_button.disabled = False
        cancel_button.disabled = True

"""### ====> **КНОПКА 2 - "АНАЛИТИКА".** Обработка и сохранение данных <===="""

# @title Функция обработки кнопки 2
def get_result_df(event, client=None, verbose_level=1):
    upload_button.disabled = True
    analytic_button.disabled = True
    final_report_button.disabled = True
    cancel_button.disabled = False
    with output_area:
        clear_output()
        # Устанавливаем начальное значение прогресс-бара
        progress.value = 0
        progress_final.value = 0

        if len(data_holder.prepared_prompts) == 0:
            display(HTML('<h2>❌ Ошибка. Нет данных для обработки. Запустите "Получение промптов".<h2>'))
            set_stop_loop()
            return

        processing_widget = widgets.HTML('<h2>🕑 Этап 1. Обработка и сохранение данных...</h2><h4>&nbsp;</h4>')
        display(processing_widget)

        progress.value = 5

        # Запустите этот код, если вводите API-ключ с клавиатуры
        # openai_key = getpass.getpass("OpenAI API Key:")
        # os.environ["OPENAI_API_KEY"] = openai_key

        progress.value = 10

        # Основной код обработки данных в OpenAI
        # Используем prepared_prompts из data_holder
        # progress = 10..80
        current_responses = process_openai_requests(data_holder.prepared_prompts, data_holder.config, prog_min=10, prog_max=80)
        # Идеальная транскрибация, 49 записей. Выполнено за 11 минут 12 секунд. Расход $ 0.17
        # Транскрибация whisper_api, 49 записей. Выполнено за 7 минут 27 секунд (447 сек). Расход $ 0.17

        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            processing_widget.value = f'<h2>❌ Этап 1. Операция отменена.</h2>'
            return

        progress.value = 80

        # Создаем копию исходного словаря, чтобы не портить оригинал
        result_responses = copy.deepcopy(current_responses)

        progress.value = 84


        # Чекпоинт (v2), если используется сохранение промежуточного результата или работа с отдельными критериями.
        # При работе с отдельными критериями (группами), использование чекпоинта обязательно.
        # Если включен режим работы по отдельным группам, то требуется сперва сохранить общий файл (обработать данные полностью), а затем использовать его для обновления выбранных групп.
        # Метод, в дальнейшем, требует доработки и адаптации под рабочую таблицу.
        if save_responses_to_tmp:
            result_responses = process_checkpoint(result_responses, OUTPUT_PATH, OUTPUT_PATH_ALL, test_with_criteria_list)

        progress.value = 88

        # Создаем копию исходного словаря, чтобы не портить оригинал
        backup_data = copy.deepcopy(result_responses)

        progress.value = 90

        # Готовим таблицу в DataFrame

        result_df = prepare_dataframe(result_responses, data_holder.dialogue_df,
                                      backup_data=backup_data,
                                      use_decomposition=USE_DECOMPOSITION,
                                      corr_replace_ac=corr_replace_ac,
                                      columns_to_replace=columns_to_replace)
        progress.value = 92

        if verbose_level >= 2:
            result_df.head()
            display (result_df)

        progress.value = 96

        # Сохраняем данные
        current_spreadsheet_url = data_holder.config['CURRENT_SPREADSHEET_URL']
        save_masterdata_df(gs_client, current_spreadsheet_url, data_holder.config, result_df)

        display(processing_widget)
        processing_widget.value = f'<h2>✅ Данные успешно обработаны и сохранены.</h2><h4><a href="{current_spreadsheet_url}" target="_blank">Перейти к таблице</a></h4>'

        progress.value = 100

        if not USE_SEPARATE_BUTTONS:
            sleep(2)
            make_final_report(event, client, verbose_level)

        upload_button.disabled = False
        analytic_button.disabled = False
        final_report_button.disabled = False
        cancel_button.disabled = True

"""### ====> **КНОПКА 3 - "ИТОГОВЫЙ ОТЧЕТ".** Создание итогового отчета <===="""

# @title Функция кнопки 3 - Создание итогового отчета

def make_final_report(event, client=None, verbose_level=1):

    data_holder.start_operation()  # Сбрасываем флаг перед началом выполнения

    upload_button.disabled = True
    analytic_button.disabled = True
    final_report_button.disabled = True
    cancel_button.disabled = False

    with output_area:
        clear_output(wait=True)
        processing_widget = widgets.HTML('<h2>🕑 Этап 2. Создание итоговых отчетов...</h2><h4>&nbsp;</h4>')
        display(processing_widget)

        # Устанавливаем начальное значение прогресс-бара
        progress_final.value = 0
        reasons_widget = widgets.HTML('🕑 Загрузка выводов модели, из таблицы Google...')
        display(reasons_widget)

        progress_final.value = 5

        # @title Загрузка листа MasterData из таблицы Google
        current_spreadsheet_url = data_holder.config['CURRENT_SPREADSHEET_URL']
        results_df = load_masterdata_df(gs_client, current_spreadsheet_url, data_holder.config)

        progress_final.value = 10
        reasons_widget.value = f'✅ Выводы модели успешно загружены.'
        sleep(1)

        # Восстанавливаем текстовые данные столбца 'Почему я так решил', приведя его к словарю с данными
        results_df['Почему я так решил'] = results_df['Почему я так решил'].apply(parse_reasoning)

        # Группировка по оператору
        results_dfs = results_df.groupby('Оператор')
        # Создаем список датафреймов, каждый из которых соответствует одному оператору
        results_dfs = [group for _, group in results_dfs]

        # Исключать ответы "B" из словарей "Почему я так решил"
        if data_holder.config['EXCLUDE_B']:
            update_exclude_b(results_dfs)

        progress_final.value = 20
        reasons_widget.value = f'✅ Выводы модели успешно загружены и обработаны.'
        sleep(1)



        prompts_widget = widgets.HTML('🕑 Загрузка промтов...')
        display(prompts_widget)

        # Промпты по группам
        prompts_final = load_prompt(data_holder.config['PROMPTS_URL_FINAL'])

        progress_final.value = 30
        prompts_widget.value = f'🕑 Формирование промптов для модели...'
        sleep(1)

        # Формирование итоговой структуры отчетов для подачи в модель
        prepared_prompts = get_prepared_prompts_final_from_results_dfs(results_dfs, prompts_final)
        if verbose_level >= 2:
            display(prepared_prompts)

        progress_final.value = 40
        prompts_widget.value = f'✅ Промты успешно загружены и подготовлены.'
        sleep(1)



        openai_widget = widgets.HTML('🕑 Создание отчетов...')
        display(openai_widget)

        # @title Основной код запросов к OpenAI
        current_responses = process_openai_requests_final(prepared_prompts, data_holder.config, prog_min=40, prog_max=75)

        # Проверяем значение stopLoop из JavaScript
        if check_stop_loop():
            processing_widget.value = f'<h2>❌ Этап 2. Операция отменена.</h2><h4>&nbsp;</h4>'
            return

        progress_final.value = 75
        openai_widget.value = f'✅ Отчеты успешно сформированы.'
        sleep(1)



        postproc_widget = widgets.HTML('🕑 Постобработка отчетов...')
        display(postproc_widget)

        # Сохранение текущих ответов модели current_responses
        if save_responses_to_tmp:
            save_responses_to_file(current_responses, FINAL_REPORT_PATH)

        progress_final.value = 80

        # @title Производим переформатирование структуры данных в соответствии с операторами
        restructured_data_df = get_restructured_data_df(current_responses)

        # @title Подготовка списка индивидуальных датафреймов для каждого оператора
        operator_dataframes = get_operator_dataframes(restructured_data_df)


        # Получаем датафрейм по всем операторам
        all_operators_df = get_all_operators_df(operator_dataframes)
        if verbose_level >= 2:
            display(all_operators_df)

        progress_final.value = 90
        postproc_widget.value = f'🕑 Сохранение отчетов...'
        sleep(1)

        # Сохраняем итоговые отчеты в таблицу Google SpreadSheets
        save_final_reports_df(gs_client, spreadsheet_url, data_holder.config, all_operators_df)

        progress_final.value = 100
        postproc_widget.value = f'✅ Отчеты успешно сохранены.'
        sleep(1)

        processing_widget.value = f'<h2>✅ Данные успешно обработаны и сохранены.</h2><h4><a href="{current_spreadsheet_url}" target="_blank">Перейти к таблице</a></h4>'

        upload_button.disabled = False
        analytic_button.disabled = False
        final_report_button.disabled = False
        cancel_button.disabled = True

"""### ====> **КНОПКА 4 - "ОТМЕНА".** Отмена обработки <===="""

def canсel_operation(event, client=None, verbose_level=1):
    #global is_running
    if not cancel_button.disabled:
        data_holder.is_running = False  # Устанавливаем флаг в False для отмены операции
        upload_button.disabled = False
        analytic_button.disabled = False
        final_report_button.disabled = False
        cancel_button.disabled = True
        reset_stop_loop()
        with output_area:
            print("❌ Операция отменена")
        progress.value =       0
        progress_final.value = 0

"""# Панель управления модулем аналитики транскрибаций"""

# @title Панель управления модулем аналитики транскрибаций
import ipywidgets as widgets
from IPython.display import display, clear_output, Javascript
from IPython.core.display import HTML
from functools import partial

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
</style>
""")

display(style_html)


# Приветственная надпись
welcome_label = widgets.HTML(
    value=f"""
    <div class='medsonar-header'>
        <span style='font-size: 2rem; font-weight:bold; color:#333;'>Система нейроконтроля качества медицинского центра Медсонар</span>
        <span style='font-size: 1rem; font-weight:bold; color:#333;'><br>Модуль 2. Аналитика транскрибаций</span>
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
    display(HTML("<h1 style='font-size: 20px;'><center>Вас приветствует система нейроконтроля качества! <br><br> Запустите получение конфига и промтов</center></h1>"))

#Виджет полосы статуса
progress =       widgets.IntProgress(min=0, max=100, value=0, layout=widgets.Layout(width='1020px'))
progress_final = widgets.IntProgress(min=0, max=100, value=0, layout=widgets.Layout(width='1020px'))

# Кнопки
upload_button = widgets.Button(description="Получение промтов", layout=widgets.Layout(height='50px', width='300px'))
analytic_button = widgets.Button(description="Аналитика", layout=widgets.Layout(height='50px', width='300px'))
final_report_button = widgets.Button(description="Итоговый отчет", layout=widgets.Layout(height='50px', width='300px'))
cancel_button = widgets.Button(description="Отмена", layout=widgets.Layout(height='50px', width='300px'))
# table_button = widgets.Button(description="Таблица с результатами", layout=widgets.Layout(height='50px', width='300px'))

# Применение стиля к кнопкам и форме для служеьной информации
upload_button.add_class('custom-button')
analytic_button.add_class('custom-button')
final_report_button.add_class('custom-button')
cancel_button.add_class('custom-button')
cancel_button.add_class('cancel-button')
cancel_button.disabled = True
if 'jupyter-button' in cancel_button._dom_classes:
    cancel_button._dom_classes.remove('jupyter-button')
# table_button.add_class('custom-button')
output_area.add_class('output-area')


# Функция отображает интерфейс с кнопками и областями для вывода и прогресса
def display_buttons():
    clear_output(wait=True)
    display(welcome_label)
    # Создаем вертикальный контейнер для кнопок
    if USE_SEPARATE_BUTTONS:
        button_box = widgets.VBox([upload_button, analytic_button, final_report_button, cancel_button],
                                layout=widgets.Layout(width='350px'))
    else:
        analytic_button.description = 'Аналитика + Отчеты'
        button_box = widgets.VBox([upload_button, analytic_button, cancel_button],
                                layout=widgets.Layout(width='350px'))
    # Создаем вертикальный контейнер для output_area и progress
    output_and_progress_box = widgets.VBox([output_area, progress, progress_final])
    # Создаем горизонтальный контейнер
    hbox = widgets.HBox([button_box, output_and_progress_box])
    display(style_html)
    display(hbox)

# Назначение обработчика на кнопку с использованием partial (Кнопка #1)
handler = partial(on_upload_button_click, client=gs_client, verbose_level=VERBOSE_LEVEL)
upload_button.on_click(handler)

# Назначение обработчика на кнопку с использованием partial (Кнопка #2)
handler = partial(get_result_df, client=gs_client, verbose_level=VERBOSE_LEVEL)
analytic_button.on_click(handler)

# Назначение обработчика на кнопку с использованием partial (Кнопка #3)
handler = partial(make_final_report, client=gs_client, verbose_level=VERBOSE_LEVEL)
final_report_button.on_click(handler)

# Назначение обработчика на кнопку с использованием partial (Кнопка #4)
handler = partial(canсel_operation, client=gs_client, verbose_level=VERBOSE_LEVEL)
cancel_button.on_click(handler)

# Вывод виджетов
display(style_html)
display_buttons()

js_code = """
<script>
    // Функция для сброса флага остановки цикла
    function resetStopLoop() {
        if (stopLoop) {
            stopLoop = false;
            console.log("JavaScript: Флаг остановки сброшен, stopLoop = false");
        }
    }
    // Функция для установки флага остановки цикла
    function setStopLoop() {
        cancelButton = document.getElementById('cancelButton');
        cancelButton.click();
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