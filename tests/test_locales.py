# test_locales_pytest.py
"""
Полный набор тестов для системы локализации Locales с использованием pytest.
"""
import json
import sys
import tempfile
from pathlib import Path
from enum import Enum  # Для создания фиктивного языка в тесте

import pytest

# Импорт тестируемого кода
# Предполагается, что файл называется locales.py и находится в той же директории.
# Если структура другая, например, `from src.locales import Locales, Langs`, нужно изменить импорт.
try:
    from src.locales import Locales, Langs
except ImportError as e:
    pytestmark = pytest.mark.xfail(reason=f"Не удалось импортировать модуль locales: {e}")
    sys.exit(1)


# --- Фикстуры ---

@pytest.fixture(scope="function")
def temp_locale_dir():
    """
    Фикстура: создает временную директорию с mock-файлами локализации.
    Использует данные, совместимые с примером в основном файле.
    """
    ru_data = {
        "app": {"name": "Мое Приложение", "version": "Версия 1.0.0"},
        "navigation": {"home": "Главная", "about": "О нас", "contact": "Контакты"},
        "buttons": {"save": "Сохранить", "cancel": "Отмена", "delete": "Удалить"},
        "forms": {
            "labels": {"username": "Имя пользователя", "email": "Электронная почта"},
            "errors": {"required": "Это поле обязательно.", "invalid_email": "Неверный email."}
        },
        "pages": {
            "home": {"title": "Добро пожаловать!", "features": ["Интерфейс", "Безопасность"]},
            "about": {"title": "О компании", "history": "История с 2010 года."}
        },
        "messages": {"welcome": "Добро пожаловать, {username}!"},
        "complex": {
            "level1": {
                "level2": {
                    "final_value": "Глубокое значение"
                }
            }
        }
    }

    en_data = {
        "app": {"name": "My Application", "version": "Version 1.0.0"},
        "navigation": {"home": "Home", "about": "About Us", "contact": "Contact"},
        "buttons": {"save": "Save", "cancel": "Cancel", "delete": "Delete"},
        "forms": {
            "labels": {"username": "Username", "email": "Email"},
            "errors": {"required": "This field is required.", "invalid_email": "Invalid email."}
        },
        "pages": {
            "home": {"title": "Welcome!", "features": ["Interface", "Security"]},
            "about": {"title": "About Company", "history": "History since 2010."}
        },
        "messages": {"welcome": "Welcome, {username}!"},
        "complex": {
            "level1": {
                "level2": {
                    "final_value": "Deep Value"
                }
            }
        }
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        ru_file = tmp_path / "ru.json"
        en_file = tmp_path / "en.json"

        with open(ru_file, 'w', encoding='utf-8') as f:
            json.dump(ru_data, f, ensure_ascii=False, indent=2)

        with open(en_file, 'w', encoding='utf-8') as f:
            json.dump(en_data, f, ensure_ascii=False, indent=2)

        yield tmp_path  # Передаем путь к временной директории тестовой функции


@pytest.fixture(scope="function")
def locales_instance(temp_locale_dir):
    """Фикстура: создает экземпляр Locales для тестов."""
    # Отключаем логирование в тестах для чистоты вывода
    return Locales(locale_folder=str(temp_locale_dir), log_missing=False, _debug=False)


# --- Тесты ---

class TestLocalesInitialization:
    """Тесты инициализации и базовых свойств."""

    def test_initialization_with_defaults(self, temp_locale_dir):
        """Тест: инициализация с параметрами по умолчанию."""
        locales = Locales(locale_folder=str(temp_locale_dir))
        # Проверяем, что языки доступны как атрибуты
        assert hasattr(locales, 'RU')
        assert hasattr(locales, 'EN')
        # Проверяем язык по умолчанию
        assert locales.get_default() == Langs.RU

    def test_available_languages(self, locales_instance):
        """Тест: проверка доступных языков."""
        available = locales_instance.available_languages()
        assert set(available) == {'ru', 'en'}  # Проверяем, что оба языка загружены

    def test_has_language(self, locales_instance):
        """Тест: проверка наличия конкретного языка."""
        assert locales_instance.has_language(Langs.RU) is True
        assert locales_instance.has_language(Langs.EN) is True

        # Создаем фиктивный enum для теста отсутствующего языка
        # Обходим ограничение Python 3.13 на наследование от непустого Enum
        class FakeLangEnum(Enum):
            FR = "fr"
            DE = "de"

        fake_fr = FakeLangEnum.FR

        # Проверяем, что has_language возвращает False для несуществующего языка
        assert locales_instance.has_language(fake_fr) is False


class TestLocalesDirectAccess:
    """Тесты прямого доступа к языкам."""

    def test_direct_access_ru(self, locales_instance):
        """Тест: прямой доступ к строкам на русском."""
        assert locales_instance.RU.app.name == "Мое Приложение"
        assert locales_instance.RU.buttons.save == "Сохранить"
        assert locales_instance.RU.forms.labels.username == "Имя пользователя"

    def test_direct_access_en(self, locales_instance):
        """Тест: прямой доступ к строкам на английском."""
        assert locales_instance.EN.app.name == "My Application"
        assert locales_instance.EN.buttons.save == "Save"
        assert locales_instance.EN.forms.labels.username == "Username"

    def test_direct_access_missing_key_placeholder(self, locales_instance):
        """Тест: прямой доступ к отсутствующему ключу возвращает placeholder."""
        missing_obj = locales_instance.RU.nonexistent.key
        # Объект должен существовать
        assert missing_obj is not None
        # При приведении к строке должен возвращать placeholder
        assert str(missing_obj) == "<null>"

        # Даже очень глубокий отсутствующий ключ
        deep_missing = locales_instance.EN.a.b.c.d.e.f
        assert str(deep_missing) == "<null>"


class TestLocalesGet:
    """Тесты метода get."""

    def test_get_with_default_language(self, locales_instance):
        """Тест: get использует язык по умолчанию (RU)."""
        # По умолчанию RU
        assert locales_instance.get("app.name") == "Мое Приложение"
        assert locales_instance.get("buttons.save") == "Сохранить"
        assert locales_instance.get("pages.home.title") == "Добро пожаловать!"

    def test_get_with_explicit_language(self, locales_instance):
        """Тест: get с явным указанием языка."""
        assert locales_instance.get("app.name", Langs.EN) == "My Application"
        assert locales_instance.get("buttons.save", Langs.EN) == "Save"
        assert locales_instance.get("pages.home.title", Langs.EN) == "Welcome!"

    def test_get_nested_keys(self, locales_instance):
        """Тест: get с вложенными ключами."""
        assert locales_instance.get("complex.level1.level2.final_value") == "Глубокое значение"
        assert locales_instance.get("complex.level1.level2.final_value", Langs.EN) == "Deep Value"

    def test_get_list_items(self, locales_instance):
        """
        Тест: get с доступом к ключу, значением которого является список.
        Текущая реализация Locales.get возвращает str(список).
        """
        # Метод get НЕ поддерживает индексацию списков через точку (например, "features.0").
        # Вместо этого, если путь валиден и указывает на список, он возвращает его строковое представление.
        result = locales_instance.get("pages.home.features")
        # Проверяем, что возвращается строковое представление списка
        assert result == "['Интерфейс', 'Безопасность']"

        result_en = locales_instance.get("pages.home.features", Langs.EN)
        assert result_en == "['Interface', 'Security']"

        # Проверим, что попытка доступа к несуществующему индексу через get в ключе ведет к placeholder
        # Так как "features.0" не является валидным ключом в словаре (ключ "features.0" отсутствует),
        # а "features" - это список, то get("features.0") должен вернуть placeholder.
        result_invalid_key = locales_instance.get("pages.home.features.0")
        assert result_invalid_key == "<null>"  # Потому что ключ "features.0" не найден в словаре

    def test_get_incomplete_path_to_dict(self, locales_instance):
        """Тест: get с неполным путем, указывающим на словарь."""
        # Путь указывает на словарь, а не на конечную строку/значение
        result = locales_instance.get("app")  # "app" -> {"name": "...", "version": "..."}
        assert result == "<null>"  # get должен вернуть placeholder для неполных путей к словарям

    def test_get_missing_key_with_default(self, locales_instance):
        """Тест: get с отсутствующим ключом и значением по умолчанию."""
        result = locales_instance.get("non.existent.key", default="[Not Found]")
        assert result == "[Not Found]"

    def test_get_missing_key_without_default(self, locales_instance):
        """Тест: get с отсутствующим ключом без значения по умолчанию."""
        result = locales_instance.get("another.missing.key")
        assert result == "<null>"  # Должен вернуть placeholder


class TestLocalesGetRaw:
    """Тесты метода get_raw."""

    def test_get_raw_existing_key(self, locales_instance):
        """Тест: get_raw с существующим ключом."""
        assert locales_instance.get_raw("buttons.cancel") == "Отмена"
        assert locales_instance.get_raw("buttons.cancel", Langs.EN) == "Cancel"

    def test_get_raw_missing_key_with_default(self, locales_instance):
        """Тест: get_raw с отсутствующим ключом и значением по умолчанию."""
        result = locales_instance.get_raw("missing.key", _default="DefValue")
        assert result == "DefValue"

    def test_get_raw_missing_key_without_default(self, locales_instance):
        """Тест: get_raw с отсутствующим ключом без значения по умолчанию."""
        result = locales_instance.get_raw("missing.key")
        assert result is None  # Должен вернуть None


class TestLocalesDefaultLanguage:
    """Тесты установки и получения языка по умолчанию."""

    def test_set_default_language(self, locales_instance):
        """Тест: установка и получение языка по умолчанию."""
        # Изначально RU
        assert locales_instance.get_default() == Langs.RU

        # Устанавливаем EN
        locales_instance.set_default(Langs.EN)
        assert locales_instance.get_default() == Langs.EN

        # Проверяем, что доступ через язык по умолчанию теперь использует EN
        assert locales_instance.app.name == "My Application"  # Доступ через __getattr__
        assert locales_instance.get("app.name") == "My Application"  # get без указания языка

    def test_direct_access_via_default_language(self, locales_instance):
        """Тест: прямой доступ через язык по умолчанию."""
        # Сначала RU
        assert locales_instance.buttons.save == "Сохранить"

        # Переключаем на EN
        locales_instance.set_default(Langs.EN)
        assert locales_instance.buttons.save == "Save"

        # Переключаем обратно на RU
        locales_instance.set_default(Langs.RU)
        assert locales_instance.buttons.save == "Сохранить"


class TestLocalesReload:
    """Тесты перезагрузки локализаций."""

    def test_reload_adds_new_key(self, temp_locale_dir, locales_instance):
        """Тест: reload подхватывает изменения в файлах."""
        # Проверяем, что ключа пока нет
        assert locales_instance.get("newly_added_key") == "<null>"

        # Модифицируем файл ru.json
        ru_file_path = temp_locale_dir / "ru.json"
        with open(ru_file_path, 'r+', encoding='utf-8') as f:
            ru_data_updated = json.load(f)
            ru_data_updated['newly_added_key'] = 'Новый ключ'
            f.seek(0)
            json.dump(ru_data_updated, f, ensure_ascii=False, indent=2)
            f.truncate()

        # Перед перезагрузкой ключа все еще нет
        assert locales_instance.get("newly_added_key") == "<null>"

        # Перезагружаем
        locales_instance.reload()

        # После перезагрузки ключ должен быть доступен
        assert locales_instance.RU.newly_added_key == "Новый ключ"
        assert locales_instance.get("newly_added_key") == "Новый ключ"  # Через язык по умолчанию (RU)


class TestLocalesConfiguration:
    """Тесты настроек placeholder и логирования."""

    def test_set_placeholder(self, temp_locale_dir):
        """Тест: установка пользовательского placeholder'а."""
        locales = Locales(locale_folder=str(temp_locale_dir), log_missing=False)
        assert locales.get("missing.key") == "<null>"  # Placeholder по умолчанию

        locales.set_placeholder("[MISSING]")
        assert locales.get("missing.key") == "[MISSING]"  # Новый placeholder

# --- Конец файла ---