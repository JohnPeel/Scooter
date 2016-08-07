# -*- coding: utf-8 -*-

import pydle
import re
import isodate
import collections
from urllib.parse import urlparse, parse_qs
from youtube import yt_service

url = re.compile('(((https?|ftp):\/\/)|www\.)?(([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)|localhost|([a-zA-Z0-9\-]+\.)*[a-zA-Z0-9\-]+\.(com|net|org|info|biz|gov|name|edu|pro|[a-zA-Z][a-zA-Z]))(:[0-9]+)?((\/|\?)[^ "]*[^ ,;\.:">)])?', re.I)
def has_url(data):
    url_pos = url.search(data)
    if url_pos:
        urldata = urlparse(data[url_pos.start():url_pos.end()])
        if (not urldata.scheme):
            urldata = urlparse('http://' + data[url_pos.start():url_pos.end()])
        return urldata
    return None

badwords = []
goodword = r'\1' + '\xe2\x80\x8c' + r'\2'

def load_badwords(new_badwords):
    global badwords
    badwords = []
    for badword in new_badwords:
        badwords.append(re.compile(r'(\s*' + badword[:1] + r')('+ badword[1:] + r'\s*)', re.I or re.U))

def sanitize(data):
    for badword in badwords:
        data = badword.sub(goodword, data)
    return data

last_vids = {}
def get_youtube_info(target, vid):
    global last_vids
    if (not (target in last_vids)):
        last_vids[target] = collections.deque(5*[''], 5)
    
    if (vid in last_vids[target]):
        return None

    last_vids[target].pop()
    last_vids[target].appendleft(vid)

    entry = yt_service.list(part='snippet,statistics,contentDetails', id=vid, maxResults=1).execute()['items'][0]

    ret = u'[YouTube]: %s' % (entry['snippet']['title'])

    if ('duration' in entry['contentDetails']) and (len(entry['contentDetails']['duration']) > 0):
        ret += u' [%s]' % (isodate.strftime(isodate.parse_duration(entry['contentDetails']['duration']), '%H:%M:%S'))

    ret += u' (Views: %s)' % entry['statistics']['viewCount']
    
    return sanitize(ret)

def process_url(target, url):
    url_hooks = {
        'www.youtube.com': lambda x: get_youtube_info(target, x.path[3:]) if (x.path[0:2] == '/v') else get_youtube_info(target, parse_qs(x.query)['v'][0]),
        'youtube.com': lambda x: get_youtube_info(target, x.path[3:]) if (x.path[0:2] == '/v') else get_youtube_info(target, parse_qs(x.query)['v'][0]),
        'youtu.be': lambda x: get_youtube_info(target, x.path[1:]),
    }

    if (url.netloc.lower() in url_hooks):
        return url_hooks[url.netloc.lower()](url)
    return None

def requires_admin(method):
    @pydle.coroutine
    def wrapper(client, source, target, message):
        is_admin = yield client.is_admin(target)
        if (is_admin):
            method(client, source, target, message)
        else:
            client.message(target, 'You do not have permission to use that command.')
    return wrapper