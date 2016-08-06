#!/usr/bin/env python
# -*- coding: utf-8 -*-

import irc
import irc.bot
import irc.strings
import irc.connection
import ssl
import yaml
import re, json
import collections
import isodate
from urllib.parse import urlparse, parse_qs
from youtube import yt_service

last_vids = {}
def get_youtube(target, vid):
    global last_vids
    if (not (target in last_vids)):
        last_vids[target] = collections.deque(5*[''], 5)
    
    if (vid in last_vids[target]):
        return False, ''

    last_vids[target].pop()
    last_vids[target].appendleft(vid)

    entry = yt_service.list(part='snippet,statistics,contentDetails', id=vid, maxResults=1).execute()['items'][0]
    ret = [True, u'[YouTube]: %s' % (entry['snippet']['title'])]

    if ('duration' in entry['contentDetails']) and (len(entry['contentDetails']['duration']) > 0):
        ret[1] += u' [%s]' % (isodate.strftime(isodate.parse_duration(entry['contentDetails']['duration']), '%H:%M:%S'))

    ret[1] += u' (Views: %s)' % entry['statistics']['viewCount']
    
    return ret

url = re.compile('(((https?|ftp):\/\/)|www\.)?(([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)|localhost|([a-zA-Z0-9\-]+\.)*[a-zA-Z0-9\-]+\.(com|net|org|info|biz|gov|name|edu|pro|[a-zA-Z][a-zA-Z]))(:[0-9]+)?((\/|\?)[^ "]*[^ ,;\.:">)])?', re.I)
badwords = []
goodword = r'\1' + '\xe2\x80\x8c' + r'\2'

def load_badwords(new_badwords):
    global badwords
    badwords = []
    for badword in new_badwords:
        badwords.append(re.compile(r'(\s*' + badword[:1] + r')('+ badword[1:] + r'\s*)', re.I or re.U))

url_hooks = {
    'www.youtube.com': [get_youtube, lambda x: x.path[3:] if (x.path[0:2] == '/v') else parse_qs(x.query)['v'][0]],
    'youtube.com': [get_youtube, lambda x: x.path[3:] if (x.path[0:2] == '/v') else parse_qs(x.query)['v'][0]],
    'youtu.be': [get_youtube, lambda x: x.path[1:]],
}

class Scooter(irc.bot.SingleServerIRCBot):
    def __init__(self, nickname, realname, channels, server, admin_key, use_ssl, port=6667):
        if use_ssl:
            super(Scooter, self).__init__([(server, port)], nickname, realname, connect_factory=irc.connection.Factory(wrapper=ssl.wrap_socket))
        else:
            super(Scooter, self).__init__([(server, port)], nickname, realname)

        self.chans = channels
        self.admin = None
        self.admin_key = admin_key

    def reload_config(self, c):
        global badwords
        config = yaml.safe_load(open('config.yaml', 'r'))
        
        load_badwords(config['badwords'])

        if (not (config['server']['nick'] == c.get_nickname())):
            c.nick(config['server']['nick'])

        cur_channels = set(self.channels.keys())
        new_channels = set(config['server']['channels'])

        for channel in cur_channels - new_channels: c.part(channel)
        for channel in new_channels - cur_channels: c.join(channel)

    def on_nicknameinuse(self, c, e):
        c.nick('_' + c.get_nickname())

    def on_welcome(self, c, e):
        c.mode(c.get_nickname(), '-x')
        for channel in self.chans:
            c.join(channel)

    def set_admin(self, admin):
        self.admin = admin # Meh, lambda wont allow just an assign...
        
    def process_command(self, c, e):
        commands = {
            'login': lambda c, e: self.set_admin(e.source) if ((len(e.arguments) == 2) and (e.arguments[1] == self.admin_key)) else c.notice(e.source.nick, 'You do not have access to that command.'),
            'reload': lambda c, e: self.reload_config(c) if ((len(e.arguments) == 1) and (e.source == self.admin)) else c.notice(e.source.nick, 'You do not have access to that command.'),
            'nick': lambda c, e: c.nick(e.arguments[1]) if ((len(e.arguments) == 2) and (e.source == self.admin)) else c.notice(e.source.nick, 'You do not have access to that command.'),
            'say': lambda c, e: c.privmsg(e.arguments[1], ' '.join(e.arguments[2:])) if ((len(e.arguments) >= 3)) and (e.source == self.admin) else c.notice(e.source.nick, 'You do not have access to that command.'),
            'action': lambda c, e: c.action(e.arguments[1], ' '.join(e.arguments[2:])) if ((len(e.arguments) >= 3)) and (e.source == self.admin) else c.notice(e.source.nick, 'You do not have access to that command.'),
            'join': lambda c, e: c.join(e.arguments[1]) if ((len(e.arguments) == 2) and (e.source == self.admin)) else c.notice(e.source.nick, 'You do not have access to that command.'),
            'part': lambda c, e: c.part(e.arguments[1]) if ((len(e.arguments) == 2) and (e.source == self.admin)) else c.notice(e.source.nick, 'You do not have access to that command.'),
        }

        if (e.arguments[0].lower() in commands):
            commands[e.arguments[0].lower()](c, e)

    def on_privmsg(self, c, e):
        message = ' '.join(e.arguments)
        e.arguments = message.split(' ')
        print('[%s] %s: %s' % (e.target, e.source.split('!')[0], message))
        self.process_command(c, e)

    def on_pubmsg(self, c, e):
        message = e.arguments[0]
        e.arguments = message.split(' ')
        print('[%s] %s: %s' % (e.target, e.source.split('!')[0], message))
        
        if (e.arguments[0].lower() == c.get_nickname().lower() + ':'):
            e.arguments.pop(0)
            self.process_command(c, e)

        url_pos = url.search(message)
        if url_pos:
            urldata = urlparse(message[url_pos.start():url_pos.end()])
            if (not urldata.scheme):
                urldata = urlparse('http://' + message[url_pos.start():url_pos.end()])

            netloc = urldata.netloc.lower()
            if (netloc in url_hooks):
                ret = [False, '']
                try:
                    ret = url_hooks[netloc][0](e.target, url_hooks[netloc][1](urldata))
                    for badword in badwords:
                        ret[1] = badword.sub(goodword, ret[1])
                except Exception as e:
                    print('Exception: %s (on %s)' % (e, urldata))

                if ret[0]:
                    c.privmsg(e.target, ret[1])


import logging

def main():
    global badwords
    try:
        config = yaml.safe_load(open('config.yaml', 'r'))

        load_badwords(config['badwords'])

        bot = Scooter(config['server']['nick'], config['server']['real'], config['server']['channels'], config['server']['addr'], config['server']['admin_key'], config['server']['ssl'], config['server']['port'])
        bot.start()
    except yaml.YAMLError as e:
        print("Error in configuration file: ", e)

if __name__ == '__main__':
    main()
