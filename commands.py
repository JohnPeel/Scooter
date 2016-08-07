# -*- coding: utf-8 -*-

import pydle
from util import requires_admin, sanitize

@requires_admin
def do_join(client, source, target, arguments):
    if (len(arguments) == 1):
        client.notice(target, 'Joining "%s"...' % arguments[0])
        client.join(arguments[0])
    else:
        client.notice(target, 'Usage: join [channel]')

@requires_admin
def do_part(client, source, target, arguments):
    if (len(arguments) == 1):
        client.notice(target, 'Parting "%s"...' % arguments[0])
        client.part(arguments[0])
    else:
        client.notice(target, 'Usage: part [channel]')

@requires_admin
def do_say(client, source, target, arguments):
    if (len(arguments) > 1):
        client.notice(target, 'Sending "%s" to "%s".' % (' '.join(arguments[1:]), arguments[0]))
        client.message(arguments[0], sanitize(' '.join(arguments[1:])))
    else:
        client.notice(target, 'Usage: say [channel or nick] [message]')

@requires_admin
def do_notice(client, source, target, arguments):
    if (len(arguments) > 1):
        client.notice(target, 'Sending "%s" to "%s".' % (' '.join(arguments[1:]), arguments[0]))
        client.notice(arguments[0], sanitize(' '.join(arguments[1:])))
    else:
        client.notice(target, 'Usage: notice [channel or nick] [message]')

@pydle.coroutine
def process_command(client, source, target, command, arguments):
    if ('do_%s' % command in globals()):
        yield globals()['do_%s' % command](client, source, target, arguments)