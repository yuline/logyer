#encoding=utf-8

import re 
import socket
import sys
from parser.LogParser_helper import LogParser
from operator import itemgetter
from collections import defaultdict


class NginxLogParser(LogParser):
    def __init__(self, duration, time_options, servernames, sender_file='/tmp/sender_file', pattern_str=r'(?P<domain>[\w\d\S.]+)\s(?P<ip>(?:\d{1,3}\.){3}\d{1,3})(?:,\s(?:\d{1,3}\.){3}\d{1,3})*\s(?P<response_time>[\d.]+)s\s-\s\[.*?\]\s"(?P<method>[A-Z]+)\s(?P<uri>[^?]+)(?:\?(?P<query_string>[\S]+))?\sHTTP/1.\d"\s(?P<http_code>\d{3})\s\d+\s.*',):
#        super(NginxLogParser,self).__init__()
        self.sender_file=sender_file
        self.time_options=time_options
        self.duration=duration
        self.servernames=servernames
        self.mobjs=dict(zip(servernames, (MetricObject() for i in xrange(len(servernames)))))
        self.regex=re.compile(pattern_str)        
    
    def parse_line(self, line):
        match=self.regex.match(line)
        try:
            if  match:
                res_dict=match.groupdict()
                if not res_dict['domain'] in self.servernames:
                    return
                else:
                    ht=res_dict['domain']
                    uri=res_dict['uri']
                    http_status=int(res_dict['http_code'])
                    response_time=float(res_dict['response_time'])
                    
                    self.mobjs[ht].total+=1
                     
                    # check the http_code
                    if 200 <= http_status < 300:
                        self.mobjs[ht].http_2xx += 1

                        #check the response time
                        if response_time < self.time_options.expect:
                            self.mobjs[ht].time_expect += 1
                        elif response_time < self.time_options.timeout:
                            self.mobjs[ht].time_accept += 1
                        else :
                            self.mobjs[ht].time_timeout += 1
                            url='{domain}{uri}'.format(domain=ht, uri=uri)
                            self.mobjs[ht].timeout_urls[url] += 1
                            raise ParserException('Timeout Response! %s' %  line)
                    elif http_status < 400:
                        self.mobjs[ht].http_3xx += 1
                    elif http_status < 500:
                        self.mobjs[ht].http_4xx += 1
                    else :
                        self.mobjs[ht].http_5xx += 1
                        url='{domain}{uri}'.format(domain=ht, uri=uri)
                        self.mobjs[ht].err5xx_urls[url] += 1
                        raise ParserException('Http 5xx Error! %s' % line)
                    
            
            # the line does not match pattern
            else :
                raise ParserException('Not Match! %s' % line)
        except Exception, e:
            raise
    
    def _get_qps(self):
        for ht in self.servernames:
            self.mobjs[ht].qps = round(self.mobjs[ht].total/self.duration)
        

    def write_sender_file(self):
        self._get_qps()
        content=''
        hostname=socket.gethostname()
        
        for ht in self.servernames:
            sorted_err5xx=sorted(self.mobjs[ht].err5xx_urls.iteritems(), key=itemgetter(1), reverse=True)
            sorted_timeout=sorted(self.mobjs[ht].timeout_urls.iteritems(), key=itemgetter(1), reverse=True)
            err5xx_urls='\t'.join('{0}<{1}>'.format(k,v) for k,v in sorted_err5xx) if sorted_err5xx else 'None'
            timeout_urls='\t'.join('{0}<{1}>'.format(k,v) for k,v in sorted_timeout) if sorted_timeout else 'None'
            
            #err5xx_urls='\t'.join(list(self.mobjs[ht].err5xx_urls)) if self.mobjs[ht].err5xx_urls else 'None'
            #timeout_urls='\t'.join(list(self.mobjs[ht].timeout_urls)) if self.mobjs[ht].timeout_urls else 'None'

            time_expect_key='nums_%ss' % self.time_options.expect
            time_accept_key='nums_%ss' % self.time_options.timeout
            timeout_key='nums_%ss_more' % self.time_options.timeout

#            short_key_tuple=('http_2xx','http_3xx','http_4xx','http_5xx',time_expect_key,time_accept_key,timeout_key,'qps', '5xx_urls', 'timeout_urls')
#            key_tuple=tuple('{0}_{1}'.format(ht, item) for item in short_key_tuple)
#            value_tuple=(self.mobjs[ht].http_2xx, self.mobjs[ht].http_3xx, self.mobjs[ht].http_4xx, self.mobjs[ht].http_5xx, self.mobjs[ht].time_expect, self.mobjs[ht].time_accept, self.mobjs[ht].time_timeout, self.mobjs[ht].qps, err5xx_urls, timeout_urls)
            
            short_key_tuple=('http_5xx',timeout_key,'qps', '5xx_urls', 'timeout_urls')
            key_tuple=tuple('{0}_{1}'.format(ht, item) for item in short_key_tuple)
            value_tuple=(self.mobjs[ht].http_5xx, self.mobjs[ht].time_timeout, self.mobjs[ht].qps, err5xx_urls, timeout_urls)

            for key,value in zip(key_tuple, value_tuple):
                content='\n'.join([content, '{hostname} {k} {v}'.format(hostname=hostname, k=key, v=value)])

        content=content[1:]+'\n'
        with open(self.sender_file, 'a') as f:
            f.write(content)
        
        return content

class ParserException(Exception):
    """Raise this exception if the parse_line function wants to
        throw a 'recoverable' exception - i.e. you want parsing
        to continue but want to skip this line and log a failure."""
    pass


class MetricObject(object):
    def __init__(self):
        self.http_2xx=0
        self.http_3xx=0
        self.http_4xx=0
        self.http_5xx=0
        self.total=0
        self.qps=0
        self.time_expect=0
        self.time_accept=0
        self.time_timeout=0
        self.err5xx_urls=defaultdict(int)
        self.timeout_urls=defaultdict(int)
