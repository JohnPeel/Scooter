#!/usr/bin/env python
# -*- coding: utf-8 -*-

import irc
import irc.bot
import irc.strings
import re, json
import collections
from urllib.parse import urlparse, parse_qs
from youtube import yt_service

def to_secs(data):
    data = re.split('(\d+)', data)

    hour = min = sec = 0
    in_time = False
    assert data[0][0] == 'P'
    data[0] = data[0][1:]

    while (len(data) > 0):
        if (data[0] == 'T'):
            in_time = True
            data = data[1:]

        # Implement date....

        if (in_time):
            if (data[1] == 'H'):
                hour = int(data[0])
            if (data[1] == 'M'):
                min = int(data[0])
            if (data[1] == 'S'):
                sec = int(data[0])

        data = data[2:]

    return (hour, min, sec)

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
        (hours, mins, secs) = to_secs(entry['contentDetails']['duration'])
        ret[1] += u' [%.2d:%.2d:%.2d]' % (hours, mins, secs)

    ret[1] += u' (Views: %s)' % entry['statistics']['viewCount']
    
    return ret

url = re.compile('(((https?|ftp):\/\/)|www\.)?(([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)|localhost|([a-zA-Z0-9\-]+\.)*[a-zA-Z0-9\-]+\.(com|net|org|info|biz|gov|name|edu|pro|[a-zA-Z][a-zA-Z]))(:[0-9]+)?((\/|\?)[^ "]*[^ ,;\.:">)])?', re.I)
badwords = ['.kb Wizzup', 's\'cute', 'gucci', 'should of', 'would of', 'could of',
            'need to of', 'alot', 'wouldn\'t of', 'couldn\'t of', 'shouldn\'t of',
            'shouldnt of', 'couldnt of', 'wouldnt of', '.k BenLand100', '.kb BenLand100',
            '.op', 'thru', 'eet', 'ghey', 'dontjoinitsatrap', 'guize', 'exhentai']
for i, badword in enumerate(badwords):
    badwords[i] = re.compile(r'(\s*' + badword[:1] + r')('+ badword[1:] + r'\s*)', re.I or re.U)
goodword = r'\1' + '\xe2\x80\x8c' + r'\2'

url_hooks = {
    'www.youtube.com': [get_youtube, lambda x: x.path[3:] if (x.path[0:2] == '/v') else parse_qs(x.query)['v'][0]],
    'youtube.com': [get_youtube, lambda x: x.path[3:] if (x.path[0:2] == '/v') else parse_qs(x.query)['v'][0]],
    'youtu.be': [get_youtube, lambda x: x.path[1:]],
}

class Scooter(irc.bot.SingleServerIRCBot):
    def __init__(self, nickname, realname, channels, server, port=6667):
        super(Scooter, self).__init__([(server, port)], nickname, realname)
        self.chans = channels
    
    def on_nicknameinuse(self, c, e):
        c.nick('_' + c.get_nickname())

    def on_welcome(self, c, e):
        c.mode(c.get_nickname, '-x')
        for channel in self.chans:
            c.join(channel)

    def on_pubmsg(self, c, e):
        message = ' '.join(e.arguments)
        print('[%s] %s: %s' % (e.target, e.source.split('!')[0], message))
        
        url_pos = url.search(message)
        if url_pos:
            urldata = urlparse(message[url_pos.start():url_pos.end()])
            if (not urldata.scheme):
                urldata = urlparse('http://' + message[url_pos.start():url_pos.end()])

            if (urldata.netloc in url_hooks):
                ret = [False, '']
                try:
                    ret = url_hooks[urldata.netloc][0](e.target, url_hooks[urldata.netloc][1](urldata))
                    for badword in badwords:
                        ret[1] = badword.sub(goodword, ret[1])
                except GeneratorExit:
                    pass
                except Exception as e:
                    print('Exception: %s (on %s)' % (e, urldata))

                if ret[0]:
                    c.privmsg(e.target, ret[1])


def main():
    bot = Scooter('Scooter2', 'Scott Daisy', ['#dgby'], 'irc.rizon.net')
    bot.start()

if __name__ == '__main__':
    main()