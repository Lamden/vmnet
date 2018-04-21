import re
import os
import time

def ip_address_regex():
    return r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'

def port_regex():
    return r'([0-9]{4,5})'

def parse_listeners(content):
    listeners = {}
    p_ports = re.compile(r'listening on tcp\:\/\/'+ip_address_regex()+r'\:'+port_regex())
    p_client = re.compile(r'Started listening as '+ip_address_regex())
    for line in content:
        matches = re.findall(p_ports, line)
        for m in matches:
            if not listeners.get(m[1]):
                listeners[m[1]] = 0
            listeners[m[1]] += 1
        matches = re.findall(p_client, line)
        for m in matches:
            listeners[m] = True
    return listeners

def parse_sender_receiver(content):
    senders = []
    receivers = []
    p_sender = re.compile(r'Sending to\.\.\.\ '+ip_address_regex())
    p_receiver = re.compile(ip_address_regex()+r'\: received .* "key": "'+ip_address_regex()+r'"')
    for line in content:
        matches = re.findall(p_sender, line)
        for m in matches:
            senders.append(m)
        matches = re.findall(p_receiver, line)
        for m in matches:
            receivers.append(m)
    return senders, receivers
