"""
Общие константы приложения: режимы, диапазоны, поля QSO.
Изменения здесь автоматически учитываются в форме, журнале и экспорте.
"""

# Режимы связи для выбора в форме
MODES = ["AM", "FM", "SSB", "CW", "FT8", "MFSK"]

# Диапазоны для выбора в форме
BANDS = [
    "160M", "80M", "40M", "30M", "20M", "17M", "15M", "12M", "10M", "6M", "2M", "70CM"
]

# Порядок полей одной записи QSO (ключи словаря); совпадает с колонками журнала
QSO_FIELD_NAMES = (
    "call", "name", "city", "qth", "band", "mode",
    "rst_received", "rst_sent", "freq", "comment", "datetime"
)

# Индексы по умолчанию для Choice (SSB=2, 40m=2)
DEFAULT_MODE_INDEX = 2   # SSB
DEFAULT_BAND_INDEX = 2   # 40m

# Заголовки и ширина колонок журнала (порядок должен совпадать с QSO_FIELD_NAMES)
JOURNAL_COLUMNS = [
    ("journal.callsign", 120),
    ("journal.name", 100),
    ("journal.city", 120),
    ("journal.qth", 120),
    ("journal.band", 80),
    ("journal.mode", 80),
    ("journal.rst_received", 120),
    ("journal.rst_sent", 120),
    ("journal.freq", 80),
    ("journal.comment", 250),
    ("journal.datetime", 150),
]
