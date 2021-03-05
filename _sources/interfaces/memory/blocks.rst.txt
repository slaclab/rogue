.. _interfaces_memory_blocks:

===============
Blocks & Models
===============

In the Rogue memory interface, the block provides a representation of the underlying hardware memory
space, hosting one or more Variable objects. It is in the Block where native python types are converted
into the bits and byte that are ultimately written to the hardware devices.

When Variables are created in a Device they are arranged into Blocks which may host multiple variables. The
mapping of Variables to Blocks is determined by the minimum register transaction size supported by the
hardware. For example if the hardware requires a minimum transaction size of 32-bits, a set of Variables
which access space in a single 32-bit register will be mapped to the same Block. The user may also
pre-build blocks in Device with a specific size in order to enforece a larger grouping of Variables into
a Block.

The Block object will keep track of the "stale" state of the shadow memory space. This allows the various
Variables in a Block to be updated, followed by a single transaction that commits the Block memory space
to hardware. For very large Blocks which are much larger than the minimum transaction size, the user may
initiate sub-block transactions which only update the "stale" portion of the Block space. This allows the
user to perform high rate, low overhead transactions to individual sections of a Block while also supporting
larger burst transactions when the entire Block is read from or written to memory.

In most cases the user will simply add Variables to a Device with little attention to how the Blocks are
created and assigned to Variables. In some cases the user may want to set the size of specific
Blocks for performance reasons. In more advanced cases the user can also sub-class a Block, creating
a custom device which allows new types of transactions, and also allows lower level complex register
transactions to occur at a lower level in the Block.

See :ref:`interfaces_memory_blocks_advanced` for more information about the advanced features of the Block class.

The translation of native python types to lower level bits and bytes is controlled by the Model class, which is
a special Python class in Rogue which defines how a register type is converted, accessed and displayed. The Model
class works closely with the Block, with the Block having lower level routines which are directly associated
with the standard set of Rogue Models.

The following Models are currently supported in Rogue:

+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| Model                                       | Hardware Type         | Python Type       | Bit Size       | Notes                                          |
+=============================================+=======================+===================+================+================================================+
| :ref:`interfaces_memory_model_uint`         | unsigned integer      | int               | unconstrained  | Little endian                                  |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_uintbe`       | unsigned integer      | int               | unconstrained  | Same as UInt but big endian                    |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_uintreversed` | unsigned integer      | int               | unconstrained  | Same as UInt but with a reversed bit order.    |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_int`          | signed integer        | int               | unconstrained  | Little endian                                  |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_intbe`        | signed integer        | int               | unconstrained  | Same as Int but big endian                     |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_bool`         | bit                   | bool              | 1-bit          |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_string`       | bytes                 | string            | unconstrained  |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_float`        | 32-bit float          | float             | 32-bits        |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_floatbe`      | 32-bit float          | float             | 32-bits        | Same as float but big endian                   |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_double`       | 64-bit float          | float             | 64-bits        |                                                |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_doublebe`     | 64-bit float          | float             | 64-bits        | Same as float but big endian                   |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+
| :ref:`interfaces_memory_model_fixed`        | fixed point           | float             | unconstrained  | Not fully functional yet                       |
+---------------------------------------------+-----------------------+-------------------+----------------+------------------------------------------------+

Most of the above types perform the python to byte conversions in low level C++ calls in the Block class for performance reasons.
An exception to this is UInt and Int types that exceed 64-bits. These conversions are performed in the Model class at the python
level.

Custom Models
-------------

The user has the ability to create application specific data types by sub-classing the Model in python and providing the
toByte and fromBytes functions that are called by the Block to perform the data conversions. This allows for a quick method to
support odd data types.

The block class also supports any of the above Models as a list. See the Variable class description for more details.

Below is an example of a user defined Model for a special data type:

.. code-block:: python

    import pyrogue
    import rogue.interfaces.memory

    # Create a sub-class of a model
    class MyUInt(pyrogue.Model):

        # Setup the class parameters
        ptype = int
        defaultdisp = '{:#x}'
        modelId = rogue.interfaces.memory.PyFunc

       def __init__(self, bitsize):
         super().__init__(bitsize)

       # This function receives the native python type and converts it to a byte array
       def toBytes(self, value):
           return value.to_bytes(byteCount(self.bitSize), 'little', signed=False)

       # This function receives a byte array and converts it to the native python type
       def fromBytes(self, ba):
           return int.from_bytes(ba, 'little', signed=False)

       # Convert a string representation to the python native type
       def fromString(self, string):
           return int(string, 0)

       # Return the minimum value
       def minValue(self):
           return 0

       # Return the maximum value
       def maxValue(self):
           return (2**32)-1

The user may also want to perform the python type conversion in lower level C++. In order to do this they
must sub-class the Block class and add it to a user specific library. They can then use a modeId in the
range 0x80 - 0xFF.  See :ref:`interfaces_memory_blocks_advanced` for more information about the advanced features of the Block class.


Using Custom Models
-------------------

The following shows an example of using the above custom model in Rogue. The code blow is executed during the
creation of a custom Device class. See xxxx for more details.

.. code-block:: python

   # Create a variable using my custom Model
   self.add(pyrogue.RemoteVariable(
      name="MyRegister",
      description="My register with my model",
      offset=0x1000,
      bitSize=32,
      bitOffset=0,
      base=MyUInt,
      mode="RW"))

The custom model is passed to the RemoteVariable base parameter. A Block of the appropriate size will be created
and assocaited with the above RemoteVariable as approprite.

Pre-Allocating Blocks
---------------------

In some cases the user may want to pre-create blocks of a specific size to better group Variables that are more
effeciently accessed in larger burst transactions. With larger blocks the user can initiate transactions
on a sub-portion of the block by accessing the variable directly, or the user can force larger burst transactions
of the larger block in operations which require it.

The following shows an example of pre-allocating a block for association with a Variable. The Variables are assigned to
blocks the overlap their address space. The code blow is executed during the creation of a custom Device class. See xxxx for more details.

.. code-block:: python

   # Pre-Allocate a large block to hold our variables, offset = 0x1000, size = 128
   self.addCustomBlock(rogue.interfaces.memory.Block(0x1000,128))

   # Create a variable using my custom Model
   self.add(pyrogue.RemoteVariable(
      name="MyRegister",
      description="My register with my model",
      offset=0x1000,
      bitSize=32,
      bitOffset=0,
      base=MyUInt,
      mode="RW"))

For more information see the :ref:`interfaces_memory_block` and :ref:`interfaces_memory_model` class descriptions.

