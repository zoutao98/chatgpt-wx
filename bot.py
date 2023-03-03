# MIT License
import subprocess
import requests
import sys
import pathlib
import os

import json
import threading
import socketserver
from revChatGPT.V3 import Chatbot
import re

my_id = ''
apikey = {'apikey':''}
try:
    with open('apiconfig.json', 'r') as f:
        jsonStr = f.read()
        apikey = json.loads(jsonStr)
except:
    with open('apiconfig.json', 'w') as f:
        json.dump(apikey, f)

if apikey['apikey']:
    chatbot = Chatbot(api_key=apikey['apikey'])
else:
    print(f'请完成apiconfig.json文件中完成key的配置')
    sys.exit()
def inject():
    # WX版本3.9.0.28
    cwd = pathlib.Path(__file__).cwd()
    inject_exe = os.path.join(cwd,'ConsoleInject.exe')
    inject_dll = os.path.join(cwd,'wxhelper.dll')
    subprocess.run(f'{inject_exe} -i WeChat.exe -p {inject_dll}')

def testInject():
    url = 'http://127.0.0.1:19088/api/?type=0'
    for i in range(2):
        try:
            requests.post(url=url)
            return
        except:
            print(f'尝试继续注入hook')
            inject()
    print(f'注入未成功,程序退出')
    sys.exit()

def getSelfId():
    url = 'http://127.0.0.1:19088/api/?type=1'
    response = requests.post(url=url)
    global my_id
    my_id = response.json()['data']['wxid']
    print(my_id)

def startHook():
    url = 'http://127.0.0.1:19088/api/?type=9'
    data = {
        "port": "19099",
        "ip":"127.0.0.1"
    }
    requests.post(url, data=json.dumps(data))


class ReceiveMsgSocketServer(socketserver.BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self):
        conn = self.request
        while True:
            try:
                ptr_data = b""
                while True:
                    data = conn.recv(1024)
                    ptr_data += data
                    if len(data) == 0 or data[-1] == 0xA:
                        break

                msg = json.loads(ptr_data)
                # ReceiveMsgSocketServer.msg_callback(msg)
                thread_msg = threading.Thread(target=ReceiveMsgSocketServer.msg_callback, args=[msg])
                thread_msg.setDaemon(True)
                thread_msg.start()

            except OSError:
                break
            except json.JSONDecodeError:
                pass
            conn.sendall("200 OK".encode())
        conn.close()

    @staticmethod
    def msg_callback(msg):
        msg_type = msg['type']
        content = msg['content']
        from_user = msg['fromUser']
        from_group = msg['fromGroup']
        if msg_type != 49:
            print(msg)
        global my_id
        print(msg_type == 1 and not re.search('chatroom', from_user) and not re.search('chatroom', from_group) and from_user != my_id)
        if msg_type == 1 and not re.search('chatroom', from_user) and not re.search('chatroom', from_group) and from_user != my_id:
            response = chatbot.ask(content)
            url = 'http://127.0.0.1:19088/api/?type=2'
            print(response)
            data = {
                "wxid": from_user,
                "msg": response
            }
            requests.post(url, data=json.dumps(data))


def start_socket_server(port: int = 19099,
                        request_handler=ReceiveMsgSocketServer,
                        main_thread: bool = True) -> int or None:
    ip_port = ("127.0.0.1", port)
    try:
        s = socketserver.ThreadingTCPServer(ip_port, request_handler)
        if main_thread:
            s.serve_forever()
        else:
            socket_server = threading.Thread(target=s.serve_forever)
            socket_server.setDaemon(True)
            socket_server.start()
            return socket_server.ident
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    return None

if __name__ == '__main__':
    testInject()
    getSelfId()
    startHook()
    start_socket_server()

