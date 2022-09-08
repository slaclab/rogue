#-----------------------------------------------------------------------------
# Title      : PyRogue - SQL Logging Module
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr
import sqlalchemy
import threading
import queue


class SqlLogger(object):

    def __init__(self, url):
        self._log = pr.logInit(cls=self,name="SqlLogger",path=None)
        self._url = url
        self._engine   = None
        self._thread = None
        self._queue  = queue.Queue()
        self._thread = threading.Thread(target=self._worker)
        self._thread.start()
        try:
            engine = sqlalchemy.create_engine(self._url) #, isolation_level="AUTOCOMMIT")
            self._log.info("Opened database connection to {}".format(self._url))
        except Exception as e:
            self._log.error("Failed to open database connection to {}: {}".format(self._url,e))
            return

        self._metadata = sqlalchemy.MetaData(engine)

        self._varTable = sqlalchemy.Table(
            'variables', self._metadata,
            sqlalchemy.Column('id',        sqlalchemy.Integer, primary_key=True),
            sqlalchemy.Column('timestamp', sqlalchemy.DateTime(timezone=True), server_default=sqlalchemy.func.now()),
            sqlalchemy.Column('path',      sqlalchemy.String),
            sqlalchemy.Column('enum',      sqlalchemy.String),
            sqlalchemy.Column('disp',      sqlalchemy.String),
            sqlalchemy.Column('value',     sqlalchemy.String),
            sqlalchemy.Column('valueDisp', sqlalchemy.String),
            sqlalchemy.Column('severity',  sqlalchemy.String),
            sqlalchemy.Column('status',    sqlalchemy.String))

        self._logTable = sqlalchemy.Table(
            'syslog', self._metadata,
            sqlalchemy.Column('id',          sqlalchemy.Integer, primary_key=True),
            sqlalchemy.Column('timestamp',   sqlalchemy.DateTime(timezone=True), server_default=sqlalchemy.func.now()),
            sqlalchemy.Column('name',        sqlalchemy.String),
            sqlalchemy.Column('message',     sqlalchemy.String),
            sqlalchemy.Column('exception',   sqlalchemy.String),
            sqlalchemy.Column('levelName',   sqlalchemy.String),
            sqlalchemy.Column('levelNumber', sqlalchemy.Integer))

        self._varTable.create(engine, checkfirst=True)
        self._logTable.create(engine, checkfirst=True)
        self._engine = engine

    def logVariable(self, path, varValue):
        if self._engine is not None:
            self._queue.put((path,varValue))

    def logSyslog(self, syslogData):
        if self._engine is not None:
            self._queue.put((None,syslogData))

    def _stop(self):
        if not self._queue.empty():
            print("Waiting for sql logger to finish...")
        self._queue.put(None)
        self._thread.join()
        print('Sql logger stopped')


    def insert_from_q(self, entry, conn):

        # Variable
        if entry[0] is not None:

            # Handle corner cases
            value = entry[1].value
            if isinstance(value, int) and value.bit_length() > 64:
                # Support >64 bit ints
                value = entry[1].valueDisp
            elif isinstance(value, tuple):
                # Support tuples
                value = str(value)

            ins = self._varTable.insert().values(
                path=entry[0],
                enum=str(entry[1].enum),
                disp=entry[1].disp,
                value=value,
                valueDisp=entry[1].valueDisp,
                severity=entry[1].severity,
                status=entry[1].status)

        # Syslog
        else:
            ins = self._logTable.insert().values(
                name=entry[1]['name'],
                message=entry[1]['message'],
                exception=entry[1]['exception'],
                levelName=entry[1]['levelName'],
                levelNumber=entry[1]['levelNumber'])

        conn.execute(ins)


    def _worker(self):
        while True:
            # Block and wait for a queue entry to arrive
            entry = self._queue.get()

            # Exit thread if None entry received
            if entry is None:
                return

            # Do nothing with the data if db connection not present
            if self._engine is None:
                continue

            # If there are multiple entries in the queue
            # write them to the DB in a single transaction
            try:
                with self._engine.begin() as conn:
                    while True:
                        #Need to check for null again from loop
                        if entry is None:
                            return

                        # Insert the entry
                        self.insert_from_q(entry, conn)

                        # Break from loop and close the transaction
                        # when queue has been emptied
                        if self._queue.qsize() == 0:
                            break

                        # Read the next queue entry and loop
                        entry = self._queue.get()


            except Exception as e:
                self._engine = None
                pr.logException(self._log,e)
                self._log.error("Lost database connection to {}".format(self._url))




class SqlReader(object):

    def __init__(self, url):
        self._log = pr.logInit(cls=self,name="SqlReader",path=None)
        self._url = url
        self._engine = None

        try:
            engine = sqlalchemy.create_engine(self._url)
            self._log.info("Opened database connection to {}".format(self._url))
        except Exception as e:
            self._log.error("Failed to open database connection to {}: {}".format(self._url,e))
            return

        self._metadata = sqlalchemy.MetaData(engine)

        self._varTable = sqlalchemy.Table('variables', self._metadata, autoload=True)
        self._logTable = sqlalchemy.Table('syslog', self._metadata, autoload=True)
        self._engine = engine

    # Make this more useful
    def getVariable(self):
        r = self._conn.execute(sqlalchemy.select([self._varTable]))
        print(r.fetchall())

    # Make this more useful
    def getSyslog(self, syslogData):
        r = self._conn.execute(sqlalchemy.select([self._logTable]))
        print(r.fetchall())
