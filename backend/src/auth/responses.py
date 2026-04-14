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

AUTH_LOGIN_RESPONSES = {
    HTTPStatus.UNPROCESSABLE_ENTITY.value: {
        'description': 'Неверные имя пользователя или пароль',
        'content': {
            'application/json': {
                'schema': CUSTOM_ERROR_SCHEMA,
            },
        },
    },
}
