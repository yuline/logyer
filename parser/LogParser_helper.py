#encodeing = utf-8

class LogParser(object):
    def parse_line(self, line):
        pass

    def _write_sender_file(self):
        pass

    def submit_to_zabbix(self):
        pass

class ParserException(Exception):
    """Raise this exception if the parse_line function wants to
        throw a 'recoverable' exception - i.e. you want parsing
        to continue but want to skip this line and log a failure."""
    pass
