# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

import mock
from twisted.trial import unittest
from twisted.internet import defer
from buildbot import config
from buildbot.mq import connector, base

class FakeMQ(config.ReconfigurableServiceMixin, base.MQBase):

    new_config = "not_called"

    def reconfigService(self, new_config):
        self.new_config = new_config
        return defer.succeed(None)


class MQConnector(unittest.TestCase):

    def setUp(self):
        self.master = mock.Mock(name='master')
        self.mqconfig = self.master.config.mq = {}
        self.conn = connector.MQConnector(self.master)

    def test_setup_unknown_type(self):
        self.mqconfig['type'] = 'unknown'
        self.assertRaises(AssertionError, lambda :
                self.conn.setup())

    def test_setup_simple_type(self):
        self.patch(connector.MQConnector, 'classes',
                    dict(simple='buildbot.test.unit.test_mq_connector.FakeMQ'))
        self.mqconfig['type'] = 'simple'
        self.conn.setup()
        self.assertIsInstance(self.conn.impl, FakeMQ)
        self.assertEqual(self.conn.impl.produce, self.conn.produce)
        self.assertEqual(self.conn.impl.consume, self.conn.consume)

    def test_reconfigService(self):
        self.patch(connector.MQConnector, 'classes',
                    dict(fake='buildbot.test.unit.test_mq_connector.FakeMQ'))
        self.mqconfig['type'] = 'fake'
        self.conn.setup()
        new_config = mock.Mock()
        new_config.mq = dict(type='fake')
        d = self.conn.reconfigService(new_config)
        @d.addCallback
        def check(_):
            self.assertIdentical(self.conn.impl.new_config, new_config)
        return d

    @defer.deferredGenerator
    def test_reconfigService_change_type(self):
        self.patch(connector.MQConnector, 'classes',
                    dict(fake='buildbot.test.unit.test_mq_connector.FakeMQ'))
        self.mqconfig['type'] = 'fake'
        self.conn.setup()
        new_config = mock.Mock()
        new_config.mq = dict(type='other')
        try:
            wfd = defer.waitForDeferred(
                self.conn.reconfigService(new_config))
            yield wfd
            wfd.getResult()
        except AssertionError:
            pass # expected
        else:
            self.fail("should have failed")
