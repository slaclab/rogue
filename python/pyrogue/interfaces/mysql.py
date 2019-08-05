#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue mysql interface
#-----------------------------------------------------------------------------
# File       : pyrogue/interfaces/mysql.py
# Created    : 2016-09-29
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import threading
import pyrogue
import time
import MySQLdb
import datetime

class MysqlException(Exception):
    pass

def mysqlString(field):
    return MySQLdb.escape_string(str(field)).decode('UTF-8')

def setupDb (dbHost, dbName, dbUser, dbPass):
    db = MySQLdb.connect(host=dbHost,user=dbUser,passwd=dbPass,db=dbName)

    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('drop table if exists variable, command')

    sql  = "create table variable ("
    sql += "name varchar(255) unique key,"
    sql += "description varchar(255),"
    sql += "value varchar(1000),"
    sql += "set_value varchar(100),"
    sql += "create_ts datetime,"
    sql += "server_ts datetime,"
    sql += "server_ser int,"
    sql += "client_ts datetime,"
    sql += "client_ser int,"
    sql += "client_ack int,"
    sql += "mode varchar(20),"
    sql += "units varchar(20),"
    sql += "minimum varchar(80),"
    sql += "maximum varchar(80),"
    sql += "disp varchar(80),"
    sql += "enum varchar(80),"
    sql += "typeStr varchar(20),"
    sql += "hidden varchar(20))"
    cursor.execute(sql)

    sql  = "create table command ("
    sql += "name varchar(255) unique key,"
    sql += "description varchar(255),"
    sql += "arg varchar(100),"
    sql += "hasArg varchar(20),"
    sql += "create_ts datetime,"
    sql += "client_ts datetime,"
    sql += "client_ser int,"
    sql += "client_ack int,"
    sql += "units varchar(20),"
    sql += "minimum varchar(80),"
    sql += "maximum varchar(80),"
    sql += "disp varchar(80),"
    sql += "enum varchar(80),"
    sql += "typeStr varchar(20),"
    sql += "hidden varchar(20))"
    cursor.execute(sql)

