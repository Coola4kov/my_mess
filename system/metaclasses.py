import socket
import dis

from .errors import SocketUseError
from .config import *


class Verifier(type):
    """
    Класс необходимый для проверки использования методов класса socket.socket в клиентской
    и серверной части
    """
    client_class = True

    def __init__(cls, *args, **kwargs):
        cls.verify_socket_methods()
        super().__init__(*args, **kwargs)

    def verify_socket_methods(cls):
        """
        Выполняется проверка используемых в экземпляре метакласса (классе) методов и использование
        объектов socket.socket вне конкретного метода
        :return:
        """
        # print(cls.__dict__)
        for key, value in cls.__dict__.items():
            if not key.startswith('__') or key == '__init__':
                if hasattr(value, '__call__'):
                    cls._attr_check(value)
                elif isinstance(value, socket.socket):
                    raise SocketUseError(class_name=cls.__name__)

    def _attr_check(cls, func):
        """
        Осуществляется провера на использование методов. Проверка осуществляется на основе
        переданного параетра (метода класса). Способ проверки зависит от переменной client_class
        определяющей, является ли класс - клиентской частью приложения или серверной
        :param func:
        :return:
        """
        if cls.client_class:
            methods = CLIENTS_METHOD_DENIED
        else:
            methods = SERVER_METHOD_DENIED
        bytecode = dis.get_instructions(func)
        for instr in bytecode:
            if instr.opname == 'LOAD_ATTR' and instr.argval in methods:
                raise SocketUseError(cls.__name__, func.__name__)
            elif instr.argval in SOCK_DENIED:
                raise SocketUseError(cls.__name__, wrong_stream=True)


class ServerVerifier(Verifier):
    client_class = False


class ClientVerifier(Verifier):
    pass
