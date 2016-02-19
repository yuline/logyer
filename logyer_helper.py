#encoding=utf-8
import os
import sys
import traceback
import logging
import logging.handlers
from ConfigParser import SafeConfigParser

#初始化logger对象，返回一个logger元组，分别用于statelog与parselog.采用rorate file类型
def init_loggers(log_dir):
    maxsize=100*1024*1024
    rotate_file_nums=2

    state_log_file=os.path.join(log_dir, 'state.log')
    state_logger=logging.getLogger('slogger')
    state_logger.setLevel(logging.INFO)
    StateFileHandler=logging.handlers.RotatingFileHandler(state_log_file, maxBytes=maxsize, backupCount=rotate_file_nums)
    formatter1=logging.Formatter('%(levelname)s %(asctime)s %(message)s', '%Y/%m/%d_%X')
    StateFileHandler.setFormatter(formatter1)
    state_logger.addHandler(StateFileHandler)

    parse_log_dir=os.path.join(log_dir, 'parse')
    parse_log_file=os.path.join(parse_log_dir, 'unmatch.log')
    parse_logger=logging.getLogger('plogger')
    parse_logger.setLevel(logging.INFO)
    ParseFileHandler=logging.handlers.RotatingFileHandler(parse_log_file, maxBytes=maxsize, backupCount=rotate_file_nums)
    formatter2=logging.Formatter('%(asctime)s %(message)s', '%d/%b/%Y:%X')
    ParseFileHandler.setFormatter(formatter2)
    parse_logger.addHandler(ParseFileHandler)

    loggers=[state_logger, parse_logger]
    for file in ('err5xx.log', 'timeout.log'):
        fpath=os.path.join(parse_log_dir, file)
        logger=logging.getLogger(file.split('.')[0])
        logger.setLevel(logging.WARNING)
        handler=logging.handlers.RotatingFileHandler(fpath, maxBytes=maxsize, backupCount=rotate_file_nums)
        formatter=logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        loggers.append(logger)
    return tuple(loggers)

def exit(num,lock_file):
    """Used to exit the process when catch the exception """
    if os.path.exists(lock_file):
        os.unlink(lock_file)
    sys.exit(num)

def log_state(logger, msg):
    """Used to log the state when catch the exception"""
    tracemsg=traceback.format_exc()
    logmsg='{0}\n{1}'.format(msg, tracemsg).strip()
    logger.error(logmsg)

def read_conf(file):
    """parse the config file and return a list of dict, return empty dict with wrong config"""
    res=[]
    need_options=set(['cut_interval', 'expect_time', 'accept_time', 'servernames', 'pattern'])
    number_options=('cut_interval','expect_time','accept_time')
    parser=SafeConfigParser()
    parser.read(file)
    for fname in parser.sections():
        options=set(parser.options(fname))
        if need_options <= options:
            parser_dict=dict(parser.items(fname))
            d={'logfile':fname}
            #d.update(dict((k,float(v) if '.' in v else int(v) ) for k,v in  parser.items(fname)))
            #d.update({k:float(v) if '.' in v else int(v)  for k,v in  parser.items(fname)})
            d.update({}.fromkeys(options))
            for op in number_options:
                d[op]=float(parser_dict[op]) if '.' in parser_dict[op] else int(parser_dict[op])
            d['servernames']=tuple(s.strip() for s in parser_dict['servernames'].split(','))
            d['pattern']= parser.get(fname, 'pattern')
            res.append(d)
        else :
            print 'Wrong config with {0}'.format(fname)
            continue
    #if res and 'zabbix_server' in parser.defaults():
    #    res.append(parser.defaults()['zabbix_server'])
    return res

if __name__ == '__main__':
    d=read_conf('conf/logster.conf')
    print d
