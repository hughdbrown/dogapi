from functools import wraps
import logging
import time

from fabric.tasks import WrappedCallableTask
from dogapi import dog_http_api

logger = logging.getLogger("fabric")


def setup(api_key):
    # global dog_http_api
    dog_http_api.api_key = api_key


def human_duration(d):
    def pluralize(quantity, noun):
        return "{0} {1}{2}".format(quantity, noun, "s" if quantity >= 2 else "")

    seconds = int(d)
    h, m, s = seconds // 3600, (seconds // 60) % 60, seconds % 3600
    if h and m:
        return "{0} {1}".format(pluralize(h, "hour"), pluralize(m, "minute"))
    elif m:
        return "{0}".format(pluralize(m, "minute"))
    elif s:
        return "{0}".format(pluralize(s, "second"))
    else:
        return "less than 1 second"


def notify(t):
    """Decorates a fabric task"""
    @wraps(t)
    def wrapper(*args, **kwargs):
        notify_datadog = True

        if type(t) != WrappedCallableTask:
            logger.warn("@notify decorator only works on a new-style Fabric Task")
            notify_datadog = False

        start = time.time()

        try:
            r = t(*args, **kwargs)
            end = time.time()
            duration = end - start
            if notify_datadog:
                try:
                    task_full_name = "%s.%s" % (t.__module__, t.wrapped.func_name)

                    dog_http_api.event("{0}".format(task_full_name),
                                       "{0} ran for {1}.".format(task_full_name, human_duration(duration)),
                                       source_type_name="fabric",
                                       alert_type="success",
                                       priority="normal",
                                       aggregation_key=task_full_name)
                except:
                    logger.warn("Datadog notification failed but task {0} completed".format(t.wrapped.func_name))
            return r
        except Exception as e:
            # If notification is on, create an error event
            end = time.time()
            duration = end - start
            if notify_datadog:
                try:
                    task_full_name = "%s.%s" % (t.__module__, t.wrapped.func_name)
                    dog_http_api.event("{0}".format(task_full_name),
                                       "{0} failed after {1} because of {2}.".format(task_full_name, human_duration(duration), e),
                                       source_type_name="fabric",
                                       alert_type="error",
                                       priority="normal",
                                       aggregation_key=task_full_name)
                except:
                    logger.exception("Datadog notification failed")
            # Reraise
            raise

    return WrappedCallableTask(wrapper)
