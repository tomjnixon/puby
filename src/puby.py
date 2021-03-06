from cffi import FFI

def get_verify_args():
	"""Discover lib and include dirs for the current ruby."""
	import subprocess
	args = [
			"ruby", "-rrbconfig",
			"-e", "puts RbConfig::CONFIG['rubyhdrdir']",
			"-e", "puts File.join(RbConfig::CONFIG['rubyhdrdir'], RbConfig::CONFIG['arch'])",
			"-e", "puts RbConfig::CONFIG['libdir']",
			]
	hdrdir, archhdrdir, libdir = subprocess.check_output(args).splitlines()
	
	return dict(
			libraries=["ruby"],
			library_dirs=[libdir],
			runtime_library_dirs=[libdir],
			include_dirs=[hdrdir, archhdrdir])

ffi = FFI()
ffi.cdef("""
typedef uintptr_t VALUE;
typedef uintptr_t ID;

// Initialisation.
void ruby_init(void);
void ruby_script(const char*);
void *ruby_options(int, char**);

// For testing.
VALUE rb_eval_string(const char*);
VALUE rb_equal(VALUE,VALUE);

extern VALUE rb_cObject;
void rb_gc_register_address(VALUE*);
void rb_gc_unregister_address(VALUE*);
VALUE rb_gv_get(const char*);
ID rb_intern(const char*);

static inline int rb_type(VALUE obj);
VALUE rb_proc_new(VALUE (*)(), VALUE);


#define T_NONE   ...
#define T_NIL    ...
#define T_OBJECT ...
#define T_CLASS  ...
#define T_ICLASS ...
#define T_MODULE ...
#define T_FLOAT  ...
#define T_STRING ...
#define T_REGEXP ...
#define T_ARRAY  ...
#define T_HASH   ...
#define T_STRUCT ...
#define T_BIGNUM ...
#define T_FILE   ...
#define T_FIXNUM ...
#define T_TRUE   ...
#define T_FALSE  ...
#define T_DATA   ...
#define T_MATCH  ...
#define T_SYMBOL ...
#define T_RATIONAL ...
#define T_COMPLEX ...
#define T_UNDEF  ...
#define T_NODE   ...
#define T_ZOMBIE ...
#define T_MASK   ...

#define Qfalse ...
#define Qtrue  ...
#define Qnil   ...

long FIX2LONG_f(VALUE x);

char *RSTRING_PTR_f(VALUE x);
size_t RSTRING_LEN_f(VALUE x);
double RFLOAT_VALUE_f(VALUE x);

VALUE rb_sym_to_s(VALUE);

typedef struct {
	size_t len;
	VALUE *ptr;
} arr_len_and_ptr;
arr_len_and_ptr arr_len_and_ptr_f(VALUE x);

VALUE INT2NUM_f(int x);
VALUE rb_float_new(double);
VALUE rb_str_new(const char*, long);
VALUE rb_ary_new4(long, const VALUE *);
VALUE rb_hash_new(void);
VALUE rb_hash_aset(VALUE, VALUE, VALUE);
VALUE rb_sym_new(char *s, long len);

// Safe wrappers.
VALUE safe_rb_funcall2(VALUE obj, ID func, int argc, const VALUE *argv, int *error);
VALUE safe_rb_const_get(VALUE obj, ID name, int *error);
VALUE safe_rb_require(char *mod, int *error);
""")

