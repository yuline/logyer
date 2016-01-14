#!/usr/bin/env python
#encoding=utf-8
import os
import sys
import collections
import commands
import time
import multiprocessing
from pygtail.tailer import Tailer, TailerException
from parser.NginxLogParser import NginxLogParser, ParserException
from logster_helper import *

current_dir=os.path.dirname(os.path.realpath(__file__))
conf_file=os.path.join(current_dir, 'conf', 'logster.conf')
offset_dir=os.path.join(current_dir,'offset')
log_dir=os.path.join(current_dir, 'log')
lock_file=os.path.join(current_dir, 'logster.lock')
sender_file='/tmp/sender_file'

#初始化logger对象
state_logger, parse_logger, err5xx_logger, timeout_logger = init_loggers(log_dir)

def main():
    confs=read_conf(conf_file)
    if not confs:
        state_logger.error('Get noting from config file, please check the config file') 
        sys.exit(1)
    
    if os.path.exists(lock_file):
        state_logger.error('Lock file already exists, EXIT!\n')
        sys.exit(1)
    else:
        with open(lock_file,'w') as fd:
            fd.write('{0}'.format(os.getpid()))

    with open(sender_file, 'w') as f:
        pass

    try:
        if len(confs) > 1:
            pool=multiprocessing.Pool(2)
            outputs=pool.map(process, confs)
            pool.close()
            pool.join()
            res=filter(lambda x: '0' in x or '1' in x, outputs)
            if not res:
                raise Exception('Something wrong with tailer, please check state log')
            elif len(res) < len(outputs):
                state_logger.error('Some Task <not all> wrong , please check state log')
        else :
            res=process(confs[0])
            if res != '0' and res != '1' :
                raise Exception('Something wrong with tailer, please check state log')
        
        #将sender file发送到zabbix server
        command_str='/usr/bin/zabbix_sender -c /etc/zabbix/zabbix_agentd.conf -i {0}'.format(sender_file)
        status, result=commands.getstatusoutput(command_str)
        if status != 0:
            state_logger.error('Failed to execute  /usr/bin/zabbix_sender on the system. The Command is %s' % command_str)
    except Exception ,e:
        if not isinstance(e, (TailerException, ParserException)):
            tracemsg=traceback.format_exc()
            print tracemsg, e
            state_logger.error('%s\n%s' % (tracemsg, e))
    except KeyboardInterrupt:
        print 'Quit from console order ctrl+c'
    finally :
        if os.path.exists(sender_file):
            os.unlink(sender_file)
        os.unlink(lock_file)
        state_logger.debug('Unlink Lock file')

def process(conf):
    log_file=conf['logfile']
    offset_file=os.path.join(offset_dir,'%s.offset' % os.path.split(log_file)[1])
    cut_interval, servernames, pattern=conf['cut_interval'], conf['servernames'], conf['pattern']
    time_options=(conf['expect_time'], conf['accept_time'])

    #初始化tailer对象，准备迭代日志行
    print time.strftime('%Y/%m/%d_%X', time.localtime())
    tailer=Tailer(log_file, offset_file)
    state_logger.debug('Initialize Tailer object of {0}'.format(log_file))

    #判断offset_file是否存在，不存在则空运行pygtail,以创建offset_file
    if not os.path.isfile(offset_file):
        tailer.create_state_file()
        state_logger.warning('Create the Offset_file {offset_file} for the Logfile({logfile}) AND EXIT!\n'.format(logfile=log_file, offset_file=offset_file))
        print 'Create the Offset_file {offset_file} for the Logfile({logfile})!'.format(logfile=log_file, offset_file=offset_file)
        return '1'       


    #初始化nametuple对象，用于存储日志响应时间设置的二元组
    Times=collections.namedtuple('TimeOptions', 'expect timeout')
    time_tuple=Times(*time_options)

    state_logger.debug('Start to get duration of {0}'.format(log_file))
    try:
        #获取本次分析的日志的 合适的 时间间隔
        duration=int(tailer.get_duration(cut_interval))
        print 'duration: {0}s --- {1}'.format(duration, log_file)
        state_logger.debug('Parse {0}\'s duation: {1}'.format(log_file, duration) )
        parser=NginxLogParser(duration, time_tuple, servernames, sender_file, pattern)

        state_logger.debug('Start to yield line of {0}'.format(log_file))
        for line in tailer.yield_line():
            try :
                parser.parse_line(line)
            except ParserException, e:
                se=str(e)
                if 'Not Match' in se:
                    parse_logger.warning(se)
                elif '5xx' in se:
                    err5xx_logger.warning(line)
                elif 'Timeout' in se:
                    timeout_logger.warning(line)
                else:
                    parse_logger.error(se)
    except TailerException, t:
        log_state(state_logger, t)
        return '2'
    except Exception, e:
        log_state(state_logger, e)
        return '3'
    else :
        #修正offset_file的mtime为script_start_time
        tailer.modify_time()
    
    state_logger.debug('Start to write result to sendfile of {0} '.format(log_file))

    #将parse result写入sender_file中
    cont=parser.write_sender_file()
    state_logger.debug('Complete the sender file of {0}'.format(log_file))
    print cont
    return '0'

if __name__ == '__main__':
    main()
