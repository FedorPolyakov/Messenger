import subprocess

PROCESS = []

while True:
    CLIENTS = input(f'сколько клиентов нужно будет запустить? ')
    if not CLIENTS.isnumeric():
        print('нужно ввести число!')
    else:
        break

while True:
    ACTION = input(f'Введите q - для закрытия программы, x - для закрытия всех окон, '
                   f's - для запуска сервера и клиента: ')
    if ACTION == 'q':
        break
    elif ACTION == 's':
        PROCESS.append(subprocess.Popen('python server.py', creationflags=subprocess.CREATE_NEW_CONSOLE))
        for i in range(int(CLIENTS)):
            PROCESS.append(subprocess.Popen(f'python client.py -n test_{str(i+1)}',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif ACTION == 'x':
        while PROCESS:
            KILL_ITEM = PROCESS.pop()
            KILL_ITEM.kill()
