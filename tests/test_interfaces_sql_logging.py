import json
import logging

import pyrogue as pr
import pyrogue.interfaces as pr_intf
import pyrogue.interfaces._SqlLogging as sql_logging_mod
import sqlalchemy


class SqlTestDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.LocalVariable(name="Value", value=1))


class SqlTestRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False, maxLog=10)
        self.add(SqlTestDevice(name="Dev"))


def _read_rows(url, table):
    engine = sqlalchemy.create_engine(url)
    with engine.connect() as conn:
        return conn.execute(sqlalchemy.text(f"SELECT * FROM {table}")).fetchall()


def test_sql_logger_writes_variable_and_syslog_rows(tmp_path):
    db_path = tmp_path / "sql_logger.db"
    url = f"sqlite:///{db_path}"
    log = logging.getLogger("pyrogue.test.sql")
    log.setLevel(logging.INFO)

    with SqlTestRoot() as root:
        logger = pr_intf.SqlLogger(root=root, url=url)

        # Queue one variable row directly so the assertion does not depend on
        # Root listener timing; the syslog row below still exercises the live
        # listener path.
        root.Dev.Value.set(5)
        logger._varUpdate(root.Dev.Value.path, root.Dev.Value.getVariableValue(read=False))

        # RootLogHandler stores this in SystemLogLast, which the SqlLogger sees
        # as just another variable update on the subscribed path.
        log.info("sql logger message")

        logger._stop()

    variables = _read_rows(url, "variables")
    syslog = _read_rows(url, "syslog")

    assert any(row.path == "root.Dev.Value" and str(row.value) == "5" for row in variables)
    assert any(row.name == "pyrogue.test.sql" and row.message == "sql logger message" for row in syslog)


def test_sql_logger_handles_large_ints_and_tuples(tmp_path):
    db_path = tmp_path / "sql_logger_types.db"
    url = f"sqlite:///{db_path}"

    with SqlTestRoot() as root:
        logger = pr_intf.SqlLogger(root=root, url=url)

        # Exercise the special-case serialization paths directly so the test is
        # independent of any variable-type limitations in the tree layer.
        big_value = type(
            "BigValue",
            (),
            {
                "value": 1 << 80,
                "valueDisp": str(1 << 80),
                "enum": None,
                "disp": "{}",
                "severity": "Good",
                "status": "Good",
            },
        )()
        tuple_value = type(
            "TupleValue",
            (),
            {
                "value": (1, 2),
                "valueDisp": "(1, 2)",
                "enum": None,
                "disp": "{}",
                "severity": "Good",
                "status": "Good",
            },
        )()

        with logger._engine.begin() as conn:
            logger.insert_from_q(("root.Dev.Big", big_value), conn)
            logger.insert_from_q(("root.Dev.Tuple", tuple_value), conn)

        logger._stop()

    rows = _read_rows(url, "variables")
    assert any(row.path == "root.Dev.Big" and row.value == str(1 << 80) for row in rows)
    assert any(row.path == "root.Dev.Tuple" and row.value == "(1, 2)" for row in rows)


def test_sql_logger_open_failure_and_worker_disconnect(monkeypatch, tmp_path, caplog):
    with SqlTestRoot() as root:
        with monkeypatch.context() as m:
            m.setattr(sql_logging_mod.sqlalchemy, "create_engine", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("open failed")))
            failed_logger = pr_intf.SqlLogger(root=root, url="sqlite:///ignored.db")
        assert failed_logger._engine is None
        failed_logger._stop()

    db_path = tmp_path / "sql_logger_disconnect.db"
    url = f"sqlite:///{db_path}"

    with SqlTestRoot() as root:
        logger = pr_intf.SqlLogger(root=root, url=url)

        # Force the worker transaction path to fail once and verify it disables
        # the engine instead of looping forever on a dead connection.
        monkeypatch.setattr(logger, "insert_from_q", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("write failed")))
        with caplog.at_level(logging.ERROR):
            logger._varUpdate("root.Dev.Value", root.Dev.Value.getVariableValue(read=False))
            logger._stop()

        assert logger._engine is None
        assert "Lost database connection" in caplog.text


def test_sql_logger_syslog_insert_from_queue(tmp_path):
    db_path = tmp_path / "sql_logger_syslog.db"
    url = f"sqlite:///{db_path}"

    with SqlTestRoot() as root:
        logger = pr_intf.SqlLogger(root=root, url=url)
        syslog_entry = json.dumps({
            "name": "pyrogue.test.sql",
            "message": "entry",
            "exception": None,
            "levelName": "INFO",
            "levelNumber": 20,
        })

        with logger._engine.begin() as conn:
            logger.insert_from_q((root.SystemLogLast.path, syslog_entry), conn)

        logger._stop()

    rows = _read_rows(url, "syslog")
    assert any(row.name == "pyrogue.test.sql" and row.message == "entry" for row in rows)
