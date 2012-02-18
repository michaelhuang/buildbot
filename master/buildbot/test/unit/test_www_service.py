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
from buildbot.www import service, ui, json
from twisted.trial import unittest
from twisted.web import static
from buildbot.test.util import www

class Test(www.WwwTestMixin, unittest.TestCase):

    def setUp(self):
        self.master = mock.Mock()
        self.svc = service.WWWService(self.master)

    def makeConfig(self, **kwargs):
        w = dict(url='h:/', port=None)
        w.update(kwargs)
        new_config = mock.Mock()
        new_config.www = w
        self.master.config = new_config
        return new_config

    def test_reconfigService_no_port(self):
        new_config = self.makeConfig()
        d = self.svc.reconfigService(new_config)
        @d.addCallback
        def check(_):
            self.assertEqual(self.svc.site, None)
        return d

    def test_reconfigService_port(self):
        new_config = self.makeConfig(port=20)
        d = self.svc.reconfigService(new_config)
        @d.addCallback
        def check(_):
            self.assertNotEqual(self.svc.site, None)
            self.assertNotEqual(self.svc.port_service, None)
            self.assertEqual(self.svc.port, 20)
        return d

    def test_reconfigService_port_changes(self):
        new_config = self.makeConfig(port=20)
        d = self.svc.reconfigService(new_config)
        @d.addCallback
        def reconfig(_):
            newer_config = self.makeConfig(port=999)
            return self.svc.reconfigService(newer_config)
        @d.addCallback
        def check(_):
            self.assertNotEqual(self.svc.site, None)
            self.assertNotEqual(self.svc.port_service, None)
            self.assertEqual(self.svc.port, 999)
        return d

    def test_reconfigService_port_changes_to_none(self):
        new_config = self.makeConfig(port=20)
        d = self.svc.reconfigService(new_config)
        @d.addCallback
        def reconfig(_):
            newer_config = self.makeConfig()
            return self.svc.reconfigService(newer_config)
        @d.addCallback
        def check(_):
            # (note the site sticks around)
            self.assertEqual(self.svc.port_service, None)
            self.assertEqual(self.svc.port, None)
        return d

    def test_setup_site(self):
        self.svc.setup_site(self.makeConfig())
        site = self.svc.site

        # check that it has the right kind of resources attached to its
        # root
        root = site.resource
        req = mock.Mock()
        self.assertIsInstance(root.getChildWithDefault('ui', req),
                ui.UIResource)
        self.assertIsInstance(root.getChildWithDefault('json', req),
                json.JsonRootResource)
        self.assertIsInstance(root.getChildWithDefault('static', req),
                static.File)

        # ..and that the / URI redirects properly
        req = self.make_request([''])
        self.render_resource(site.getResourceFor(req), request=req)
        self.assertEqual(self.request.redirected_to, 'h:/ui/')
