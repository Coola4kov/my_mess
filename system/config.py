"""Константы для jim протокола, настройки"""

# Недопустимые клиентские методы
CLIENTS_METHOD_DENIED = ['accept', 'listen']
SERVER_METHOD_DENIED = ['connect']
# Недопустимый потоки данных для клиентского сокента
SOCK_DENIED = ['SOCK_DGRAM']

# Ключи
ACTION = 'action'
TIME = 'time'
USER = 'user'
PASSWORD = 'password'
TYPE = 'type'
TO = 'to'
FROM = 'from'
ENCODING = 'encoding'
MESSAGE = 'message'
ACCOUNT_NAME = 'account_name'
STATUS = 'status'
RESPONSE = 'response'
ERROR = 'error'
ALERT = 'alert'
USER_ID = 'user_id'
QUANTITY = 'quantity'
ROOM = 'room'


# Значения action
PRESENCE = 'presence'
MSG = 'msg'
GET_CONTACTS = 'get_contacts'
CONTACT_LIST = 'contact_list'
ADD_CONTACT = 'change_contact_global'
DEL_CONTACT = 'del_contact'
JOIN = 'join'
LEAVE = 'leave'
PROBE = 'probe'
AUTH = 'authenticate'

# Коды ответов (будут дополняться)
BASIC_NOTICE = 100
OK = 200
ACCEPTED = 202
WRONG_REQUEST = 400  # неправильный запрос/json объект
SERVER_ERROR = 500

# Кортеж из кодов ответов
RESPONSE_CODES = (BASIC_NOTICE, OK, ACCEPTED, WRONG_REQUEST, SERVER_ERROR)
