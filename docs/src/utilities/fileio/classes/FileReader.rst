.. _utilities_fileio_FileReader

File Reader
===========

.. module:: _FileReader
   :synopsis: Lightweight reader for Rogue data files, with optional batched data support.

Overview
--------

The :mod:`_FileReader` module provides a lightweight interface for reading
binary data files produced by the `Rogue` framework. It can be used both
inside and outside a full `pyrogue` installation.

Two header formats are supported:

* A **Rogue header** that precedes every record in the file.
* An optional **batch header** used when the file contains batched data
  (multiple sub-frames per record).

The main entry point is the :class:`FileReader` class, which acts as an
iterator over records in one or more files.

Constants
---------

.. data:: RogueHeaderSize

   Size, in bytes, of the Rogue record header.

.. data:: RogueHeaderPack

   Struct packing format string for the Rogue header (``'IHBB'``).

.. data:: BatchHeaderSize

   Size, in bytes, of the batch header for batched data.

.. data:: BatchHeaderPack

   Struct packing format string for the batch header (``'IBBBB'``).

RogueHeader
-----------

.. class:: RogueHeader

   Dataclass describing the fixed Rogue record header.

   Each record in the file starts with a Rogue header, followed by the
   record payload.

   Attributes
   ----------

   .. attribute:: size
      :type: int

      Size of the record payload in bytes, *excluding* the header.

   .. attribute:: flags
      :type: int

      Frame flags associated with the record.

   .. attribute:: error
      :type: int

      Error status code for the record.

   .. attribute:: channel
      :type: int

      Channel identifier for the record.

BatchHeader
-----------

.. class:: BatchHeader

   Dataclass describing the header for a single batched sub-frame.

   When the :class:`FileReader` is configured for batched data
   (``batched=True``), each record may contain multiple sub-frames,
   each preceded by a batch header.

   Attributes
   ----------

   .. attribute:: size
      :type: int

      Size in bytes of the batched sub-frame payload.

   .. attribute:: tdest
      :type: int

      TDEST value taken from the AXI stream frame.

   .. attribute:: fUser
      :type: int

      First USER value from the AXI stream frame.

   .. attribute:: lUser
      :type: int

      Last USER value from the AXI stream frame.

   .. attribute:: width
      :type: int

      Width of the batched data in bytes. This is mapped from an encoded
      value in the file to one of ``2, 4, 8, 16``.

Exceptions
----------

.. class:: FileReaderException

   Custom exception type raised for file reader errors such as:

   * Unreadable input files.
   * Unexpected end of file.
   * Header or payload underruns.
   * Configuration dictionary lookup failures.

FileReader
----------

.. class:: FileReader(files, configChan=None, log=None, batched=False)

   A lightweight reader for Rogue data files.

   The :class:`FileReader` iterates over records in one or more binary
   files, exposing the record headers and payloads through the
   :meth:`records` generator.

   Parameters
   ----------

   .. py:parameter:: files
      :type: str or list[str]

      A single filename or list of filenames to read data from. All files
      must be readable; otherwise a :class:`FileReaderException` is raised.

   .. py:parameter:: configChan
      :type: int or None
      :default: None

      Channel ID of the configuration/status stream embedded in the data
      file. If set to ``None`` (the default), configuration records are not
      processed. When provided, records whose Rogue header channel matches
      ``configChan`` are parsed as YAML configuration updates.

   .. py:parameter:: log
      :type: logging.Logger or None
      :default: None

      Logger instance used for diagnostic messages. If ``None``, a new
      logger named ``"pyrogue.FileReader"`` is created.

   .. py:parameter:: batched
      :type: bool
      :default: False

      Indicates whether the input files contain batched data. When
      ``True``, each record may contain multiple sub-frames, and the
      :meth:`records` generator yields an additional :class:`BatchHeader`
      object for each sub-frame.

   Attributes
   ----------

   .. attribute:: currCount
      :type: int

      Number of data records processed in the *current* file.

   .. attribute:: totCount
      :type: int

      Total number of data records processed across all files.

   .. attribute:: configDict
      :type: dict

      Current configuration/status dictionary constructed from YAML
      configuration records (if ``configChan`` is not ``None``).

Record iteration
~~~~~~~~~~~~~~~

.. method:: FileReader.records()

   Iterate over data records in all configured files.

   Depending on whether the reader is configured for batched data, this
   generator yields:

   * **Non-batched mode** (``batched=False``):

     .. code-block:: python

        for header, data in reader.records():
            ...

     Where:

     * ``header`` is a :class:`RogueHeader` instance.
     * ``data`` is a NumPy array of ``int8`` containing the record payload.

   * **Batched mode** (``batched=True``):

     .. code-block:: python

        for header, batch_header, data in reader.records():
            ...

     Where:

     * ``header`` is a :class:`RogueHeader` instance for the whole record.
     * ``batch_header`` is a :class:`BatchHeader` instance for the current
       sub-frame.
     * ``data`` is a NumPy array of ``int8`` containing the sub-frame payload.

   All configuration records (matching ``configChan``) are consumed
   internally and used to update :attr:`configDict`; they are not yielded
   by this generator.

Properties
~~~~~~~~~

.. py:property:: FileReader.currCount

   Number of data records processed in the current file.

.. py:property:: FileReader.totCount

   Total number of data records processed across all files.

.. py:property:: FileReader.configDict

   Dictionary holding the current configuration/status state as assembled
   from YAML records encountered while reading.

Configuration access
~~~~~~~~~~~~~~~~~~~

.. method:: FileReader.configValue(path)

   Retrieve a configuration or status value from :attr:`configDict`.

   Parameters
   ----------

   .. py:parameter:: path
      :type: str

      Dotted path to the desired configuration key. For example,
      ``"top.block.parameter"`` looks up nested keys in
      :attr:`configDict`.

   Returns
   -------

   object
      The requested configuration/status value.

   Raises
   ------

   :class:`FileReaderException`
      If the given path cannot be resolved in the configuration dictionary.

Context manager support
~~~~~~~~~~~~~~~~~~~~~~

.. method:: FileReader.__enter__()

   Enter the runtime context related to this object. Returns ``self``.

.. method:: FileReader.__exit__(exc_type, exc_val, exc_tb)

   Exit the runtime context. Currently a no-op.

Usage examples
--------------

Basic non-batched reading
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from _FileReader import FileReader

   reader = FileReader("data.dat")

   for header, data in reader.records():
       print(header, len(data))

Reading batched data
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   reader = FileReader("batched.dat", batched=True)

   for header, batch_header, data in reader.records():
       print(batch_header, len(data))

Using a configuration channel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   reader = FileReader("data_with_config.dat", configChan=0)

   for header, data in reader.records():
       value = reader.configValue("adc.gain")
       print(value)

