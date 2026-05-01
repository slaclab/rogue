#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue - SQL Logging Module
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
import json
from typing import Any


class SqlLogger(object):
    """Logs variable updates and system log entries to a SQL database.

    Parameters
    ----------
    root : pr.Root
        PyRogue root node to monitor.
    url : str
        SQLAlchemy database URL.
    incGroups : object, optional
        Groups to include in variable updates.
    excGroups : object, optional
        Groups to exclude from variable updates.
    """

    def __init__(
        self,
        *,
        root: pr.Root,
        url: str,
        incGroups: str | list[str] | None = None,
        excGroups: str | list[str] | None = ['NoSql'],
    ) -> None:
        self._log = pr.logInit(cls=self,name="SqlLogger",path=None)
        self._url = url
        self._engine = None
        self._thread = None
        self._queue  = queue.Queue()
        self._thread = threading.Thread(target=self._worker)
        self._thread.start()

        self._sysLogPath = root.SystemLogLast.path
        root.addVarListener(func=self._varUpdate, done=None, incGroups=incGroups, excGroups=excGroups)

        try:
            engine = sqlalchemy.create_engine(self._url) #, isolation_level="AUTOCOMMIT")
            self._log.info("Opened database connection to %s", self._url)
        except Exception as e:
            self._log.error("Failed to open database connection to %s: %s", self._url, e)
            return

        #self._metadata = sqlalchemy.MetaData(engine)
        self._metadata = sqlalchemy.MetaData()

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

    def _stop(self) -> None:
        """Stop the worker, flush pending entries, and release the SQLAlchemy engine."""
        if not self._queue.empty():
            print("Waiting for sql logger to finish...")
        self._queue.put(None)

        # Self-thread guard prevents deadlock if called from inside the worker.
        thr = self._thread
        if (thr is not None
                and hasattr(thr, 'is_alive') and thr.is_alive()
                and hasattr(thr, 'join')
                and threading.current_thread() is not thr):
            thr.join()

        if self._engine is not None:
            try:
                self._engine.dispose()
            except Exception:
                pass
            self._engine = None

        print('Sql logger stopped')

    def insert_from_q(self, entry: tuple[str, pr.VariableValue], conn: sqlalchemy.Connection) -> None:
        """
        Insert a single queue entry into the database.

        Parameters
        ----------
        entry : tuple
            ``(path, var_value)`` from a root variable listener callback.
        conn : object
            SQLAlchemy connection for the transaction.
        """

        # Syslog
        if entry[0] == self._sysLogPath:
            val = json.loads(entry[1].value)

            ins = self._logTable.insert().values(
                name=val['name'],
                message=val['message'],
                exception=val['exception'],
                levelName=val['levelName'],
                levelNumber=val['levelNumber'])

        # Variable
        else:

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

        conn.execute(ins)

    def _worker(self) -> None:
        """Worker thread that processes queue entries and writes to the database."""
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
                self._log.error("Lost database connection to %s", self._url)

    def _varUpdate(self, path: str, value: Any) -> None:
        """Queue a variable update for the worker to write to the database."""
        self._queue.put((path,value))


class SqlReader(object):
    """Read variable and syslog data from a SQL database.

    Parameters
    ----------
    url : str
        SQLAlchemy database URL.
    """

    def __init__(self, url: str) -> None:
        self._log = pr.logInit(cls=self,name="SqlReader",path=None)
        self._url = url
        self._engine = None

        try:
            engine = sqlalchemy.create_engine(self._url)
            self._log.info("Opened database connection to %s", self._url)
        except Exception as e:
            self._log.error("Failed to open database connection to %s: %s", self._url, e)
            return

        self._metadata = sqlalchemy.MetaData(engine)

        self._varTable = sqlalchemy.Table('variables', self._metadata, autoload=True)
        self._logTable = sqlalchemy.Table('syslog', self._metadata, autoload=True)
        self._engine = engine

    def getVariable(self) -> None:
        """Fetch and print all variable entries. Placeholder for future enhancement."""
        r = self._conn.execute(sqlalchemy.select([self._varTable]))
        print(r.fetchall())

    def getSyslog(self, syslogData: Any) -> None:
        """Fetch and print syslog entries. Placeholder for future enhancement."""
        r = self._conn.execute(sqlalchemy.select([self._logTable]))
        print(r.fetchall())
