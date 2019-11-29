import threading

def run_in_new_thread(fn):

    def run(*k, **kw):
        t = threading.Thread(target=fn, args=k, kwargs=kw)
        t.start()
        return t

    run.thread_decorated = True
    return run

"""
class RunInNewThreadDecorate(type):
    def __new__(mcls, name, bases, attrs):
        if name.startswith('None'):
            return None

        newattrs = attrs
        if len(bases) > 0:
            base_class = bases[0]
            # Go over attributes and see if they should be renamed.
            for attrname, attrvalue in attrs.items():
                if attrname in dir(base_class):
                    original_method = getattr(base_class, attrname)
                    if hasattr(original_method, 'thread_decorated'):
                        newattrs[attrname] = run_in_new_thread(attrvalue)
                else:
                    newattrs[attrname] = attrvalue

        return super(RunInNewThreadDecorate, mcls).__new__(mcls, name, bases, newattrs)
"""

