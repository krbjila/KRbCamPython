"""
### BEGIN NODE INFO
[info]
name = andor
version = 1
description = server for configuring andor cameras
instancename = %LABRADNODE%_andor
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import sys
from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, returnValue

class AndorServer(LabradServer):
    """Allows configuration of save path for Andor cameras"""
    name = '%LABRADNODE%_andor'

    def __init__(self):
        self.name = 'krbhyperimage_andor'
        super(AndorServer, self).__init__()
        self.axial_fname = ''
        self.vertical_fname = ''

    @setting(1, filename='s', axial='b')
    def set_filename(self, c, filename='', axial=True):
        if axial:
            self.axial_fname = filename
        else:
            self.vertical_fname = filename

    @setting(2, returns='s')
    def get_filename(self, c):
        if c["axial"]:
            returnValue(self.axial_fname)
        else:
            returnValue(self.vertical_fname)

    @setting(3, axial='b')
    def set_axial(self, c, axial):
        c["axial"] = axial

if __name__ == '__main__':
    from labrad import util
    util.runServer(AndorServer())