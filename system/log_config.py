import logging
import logging.handlers as handlers
import os

# создаём форматер
_formatter = logging.Formatter('%(asctime)s %(levelname)-10s %(module)s %(funcName)s: %(message)s')
# форматер для дебаггинга посредством @log из модуля decorators
debug_formatter = logging.Formatter('%(asctime)s %(levelname)-10s: %(message)s')

# меняем директорию для записи лога
LOG_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
os.chdir(LOG_FOLDER_PATH)

# добавляем хендлеры
client_hand = logging.FileHandler('client.log', encoding='utf-8', delay=True)
client_hand.setFormatter(_formatter)
client_hand.setLevel(logging.INFO)
serv_hand = handlers.TimedRotatingFileHandler('server_log.log', when='S', encoding='utf-8', backupCount=10)
serv_hand.setFormatter(_formatter)
serv_hand.setLevel(logging.INFO)
# хэндер для дебаггинга посредством декоратора @log из модуля decorators
debug_hand = logging.FileHandler('debug_messenger.log', encoding='utf-8', delay=True)
debug_hand.setFormatter(debug_formatter)
debug_hand.setLevel(logging.DEBUG)

# создаём логеры для разных модулей мессенджера
log = logging.getLogger('messenger')
log.setLevel(logging.DEBUG)
log_client = logging.getLogger('messenger.client')
log_client.addHandler(client_hand)
log_server = logging.getLogger('messenger.server')
log_server.addHandler(serv_hand)
log_debug = logging.getLogger('messenger.debug')
log_debug.addHandler(debug_hand)

