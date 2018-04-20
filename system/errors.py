class DecodedMessageError(Exception):

    def __str__(self):
        return 'Cообщение не является кодированным JSON'


class ClosedSocketError(Exception):
    def __init__(self, sock, *args):
        Exception.__init__(self, *args)
        self.sock = sock

    def __str__(self):
        return 'Пришло пустое сообщение от {}, сокет закрыт'.format(self.sock.getpeername())


class SocketUseError(Exception):
    def __init__(self, class_name, method_name=None, wrong_stream=False, *args):
        self.cls_name = class_name
        self.mth_name = method_name
        self.wrong_stream = wrong_stream
        Exception.__init__(self, *args)

    def __str__(self):
        if self.wrong_stream:
            output = 'Разрешено только использовать транспортный протокол TCP (SOCK_STREAM)'
        elif self.mth_name:
            output = 'Метод {} класса {} использует не доспустимые методы сокетов'.format(self.mth_name, self.cls_name)
        else:
            output = 'Создание сокета вне метода класса {} не разрешено'.format(self.cls_name)
        return output


class WrongPortError(Exception):
    def __init__(self, port=None, *args):
        Exception.__init__(self, *args)
        self.port = port

    def __str__(self):
        if self.port:
            output = 'Данный порт {} не может быть выбран'.format(self.port)
        else:
            output = 'Неверное знаение порта, должен быт integer'
        return output


class WrongInterfaceError(Exception):
    def __init__(self, interface_add, *args):
        Exception.__init__(self, *args)
        self.if_add = interface_add

    def __str__(self):
        return 'Данный интерфейс {} не настроен на сервере'.format(self.if_add)
