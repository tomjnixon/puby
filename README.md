puby: wrap ruby in python
=========================

A python interface to the ruby interpreter, because we can.

What can it do?
---------------

Parse HTML:
```python
# python                                   # # ruby
from puby import Object as rb              # 
rb.require("nokogiri")                     # require "nokogiri"
rb.require("open-uri")                     # require "open-uri"

url = "http://www.google.com/search?q=foo" # url = "http://www.google.com/search?q=foo"
doc = rb.Nokogiri.HTML.parse(rb.open(url)) # doc = Nokogiri::HTML.parse(open(url))

for link in doc.css("h3.r a"):             # doc.css("h3.r a").each do |link|
    print link.content()                   #     puts link.content
                                           # end
```

Execute JavaScript:
```python
from puby import Object as rb              # 
rb.require('v8')                           # require "v8"

ctx = rb.V8.Context.new()                  # ctx = V8::Context.new
print ctx.eval("'Xzibit ' + 7 * 6")        # puts ctx.eval "'Xzibit ' + 7 * 6"
```

Run a web server:
```python
from puby import Object as rb              # 
rb.require("rack")                         # require "rack"
                                           # 
def application(env):                      # def application(env)
    return [200,                           #   [200,
            {"Content-Type": "text/html"}, #    {"Content-Type" => "text/html"},
            ["Hello Puby!"]]               #    ["Hello Puby!"]]
                                           # end
rb.Rack.Handler.Thin.run(application)      # Rack::Handler::Thin.run method(:application)
```

The first person to build a rack-WSGI adapter wins a cookie.

Install
-------

```
$ pip install git+git://github.com/tomjnixon/puby.git
```

Usage
-----

### Import

The `puby` module contains an `Object` attribute, corresponding to the `Object`
class in ruby. All globals (modules and methods) can be accessed through this
class.

```python
from puby import Object as rb              # 
```

### Basic Types

Most basic types are converted sensibly:

```python
42                                         # 42
True                                       # true
False                                      # false
None                                       # nil
"foo"                                      # "foo"
0.1                                        # 0.1
[1, 2, 3, 4]                               # [1,2,3,4]
{1: 2, 3: 4}                               # {1=>2, 3=>4}
```

### Object Proxy

Ruby objects are represented in python by a proxy object that imitates the
behaviour of the underlying ruby object.

Unlike in ruby, we generally use parentheses to call methods. Method names are
munged to make calling `?` and `!` methods easier.

```python
obj.method()                               # obj.method
obj.method(arg)                            # obj.method arg
obj.method(arg1, arg2)                     # obj.method arg1, arg2
obj.predicate_p(arg)                       # obj.predicate? arg
obj.mutator_b(arg)                         # obj.mutator! arg
```

Setters are the exception to the rule:

```python
obj.prop = x                               # obj.prop = x
```

A few python special methods are implemented:

```python
str(obj)                                   # obj.to_s
iter(obj)                                  # obj.to_a
```

Finally, `repr(obj)` returns a string containing the output of `obj.inspect()`.

### Module and Class Proxy

Proxy objects for ruby `Module` and `Class` objects behave identically to
'Object' proxies, except that upper case properties access constants:

```python
mod.Const                                  # mod::Const
```

Lower case method calls work as per Object:

```python
mod.method()                               # mod.method
```

### Callbacks

Python callable objects are automatically wrapped in a ruby Proc when passed
into a ruby method.

The python side of the wrapper is only kept alive for the duration of the
current function call; if it will potentially be called by ruby code after
that, you should use `RbCallback`, keeping the result alive for as long as it
may be called:

```python
from puby import Object as rb, RbCallback

rb.eval("""
class TestObj
    def save_callback cb
        @cb = cb
    end
    def call_callback x
        @cb.call(x)
    end
end
""")
obj = rb.TestObj.new()

def callback(x):
    return x+1

callback_rb = RbCallback(callback)
obj.save_callback(callback_rb)
print obj.call_callback(5)
```

Note that both of these would segfault:
```python
obj.save_callback(callback)
print obj.call_callback(5)
```
```python
obj.save_callback(RbCallback(callback))
print obj.call_callback(5)
```

### Symbols

Ruby symbols are converted to/from objects of the `RbSymbol` class an empty
subclass of `str`.

```python
obj.method(RbSymbol("foo"))                # mod.method :foo
```

Todo
----

- A general tidy up; everything is still a bit of a mess.
- Make sure everything is safe. Everything is mostly OK, but there are a few
  situations where a garbage collection would probably be bad news.
- Add a way of proxying python objects into ruby land.
- More crazy examples.

About
-----

MIT licensed; see `LICENSE`.

Lovingly hacked together by [Tom Nixon](https://github.com/tomjnixon).
