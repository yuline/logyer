#encoding=utf-8

import re
import socket
import sys
from collections import defaultdict
from parser.LogParser_helper import *
from operator import itemgetter

class ProxyParser(LogParser):
    def __init__(self, duration, sender_file='/tmp/sender_file', pattern_str=r'(?P<domain>[\w\d\S.]+)\s(?P<ip>(?:\d{1,3}\.){3}\d{1,3})(?:,\s(?:\d{1,3}\.){3}\d{1,3})*\s(?P<response_time>[\d.]+)s\s-\s\[.*?\]\s"(?P<method>[A-Z]+)\s(?P<uri>[^?]+)(?:\?(?P<query_string>[\S]+))?\sHTTP/1.\d"\s(?P<http_code>\d{3})\s\d+\s.*'):
        super(ProxyParser, self).__init__()
        self.duration=duration
        self.sender_file=sender_file
        self.regex=re.compile(pattern_str)
        self.uris=defaultdict(int)
        self.ips=defaultdict(int)
        self.queries=0
    
    def _is_inner(self, ipaddr):
        if ipaddr == '127.0.0.1':
            return True
        patt='(192.168|172.(1[6-9]|2[0-9]|3[01])|10)[\d.]+'
        reg=re.compile(patt)
        return reg.match(ipaddr)

    def parse_line(self, line):
        match=self.regex.match(line)
        try:
            if match :
                res_dict=match.groupdict()
                url=res_dict['uri']
                ip=res_dict['ip']
                if not self._is_inner(ip):
                    self.uris[url] += 1
                    self.ips[ip] += 1
                    self.queries += 1
            #else:
            #    print 'not match: {error_line}'.format(error_line=line)
            #    raise ParserException('Not Match! %s' % line)
        except Exception, e:
            raise ParserException(e)

    def write_sender_file(self):
        hostname=socket.gethostname()
        sorted_uris=sorted(self.uris.iteritems(), key=itemgetter(1), reverse=True)
        sorted_ips=sorted(self.ips.iteritems(), key=itemgetter(1), reverse=True)
        top_uris=' '.join(['{0}<{1}>'.format(k,v) for k,v in sorted_uris[:15] if self._legal_uri(k)])
        top_ips=' '.join('{0}<{1}>'.format(k,v) for k,v in sorted_ips[:10])
        qps=round(self.queries/self.duration)
        content='{hostname} blog_front_top_uris {uris}\n{hostname} blog_front_top_ips {ips}\n{hostname} blog_front_qps {qps}\n'.format(hostname=hostname, uris=top_uris, ips=top_ips, qps=qps)
        with open(self.sender_file, 'a') as f:
            f.write(content)
        return content

    def _legal_uri(self, uri):
        filters=('favicon','lm','main_v5')
        for f in filters:
            if f in uri:
                return False
        return True
        
        
        

