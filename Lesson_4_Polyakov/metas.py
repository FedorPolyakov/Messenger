import dis


class ServerMaker(type):
    def __init__(self, class_name, class_bases, class_dict):
        # список методов класса, использущиеся в функциях класса
        methods = []
        # список атрибутов, использующиеся в классе
        attrs = []
        for obj in class_dict:
            try:
                func = dis.get_instructions(class_dict[obj])
            except TypeError:
                pass
            else:
                # если функция, то разбираем ее и смотрим ее методы и атрибуты
                for i in func:
                    # print(i)
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        # print(methods)
        # print(attrs)
        if 'connect' in methods:
            raise TypeError('Использование метода connect недопустимо в серверном классе')
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError('Некорректно инициализирован сокет для работы по TCP')
        
        super().__init__(class_name, class_bases, class_dict)


class ClientMaker(type):
    def __init__(self, class_name, class_bases, class_dict):
        # список методов класса, использущиеся в функциях класса
        methods = []
        # список атрибутов, использующиеся в классе
        attrs = []
        for obj in class_dict:
            try:
                func = dis.get_instructions(class_dict[obj])
            except TypeError:
                pass
            else:
                # если функция, то разбираем ее и смотрим ее методы и атрибуты
                for i in func:
                    # print(i)
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        # print(methods)
        # print(attrs)
        if 'connect' in methods or 'listen' in methods or 'socket' in methods:
            raise TypeError('Использование метода недопустимо в серверном классе')
        if 'get_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError('Отсутствуют вызовы функций, работающих с сокетом')
        super().__init__(class_name, class_bases, class_dict)