class MysqlGw(object):

    def __init__(self, *, dbHost, dbName, dbUser, dbPass, root):
        self._host    = dbHost
        self._port    = 3306
        self._user    = dbUser
        self._pass    = dbPass
        self._dbase   = dbName
        self._root    = root
        self._cmdTs   = None
        self._varTs   = None
        self._db      = None
        self._dbLock  = threading.Lock()
        self._varSer  = {}
        self._cmdSer  = {}
        self._runEn   = False
        self._thread  = None
        self._log     = pyrogue.logInit(cls=self)

        if not root.running:
            raise Exception("MysqlGw can not be setup on a tree which is not started")

        # Connect to server
        with self._dbLock:
            if not self._connect():
                return

            # Create PVs
            for v in self._root.variableList:
                if v.isCommand:
                    self._addCommand(v)
                elif v.isVariable:
                    self._addVariable(v)
            self._db.commit()
            self._delOldEntries()

    def start(self):
        self._runEn = True
        self._thread = threading.Thread(target=self._workRun)
        self._thread.start()

    def _connect(self):
        if self._db is not None:
            return True

        try:
            #self._log.error("Connecting to Mysql server {}".format(self._host))
            self._log.info("Connecting to Mysql server {}".format(self._host))
            newDb = MySQLdb.connect(
                host=self._host,
                user=self._user,
                passwd=self._pass,
                db=self._dbase,
                port=self._port)

            cursor = newDb.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT VERSION()")
            self._db = newDb
            return True

        except MySQLdb.Error as e:
            self._log.error("Failed to connect to Mysql server {}: {}".format(self._host,e))
            self._db = None
            return False

    def stop(self):
        self._runEn = False
        if self._thread is not None:
            self._thread.join()

        with self._dbLock:
            if self._db is not None:
                self._db.close()
                self._db = None

    def _addVariable(self, variable):
        cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

        sql =  "replace into variable ("
        sql += "variable.name,"
        sql += "variable.description,"
        sql += "variable.value,"
        sql += "variable.set_value,"
        sql += "variable.create_ts,"
        sql += "variable.server_ts,"
        sql += "variable.server_ser,"
        sql += "variable.client_ts,"
        sql += "variable.client_ser,"
        sql += "variable.client_ack,"
        sql += "variable.mode,"
        sql += "variable.units,"
        sql += "variable.minimum,"
        sql += "variable.maximum,"
        sql += "variable.disp,"
        sql += "variable.enum,"
        sql += "variable.typeStr,"
        sql += "variable.hidden)"
        sql += "values ("

        sql += "'{}',".format(mysqlString(variable.path))
        sql += "'{}',".format(mysqlString(variable.description))
        sql += "'{}',".format(mysqlString(variable.valueDisp()))
        sql += "'',"     # set_value
        sql += "now(),"  # create_ts
        sql += "now(),"  # server_ts
        sql += "'0',"    # server_ser
        sql += "now(),"  # client_ts
        sql += "'0',"    # client_ser
        sql += "'0',"    # client_ack
        sql += "'{}',".format(mysqlString(variable.mode))
        sql += "'{}',".format(mysqlString(variable.units))
        sql += "'{}',".format(mysqlString(variable.minimum))
        sql += "'{}',".format(mysqlString(variable.maximum))
        sql += "'{}',".format(mysqlString(variable.disp))
        sql += "'{}',".format(mysqlString(variable.enum))
        sql += "'{}',".format(mysqlString(variable.typeStr))
        sql += "'{}')".format(mysqlString(variable.hidden))

        cursor.execute(sql)
        self._varSer[variable.path] = 0
        variable.addListener(self._updateVariables)

    def _updateVariables (self, path, val):
        with self._dbLock:
            if self._db is None:
                #self._log.error("Not connected to Mysql server " + self._host)
                return

            try:
                cursor = self._db.cursor(MySQLdb.cursors.DictCursor)
                sql = "update variable set value='{}', server_ts=now(),".format(mysqlString(val.valueDisp))
                sql += "server_ser = (server_ser + 1) where name='{}'".format(path)
                cursor.execute(sql)
                self._db.commit()
            except:
                self._log.error("Error executing sql.")
                self._db = None

    def _addCommand (self, command):
        cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

        sql =  "replace into command ("
        sql += "command.name,"
        sql += "command.description,"
        sql += "command.arg,"
        sql += "command.hasArg,"
        sql += "command.create_ts,"
        sql += "command.client_ts,"
        sql += "command.client_ser,"
        sql += "command.client_ack,"
        sql += "command.units,"
        sql += "command.minimum,"
        sql += "command.maximum,"
        sql += "command.disp,"
        sql += "command.enum,"
        sql += "command.typeStr,"
        sql += "command.hidden)"
        sql += "values ("

        sql += "'{}',".format(mysqlString(command.path))
        sql += "'{}',".format(mysqlString(command.description))
        sql += "'',"      # Arg
        sql += "'{}',".format(mysqlString(command.arg))
        sql += "now(),"   # create_ts
        sql += "now(),"   # client_ts
        sql += "'0',"     # client_ser
        sql += "'0',"     # client_ack
        sql += "'{}',".format(mysqlString(command.units))
        sql += "'{}',".format(mysqlString(command.minimum))
        sql += "'{}',".format(mysqlString(command.maximum))
        sql += "'{}',".format(mysqlString(command.disp))
        sql += "'{}',".format(mysqlString(command.enum))
        sql += "'{}',".format(mysqlString(command.typeStr))
        sql += "'{}')".format(mysqlString(command.hidden))

        cursor.execute(sql)
        self._cmdSer[command.path] = 0

    def _delOldEntries(self):
        cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("delete from command  where create_ts < (now() - interval 1 minute)")
        cursor.execute("delete from variable where create_ts < (now() - interval 1 minute)")
        self._db.commit()

    def _pollVariables(self):
        rows = []
        with self._dbLock:
            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            # Setup query
            query = "select name, set_value, client_ser, now() as tstamp from variable"

            # Filter with optional passed time 
            if self._varTs:
                query += " where client_ts > ('{}' - interval 1 second)".format(self._varTs)

            # Execute query
            cursor.execute(query)
            rows = cursor.fetchall()

        # Process variables
        for row in rows:
            self._varTs = row['tstamp']
            if self._varSer[row['name']] != row['client_ser']:
                self._varSer[row['name']] = row['client_ser']

                if row['set_value'] == 'None':
                    val = None
                else:
                    val = row['set_value']

                self._root.setDisp(row['name'],val)

        with self._dbLock:
            for row in rows:
                cursor.execute("update variable set client_ack = client_ser where name='{}'".format(row['name']))

    def _pollCommands(self):
        rows = []
        with self._dbLock:
            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            # Setup query
            query = "select name, arg, client_ser, now() as tstamp from command"

            # Filter with optional passed time 
            if self._cmdTs:
                query += " where client_ts > ('{}' - interval 1 second)".format(self._cmdTs)

            # Execute query
            cursor.execute(query)
            rows = cursor.fetchall()

        # Process variables
        for row in rows:
            self._cmdTs = row['tstamp']
            if self._cmdSer[row['name']] != row['client_ser']:
                self._cmdSer[row['name']] = row['client_ser']
                if row['arg'] == 'None':
                    arg = None
                else:
                    arg = row['arg']

                self._root.exec(row['name'],arg)

        with self._dbLock:
            for row in rows:
                cursor.execute("update command set client_ack = client_ser where name='{}'".format(row['name']))

    def _workRun(self):
        while(self._runEn):
            time.sleep(0.5)
            with self._dbLock:
                if not self._connect():
                    time.sleep(5)
                    continue;

            try:
                self._pollCommands()
                self._pollVariables()
            except Exception as e:
                self._log.error("Mysql error: " + str(e))
                with self._dbLock:
                    self._db = None


