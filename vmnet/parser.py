import inspect, re, dill, os

def get_fn_str(fn, profiling):
    return """
import os, dill
os.environ["PROFILING"] = "{profiling}"
{fn_str}
{fnname}()
    """.format(fn_str=_get_fn_str(fn), fnname=fn.__name__, profiling=profiling if profiling else '')

def _get_fn_str(fn, indent=0):
    if not callable(fn): return ''
    cv = inspect.getclosurevars(fn)
    non_locals = dict(cv.nonlocals)
    globals = dict(cv.globals)
    full_fn_str = _clear_indents(inspect.getsource(fn))
    fn_str = indent * '    ' + full_fn_str[0] + '\n'
    for m in globals:
        fn_str += (indent+1) * '    ' + '{} = dill.loads({})'.format(m, dill.dumps(globals[m])) + '\n'
    for m in non_locals:
        if not callable(non_locals[m]):
            fn_str += (indent+1) * '    ' + '{} = dill.loads({})'.format(m, dill.dumps(non_locals[m])) + '\n'
    for m in non_locals:
        if callable(non_locals[m]):
            added_fn_str = _get_fn_str(non_locals[m], indent+1) + '\n'

            added_fn_str = re.sub(r"def ("+non_locals[m].__name__+r")\(", 'def {}('.format(m), added_fn_str)
            fn_str += added_fn_str
    for l in full_fn_str[1:]:
        fn_str += indent * '    ' + l + '\n'
    return fn_str

def _clear_indents(s):
    new_fn_str = ''
    pattern = re.compile('^    ')
    lines = s.split('\n')
    new_lines = []
    for line in lines:
        if not pattern.match(line) and line != '':
            return lines
        new_lines.append(pattern.sub('', line))
    return new_lines
