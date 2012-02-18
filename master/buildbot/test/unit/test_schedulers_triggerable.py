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

from twisted.trial import unittest
from buildbot.schedulers import triggerable
from buildbot.process import properties
from buildbot.test.util import scheduler
from buildbot.test.fake import fakedb

class Triggerable(scheduler.SchedulerMixin, unittest.TestCase):

    OBJECTID = 33

    def setUp(self):
        self.setUpScheduler()
        self.subscription = None

    def tearDown(self):
        self.tearDownScheduler()

    def makeScheduler(self, **kwargs):
        sched = self.attachScheduler(
                triggerable.Triggerable(name='n', builderNames=['b']),
                self.OBJECTID)

        return sched

    # tests

    # NOTE: these tests take advantage of the fact that all of the fake
    # scheduler operations are synchronous, and thus do not return a Deferred.
    # The Deferred from trigger() is completely processed before this test
    # method returns.

    def test_trigger(self):
        sched = self.makeScheduler()
        self.db.insertTestData([
            fakedb.SourceStampSet(id=1091),
            fakedb.SourceStamp(id=91, sourcestampsetid=1091, revision='myrev', branch='br',
                project='p', repository='r'),
        ])

        # no subscription should be in place yet
        self.assertEqual(sched.master.mq.qrefs, [])

        # trigger the scheduler, exercising properties while we're at it
        set_props = properties.Properties()
        set_props.setProperty('pr', 'op', 'test')
        d = sched.trigger(91, set_props=set_props)

        bsid = self.db.buildsets.assertBuildset('?',
                dict(external_idstring=None,
                     properties=[
                         ('pr', ('op', 'test')),
                         ('scheduler', ('n', 'Scheduler')),
                     ],
                     reason='Triggerable(n)',
                     sourcestampsetid=1091),
                {'r':
                 dict(branch='br', project='p', repository='r',
                     revision='myrev', sourcestampsetid=1091)
                })

        # set up a boolean so that we can know when the deferred fires
        self.fired = False
        def fired((result, brids)):
            self.assertEqual(result, 13) # 13 comes from the result below
            self.assertEqual(brids, self.db.buildsets.allBuildRequests(bsid))
            self.fired = True
        d.addCallback(fired)

        # check that the scheduler has subscribed to buildset changes, but
        # not fired yet
        self.assertEqual(
            [ q.topics for q in sched.master.mq.qrefs ],
            [('buildset.*.complete',)])
        self.assertFalse(self.fired)

        # pretend a non-matching buildset is complete
        sched.master.mq.call_consumer('buildset.*.complete',
                'buildset.%d.complete' % (bsid+27),
                dict(bsid=bsid+27, result=3))

        # scheduler should not have reacted
        self.assertEqual(
            [ q.topics for q in sched.master.mq.qrefs ],
            [('buildset.*.complete',)])
        self.assertFalse(self.fired)

        # pretend the matching buildset is complete
        sched.master.mq.call_consumer('buildset.*.complete',
                'buildset.%d.complete' % bsid,
                dict(bsid=bsid, result=13))

        # scheduler should have reacted
        self.assertEqual(sched.master.mq.qrefs, [])
        self.assertTrue(self.fired)

    def test_trigger_overlapping(self):
        sched = self.makeScheduler()
        self.db.insertTestData([
            fakedb.SourceStampSet(id=1091),
            fakedb.SourceStampSet(id=1092),
            fakedb.SourceStamp(id=91, sourcestampsetid=1091, revision='myrev1',
                branch='br', project='p', repository='r'),
            fakedb.SourceStamp(id=92, sourcestampsetid=1092, revision='myrev2',
                branch='br', project='p', repository='r'),
        ])

        # no subscription should be in place yet
        self.assertEqual(sched.master.mq.qrefs, [])

        # trigger the scheduler the first time
        d = sched.trigger(91)
        bsid1 = self.db.buildsets.assertBuildset('?',
                dict(external_idstring=None,
                     properties=[('scheduler', ('n', 'Scheduler'))],
                     reason='Triggerable(n)',
                     sourcestampsetid=1091),
                {'r':
                dict(branch='br', project='p', repository='r',
                     revision='myrev1', sourcestampsetid=1091)})
        d.addCallback(lambda (res, brids) : self.assertEqual(res, 11) 
                                        and self.assertEqual(brids, self.db.buildsets.allBuildRequests(bsid1)))

        # and the second time
        d = sched.trigger(92)
        bsid2 = self.db.buildsets.assertBuildset(bsid1+1, # assumes bsid's are sequential
                dict(external_idstring=None,
                     properties=[('scheduler', ('n', 'Scheduler'))],
                     reason='Triggerable(n)', sourcestampsetid=1092),
                {'r':
                dict(branch='br', project='p', repository='r',
                     revision='myrev2', sourcestampsetid=1092)})
        d.addCallback(lambda (res, brids) : self.assertEqual(res, 22) 
                                        and self.assertEqual(brids, self.db.buildsets.allBuildRequests(bsid2)))

        # check that the scheduler has subscribed to buildset changes
        self.assertEqual(
            [ q.topics for q in sched.master.mq.qrefs ],
            [('buildset.*.complete',)])

        # let a few buildsets complete
        sched.master.mq.call_consumer('buildset.*.complete',
                'buildset.%d.complete' % (bsid2+27,),
                dict(bsid=bsid2+27, result=3))
        sched.master.mq.call_consumer('buildset.*.complete',
                'buildset.%d.complete' % (bsid2,),
                dict(bsid=bsid2, result=22))
        sched.master.mq.call_consumer('buildset.*.complete',
                'buildset.%d.complete' % (bsid2+7,),
                dict(bsid=bsid2+7, result=3))
        sched.master.mq.call_consumer('buildset.*.complete',
                'buildset.%d.complete' % (bsid1,),
                dict(bsid=bsid1, result=11))

        # both should have triggered with appropriate results, and the
        # subscription should be cancelled
        self.assertEqual(sched.master.mq.qrefs, [])
