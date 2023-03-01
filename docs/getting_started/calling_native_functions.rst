Calling native functions
========================

In ``rpc-project``, almost everything is wrapped using the ``Symbol``
Object. Symbol is just a nicer way for referring to addresses
encapsulated with an object allowing to deref the memory inside, or use
these addresses as functions.

In order to create a symbol from a given address, please use:

.. code:: python

   s = p.symbol(0x12345678)

   # the Symbol object extends `int`
   True == isinstance(s, int)

   # write into this memory
   s.poke(b'abc')

   # peek(/read) 20 bytes of memory
   print(s.peek(20))

   # jump to `s` as a function, passing (1, "string") as its args 
   s(1, "string")

   # change the size of each item_size inside `s` for derefs
   s.item_size = 1

   # *(char *)s = 1
   s[0] = 1

   # *(((char *)s)+1) = 1
   s[1] = 1

   # symbol inherits from int, so all int operations apply
   s += 4

   # change s item size back to 8 to store pointers
   s.item_size = 8

   # *(intptr_t *)s = 1
   s[0] = 1

   # storing the return value of the function executed at `0x11223344`
   # into `*s`
   s[0] = p.symbol(0x11223344)()  # calling symbols also returns symbols 

   # query in which file 0x11223344 is loaded from
   print(p.symbol(0x11223344).filename)

Globalized symbols
------------------

Usually you would want/need to use the symbols already mapped into the
currently running process. To do so, you can access them using
``symbols.<symbol-name>``. The ``symbols`` global object is of type
``SymbolsJar``, which is a wrapper to ``dict`` for accessing all
exported symbols. For example, the following will generate a call to the
exported ``malloc`` function with ``20`` as its only argument:

.. code:: python

   x = symbols.malloc(20)

You can also just write their name as if they already were in the global
scope. The client will check if no name collision exists, and if so,
will perform the following lazily for you:

.. code:: python

   x = malloc(20)

   # is equivalent to:
   malloc = symbols.malloc
   x = malloc(20)

ObjC support
------------

When working on Darwin based systems, it can be sometimes easier to use
the builtin ObjC support.

.. code:: python

   # creating CF/NSObjets using the builtin cf() method
   some_cf_string = p.cf('some string')

   # create a new NSMutableDictionary
   a = NSMutableDictionary.new()

   # tell where this class is loaded from
   print(NSMutableDictionary.bundle_path)

   # which is a short-hand for objc_get_class(class_name)
   a = p.objc_get_class('NSMutableDictionary').new()

   # each darwin object is a "DarwinSymbol", instead of a "simple Symbol"
   # that mean it has the special method: objc_call("selector", ...)
   a.objc_call('setObject:forKey:', p.cf('value'), p.cf('key'))

   # we can look at the CFDescription of every DarwinSymbol using the "cfdesc" property
   a.cfdesc

   # it can be easier to use further ObjC capabilities by converting the current DarwinSymbol into an ObjectiveCSymbol instead
   a = a.objc_symbol

   # We can now examine the class/objects properties
   a.show()

   # now we'll have a auto-complete for all of its selectors, ivars, etc.
   a.setObject_forKey_(p.cf('value2'), p.cf('key2'))

   # and we can easily convert this object to python native using the py() method. please note that this is done behind-the-scene using plistlib, meaning only plist-serializable objects (and None) can be coverted this way.
   a = a.py()

   # attempt to load all frameworks for auto-completions of all ObjC classes
   # (equivalent to running the client with -l -r)
   p.load_all_libraries()

.. |Server application| image:: https://img.shields.io/github/actions/workflow/status/doronz88/rpc-project/server-app.yml?branch=master&label=python%20package&style=plastic
   :target: https://github.com/doronz88/rpc-project/actions/workflows/server-app.yml
.. |Python application| image:: https://img.shields.io/github/actions/workflow/status/doronz88/rpc-project/python-app.yml?branch=master&label=server%20build&style=plastic
   :target: https://github.com/doronz88/rpc-project/actions/workflows/python-app.yml

