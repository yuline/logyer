# encoding=utf-8
import os
import time
import math
import linecache
from pygtail.my_pygtail import Pygtail

class Tailer(object):
    def __init__(self, target_file, offset_file):
        self.target_file=target_file
        self.offset_file=offset_file 
        self.start_time=math.floor(time.time())
        self.duration=0
        try:
            self.pygtailer=Pygtail(target_file, offset_file=offset_file, copytruncate=False)
        except Exception, e:
            raise TailerException(e)

    def yield_line(self):
        #tailer=Pygtail(self.target_file, offset_file=self.offset_file, copytruncate=True)
        try:
            for line in self.pygtailer:
                yield line
        except Exception, e:
            raise TailerException(e)

    def create_state_file(self):
        try :
            for _ in self.pygtailer:
                pass 
        except Exception, e:
            raise TailerException(e)
    
    def _is_rotated(self, cut_interval):
        """
        If the log_file has rotated ,Reture TRUE; otherwise False
        Notice: it only used to detemine the duration between current case and last, so it doesn't achieve the functions.
                part is achieved in Pygtail Class! 
        """
        self.offset_time=math.floor(os.stat(self.offset_file).st_mtime)
        self.duration=self.start_time-self.offset_time

#        offset_last=int(linecache.getline(self.offset_file, 2).strip())
#        current_size=int(os.path.getsize(self.target_file))

#        if current_size < offset_last or self.duration > cut_interval:
#            if self.pygtailer.offset:
#                self.pygtailer.offset=0
#            return True
        if  self.duration > cut_interval:
            self.pygtailer.offset=0

        return self.pygtailer.offset == 0
        
#    def get_duration(self, cut_interval):
#        """
#        Return the appropriate time interval of the readed log lines
#        Notice: when file rotate, will find start time from parse log. It means we have to fix it to other file format
#        """
#        if self._is_rotated(cut_interval):
#            i=1
#            while True:
#                line=linecache.getline(self.target_file, i)
#                if not line:
#                    self.duration = 0
#                else:
#                    for item in line.split():
#                        if '[' == item[0]:
#                            break
#                    else :
#                        i+=1
#                        continue 
#                    time_str=item[1:]
#                    log_start_time=time.mktime(time.strptime(time_str,'%d/%b/%Y:%X'))
#                    self.duration=self.start_time - math.floor(log_start_time)
#                break
#        if self.duration <= 0 :
#            raise TailerExcetion('The calculated duration({value})<=0'.format(value=self.duration))
#        else:
#            return self.duration

    def get_duration(self, cut_interval):
        """
        Return the appropriate time interval of the readed log lines
        Notice: when file rotate, will find start time from parse log. It means we have to fix it to other file format
        """
        if self._is_rotated(cut_interval):
            with open(self.target_file, 'r') as f:
                for line in f:
                    if not line:
                        self.duration=0
                    else:
                        for item in line.split():
                            if '[' == item[0]:
                                time_str=item[1:]
                                log_start_time=time.mktime(time.strptime(time_str, '%d/%b/%Y:%X'))
                                self.duration=self.start_time - math.floor(log_start_time)
                                break
                        else:
                            continue
                    break
        if self.duration <= 0 :
            raise TailerException('The calculated duration({value})<=0'.format(value=self.duration))
        else:
            return self.duration

    def modify_time(self):
        os.utime(self.offset_file, (self.start_time, self.start_time))

class TailerException(Exception):
    pass
