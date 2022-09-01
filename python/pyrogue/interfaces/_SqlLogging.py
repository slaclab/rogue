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

        self._varTable = sqlalchemy.Table('variables', self._metadata,
            sqlalchemy.Column('id',        sqlalchemy.Integer, primary_key=True),
            sqlalchemy.Column('timestamp', sqlalchemy.DateTime(timezone=True), server_default=sqlalchemy.func.now()),
            sqlalchemy.Column('path',      sqlalchemy.String),
#            sqlalchemy.Column('enum',      sqlalchemy.String),
#            sqlalchemy.Column('disp',      sqlalchemy.String),
            sqlalchemy.Column('value',     sqlalchemy.String),
            sqlalchemy.Column('valueDisp', sqlalchemy.String))                                          
#            sqlalchemy.Column('severity',  sqlalchemy.String),
#            sqlalchemy.Column('status',    sqlalchemy.String))

        self._logTable = sqlalchemy.Table('syslog', self._metadata,
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


    def insert_from_q(self, ent, conn):
        # Variable        
        if ent[0] is not None:
            value = ent[1].value
            if isinstance(value, int) and value.bit_length() > 64:
                value = ent[1].valueDisp
            elif isinstance(value, tuple):
                value = str(value)
        
            ins = self._varTable.insert().values(
                path=ent[0],
#                enum=str(ent[1].enum),
#                disp=ent[1].disp,
                value=value,
                valueDisp=ent[1].valueDisp)
#                severity=ent[1].severity,
#                status=ent[1].status)

        # Syslog
        else:
            ins = self._logTable.insert().values(
                name=ent[1]['name'],
                message=ent[1]['message'],
                exception=ent[1]['exception'],
                levelName=ent[1]['levelName'],
                levelNumber=ent[1]['levelNumber'])

        conn.execute(ins)
        
        
    def _worker(self):
        while True:
            ent = self._queue.get()
            print(f'q size = {self._queue.qsize()}')
            # Done
            if ent is None:
                return

            if self._engine is not None:
                try:                
                    with self._engine.begin() as conn:
                        self.insert_from_q(ent, conn)

                        for i in range(self._queue.qsize()):
                            ent = self._queue.get()
                            if ent is None:
                                return
                            self.insert_from_q(ent, conn)

                    
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