class MysqlClient(object):

    def __init__(self, *, dbHost, dbName, dbUser, dbPass):
        self._host    = dbHost
        self._port    = 3306
        self._user    = dbUser
        self._pass    = dbPass
        self._dbase   = dbName
        self._db      = None
        self._dbLock  = threading.Lock()

        # Connect to server
        with self._dbLock:
            self._connect()

    def _connect(self):
        if self._db is not None:
            return

        self._db = MySQLdb.connect(host=self._host,user=self._user,passwd=self._pass,db=self._dbase,port=self._port)

        cursor = self._db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT VERSION()")
        self._db.autocommit(True)

    def get(self, path):
        with self._dbLock:
            self._connect()
            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            sql = "select value from variable where name='{}'".format(path)
            cursor.execute(sql)
            row = cursor.fetchone()

            if row is not None:
                return row['value']
            else:
                return None

    def set(self, path, value):
        with self._dbLock:
            self._connect()
            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            sql = "update variable set set_value='{}', client_ts=now(),".format(mysqlString(value))
            sql += "client_ser = (client_ser + 1) where name='{}'".format(path)

            cursor.execute(sql)

            while(True):
                sql = "select client_ser, client_ack from variable where name='{}'".format(path)
                cursor.execute(sql)
                row = cursor.fetchone()
                if row['client_ser'] == row['client_ack']:
                    return
                time.sleep(.1)

    def exec (self, path, arg=None):
        with self._dbLock:
            self._connect()
            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            sql = "update command set arg='{}', client_ts=now(),".format(mysqlString(arg))
            sql += "client_ser = (client_ser + 1) where name='{}'".format(path)

            cursor.execute(sql)

            while(True):
                sql = "select client_ser, client_ack from command where name='{}'".format(path)
                cursor.execute(sql)
                row = cursor.fetchone()
                if row['client_ser'] == row['client_ack']:
                    return
                time.sleep(.1)
