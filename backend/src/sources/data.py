from src.core.constants import SourceType

SOURCES = {
    (
        'Клинические_рекомендации_'
        'Ишемический_инсульт_и_транзиторная_'
        'ишемическая_атака_2024.pdf'
    ): {
        'type': SourceType.CR,
        'name': 'Ишемический инсульт и транзиторная ишемическая атака',
        'date': 2024,
        'url': 'https://cr.minzdrav.gov.ru/preview-cr/814_1',
    },
    'Клинические_рекомендации_геморрагический_инсульт.pdf': {
        'type': SourceType.CR,
        'name': 'Геморрагический инсульт',
        'date': 2025,
        'url': 'https://cr.minzdrav.gov.ru/preview-cr/523_3',
    },
    'Выговская_ОН_реабилитация_после_инсульта.pdf': {
        'type': SourceType.FOND,
        'name': '"Реабилитация после инсульта" Выговская О.Н.',
    },
}
