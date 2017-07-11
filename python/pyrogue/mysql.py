#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue mysql interface
#-----------------------------------------------------------------------------
# File       : pyrogue/mysql.py
# Author     : Ryan Herbst, rherbst@slac.stanford.edu
# Created    : 2016-09-29
# Last update: 2016-09-29
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
        self._runEn   = True
        self._thread  = None
        self._log     = pyrogue.logInit(self)

        if not root.running:
            raise Exception("MysqlGw can be setup on a tree which is not started")

        # Connect to server
        with self._dbLock:
            if not self._connect():
                return

            # Create PVs
            self._addDevice(self._root)
            self._delOldEntries()

        self._thread = threading.Thread(target=self._workRun)

    def _connect(self):
        if self._db is not None:
            return True

        try:
            self._log.info("Connecting to Mysql server {}".format(self._host)
            self._db = MySQLdb.connect(host=self._host,user=self._user,passwd=self._pass,db=self._dbase,port=self._port)

            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT VERSION()")
            self._db.autocommit(True)
            return True

        except MySQLdb.Error:
            self._log.error("Failed to connect to Mysql server {}".format(self._host)
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

    def _addDevice(self,device):
        for key,value in device.variables.items():
            self._addVariable(value)

        for key,value in device.commands.items():
            self._addCommand(value)

        for key,value in device.devices.items():
            self._addDevice(value)

    def _addVariable(self, variable):
        cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

        sql =  "replace into variable ("
        sql += "variable.name,"
        sql += "variable.description,"
        sql += "variable.value,"
        sql += "variable.create_ts,"
        sql += "variable.server_ts,"
        sql += "variable.server_ser,"
        sql += "variable.client_ts,"
        sql += "variable.client_ser,"
        sql += "variable.mode,"
        sql += "variable.units,"
        sql += "variable.minimum,"
        sql += "variable.maximum,"
        sql += "variable.disp,"
        sql += "variable.enum,"
        sql += "variable.typeStr,"
        sql += "variable.hidden)"
        sql += "values ("

        sql += "'{}',".format(variable.name)
        sql += "'{}',".format(variable.description)
        sql += "'{}',".format(variable.valueDisp())
        sql += "'now()'," # create_ts
        sql += "'now()'," # server_ts
        sql += "'0',"     # server_ser
        sql += "'now()'," # client_ts
        sql += "'0',"     # client_ser
        sql += "'{}',".format(variable.mode)
        sql += "'{}',".format(variable.units)
        sql += "'{}',".format(variable.minimum)
        sql += "'{}',".format(variable.maximum)
        sql += "'{}',".format(variable.disp)
        sql += "'{}',".format(variable.enum)
        sql += "'{}',".format(variable.typeStr)
        sql += "'{}')".format(variable.hidden)

        cursor.execute(sql)
        self._varSer[var.path] = 0

        self.addListener(self._updateVariable)

    def _updateVariable (self, var, value, disp):
        with self._dbLock:
            if self._db is None:
                raise MysqlException("Not connected to Mysql server " + self._host)

            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            sql = "update variable set value='{}', server_ts=now(),".format(disp)
            sql += "server_ser = (server_ser + 1) where name='{}'".format(var.path)

            cursor.execute(sql)

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
        sql += "command.units,"
        sql += "command.minimum,"
        sql += "command.maximum,"
        sql += "command.disp,"
        sql += "command.enum,"
        sql += "command.typeStr,"
        sql += "command.hidden)"
        sql += "values ("

        sql += "'{}',".format(command.name)
        sql += "'{}',".format(command.description)
        sql += "'',"      # Arg
        sql += "'{}',".format(command.arg)
        sql += "'now()'," # create_ts
        sql += "'now()'," # client_ts
        sql += "'0',"     # client_ser
        sql += "'{}',".format(command.units)
        sql += "'{}',".format(command.minimum)
        sql += "'{}',".format(command.maximum)
        sql += "'{}',".format(command.disp)
        sql += "'{}',".format(command.enum)
        sql += "'{}',".format(command.typeStr)
        sql += "'{}')".format(command.hidden)

        cursor.execute(sql)
        self._cmdSer[cmd.path] = 0

    def _delOldEntries(self):
        cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("delete from command  where create_ts < (now() - interval 1 minute)")
        cursor.execute("delete from variable where create_ts < (now() - interval 1 minute)")

        self._dbLock.release()

    def _pollVariables(self):
        if self._db is None:
            return

        rows = []
        with self._dbLock:
            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            # Setup query
            query = "select name, value, client_ser, now() as tstamp from variables"

            # Filter with optional passed time 
            if self._varTs:
                query += " where client_ts > ('{}' - interval 1 second)".format(self._varTs)

            # Execute query
            cursor.execute(query)
            rows = cursor.fetchall()

        # Process variables
        for row in rows:
            self._varTs = row['tstamp']
            if self._varSer != row['client_ser']:
                self._varSer = row['client_ser']

                try:
                    self._root.setOrExecPath(row['name'],row['value'])
                except:
                    pass

    def _pollCommands(self):
        if self._db is None:
            return

        rows = []
        with self._dbLock:
            cursor = self._db.cursor(MySQLdb.cursors.DictCursor)

            # Setup query
            query = "select name, arg, client_ser, now() as tstamp from commands"

            # Filter with optional passed time 
            if self._cmdTs:
                query += " where client_ts > ('{}' - interval 1 second)".format(self._cmdTs)

            # Execute query
            cursor.execute(query)
            rows = cursor.fetchall()

        # Process variables
        for row in rows:
            self._cmdTs = row['tstamp']
            if self._cmdSer != row['client_ser']:
                self._cmdSer = row['client_ser']

                try:
                    self._root.setOrExecPath(row['name'],row['arg'])
                except:
                    pass

    def _workRun(self):
        while(self._runEn):
            time.sleep(0.5)
            with self._dbLock:
                if not self._connect():
                    time.sleep(1)
            self._pollCommands()
            self._pollVariables()