C = ffi.verify("""
#include <ruby.h>

long FIX2LONG_f(VALUE x) {
	return FIX2LONG(x);
}

char *RSTRING_PTR_f(VALUE x) {
	return RSTRING_PTR(x);
}

size_t RSTRING_LEN_f(VALUE x) {
	return RSTRING_LEN(x);
}

double RFLOAT_VALUE_f(VALUE x) {
	return RFLOAT_VALUE(x);
}

typedef struct {
	size_t len;
	VALUE *ptr;
} arr_len_and_ptr;

arr_len_and_ptr arr_len_and_ptr_f(VALUE x) {
	return (arr_len_and_ptr){RARRAY_LEN(x), RARRAY_PTR(x)};
}


VALUE INT2NUM_f(int x) {
	return INT2NUM(x);
}

typedef struct {
	VALUE object;
	ID func;
	int argc;
	VALUE *argv;
} rb_funcall2_args;

VALUE rb_funcall2_wrap(rb_funcall2_args *args) {
	return rb_funcall2(args->object, args->func, args->argc, args->argv);
}

VALUE safe_rb_funcall2(VALUE obj, ID func, int argc, const VALUE *argv, int *error) {
	rb_funcall2_args args = {obj, func, argc, argv};
	return rb_protect((VALUE (*)(VALUE))rb_funcall2_wrap, &args, error);
}

typedef struct {
	VALUE object;
	ID name;
} rb_const_get_args;

VALUE rb_const_get_wrap(rb_const_get_args *args) {
	return rb_const_get(args->object, args->name);
}

VALUE safe_rb_const_get(VALUE obj, ID name, int *error) {
	rb_const_get_args args = {obj, name};
	return rb_protect((VALUE (*)(VALUE))rb_const_get_wrap, &args, error);
}

VALUE safe_rb_require(char *mod, int *error) {
	return rb_protect((VALUE (*)(VALUE))rb_require, (VALUE)mod, error);
}

VALUE rb_sym_new(const char *s, long len) {
	return ID2SYM(rb_intern2(s, len));
}

""",
	**get_verify_args())

# Initialise the interpreter.
C.ruby_init()
C.ruby_script("embed")
# trick is from the subtle wm project; this seems to be needed to make gem
# loading and encodings to work...
args = [ffi.new("char[]", "ruby"),
        ffi.new("char[]", "-e;")]
C.ruby_options(2, args)

intern = C.rb_intern

def _call_safe_wrap(f, *args):
	"""Call f with args, plus an int* that f should use to indicate an error.
	If an error occurs, it will be raised, otherwise the return of f is converted
	to python and returned.
	"""
	is_error = ffi.new("int *")
	res = f(*args + (is_error,))
	
	if is_error[0]:
		raise RubyException.get_current()
	
	return rb_to_py(res)

def call(obj, message, *args):
	keepalive = []
	rb_args = ffi.new("VALUE []", [py_to_rb(arg, keepalive.append) for arg in args])
	return _call_safe_wrap(C.safe_rb_funcall2, obj, intern(message), len(rb_args), rb_args)

def const_get(obj, name):
	return _call_safe_wrap(C.safe_rb_const_get, obj, intern(name))


class RubyException(Exception):
	"""An exception thrown by ruby code.
	
	The message is obtained from the ruby inspect method.
	The original ruby exception can be accessed via the rb_exception attribute.
	"""
	
	def __init__(self, rb_exception):
		Exception.__init__(self, rb_exception.inspect())
		
		self.rb_exception = rb_exception
	
	@classmethod
	def get_current(cls):
		"""Get the current exception in rubyland, wrapped as appropriate."""
		rb_exception = rb_to_py(C.rb_gv_get("$!"))
		return cls(rb_exception)


class RbProxy(object):
	"""A wrapper around any ruby VALUE.
	Does nothing except store the value, and maintain it's ruby GC state.
	"""
	
	def __init__(self, value):
		value_ptr = ffi.gc(ffi.new("VALUE *", value), C.rb_gc_unregister_address)
		C.rb_gc_register_address(value_ptr)
		object.__setattr__(self, "_value", value_ptr)


class RbObjectProxy(RbProxy):
	"""A wrapper around a ruby object."""
	
	def __getattr__(self, attr):
		if attr[-2:] == "_p":
			attr = attr[:-2] + "?"
		elif attr[-2:] == "_b":
			attr = attr[:-2] + "!"
		
		def method(*args):
			return call(self._value[0], attr, *args)
		return method
	
	def __setattr__(self, attr, value):
		return call(self._value[0], attr + "=", value)
	
	def __iter__(self):
		return iter(self.to_a())
	
	def __repr__(self):
		return "{}({})".format(self.__class__.__name__, self.inspect())
	
	def __str__(self):
		return self.to_s()


