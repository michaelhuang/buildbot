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

from buildbot import config
from twisted.internet import defer
from twisted.python import  util
from twisted.application import strports, service
from twisted.web import server, static

class WWWService(config.ReconfigurableServiceMixin, service.MultiService):

    def __init__(self, master):
        service.MultiService.__init__(self)
        self.setName('www')
        self.master = master

        self.port = None
        self.port_service = None
        self.site = None

    @defer.deferredGenerator
    def reconfigService(self, new_config):
        need_new_site = False
        if self.site:
            if new_config.get('public_html') != self.site.public_html:
                need_new_site = True
        else:
            need_new_site = True

        if need_new_site:
            self.setup_site(new_config)

        if new_config.www['port'] != self.port:
            if self.port_service:
                wfd = defer.waitForDeferred(
                    self.port_service.disownServiceParent())
                yield wfd
                wfd.getResult()
                self.port_service = None

            self.port = new_config.www['port']
            if self.port:
                port = self.port
                if type(port) is int:
                    port = "tcp:%d" % port
                self.port_service = strports.service(port, self.site)
                self.port_service.setServiceParent(self)

        wfd = defer.waitForDeferred(
                config.ReconfigurableServiceMixin.reconfigService(self,
                                                            new_config))
        yield wfd
        wfd.getResult()

    def setup_site(self, new_config):
        # avoid importing these modules unless the service is enabled
        from buildbot.www import ui, resource, json

        public_html =  new_config.www.get('public_html')
        if public_html:
            root = static.File(public_html)
        else:
            root = static.Data('placeholder', 'text/plain')

        # redirect the root to UI
        root.putChild('', resource.RedirectResource(self.master, 'ui/'))

        # /ui
        root.putChild('ui', ui.UIResource(self.master))

        # /ui
        root.putChild('json', json.JsonRootResource(self.master))

        # /static
        staticdir = util.sibpath(__file__, 'static')
        root.putChild('static', static.File(staticdir))

        self.site = server.Site(root)
