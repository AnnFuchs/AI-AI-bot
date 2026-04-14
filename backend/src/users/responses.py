from http import HTTPStatus

CUSTOM_ERROR_SCHEMA = {
    'type': 'object',
    'properties': {
        'code': {'type': 'integer', 'title': 'Code'},
        'message': {'type': 'string', 'title': 'Message'},
    },
    'required': ['code', 'message'],
    'title': 'CustomError',
}

USERS_LIST_RESPONSES = {
    HTTPStatus.UNAUTHORIZED.value: {
        'description': 'Неавторизированный пользователь',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.FORBIDDEN.value: {
        'description': 'Доступ запрещен',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
}

USERS_CREATE_RESPONSES = {
    HTTPStatus.BAD_REQUEST.value: {
        'description': 'Ошибка в параметрах запроса',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.UNPROCESSABLE_ENTITY.value: {
        'description': 'Ошибка валидации данных',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
}

USER_GET_BY_ID_RESPONSES = {
    HTTPStatus.UNAUTHORIZED.value: {
        'description': 'Неавторизированный пользователь',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.FORBIDDEN.value: {
        'description': 'Доступ запрещен',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.NOT_FOUND.value: {
        'description': 'Данные не найдены',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.UNPROCESSABLE_ENTITY.value: {
        'description': 'Ошибка валидации данных',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
}

USER_UPDATE_BY_ID_RESPONSES = {
    HTTPStatus.BAD_REQUEST.value: {
        'description': 'Ошибка в параметрах запроса',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.UNAUTHORIZED.value: {
        'description': 'Неавторизированный пользователь',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.FORBIDDEN.value: {
        'description': 'Доступ запрещен',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.NOT_FOUND.value: {
        'description': 'Данные не найдены',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.UNPROCESSABLE_ENTITY.value: {
        'description': 'Ошибка валидации данных',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
}

USER_GET_ME_RESPONSES = {
    HTTPStatus.FORBIDDEN.value: {
        'description': 'Доступ запрещен',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
}

USER_UPDATE_ME_RESPONSES = {
    HTTPStatus.BAD_REQUEST.value: {
        'description': 'Ошибка в параметрах запроса',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.FORBIDDEN.value: {
        'description': 'Доступ запрещен',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
    HTTPStatus.UNPROCESSABLE_ENTITY.value: {
        'description': 'Ошибка валидации данных',
        'content': {'application/json': {'schema': CUSTOM_ERROR_SCHEMA}},
    },
}
