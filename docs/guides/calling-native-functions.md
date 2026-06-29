# Calling native functions

The core power of `rpcclient` is calling native functions and working with raw memory through
`Symbol` objects.

```python
s = p.symbol(0x12345678)

# Symbol extends `int`
assert isinstance(s, int)

# write into this memory
s.poke(b'abc')

# peek (read) 20 bytes of memory
print(s.peek(20))

# jump to `s` as a function, passing (1, "string") as its args
s(1, "string")

# change the item size used for derefs
s.item_size = 1
s[0] = 1            # *(char *)s = 1
s[1] = 1            # *(((char *)s)+1) = 1

# Symbol inherits from int, so all int operations apply
s += 4

# back to 8 to store pointers
s.item_size = 8
s[0] = 1            # *(intptr_t *)s = 1

# calling a symbol returns a symbol
s[0] = p.symbol(0x11223344)()

# which file is this address loaded from?
print(p.symbol(0x11223344).filename)
```

## Globalized symbols

Symbols already mapped into the running process are reachable through `symbols.<name>`. `symbols`
is a `SymbolsJar` — a `dict` wrapper over all exported symbols:

```python
x = symbols.malloc(20)
```

You can also use the bare name; the client checks for collisions and resolves it lazily:

```python
x = malloc(20)
# equivalent to:
malloc = symbols.malloc
x = malloc(20)
```

## ObjC support

On Darwin systems, the built-in Objective-C support is often easier:

```python
# create CF/NS objects with cf()
some_cf_string = p.cf('some string')

# create a new NSMutableDictionary
a = NSMutableDictionary.new()
print(NSMutableDictionary.bundle_path)            # where the class is loaded from
a = p.objc_get_class('NSMutableDictionary').new() # the long form

# each darwin object is a DarwinSymbol with objc_call(...)
a.objc_call('setObject:forKey:', p.cf('value'), p.cf('key'))
a.cfdesc                                           # CFDescription

# convert to an ObjectiveCSymbol for richer introspection
a = a.objc_symbol
a.show()                                           # classes/objects properties
a.setObject_forKey_(p.cf('value2'), p.cf('key2'))  # auto-completed selectors

# back to native python (via plistlib; plist-serializable objects only)
a = a.py()

# load all frameworks for ObjC auto-completion (same as client -l -r)
p.load_all_libraries()
```
