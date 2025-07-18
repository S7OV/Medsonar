# 🏥 Медсонар — система нейроконтроля качества колл-центра
## UI/UX-разработчик (Google Colab)
Сентябрь 2024 — Октябрь 2024

## Описание:
Создание системы автоматического анализа качества обслуживания клиентов в медицинском центре на основе транскрибации и ИИ-анализа аудиозаписей звонков.

## Обязанности:

- Разработка интерактивного пользовательского интерфейса в Google Colab с использованием ipywidgets, HTML, CSS и JavaScript.
- Дизайн кнопок, форм, индикаторов прогресса и панелей вывода данных.
- Интеграция стилей с внешними шрифтами (Montserrat) и адаптация под светлую/тёмную тему.
- Реализация логики "живой" отмены операций через JS.
- Тестирование и оптимизация UX для повышения удобства использования в команде.
## Результат:

Создано 2 модуля с полностью кастомным интерфейсом (транскрибация и аналитика).
Улучшена читаемость и удобство взаимодействия с ноутбуком, упрощён процесс контроля качества звонков.

### ⏹️ Интерактивная отмена операций
Реализована возможность останавливать выполнение длительных операций (например, транскрибации или анализа данных) прямо из пользовательского интерфейса Google Colab.

### Особенности:
Флаг stopLoop управляется через JavaScript.
Проверка флага выполняется в Python с помощью eval_js.
При отмене:
Кнопка блокируется
Отображается информационное сообщение
Выполнение текущего кода прекращается
Пример использования:
```
if check_stop_loop():
    return  # Прервать выполнение
```

## Использованные технологии: 
Python, ipywidgets, HTML, CSS, JavaScript, Google Colab.
