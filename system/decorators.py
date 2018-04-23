from functools import wraps

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


def mute(mutex):
    def decorator(func):
        @wraps(func)
        def decorated(self, *args, **kwargs):
            mutex.lock()
            res = func(self, *args, **kwargs)
            mutex.unlock()
            return res
        return decorated
    return decorator