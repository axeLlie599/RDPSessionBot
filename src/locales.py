"""
Система локализации с поддержкой вложенных ключей и placeholder'ов.

Пример использования:
    locales = Locales()

    # Прямой доступ к языкам
    text_ru = locales.RU.buttons.save  # "Сохранить"
    text_en = locales.EN.buttons.save  # "Save"

    # Получение строк через метод get
    text_default = locales.get("buttons.save")  # "Сохранить" (RU по умолчанию)
    text_explicit = locales.get("messages.welcome", Langs.EN)  # "Welcome!"

    # Установка языка по умолчанию
    locales.set_default(Langs.EN)
    text_via_default = locales.buttons.save  # Доступ через язык по умолчанию (EN)
    text_via_get_default = locales.get("buttons.save") # Также использует язык по умолчанию (EN)

    # Обработка отсутствующих ключей
    missing_key = locales.nonexistent.key  # Возвращает placeholder "<null>"
    missing_key_str = str(locales.nonexistent.key) # Приведение к строке даст placeholder
"""
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from src import config

# Предполагается, что logger определен в src.logger
# from src.logger import logger
# Для демонстрации используем стандартный логгер
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # Простая настройка для примера
default_logger = logging.getLogger()


class Langs(Enum):
    """Поддерживаемые языки"""
    RU = "ru"
    EN = "en"