class RbModuleProxy(RbObjectProxy):
	"""A wrapper around a ruby module."""
	
	def __getattr__(self, attr):
		if attr[0].isupper():
			return const_get(self._value[0], attr)
		else:
			return RbObjectProxy.__getattr__(self, attr)

RbClassProxy = RbModuleProxy
RbDataProxy = RbObjectProxy


class RbCallback(RbProxy):
	
	def __init__(self, f):
		def callback(args, id, argc, argv):
			res = f(*[rb_to_py(argv[i]) for i in range(argc)])
			return py_to_rb(res)
		
		self._c_callback = ffi.callback("VALUE(*)(VALUE, VALUE, int, VALUE *)", callback)
		_value = C.rb_proc_new(ffi.cast("VALUE(*)()", self._c_callback), 0)
		RbProxy.__init__(self, _value)


class RbSymbol(str):
	"""A ruby Symbol."""
	pass


def _rb_arr_to_py(value):
	len_ptr = C.arr_len_and_ptr_f(value)
	ptr = len_ptr.ptr
	
	return [rb_to_py(ptr[i]) for i in range(len_ptr.len)]

def _rb_str_to_py(value):
	return ffi.buffer(C.RSTRING_PTR_f(value), C.RSTRING_LEN_f(value))[:]

_rb_to_py_conversions = {
	C.T_FIXNUM: C.FIX2LONG_f,
	C.T_STRING: _rb_str_to_py,
	C.T_TRUE: lambda value: True,
	C.T_FALSE: lambda value: False,
	C.T_NIL: lambda value: None,
	C.T_FLOAT: C.RFLOAT_VALUE_f,
	C.T_MODULE: RbModuleProxy,
	C.T_OBJECT: RbObjectProxy,
	C.T_STRUCT: RbObjectProxy,
	C.T_CLASS: RbClassProxy,
	C.T_ARRAY: _rb_arr_to_py,
	C.T_DATA: RbDataProxy,
	C.T_HASH: lambda h: dict(RbObjectProxy(h).collect().to_a()),
	C.T_FILE: RbObjectProxy,
	C.T_SYMBOL: lambda value: RbSymbol(_rb_str_to_py(C.rb_sym_to_s(value))),
}

def rb_to_py(value):
	"""Convert a ruby VALUE to a python object."""
	type = C.rb_type(value)
	try:
		conversion = _rb_to_py_conversions[type]
	except KeyError:
		raise NotImplementedError("unimplemented type: {:#x}".format(type))
	return conversion(value)


def _py_dict_to_rb(d):
	hash = C.rb_hash_new()
	for (k, v) in d.iteritems():
		C.rb_hash_aset(hash, py_to_rb(k), py_to_rb(v))
	return hash

_py_to_rb_conversions = {
	int: C.INT2NUM_f,
	float: C.rb_float_new,
	str: lambda s: C.rb_str_new(s, len(s)),
	RbObjectProxy: lambda x: object.__getattribute__(x, "_value")[0],
	RbCallback: lambda x: object.__getattribute__(x, "_value")[0],
	list: lambda l: C.rb_ary_new4(len(l), ffi.new("VALUE []", map(py_to_rb, l))),
	bool: lambda b: C.Qtrue if b else C.Qfalse,
	type(None): lambda n: C.Qnil,
	dict: _py_dict_to_rb,
	RbSymbol: lambda s: C.rb_sym_new(s, len(s)),
}

def py_to_rb(value, keepalive=lambda x: None):
	"""Convert a python object to a ruby VALUE."""
	try:
		conversion = _py_to_rb_conversions[type(value)]
	except KeyError:
		if hasattr(value, "__call__"):
			cb_proxy = RbCallback(value)
			keepalive(cb_proxy)
			return object.__getattribute__(cb_proxy, "_value")[0]
		
		raise NotImplementedError("unimplemented type: {}".format(type(value)))
	return conversion(value)


def rb_obj(py_value):
	"""Convert a python object to a wrapped ruby object."""
	return RbObjectProxy(py_to_rb(py_value))


Object = RbClassProxy(C.rb_cObject)
