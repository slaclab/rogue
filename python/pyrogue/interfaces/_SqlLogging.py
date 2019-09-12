#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue - SQL Logging Module
#-----------------------------------------------------------------------------
# File       : pyrogue/_sqlLogging.py
# Created    : 2019-09-03
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

class SqlLogger(object):

    def __init__(self, url):
        self._log = pr.logInit(cls=self,name="SqlLogger",path=None)
        self._url = url
        self._conn = None

        try:
            conn = sqlalchemy.create_engine(self._url)
            self._log.info("Opened database connection to {}".format(self._url))
        except Exception as e:
            self._log.error("Failed to open database connection to {}: {}".format(self._url,e))
            return

        self._metadata = sqlalchemy.MetaData(conn)

        self._varTable = sqlalchemy.Table('variables', self._metadata,
            sqlalchemy.Column('id',        sqlalchemy.Integer, primary_key=True),
            sqlalchemy.Column('timestamp', sqlalchemy.DateTime(timezone=True), server_default=sqlalchemy.func.now()),
            sqlalchemy.Column('path',      sqlalchemy.String),
            sqlalchemy.Column('enum',      sqlalchemy.String),
            sqlalchemy.Column('disp',      sqlalchemy.String),
            sqlalchemy.Column('value',     sqlalchemy.String),
            sqlalchemy.Column('severity',  sqlalchemy.String),
            sqlalchemy.Column('status',    sqlalchemy.String))

        self._logTable = sqlalchemy.Table('syslog', self._metadata,
            sqlalchemy.Column('id',          sqlalchemy.Integer, primary_key=True),
            sqlalchemy.Column('timestamp',   sqlalchemy.DateTime(timezone=True), server_default=sqlalchemy.func.now()),
            sqlalchemy.Column('name',        sqlalchemy.String),
            sqlalchemy.Column('message',     sqlalchemy.String),
            sqlalchemy.Column('exception',   sqlalchemy.String),
            sqlalchemy.Column('levelName',   sqlalchemy.String),
            sqlalchemy.Column('levelNumber', sqlalchemy.Integer))

        self._varTable.create(conn, checkfirst=True)
        self._logTable.create(conn, checkfirst=True)
        self._conn = conn

    def logVariable(self, path, varValue):
        if self._conn is None:
            return

        try:
            ins = self._varTable.insert().values(path=path, 
                                                 enum=varValue.enum, 
                                                 disp=varValue.disp, 
                                                 value=varValue.valueDisp,
                                                 severity=varValue.severity, 
                                                 status=varValue.status)
            self._conn.execute(ins)
        except:
            self._conn = None
            self._log.error("Lost database connection to {}".format(self._url))

    def logSyslog(self, syslogData):
        if self._conn is None:
            return

        try:
            ins = self._logTable.insert().values(name=syslogData['name'], 
                                                 message=syslogData['message'],
                                                 exception=syslogData['exception'],
                                                 levelName=syslogData['levelName'],
                                                 levelNumber=syslogData['levelNumber'])

            self._conn.execute(ins)

        except Exception as e:
            print("-----------Error Storing Syslog To DB --------------------")
            print("Lost database connection to {}".format(self._url))
            print("Error: {}".format(e))
            print("----------------------------------------------------------")
            self._conn = None


class SqlReader(object):

    def __init__(self, url):
        self._log = pr.logInit(cls=self,name="SqlReader",path=None)
        self._url = url
        self._conn = None

        try:
            conn = sqlalchemy.create_engine(self._url)
            self._log.info("Opened database connection to {}".format(self._url))
        except Exception as e:
            self._log.error("Failed to open database connection to {}: {}".format(self._url,e))
            return

        self._metadata = sqlalchemy.MetaData(conn)

        self._varTable = sqlalchemy.Table('variables', self._metadata, autoload=True)
        self._logTable = sqlalchemy.Table('syslog', self._metadata, autoload=True)
        self._conn = conn

    # Make this more usefull
    def getVariable(self):
        r = self._conn.execute(sqlalchemy.select([self._varTable]))
        print(r.fetchall())

    # Make this more usefull
    def getSyslog(self, syslogData):
        r = self._conn.execute(sqlalchemy.select([self._logTable]))
        print(r.fetchall())

