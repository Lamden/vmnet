import os
import base64

def compose_msg(data=''):
    salt = os.getenv('SALT','cilantro')
    if type(data) != list:
        data = [data]
    return bytearray(':'.join([salt] + data), 'utf-8')

def decode_msg(msg):
    msg = b''.join(msg).decode('utf-8')
    salt = os.getenv('SALT','cilantro')
    if msg[:len(salt)] == salt:
        data = msg[len(salt)+1:].split(':')
        return data[0], data[1:]
