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
IMG_ID = 'img_id'
IMG_PCS = 'img_pcs'
IMG_SEQ = 'img_seq'
IMG_DATA = 'img_data'

# Значения action
PRESENCE = 'presence'
MSG = 'msg'
GET_CONTACTS = 'get_contacts'
GET_CONTACT_IMG = 'get_contact_img'
CONTACT_LIST = 'contact_list'
ADD_CONTACT = 'change_contact_global'
DEL_CONTACT = 'del_contact'
IMG = 'img'
IMG_PARTS = 'img_parts'
JOIN = 'join'
LEAVE = 'leave'
PROBE = 'probe'
AUTH = 'authenticate'
REGISTER = 'register'


# Коды ответов (будут дополняться)
BASIC_NOTICE = 100
OK = 200
ACCEPTED = 202
WRONG_REQUEST = 400  # неправильный запрос/json объект
WRONG_COMBINATION = 402
NOT_FOUND = 404
SERVER_ERROR = 500
CONFLICT = 409

# Кортеж из кодов ответов
RESPONSE_CODES = (BASIC_NOTICE, OK, ACCEPTED, WRONG_REQUEST, SERVER_ERROR, CONFLICT)

# глобальные переменные
SALT = "F`:z6j)BuB9#8$eV"

# расположение смайлов
SMILES = {'smile': 'system/gui/ab.gif',
          'sad': 'system/gui/ac.gif',
          'crazy': 'system/gui/ai.gif'
          }

# Паттерн для разбивки склееных сообщений с помощью re
PATTERN = r'({(?P<msg>[a-zA-Zа-яА-Я0-9\_\-\"\.\,\:\+\\\/\\n\= ])*({(?P=msg)*})*(?P=msg)*})'
