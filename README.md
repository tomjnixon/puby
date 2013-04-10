puby: wrap ruby in python
=========================

A python interface to the ruby interpreter, because we can.

What can it do?
---------------

Parse HTML:
```python
# python                                   # #ruby
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
print ctx.eval("7 * 6")                    # puts ctx.eval "7 * 6"
```
