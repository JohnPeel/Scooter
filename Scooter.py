#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pydle
import yaml
import logging
from util import has_url, get_youtube_info, load_badwords, sanitize, process_url
from commands import process_command

class Scooter(pydle.Client):
    def __init__(self, config):
        self.config = config
        super().__init__(nickname=config['nick'], username=config['user'], realname=config['real'])

    def on_connect(self):
        super().on_connect()

        for channel in self.config['channels']:
            self.join(channel)

    @pydle.coroutine
    def is_identified(self, nickname):
        if (not self.users[nickname]['identified']):
            info = yield self.whois(nickname)
            return info['identified']
        return self.users[nickname]['identified']

    @pydle.coroutine
    def is_admin(self, nickname):
        if (nickname in self.config['admins']):
            identified = yield self.is_identified(nickname)
            return identified
        return False
    
    @pydle.coroutine
    def on_privmsg(self, source, target, message):
        arguments = message.split(' ')
        if (len(arguments) > 1):
            process_command(self, source, target, arguments[0], arguments[1:])

    @pydle.coroutine
    def on_pubmsg(self, source, target, message):
        arguments = message.split(' ')
        if (len(arguments) > 2):
            if (arguments[0].lower() == self.nickname.lower() + ':'):
                process_command(self, source, target, arguments[1], arguments[2:])

        url = has_url(message)
        if url:
            data = process_url(source, url)
            if (data):
                self.message(source, data)

    @pydle.coroutine
    def on_message(self, source, target, message):
        super().on_message(source, target, message)

        if (source == self.nickname):
            self.on_privmsg(source, target, message)
        else:
            self.on_pubmsg(source, target, message)
    
    @pydle.coroutine
    def on_notice(self, source, target, message):
        super().on_notice(source, target, message)
        self.on_privmsg(source, target, message)

def main():
    pool = pydle.ClientPool()

    try:
        config = yaml.safe_load(open('config.yaml', 'r'))

        logging.basicConfig(level=config['loglevel'])

        load_badwords(config['badwords'])

        for server in config['servers']:
            client = Scooter(config['servers'][server])
            pool.connect(client, server, config['servers'][server]['port'], tls=True)
    except yaml.YAMLError as e:
        logging.exception("Error in configuration file: " + str(e))

    pool.handle_forever()

if __name__ == '__main__':
    main()