class LocalizedObject:
    """
    Динамический объект для хранения локализованных данных.
    Позволяет обращаться к ключам как к атрибутам: obj.key.subkey
    Также поддерживает списки: obj.list_attr[index]
    """
    def __init__(self, data: Optional[Union[Dict[str, Any], List[Any]]] = None, placeholder: str = "<null>",
                 log_missing_attrs: bool = False):
        """
        Инициализирует объект с данными.
        Args:
            data: Словарь, список или скалярное значение.
            placeholder: Значение для отсутствующих ключей/индексов.
            log_missing_attrs: Логировать ли обращения к отсутствующим атрибутам/индексам.
        """
        self._placeholder = placeholder
        self._log_missing_attrs = log_missing_attrs
        # Флаг, указывающий, является ли этот объект "пустышкой" для отсутствующих ключей
        self._is_missing_stub = False
        # Флаг, указывающий, представляет ли этот объект список
        self._is_list = False
        self._list_data: List[Any] = []

        if data is not None:
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Рекурсивно создаем вложенные объекты, передавая настройки
                        setattr(self, key, LocalizedObject(value, placeholder, log_missing_attrs))
                    elif isinstance(value, list):
                        # Обрабатываем список
                        setattr(self, key, LocalizedObject(value, placeholder, log_missing_attrs))
                    else:
                        setattr(self, key, value)
            elif isinstance(data, list):
                self._is_list = True
                processed_list = []
                for item in data:
                    if isinstance(item, dict):
                        processed_list.append(LocalizedObject(item, placeholder, log_missing_attrs))
                    elif isinstance(item, list):
                         # Рекурсивно обрабатываем вложенные списки
                         processed_list.append(LocalizedObject(item, placeholder, log_missing_attrs))
                    else:
                        processed_list.append(item)
                self._list_data = processed_list
            else:
                # Если data - скаляр (строка, число и т.д.), сохраняем его как атрибут
                # Это маловероятный сценарий при нормальной инициализации, но обработаем для полноты
                self._scalar_value = data

    @classmethod
    def _create_missing_stub(cls, placeholder: str = "<null>", log_missing_attrs: bool = False):
        """Фабричный метод для создания 'пустышки'."""
        instance = cls(placeholder=placeholder, log_missing_attrs=log_missing_attrs)
        instance._is_missing_stub = True
        return instance

    def __getattr__(self, name: str) -> Union['LocalizedObject', str]:
        """
        Возвращает placeholder или новый 'пустой' LocalizedObject для несуществующих атрибутов.
        Args:
            name: Имя атрибута.
        Returns:
            Значение атрибута, placeholder или новый LocalizedObject.
        """
        # Если это "пустышка", то и все её атрибуты тоже "пустышки"
        if self._is_missing_stub:
            # Возвращаем "пустышку", которая также может обрабатывать индексы []
            return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)
        # Для обычного объекта (не пустышки) проверяем, не является ли он списком
        if self._is_list:
             # Если объект представляет собой список, доступ к атрибутам не имеет смысла
             # Но для совместимости с цепочками вроде obj.missing_list.attr, возвращаем пустышку
             if self._log_missing_attrs:
                 logger.warning(f"Попытка доступа к атрибуту '{name}' у объекта-списка. Возвращается пустышка.")
             return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)

        # Для обычного словареподобного объекта логируем ошибку, если нужно, и возвращаем "пустышку"
        if self._log_missing_attrs:
            logger.error(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        # Возвращаем "пустышку", чтобы можно было продолжать цепочку вызовов
        return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)

    def __getitem__(self, index: Union[int, str]) -> Union['LocalizedObject', str]:
        """
        Позволяет обращаться к элементам, если объект представляет собой список.
        Также используется пустышками для поддержки цепочек obj.missing[0].
        Args:
            index: Индекс (int) или ключ (str) для доступа.
        Returns:
            Элемент списка/значение или пустышка.
        """
        # Если это "пустышка", то и все её элементы тоже "пустышки"
        if self._is_missing_stub:
            return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)

        if self._is_list:
            try:
                # Проверяем тип индекса
                if isinstance(index, int):
                    # Доступ по числовому индексу
                    item = self._list_data[index]
                    # Если элемент уже является LocalizedObject (например, из dict), возвращаем его
                    # Если нет, он будет автоматически преобразован в строку при str()
                    return item
                elif isinstance(index, str):
                     # Доступ по строковому ключу к списку (например, obj.list["key"])
                     # Это нестандартно для списков, но для гибкости можно вернуть пустышку
                     if self._log_missing_attrs:
                         logger.warning(f"Попытка строкового доступа ['{index}'] к списку. Возвращается пустышка.")
                     return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)
                else:
                    # Не int и не str
                    if self._log_missing_attrs:
                        logger.warning(f"Неподдерживаемый тип индекса {type(index)} для списка. Возвращается пустышка.")
                    return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)
            except IndexError:
                if self._log_missing_attrs:
                    logger.warning(f"Индекс {index} выходит за пределы списка (длина {len(self._list_data)})")
                return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)
        else:
            # Попытка индексации не по списку
            if self._log_missing_attrs:
                logger.warning(f"Попытка индексации ['{index}'] у объекта, который не является списком.")
            return LocalizedObject._create_missing_stub(self._placeholder, self._log_missing_attrs)

    def __len__(self) -> int:
        """Возвращает длину списка, если объект представляет собой список."""
        if self._is_missing_stub:
            # Длина пустышки-списка - 0
            return 0
        if self._is_list:
            return len(self._list_data)
        # Для не-списков длина не определена, но __len__ должен возвращать int
        # В реальности это может не вызываться, если объект не является списком
        # Но для полноты картины
        return 0 # Или raise TypeError, но лучше вернуть 0

    def __iter__(self):
        """Позволяет итерироваться по списку, если объект представляет собой список."""
        if self._is_missing_stub:
            # Итерация по пустому списку
            return iter([])
        if self._is_list:
            return iter(self._list_data)
        # Итерация по не-списку не поддерживается
        # raise TypeError(f"'{self.__class__.__name__}' object is not iterable")
        # Лучше вернуть пустой итератор или пустышку-итератор?
        # Для простоты и совместимости с пустышками, возвращаем пустой итератор
        return iter([])

    def __str__(self) -> str:
        """Если объект является 'пустышкой', возвращаем placeholder при приведении к строке.
           Если объект представляет собой список, возвращаем его строковое представление.
        """
        if self._is_missing_stub:
            return self._placeholder
        if self._is_list:
            # Возвращаем строковое представление внутреннего списка
            # Элементы, которые являются LocalizedObject (из dict), будут отображаться как объекты
            # если нужно их строковое значение, нужно явно вызывать str() для каждого элемента
            return str(self._list_data)
        # Если это не "пустышка" и не список, поведение по умолчанию
        # (обычно вызывает ошибку или показывает адрес объекта)
        return super().__str__()

    def __repr__(self) -> str:
        if self._is_missing_stub:
            return f"LocalizedObject(_placeholder='{self._placeholder}', _is_missing_stub=True)"
        if self._is_list:
             return f"LocalizedObject(list, len={len(self._list_data)})"
        return super().__repr__()

    def __dir__(self) -> List[str]:
        """Возвращает список доступных атрибутов."""
        if self._is_list:
            # Для списка нет атрибутов в обычном смысле, но можно добавить методы
            return ['__getitem__', '__len__', '__iter__']
        return list(self.__dict__.keys())


