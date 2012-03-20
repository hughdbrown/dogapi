__all__ = [
    'BaseDatadog',
]

import httplib
import os
import logging
import Queue
import re
import socket
import threading
import time
import urllib2
from contextlib import contextmanager
from pprint import pformat
from socket import AF_INET, SOCK_DGRAM
from urllib import urlencode

from dogapi.datadog.metricsapi import MetricsAggregator
from dogapi.datadog.periodic_timer import PeriodicTimer

try:
    import simplejson as json
except ImportError:
    import json

http_log = logging.getLogger('dogapi.http')
log = logging.getLogger('dogapi')

from dogapi.exceptions import *
from dogapi.constants import *

__all__ = [
    'BaseDatadog'
]

class BaseDatadog(object):
    def __init__(self, api_key=None, application_key=None, api_version='v1', api_host=None, timeout=2, max_timeouts=3, backoff_period=300, swallow=True, use_ec2_instance_id=False, statsd_host=None, json_responses=False):

        self.http_conn_cls = httplib.HTTPSConnection
        self._api_host = None
        self.api_host = api_host or os.environ.get('DATADOG_HOST', 'https://app.datadoghq.com')

        # http transport params
        self.backoff_period = backoff_period
        self.max_timeouts = max_timeouts
        self._backoff_timestamp = None
        self._timeout_counter = 0

        # statsd params
        self.statsd_host = statsd_host or 'localhost:8125'

        self.api_key = api_key
        self.api_version = api_version
        self.application_key = application_key
        self.timeout = timeout
        self.swallow = swallow
        self._default_host = socket.gethostname()
        self._use_ec2_instance_id = None
        self.use_ec2_instance_id = use_ec2_instance_id
        self.json_responses = json_responses

        # flush params
        self.flush_interval = 10  # Interval to wait between flushes in seconds.
        self.roll_up_interval = 5

        # We store metrics in a queue (which is thread safe) to ensure that
        # the flush thread plays nice with the main process.
        self._metrics_queue = Queue.Queue()

        self._metrics_aggregator = MetricsAggregator(self.roll_up_interval)
        self._last_flush_time = time.time()
        self._flush_thread = None

    def start_flush_thread(self):
        """
        Start a thread that will flush the metrics, instead of flushing in
        process.
        """

        def log_and_flush():
            log.debug("flushing in thread")
            self._flush_metrics()

        if not self._flush_thread:
            log.info("initializing flush thread")
            self._flush_thread = PeriodicTimer(self.flush_interval, log_and_flush)
            self._flush_thread.daemon = True
            self._flush_thread.start()
        else:
            log.info("flush thread already running")

    def start_flush_greenlet(self):
        import gevent
        def log_and_flush():
            while True:
                log.debug("flushing in greenlet")
                self._flush_metrics()
                gevent.sleep(self.flush_interval)

        gevent.spawn(log_and_flush)
        self._flush_thread = True # FIXME: So we don't flush synchronously.

    def http_request(self, method, path, body=None, **params):
        try:
            # Check if it's ok to submit
            if not self._should_submit():
                raise HttpBackoff("Too many timeouts. Won't try again for {1} seconds.".format(*self._backoff_status()))

            # Construct the url
            if self.api_key:
                params['api_key'] = self.api_key
            if self.application_key:
                params['application_key'] = self.application_key
            url = "/api/%s/%s?%s" % (self.api_version, path.lstrip('/'), urlencode(params))
            conn = self.http_conn_cls(self.api_host)

            # Construct the body, if necessary
            headers = {}
            if isinstance(body, dict):
                body = json.dumps(body)
                headers['Content-Type'] = 'application/json'

            try:
                start_time = time.time()

                # Make the request
                try:
                    conn.request(method, url, body, headers)
                except timeout_exceptions:
                    # Keep a count of the timeouts to know when to back off
                    self._timeout_counter += 1
                    raise HttpTimeout('%s %s timed out after %d seconds.' % (method, url, self.timeout))
                except socket.error, e:
                    # Translate the low level socket error into a more
                    # descriptive one
                    raise ClientError("Could not request %s %s%s: %s" % (method, self.api_host, url, e))

                # If the request succeeded, reset the timeout counter
                self._timeout_counter = 0

                # Parse the response as json
                response = conn.getresponse()
                duration = round((time.time() - start_time) * 1000., 4)
                log.info("%s %s %s (%sms)" % (response.status, method, url, duration))
                response_str = response.read()
                if response_str:
                    try:
                        response_obj = json.loads(response_str)
                    except ValueError:
                        raise ValueError('Invalid JSON response: {0}'.format(response_str))

                    if response_obj and 'errors' in response_obj:
                        raise ClientError(response_obj['errors'])
                else:
                    response_obj = {}
                return response_obj
            finally:
                conn.close()
        except ClientError, e:
            if self.swallow:
                log.error(str(e))
            else:
                raise

    def statsd_request(self, messages):
        if not isinstance(messages, (list, tuple)):
            messages = [messages]

        address = tuple(self.statsd_host.split(":"))
        address = address[0], int(address[1])
        udp_sock = socket.socket(AF_INET, SOCK_DGRAM)
        for message in messages:
            udp_sock.sendto(message, address)

    def use_ec2_instance_id():
        def fget(self):
            return self._use_ec2_instance_id

        def fset(self, value):
            self._use_ec2_instance_id = value

            if value:
                try:
                    # Remember the previous default timeout
                    old_timeout = socket.getdefaulttimeout()

                    # Try to query the EC2 internal metadata service, but fail fast
                    socket.setdefaulttimeout(0.25)

                    try:
                        host = urllib2.urlopen(urllib2.Request('http://169.254.169.254/latest/meta-data/instance-id')).read()
                    finally:
                        # Reset the previous default timeout
                        socket.setdefaulttimeout(old_timeout)
                except Exception:
                    host = socket.gethostname()

                self._default_host = host
            else:
                self._default_host = socket.gethostname()

        def fdel(self):
            del self._use_ec2_instance_id

        return locals()
    use_ec2_instance_id = property(**use_ec2_instance_id())

    def api_host():
        def fget(self):
            return self._api_host

        def fset(self, value):
            match = re.match('^(https?)://(.*)', value)
            http_conn_cls = httplib.HTTPSConnection

            if match:
                host = match.group(2)
                if match.group(1) == 'http':
                    http_conn_cls = httplib.HTTPConnection
            else:
                host = value

            self._api_host = host
            self.http_conn_cls = http_conn_cls
        return locals()
    api_host = property(**api_host())

    # Private functions

    def _should_submit(self):
        """ Returns True if we're in a state where we should make a request
        (backoff expired, no backoff in effect), false otherwise.
        """
        now = time.time()
        should_submit = False

        # If we're not backing off, but the timeout counter exceeds the max
        # number of timeouts, then enter the backoff state, recording the time
        # we started backing off
        if not self._backoff_timestamp and self._timeout_counter >= self.max_timeouts:
            log.info("Max number of dogapi timeouts exceeded, backing off for {0} seconds".format(self.backoff_period))
            self._backoff_timestamp = now
            should_submit = False

        # If we are backing off but the we've waiting sufficiently long enough
        # (backoff_retry_age), exit the backoff state and reset the timeout
        # counter so that we try submitting metrics again
        elif self._backoff_timestamp:
            backed_off_time, backoff_time_left = self._backoff_status()
            if backoff_time_left < 0:
                log.info("Exiting backoff state after {0} seconds, will try to submit metrics again".format(backed_off_time))
                self._backoff_timestamp = None
                self._timeout_counter = 0
                should_submit = True
            else:
                log.info("In backoff state, won't submit metrics for another {0} seconds".format(backoff_time_left))
                should_submit = False
        else:
            should_submit = True

        return should_submit

    def _backoff_status(self):
        now = time.time()
        backed_off_time = now - self._backoff_timestamp
        backoff_time_left = self.backoff_period - backed_off_time
        return round(backed_off_time, 2), round(backoff_time_left, 2)

