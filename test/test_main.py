import pytest
import puby as rb
rbObj = rb.Object

rbObj.eval("""
def test_toplevel(a, b)
	a*b
end

class TestClass
  def initialize
    @prop = 5
  end
  
  def test_regular
    "test_regular"
  end
  
  def test_bang!
    "test_bang!"
  end
  
  def test_pred?
    "test_pred?"
  end
  
  def prop
    @prop
  end
  def prop= x
    @prop = x
  end
  
  def to_s
  	"to_s"
  end
  
  def inspect
  	"inspect"
  end
  
  def to_a
  	[1, 2, 3]
  end
  
  def raise_exc
    raise "raised_exception"
  end
  
  def test_cb proc, arg
    proc.call arg
  end
  
  CONST = 5
end
""")

@pytest.fixture
def testobj():
	return rbObj.TestClass.new()

rb_to_py = (
	("0"           , 0          ),
	("42"          , 42         ),
	("true"        , True       ),
	("false"       , False      ),
	("nil"         , None       ),
	("'foo'"       , "foo"      ),
	('"foo\\0bar"' , "foo\0bar" ),
	("0.0"         , 0.0        ),
	("0.1"         , 0.1        ),
	("[]", []),
	("[1]", [1]),
	("[1,2,3,4]", [1,2,3,4]),
	("[[1]]", [[1]]),
	("{1=>2, 3=>4}", {1:2, 3:4}),
	(":foo", rb.RbSymbol("foo")),
)

rb_to_py_only = (
	(":foo", "foo"),
)

@pytest.mark.parametrize("case", rb_to_py + rb_to_py_only)
def test_rb_to_py(case):
	ruby, python = case
	assert rb.rb_to_py(rb.C.rb_eval_string(ruby)) == python

@pytest.mark.parametrize("case", rb_to_py)
def test_py_to_rb(case):
	ruby, python = case
	python_rb = rb.py_to_rb(python)
	ruby_rb = rb.C.rb_eval_string(ruby)
	assert rb.C.rb_equal(python_rb, ruby_rb)

def test_top_level_fun():
	assert rbObj.test_toplevel(6, 7) == 42

def test_regular_call(testobj):
	assert testobj.test_regular() == "test_regular"

def test_bang_call(testobj):
	assert testobj.test_bang_b() == "test_bang!"

def test_pred_call(testobj):
	assert testobj.test_pred_p() == "test_pred?"

def test_set(testobj):
	testobj.prop = 42
	assert testobj.prop() == 42

def test_const(testobj):
	assert rbObj.TestClass.CONST == 5

def test_str(testobj):
	assert str(testobj) == "to_s"

def test_iter(testobj):
	assert list(testobj) == [1, 2, 3]

def test_repr(testobj):
	assert repr(testobj) == "RbObjectProxy(inspect)"

def test_gc(testobj):
	# This will cause a segfault if broken. FUN TIMES.
	rbObj.GC.start()
	assert testobj.test_regular() == "test_regular"

def test_range():
	assert list(rbObj.eval("0..5")) == list(range(6))
	assert list(rbObj.Range.new(0,5)) == list(range(6))

def test_exception(testobj):
	with pytest.raises(rb.RubyException) as exception_info:
		testobj.raise_exc()
	
	exception = exception_info.value
	assert exception.message == "#<RuntimeError: raised_exception>"
	assert isinstance(exception.rb_exception, rb.RbObjectProxy)

def test_callback(testobj):
	@rb.RbCallback
	def cb(x):
		return x+1
	
	assert testobj.test_cb(cb, 5) == 6

def test_callback_gc(testobj):
	@rb.RbCallback
	def cb(x):
		return x+1
	
	rbObj.GC.start()
	assert testobj.test_cb(cb, 5) == 6

def test_cb_plain(testobj):
	def cb(x):
		return x+1
	
	assert testobj.test_cb(cb, 5) == 6