class Locales:
    """
    Система управления локализациями.
    Загружает JSON-файлы из директории локализаций и предоставляет
    удобный доступ к строкам на разных языках.
    """
    # Атрибуты для автокомплита (динамически создаются)
    RU: LocalizedObject
    EN: LocalizedObject

    def __init__(self, locale_folder: str = "./locales", placeholder: str = "<null>", log_missing: bool = True,
                 _debug: bool = False, _logger: Optional[logging.Logger] = None):
        """
        Инициализирует систему локализаций.
        Args:
            locale_folder: Путь к директории с JSON-файлами локализаций.
            placeholder: Значение для отсутствующих ключей.
            log_missing: Логировать ли отсутствующие ключи.
            _debug: Включить режим отладки (дополнительные логи).
            _logger: Кастомный логгер.
        """
        # Инициализируем базовые атрибуты
        self.RU = LocalizedObject()
        self.EN = LocalizedObject()
        self.debug = _debug
        self.logger = _logger if _logger is not None else default_logger

        # Настройки
        self._lf: Path = Path(locale_folder)
        self._placeholder: str = placeholder
        self._log_missing: bool = log_missing

        # Данные
        self._locales_data: Dict[str, Dict[str, Any]] = {}
        self._lang_cache: Dict[str, LocalizedObject] = {}

        # Язык по умолчанию
        self._default_lang: Langs = Langs.RU  # Устанавливаем RU как язык по умолчанию по умолчанию

        # Загружаем локализации
        self.reload()

    def _load_locales(self) -> None:
        """Загружает данные локализации из JSON-файлов."""
        if not (self._lf.exists() and self._lf.is_dir()):
            self.logger.warning(f"Директория локализаций не найдена: {self._lf}")
            return
        for lang in Langs:
            file_path = self._lf / f"{lang.value}.json"
            if file_path.exists() and file_path.stat().st_size > 0:
                try:
                    with open(file_path, 'r', encoding='utf-8') as _f:
                        data = json.load(_f)
                        if data is not None:
                            self._locales_data[lang.value] = data
                        else:
                            self.logger.warning(f"Файл {file_path} содержит пустой JSON")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Ошибка парсинга JSON в файле {file_path}: {e}")
                except IOError as e:
                    self.logger.error(f"Ошибка чтения файла {file_path}: {e}")

    def _create_attributes(self) -> None:
        """Создает атрибуты для каждого языка."""
        for lang_code, lang_data in self._locales_data.items():
            try:
                # Передаем placeholder и log_missing_attrs в дочерние объекты
                lang_obj = LocalizedObject(lang_data, self._placeholder, self._log_missing)
                setattr(self, lang_code.upper(), lang_obj)
                self._lang_cache[lang_code] = lang_obj
            except Exception as e:
                self.logger.error(f"Ошибка создания объекта локализации для {lang_code}: {e}")

    def __getattr__(self, name: str) -> Union[LocalizedObject, str]:
        """
        Позволяет обращаться к языкам и ключам через язык по умолчанию.
        Args:
            name: Имя атрибута (код языка или ключ).
        Returns:
            LocalizedObject для поддерживаемых языков или объект языка по умолчанию для ключей.
        Raises:
            AttributeError: Если атрибут не поддерживается и не является ключом.
        """
        # Если запрашиваемый атрибут - это поддерживаемый язык, возвращаем его объект
        if name in [lang.value.upper() for lang in Langs]:
            # Если язык еще не загружен, возвращаем пустой объект
            if not hasattr(self, name) or not isinstance(getattr(self, name), LocalizedObject):
                return LocalizedObject(placeholder=self._placeholder, log_missing_attrs=self._log_missing)
            return getattr(self, name)

        # Если это не код языка, пробуем найти ключ в языке по умолчанию
        try:
            default_lang_obj = getattr(self, self._default_lang.value.upper())
            if isinstance(default_lang_obj, LocalizedObject):
                return getattr(default_lang_obj, name)
        except AttributeError:
            pass  # Будет вызван основной AttributeError ниже

        # Если и ключ в языке по умолчанию не найден, вызываем исключение
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __dir__(self) -> List[str]:
        """Помогает IDE видеть доступные атрибуты."""
        attrs = list(self.__dict__.keys())
        attrs.extend([lang.value.upper() for lang in Langs])
        # Также добавляем ключи из языка по умолчанию для лучшей видимости в IDE (приблизительно)
        try:
            default_lang_obj = getattr(self, self._default_lang.value.upper())
            if isinstance(default_lang_obj, LocalizedObject):
                attrs.extend(dir(default_lang_obj))
        except AttributeError:
            pass
        return attrs

    def get(self, key: str, lang: Optional[Langs] = None, default: Optional[str] = None) -> str:
        """
        Получает значение по ключу для указанного (или по умолчанию) языка.
        Поддерживает вложенные ключи через точку: "buttons.save"
        Args:
            key: Ключ в формате "key.subkey.subsubkey".
            lang: Язык (по умолчанию используется язык по умолчанию экземпляра).
            default: Значение по умолчанию.
        Returns:
            Строка с переводом или placeholder/default.
        Examples:
            locales.get("buttons.save")
            locales.get("messages.welcome", Langs.EN)
            locales.get("nonexistent.key", default="Default text")
        """
        # Используем язык по умолчанию, если язык не указан
        target_lang = lang if lang is not None else self._default_lang
        try:
            # Получаем данные для языка
            data = self._locales_data.get(target_lang.value, {})
            if not data:
                if self._log_missing:
                    self.logger.warning(f"Язык {target_lang.value} не загружен")
                return default or self._placeholder
            # Разбираем вложенный ключ
            keys = key.split('.')
            current_data = data
            # Проходим по всем ключам кроме последнего
            for k in keys[:-1]:
                if not isinstance(current_data, dict) or k not in current_data:
                    if self._log_missing:
                        self.logger.warning(
                            f"Ключ '{'.'.join(keys[:keys.index(k) + 1])}' не найден в {target_lang.value}"
                        )
                    return default or self._placeholder
                current_data = current_data[k]
            # Получаем последнее значение
            final_key = keys[-1]
            if not isinstance(current_data, dict) or final_key not in current_data:
                if self._log_missing:
                    self.logger.warning(f"Ключ '{key}' не найден в {target_lang.value}")
                return default or self._placeholder
            result = current_data[final_key]
            # Если результат - словарь, это неполный путь
            if isinstance(result, dict):
                if self._log_missing:
                    self.logger.warning(f"Неполный путь к ключу '{key}' в {target_lang.value}")
                return default or self._placeholder
            return str(result)
        except Exception as e:
            if self._log_missing:
                self.logger.error(f"Ошибка получения ключа '{key}' для языка {target_lang.value}: {e}")
            return default or self._placeholder

    def get_raw(self, key: str, lang: Optional[Langs] = None, _default: Optional[str] = None) -> Optional[str]:
        """
        Получает значение по ключу без placeholder'а.
        Args:
            key: Ключ в формате "key.subkey".
            lang: Язык (по умолчанию используется язык по умолчанию экземпляра).
            _default: Значение по умолчанию.
        Returns:
            Строка с переводом, default или None.
        """
        # Используем язык по умолчанию, если язык не указан
        target_lang = lang if lang is not None else self._default_lang
        result = self.get(key, target_lang, _default)
        return result if result != self._placeholder else _default

    def reload(self) -> None:
        """Перезагружает все локализации."""
        # Очищаем данные
        self._locales_data.clear()
        self._lang_cache.clear()
        # Сбрасываем атрибуты языков
        for lang in Langs:
            if hasattr(self, lang.value.upper()):
                setattr(self, lang.value.upper(),
                        LocalizedObject(placeholder=self._placeholder, log_missing_attrs=self._log_missing))
        # Перезагружаем
        self._load_locales()
        self._create_attributes()
        if self.debug:
            self.logger.info("Локализации перезагружены")

    def available_languages(self) -> List[str]:
        """
        Возвращает список доступных языков.
        Returns:
            Список кодов доступных языков.
        """
        return list(self._locales_data.keys())

    def has_language(self, lang: Langs) -> bool:
        """
        Проверяет, загружен ли указанный язык.
        Args:
            lang: Язык для проверки.
        Returns:
            True если язык загружен, иначе False.
        """
        return lang.value in self._locales_data

    def set_placeholder(self, placeholder: str) -> None:
        """
        Устанавливает новый placeholder.
        Args:
            placeholder: Новое значение placeholder'а.
        """
        self._placeholder = placeholder

    def set_log_missing(self, log_missing: bool) -> None:
        """
        Включает/выключает логирование отсутствующих ключей.
        Args:
            log_missing: True для включения логирования.
        """
        self._log_missing = log_missing

    def set_default(self, lang: Langs) -> None:
        """
        Устанавливает язык по умолчанию для этого экземпляра.
        Args:
            lang: Язык по умолчанию (из перечисления Langs).
        Raises:
            ValueError: Если указанный язык не поддерживается.
        """
        if not isinstance(lang, Langs):
            raise ValueError("Язык должен быть элементом перечисления Langs")
        # Проверка на наличие языка в загруженных данных может быть опциональной
        # if not self.has_language(lang):
        #     self.logger.warning(f"Язык {lang.value} не загружен, но установлен как язык по умолчанию.")
        self._default_lang = lang
        if self.debug:
            self.logger.info(f"Язык по умолчанию установлен на {lang.value}")

    def get_default(self) -> Langs:
        """
        Возвращает текущий язык по умолчанию.
        Returns:
            Текущий язык по умолчанию (элемент перечисления Langs).
        """
        return self._default_lang
