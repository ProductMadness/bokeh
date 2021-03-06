import sys

from ..application.handlers.code_runner import _CodeRunner
from ..application.handlers.handler import Handler
from ..io import set_curdoc, curdoc

class ExampleHandler(Handler):
    """ A stripped-down handler similar to CodeHandler but that does
    some appropriate monkeypatching to

    """

    _output_funcs = ['output_notebook', 'output_file', 'reset_output']
    _io_funcs = ['show', 'save']

    def __init__(self, source, filename):
        super(ExampleHandler, self).__init__(self)
        self._runner = _CodeRunner(source, filename, [])

    def modify_document(self, doc):
        if self.failed:
            return

        module = self._runner.new_module()

        sys.modules[module.__name__] = module
        doc._modules.append(module)

        old_doc = curdoc()
        set_curdoc(doc)

        old_io, old_doc = self._monkeypatch()

        try:
            self._runner.run(module, lambda: None)
        finally:
            self._unmonkeypatch(old_io, old_doc)
            set_curdoc(old_doc)

    def _monkeypatch(self):

        def _pass(*args, **kw): pass
        def _add_root(obj, *args, **kw):
            from bokeh.io import curdoc
            curdoc().add_root(obj)
        def _curdoc(*args, **kw):
            return curdoc()

        # these functions are transitively imported from io into plotting,
        # so we have to patch them all. Assumption is that no other patching
        # has occurred, i.e. we can just save the funcs being patched once,
        # from io, and use those as the originals to replace everywhere
        import bokeh.io as io
        import bokeh.plotting as p
        mods = [io, p]

        # TODO (bev) restore when bkcharts package is ready (but remove at 1.0 release)
        # import bkcharts as c
        # mods.append(c)

        old_io = {}
        for f in self._output_funcs + self._io_funcs:
            old_io[f] = getattr(io, f)

        for mod in mods:
            for f in self._output_funcs:
                setattr(mod, f, _pass)
            for f in self._io_funcs:
                setattr(mod, f, _add_root)

        import bokeh.document as d
        old_doc = d.Document
        d.Document = _curdoc

        return old_io, old_doc

    def _unmonkeypatch(self, old_io, old_doc):
        import bokeh.io as io
        import bokeh.plotting as p
        mods = [io, p]

        # TODO (bev) restore when bkcharts package is ready (but remove at 1.0 release)
        # import bkcharts as c
        # mods.append(c)

        for mod in mods:
            for f in old_io:
                setattr(mod, f, old_io[f])

        import bokeh.document as d
        d.Document = old_doc

    @property
    def failed(self):
        return self._runner.failed

    @property
    def error(self):
        return self._runner.error

    @property
    def error_detail(self):
        return self._runner.error_detail
