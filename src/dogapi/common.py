import logging
import socket
import sys

import requests

from dogapi.exceptions import *
from dogapi.constants import *

log = logging.getLogger('dd.dogapi')


def is_p3k():
    return sys.version_info[0] == 3

#if is_p3k():
#    import urllib.request
#    import urllib.error
#    import urllib.parse
#else:
#    import urllib2


def get_ec2_instance_id():
    try:
        # Remember the previous default timeout
        old_timeout = socket.getdefaulttimeout()

        # Try to query the EC2 internal metadata service, but fail fast
        socket.setdefaulttimeout(0.25)

        try:
            url = 'http://169.254.169.254/latest/meta-data/instance-id'
            #if is_p3k():
            #    return urllib.request.urlopen(urllib.request.Request(url)).read()
            #else:
            #    return urllib2.urlopen(urllib2.Request(url)).read()
            return requests.get(url).text
        finally:
            # Reset the previous default timeout
            socket.setdefaulttimeout(old_timeout)
    except:
        return socket.gethostname()
