#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - PollQueue Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_PollQueue.py
# Created    : 2017-05-16
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import sys
import threading
import collections
import datetime
import itertools
import heapq
import rogue.interfaces.memory
import pyrogue as pr
import recordclass

class PollQueue(object):

    Entry = recordclass.recordclass('PollQueueEntry', ['readTime', 'count', 'interval', 'block'])

    def __init__(self,*, root):
        self._pq = [] # The heap queue
        self._entries = {} # {Block: Entry} mapping to look up if a block is already in the queue
        self._counter = itertools.count()
        self._lock = threading.RLock()
        self._update = threading.Condition()
        self._run = True
        self._root = root
        self._pollThread = threading.Thread(target=self._poll)

        # Setup logging
        self._log = pr.logInit(self)

    def _start(self):
        self._pollThread.start()
        self._log.info("PollQueue Started")

    def _addEntry(self, block, interval):
        with self._lock:
            timedelta = datetime.timedelta(seconds=interval)
            # new entries are always polled first immediately 
            # (rounded up to the next second)
            readTime = datetime.datetime.now()
            readTime = readTime.replace(microsecond=0)
            entry = PollQueue.Entry(readTime, next(self._counter), timedelta, block)
            self._entries[block] = entry
            heapq.heappush(self._pq, entry)
            # Wake up the thread
            with self._update:
                self._update.notify()

    def updatePollInterval(self, var):
        with self._lock:
            self._log.debug('updatePollInterval {} - {}'.format(var, var.pollInterval))
            # Special case: Variable has no block and just depends on other variables
            # Then do update on each dependency instead
            if var._block is None:
                if len(var.dependencies) > 0:
                    for dep in var.dependencies:
                        if dep.pollInterval == 0 or var.pollInterval < dep.pollInterval:
                            dep.pollInterval = var.pollInterval

                return

            if var._block in self._entries.keys():
                oldInterval = self._entries[var._block].interval
                blockVars = [v for v in var._block._variables if v.pollInterval > 0]
                if len(blockVars) > 0:
                    minVar = min(blockVars, key=lambda x: x.pollInterval)
                    newInterval = datetime.timedelta(seconds=minVar.pollInterval)
                    # If block interval has changed, invalidate the current entry for the block
                    # and re-add it with the new interval
                    if newInterval != oldInterval:
                        self._entries[var._block].block = None
                        self._addEntry(var._block, minVar.pollInterval)
                else:
                    # No more variables belong to block entry, can remove it
                    self._entries[var._block].block = None
            else:
                # Pure entry add
                self._addEntry(var._block, var.pollInterval)

    def _poll(self):
        """Run by the poll thread"""
        while True:
            now = datetime.datetime.now()

            if self.empty() is True:
                # Sleep until woken
                with self._update:
                    self._update.wait()
            else:
                # Sleep until the top entry is ready to be polled
                # Or a new entry is added by updatePollInterval
                readTime = self.peek().readTime
                waitTime = (readTime - now).total_seconds()
                with self._update:
                    self._log.debug('Poll thread sleeping for {}'.format(waitTime))
                    self._update.wait(waitTime)

            self._log.debug("Global reference count: %s" % (sys.getrefcount(None)))

            with self._lock:
                # Stop the thread if someone set run to False
                if self._run is False:
                    self._log.info("PollQueue thread exiting")
                    return

                # Start update capture
                self._root._initUpdatedVars()

                # Pop all timed out entries from the queue
                now = datetime.datetime.now()
                blockEntries = []
                for entry in self._expiredEntries(now):
                    self._log.debug('Polling {}'.format(entry.block._variables))
                    blockEntries.append(entry)
                    try:
                        entry.block.backgroundTransaction(rogue.interfaces.memory.Read)
                    except Exception as e:
                        self._log.exception(e)

                    # Update the entry with new read time
                    entry = entry._replace(readTime=(entry.readTime + entry.interval),
                                           count=next(self._counter))
                    # Push the updated entry back into the queue
                    heapq.heappush(self._pq, entry)

                try:
                    for entry in blockEntries:
                        entry.block._checkTransaction(update=True)
                except Exception as e:
                    self._log.exception(e)
                # End update capture
                self._root._doneUpdatedVars()

    def _expiredEntries(self, time=None):
        """An iterator of all entries that expire by a given time. 
        Use datetime.now() if no time provided. Each entry is popped from the queue before being 
        yielded by the iterator
        """
        with self._lock:
            if time == None:
                time = datetime.datetime.now()
            while self.empty() is False and self.peek().readTime <= time:
                entry = heapq.heappop(self._pq)
                if entry.block is not None:
                    yield entry


    def peek(self):
        with self._lock:
            if self.empty() is False:
                return self._pq[0]
            else:
                return None

    def empty(self):
        with self._lock:
            return len(self._pq)==0

    def stop(self):
        with self._lock, self._update:
            self._run = False
            self._update.notify()

