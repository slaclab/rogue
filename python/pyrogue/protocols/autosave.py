import threading
import os
import time
import datetime

class Autosave(object):
    """
    Autosave functionality for Epics/Epics4.

    Environment variables:    
        PYROGUE_AS_REQPATH (required)
            The request path used to find the .req file.

        PYROGUE_AS_SAVPATH (required)
            The path used to create the autosave files.

        PYROGUE_AS_INTERVAL
            The time between autosave file creations (default 5 seconds).

        PYROGUE_AS_SEQCNT
            The number of sequential backups to create (default 3).

        PYROGUE_AS_SEQINT
            The time between sequential backup creations (default 60 seconds).

    Constructor Parameters:
        iocname : str
            This is the name of the IOC, used to find the request file
            and the autosave file.

        vs : object with a "getValue(name : str) : str" method
            This is a "value store" which we use to get the values to 
            autosave.  All values should be returned as str.

    External Interface:
        getInitialValue(name : str) : str
            Return the initial value of the EPICS variable name, or None
            if an initial value is not defined.

    If a required environment variable is not set or the iocname is None,
    this is a do-nothing object.
    """ 
    def __init__(self, iocname, vs):
        self.thread = None
        self.init_ok = False
        self.init_dict = {}
        self._log = pyrogue.logInit(cls=self)
        if iocname is None:
            self._log.info("No iocname, autosave disabled!")
            return
        self.iocname = iocname
        self.vs = vs
        self.reqpath = os.getenv("PYROGUE_AS_REQPATH")
        if self.reqpath is None:
            self._log.info("No PYROGUE_AS_REQPATH, autosave disabled!")
            return
        self.savpath = os.getenv("PYROGUE_AS_SAVPATH")
        if self.savpath is None:
            self._log.info("No PYROGUE_AS_SAVPATH, autosave disabled!")
            return
        else:
            self.savpath +=  "/" + self.iocname
        s = os.getenv("PYROGUE_AS_INTERVAL")
        if s is None:
            self.interval = 5
        else:
            self.interval = float(s)
        s = os.getenv("PYROGUE_AS_SEQCNT")
        if s is None:
            self.seqcnt = 3
        else:
            self.seqcnt = int(s)
        s = os.getenv("PYROGUE_AS_SEQINT")
        if s is None:
            self.seqint = 60
        else:
            self.seqint = float(s)
        self.seqcur = 0
        self.running = False
        self.keep_running = True
        self.signal = threading.Condition()
        self.init_dict = self.read_autosave()
        self.req = self.read_req()
        self.init_ok = True

    def getInitialValue(self, n):
        if n in self.init_dict:
            return self.init_dict[n]
        else:
            return None

    def start(self):
        if self.thread is None and self.init_ok:
            self.thread = threading.Thread(target=self.threadbody)
            self.keep_running = True
            self.thread.start()

    def stop(self):
        if self.thread is not None:
            self.keep_running = False
            self.signal.acquire()
            self.signal.notify()
            self.signal.release()
            self.thread.join()
            self.thread = None

    def threadbody(self):
        next_save = time.time() + self.interval
        next_seq  = time.time() + self.seqint + 0.5
        while self.keep_running:
            t = (next_save if next_save < next_seq else next_seq) - time.time()
            self.signal.acquire()
            if self.signal.wait(t):
                break
            self.signal.release()
            if time.time() > next_save:
                self.write_autosave()
                next_save = next_save + self.interval
            if time.time() > next_seq:
                self.seq_backup()
                next_seq = next_seq + self.seqint

    def read_req(self):
        try:
            with open(self.reqpath + "/" + self.iocname + ".req") as f:
                l = f.readlines()
            l = [x.strip() for x in l]
            l = [x for x in l if x[0] != '#']
            self._log.debug("Request list: %s" % str(l))
            return l
        except:
            return []

    def read_autosave(self):
        try:
            fn = self.savpath + ".sav"
            with open(fn) as f:
                ll = f.readlines()
            if ll[-1] != "<END>\n" and ll[-1] != "<END>\r\n":
                raise Exception
        except:
            # Hmm... didn't work, try the backup!
            try:
                fn = self.savpath + ".savB"
                with open(fn) as f:
                    ll = f.readlines()
                    if ll[-1] != "<END>\n" and ll[-1] != "<END>\r\n":
                        raise Exception
            except:
                # No valid autosave!
                return {}
        self.copyfile(fn, self.savpath + datetime.datetime.now().strftime("_%y%m%d_%H%M%S"))
        d = {}
        for l in ll:
            l = l.strip()
            if l[0] == '#' or l == "<END>":
                continue
            try:
                s = l.index(' ')
                d[l[:s]] = l[s+1:]
            except:
                pass
        return d

    """
    From the EPICS autosave documentation:

    Once a save file has been created successfully, save_restore will
    not overwrite the file unless a good ".savB" backup file
    exists. Similarly, it will not overwrite the ".savB" file unless
    the save file was successfully written.

    All they are really doing is checking if the other file ends "<END>\n".
    We can do that too!

    """
    def check_file(self, fn):
        try:
            with open(fn, 'rb') as f:
                try:  # catch OSError in case of a one line file 
                    f.seek(-2, os.SEEK_END)
                    while f.read(1) != b'\n':
                        f.seek(-2, os.SEEK_CUR)
                except OSError:
                    f.seek(0)
                last_line = f.readline().decode().strip()
            return last_line == "<END>"
        except:
            return False

    def write_autosave(self):
        self._log.debug("WRITE: %s" % datetime.datetime.now())
        if not self.check_file(self.savpath + ".savB") and self.check_file(self.savpath + ".sav"):
            # .sav is good, but .savB is not.  We must have had a previous failure!
            self._log.info("savB is corrupt, making a new copy!")
            if not self.copyfile(self.savpath + ".sav", self.savpath + ".savB"):
                self._log.info("Cannot make copy?!?  Autosave failure!")
                return
        # Now, either .savB is good (we might have made it good!) or if .savB
        # is bad, .sav must be bad as well (and we did nothing above).  The 
        # latter case is startup, so we're good to go!
        l = '# python autosave - %s\n' % datetime.datetime.now()
        for n in self.req:
            v = self.vs.getValue(n)
            if v is None:
                l += '# %s is not in value store.\n' % n
            else:
                l += '%s %s\n' % (n, v)
        l += "<END>\n"
        with open(self.savpath + ".sav", "w") as f:
            f.write(l)
        with open(self.savpath + ".sav") as f:
            rb = f.read()
        if l != rb:
            self._log.info("Autosave readback failed?!?")
            return
        # .sav is good, so we can make .savB.
        if not self.copyfile(self.savpath + ".sav", self.savpath + ".savB"):
            self._log.info("Cannot make copy?!?  Autosave failure!")

    def seq_backup(self):
        self._log.debug("BACKUP: %s" % datetime.datetime.now())
        if self.copyfile("%s.sav" % (self.savpath),
                         "%s.sav%d" % (self.savpath, self.seqcur)):
            self.seqcur = (self.seqcur + 1) % self.seqcnt
        else:
            self._log.info("Failure creating sequential backup %d!\n" % self.seqcur)

    def copyfile(self, infn, outfn):
        try:
            with open(infn) as f:
                d = f.read()
            with open(outfn, "w") as f:
                f.write(d)
            with open(outfn) as f:
                d2 = f.read()
            return d == d2
        except:
            return False
