# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import json
import logging
import datetime
from six import StringIO
import glob
import re
from io import BytesIO
from requests.structures import CaseInsensitiveDict

from botocore.response import StreamingBody

from gcdt.gcdt_awsclient import AWSClient
#from gcdt.servicediscovery import UTC
ZERO = datetime.timedelta(0)


class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO


LOG_ALL_TRAFFIC = True  # False means do not log successful requests

log = logging.getLogger(__name__)
# hdlr = logging.FileHandler('./placebo.log')
# formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
# hdlr.setFormatter(formatter)
# log.addHandler(hdlr)
# log.setLevel(logging.DEBUG)


# TODO fix recording for kms, i.e. test_config_reader_aws.py tests


class FakeHttpResponse(object):
    def __init__(self, status_code):
        self.status_code = status_code


class PlaceboAWSClient(AWSClient):
    def __init__(self, session, data_path):
        """Test tool to replace AWSClient. It can record and playback calls to
        AWS services.

        :param session: botocore session
        :param data_path: basepath for your recordings
        """
        self._session = session
        self._client_cache = {}
        self._mode = None  # None, record, playback
        # TODO remove _prefix
        self._prefix = None  # not used!!
        self._data_path = data_path
        self._index = {}  # playback registry per service count
        self._events = []  # keep track of registered events
        self._filename_re = re.compile(r'.*\..*_(?P<index>\d+).json')

    def record(self, services='*', operations='*'):
        """Unregister all events and switch to 'record' mode.

        :param services: defaults to '*' but you can filter specific ones, too
        :param operations: defaults to '*' but you can filter specific ones, too
        :return:
        """
        if self._mode == 'playback':
            self.stop()
        self._mode = 'record'
        for service in services.split(','):
            for operation in operations.split(','):
                event = 'after-call.{0}.{1}'.format(
                    service.strip(), operation.strip())
                log.debug('recording: %s', event)
                self._events.append(event)
                self._session.register(
                    event, self._record_data, 'placebo-record-mode')

    def _record_data(self, http_response, parsed, model, **kwargs):
        log.debug('_record_data')
        service_name = model.service_model.endpoint_prefix
        operation_name = model.name
        self._save_response(service_name, operation_name, parsed,
                           http_response.status_code)

    def _save_response(self, service, operation, response_data,
                      http_response=200):
        """
        Store a response to the data directory.  The ``operation``
        should be the name of the operation in the service API (e.g.
        DescribeInstances), the ``response_data`` should a value you want
        to return from a placebo call and the ``http_response`` should be
        the HTTP status code returned from the service.  You can add
        multiple responses for a given operation and they will be
        returned in order.
        """
        log.debug('save_response: %s.%s', service, operation)
        filepath = self._get_new_file_path(service, operation)
        log.debug('save_response: path=%s', filepath)
        json_data = {'status_code': http_response,
                     'data': response_data}
        with open(filepath, 'w') as fp:
            json.dump(json_data, fp, indent=4, default=serialize_patch)

    def _get_new_file_path(self, service, operation):
        base_name = '{0}.{1}'.format(service, operation)
        if self._prefix:
            base_name = '{0}.{1}'.format(self._prefix, base_name)
        log.debug('get_new_file_path: %s', base_name)
        index = 0
        glob_pattern = os.path.join(self._data_path, base_name + '*')
        for file_path in glob.glob(glob_pattern):
            file_name = os.path.basename(file_path)
            m = self._filename_re.match(file_name)
            if m:
                i = int(m.group('index'))
                if i > index:
                    index = i
        index += 1
        return os.path.join(
            self._data_path, '{0}_{1}.json'.format(base_name, index))

    def playback(self):
        """Unregister all events and switch to 'playback' mode.

        :return:
        """
        if self._mode == 'record':
            self.stop()
        if self._mode is None:
            event = 'before-call.*.*'
            self._events.append(event)
            self._session.register(
                event, self._mock_request, 'placebo-playback-mode')
            self._mode = 'playback'

    def _mock_request(self, **kwargs):
        """
        A mocked out make_request call that bypasses all network calls
        and simply returns any mocked responses defined.
        """
        model = kwargs.get('model')
        service = model.service_model.endpoint_prefix
        operation = model.name
        log.debug('_make_request: %s.%s', service, operation)
        return self._load_response(service, operation)

    def _load_response(self, service, operation):
        log.debug('load_response: %s.%s', service, operation)
        response_file = self._get_next_file_path(service, operation)
        log.debug('load_responses: %s', response_file)
        with open(response_file, 'r') as fp:
            response_data = json.load(fp, object_hook=deserialize)
        return (FakeHttpResponse(response_data['status_code']),
                response_data['data'])

    def _get_next_file_path(self, service, operation):
        base_name = '{0}.{1}'.format(service, operation)
        if self._prefix:
            base_name = '{0}.{1}'.format(self._prefix, base_name)
        log.debug('get_next_file_path: %s', base_name)
        next_file = None
        while next_file is None:
            index = self._index.setdefault(base_name, 1)
            fn = os.path.join(
                self._data_path, base_name + '_{0}.json'.format(index))
            if os.path.exists(fn):
                next_file = fn
                self._index[base_name] += 1
            elif index != 1:
                self._index[base_name] = 1
            else:
                # we are looking for the first index and it's not here
                raise IOError('response file ({0}) not found'.format(fn))
        return fn

    def stop(self):
        """Unregister events and switch back to 'normal' mode.

        :return:
        """
        log.debug('stopping, mode=%s', self._mode)
        if self._mode == 'record':
            if self._session:
                for event in self._events:
                    self._session.unregister(
                        event, unique_id='placebo-record-mode')
                self._events = []
        elif self._mode == 'playback':
            if self._session:
                for event in self._events:
                    self._session.unregister(
                        event, unique_id='placebo-playback-mode')
                self._events = []
        self._mode = None


def deserialize(obj):
    """Convert JSON dicts back into objects."""
    # Be careful of shallow copy here
    target = dict(obj)
    class_name = None
    if '__class__' in target:
        class_name = target.pop('__class__')
    if '__module__' in obj:
        module_name = obj.pop('__module__')
    # Use getattr(module, class_name) for custom types if needed
    if class_name == 'datetime':
        target['tzinfo'] = UTC()
        return datetime.datetime(**target)
    if class_name == 'StreamingBody':
        return StringIO(target['body'])
    # Return unrecognized structures as-is
    return obj


def serialize_patch(obj):
    """Convert objects into JSON structures."""
    # Record class and module information for deserialization

    result = {'__class__': obj.__class__.__name__}
    try:
        result['__module__'] = obj.__module__
    except AttributeError:
        pass
    # Convert objects to dictionary representation based on type
    if isinstance(obj, datetime.datetime):
        result['year'] = obj.year
        result['month'] = obj.month
        result['day'] = obj.day
        result['hour'] = obj.hour
        result['minute'] = obj.minute
        result['second'] = obj.second
        result['microsecond'] = obj.microsecond
        return result
    if isinstance(obj, StreamingBody):
        original_text = obj.read()

        # We remove a BOM here if it exists so that it doesn't get reencoded
        # later on into a UTF-16 string, presumably by the json library
        result['body'] = original_text.decode('utf-8-sig')

        obj._raw_stream = BytesIO(original_text)
        obj._amount_read = 0
        return result
    if isinstance(obj, CaseInsensitiveDict):
        result['as_dict'] = dict(obj)
        return result
    raise TypeError('Type not serializable')
