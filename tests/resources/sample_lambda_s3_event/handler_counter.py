"""
Lambda function to count invocations.
"""

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

count = 0


def handle(event, context):
    """Lambda handler
    """
    global count
    logger.info("%s - %s", event, context)
    if "ramuda_action" in event:
        if event["ramuda_action"] == "ping":
            return "alive"
        elif event["ramuda_action"] == "count":
            return count
    else:
        count += 1
        # some changes here so we can update the handler
        return event
