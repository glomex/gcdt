# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from gcdt.yugen_main import version_cmd
from gcdt_testtools.helpers import logcapture  # fixtures!


# note: xzy_main tests have a more "integrative" character so focus is to make
# sure that the gcdt parts fit together not functional coverage of the parts.


def test_version_cmd(logcapture):
    version_cmd()
    records = list(logcapture.actual())

    assert records[0][1] == 'INFO'
    assert records[0][2].startswith('gcdt version ')
    assert records[1][1] == 'INFO'
    assert records[1][2].startswith('gcdt plugins:')
