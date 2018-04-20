from functools import wraps
from PyQt5.QtCore import QMutex

def log(logger_):
    """
    Декоратор, позволяющий записывать в лог название функции, её аргументы
    :param logger_: обрабатывающий логер
    :return: новая функция
    """
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):

            logger_.info('Выполняется функция {} с параметрами args = {}, kwargs = {}'
                         .format(func.__name__, args, kwargs))
            res = func(*args, **kwargs)
            return res
        return decorated
    return decorator