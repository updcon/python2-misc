#!/usr/bin/env python
"""
CONNECT AND CLOSE:

>>> host, port = 'localhost', 80
>>> c = SimpleHttpClient((host, port))
>>> c.connect()
>>> c.close()

or

>>> with SimpleHttpClient((host, port)) as c:
...     # ...
...     pass


COMMANDS:

>>> print(c.request('GET', '/'))
>>> print(c.request('HEAD', '/'))
>>> print(c.request('POST', '/', headers={'Content-Type':'text/plain'}, data='file content'))
>>> def rflines():
...     for l in open("file.txt"):
...         yield l
>>> print(c.request('POST', '/', headers={'Content-Type':'text/plain'}, data=rflines()))

"""

import socket
from cStringIO import StringIO
import time
import types
import ssl
import argparse
import sys

from base64 import b64encode

MSGLEN = 4096
CRLF = "\r\n"
# A SIMPLE NOT FOUND URL FOR CLOSE CONNECTION REQUEST
NOT_FOUND_URI = '/-----not-found-%s-uri----' % time.clock()


def read_until(s, match):
    tmp = " " * len(match)
    b = StringIO()

    while not tmp == match:
        c = s.recv(1)
        tmp = "%s%s" % (tmp[1:], c)
        b.write(c)

    return b.getvalue()


def longrecv(s, total):
    chunks = []
    bytes_recd = 0
    while bytes_recd < total:
        chunk = s.recv(min(total - bytes_recd, MSGLEN))
        if chunk == '':
            raise RuntimeError("socket connection broken")
        chunks.append(chunk)
        bytes_recd = bytes_recd + len(chunk)
    return ''.join(chunks)


def read_response(s, method):
    headers = read_until(s, "\r\n\r\n").strip().split("\r\n")
    protocol, status_code, status_msg = headers[0].split(" ", 2)
    status_code = int(status_code)
    headers = dict([_.split(": ", 1) for _ in headers[1:]])

    if method != 'HEAD' and 'Content-Length' in headers:
        data = longrecv(s, int(headers['Content-Length']))
    else:
        data = None

    return dict(protocol=protocol, status=(status_code, status_msg),
                headers=headers), data


class SimpleHttpClient(object):
    def __init__(self, contuple, ssl=False):
        self.contuple = contuple
        self.host = contuple[0]
        self.port = contuple[1]
        self.sock = None
        self.closed = False
        self.ssl = ssl

    def _init_sock(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.ssl:
            s = ssl.wrap_socket(s)
        return s

    def _connect(self, sock):
        sock.connect(self.contuple)

    def connect(self):
        self.sock = self._init_sock()
        self._connect(self.sock)
        self.closed = False

    def _mk_line(self, msg):
        return "%s%s" % (msg, CRLF)

    def _header_msg(self, h, v):
        return "%s: %s%s" % (h, v, CRLF)

    def send(self, *args):
        self.sock.send(*args)

    def send_header(self, h, v):
        self.send(self._header_msg(h, v))

    def send_headers(self, it):
        b = StringIO()
        map(lambda h: b.write(self._header_msg(h[0], h[1])), it)
        b.write(CRLF)
        # b.write(CRLF)
        self.send(b.getvalue())

    def send_first_line(self, hmethod, uri, protocol="HTTP/1.1"):
        self.send("%s %s %s%s" % (hmethod, uri, protocol, CRLF))

    def request(self, method, uri, protocol="HTTP/1.1", headers={}, data=None,
                close=False):
        h = {"Host": "{}:{}".format(self.host, self.port)}
        h.update(headers)

        if close:
            h['Connection'] = 'close'

        self.send_first_line(method, uri, protocol)
        self.send_headers(h.iteritems())

        if not data is None:
            if isinstance(data, types.GeneratorType):
                for d in data:
                    self.send(d)
            else:
                self.send(data)

        r = read_response(self.sock, method)

        r[0].update({'method': method, 'uri': uri, 'req_headers': h})

        if close:
            self.sock.close()
            self.closed = True
        return r

    def close(self):
        """Send a host request for a not found URI
        with 'Connection: close' Header"""
        r = self.request('HEAD', NOT_FOUND_URI, close=True)
        return r

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.closed:
            self.sock.close()
            self.closed = True


def do_test():
    host, port = 'api.tbt-post.net', 443
    with SimpleHttpClient((host, port)) as c:
        res = c.request('GET', '/api/v1/offices', headers={'content-type': 'application/json'})
        # print ">>>>", res[0]
        # pprint.pprint(json.loads(res[-1]))
        print ">>>>", res[0]['status'], len(res[-1]), "bytes"


if __name__ == '__main__':
    # do_test()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--host', help="host to connect", required=True)
    parser.add_argument('-p', '--port', help="port to connect", type=int)
    parser.add_argument('-s', '--ssl', help="use ssl", action='store_true')
    parser.add_argument('-X', '--method', help="method to use",
                        choices=['GET', 'POST', 'PUT', 'DELETE', 'HEAD'],
                        default='GET')
    parser.add_argument('-H', '--headers', help="request header pair, may be multiple", action='append', nargs='*')
    parser.add_argument('-u', '--uri', help="URI part to call")

    parser.add_argument('--user', help="username for Basic Auth")
    parser.add_argument('--password', help="password for Basic Auth")

    parser.add_argument('--process', help="output processor",
                        choices=['zOUT', 'TEXT', 'JSON'])
    parser.add_argument('infile',
                        help="input file for POST|PUT, defaults to stdin",
                        nargs='?',
                        type=argparse.FileType('r'),
                        default=sys.stdin)

    args = parser.parse_args()

    method = args.method or 'GET'
    port = args.port or 80

    if method in ('POST', 'PUT'):
        with args.infile as f:
            data = f.read()
    else:
        args.infile.close()
        del args.infile
        data = None

    headers = dict(k for k in (args.headers or []))
    if not data is None:
        headers['Content-Length'] = str(len(data))

    if args.user:
        headers.update({'Authorization':
                            'Basic %s' %
                            b64encode(str.encode(args.user +
                                                 ":" +
                                                 args.password)).decode('utf-8')})

    with SimpleHttpClient((args.host, port), args.ssl) as c:
        res = c.request(method, args.uri, headers=headers, data=data)

        if args.process == 'JSON':
            from json import loads
            from pprint import pprint

            if res[0]['status'][0] == 200:
                pprint(loads(res[-1], encoding='utf8'))

        elif args.process == 'zOUT':

            print "__RESULT:", res[0]['status']
            print "__LENGTH:", len(res[-1] or '')
            print "__BODY:", res[0]['headers'] if method == 'HEAD' else res[-1]

        elif args.process == 'TEXT':

            print res[-1]

        else:
            pass

        exit(res[0]['status'][0])
