"""
Lambda function to count invocations.
"""

import logging

log = logging.getLogger()
log.setLevel(logging.INFO)

count = 0


def handle(event, context):
    """Lambda handler
    """
    global count
    log.info("%s - %s", event, context)
    if "ramuda_action" in event:
        if event["ramuda_action"] == "ping":
            return "alive"
        elif event["ramuda_action"] == "count":
            log.info("ramuda_action \'count\' result: %d", count)
            return count
    else:
        count += 1
        log.info("count: %d", count)
        return event
