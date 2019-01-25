"""
Lambda function to count invocations.
"""

import logging

log = logging.getLogger()
log.setLevel(logging.INFO)

count = 0


def handle(event, context):
    """Lambda handler"""
    global count
    log.info('%s - %s', event, context)
    if 'ramuda_action' in event:
        if event['ramuda_action'] == 'ping':
            return 'alive'
    else:
        # we are waiting for an update of my_param in the SSM parameter store
        count += 1
        log.info('handler was invoked %d times', count)
        #print(event)
        my_param = 'blabla'
        # event detail-type is 'Parameter Store Change'
        # u'detail': {u'operation': u'Update', u'type': u'SecureString', u'name': u'blabla'},
        if event.get('operation', '') == 'Update' and event.get('name', '') == my_param:
            log.info('these aren\'t the droids you\'re looking for')
        return event
