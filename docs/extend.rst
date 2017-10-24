Extend finchan
=========================
An finchan extension is an importable Python module that has
a function with the signature::

    def load_finchan_ext(*args, **kwargs):
        # Do setup

This function is called after your extension is imported.
\*args and \*\*kwargs is passed from configure file's `config.live_track_exts` or
`config.backtrack_exts` 's extension module name section depend on the run mode.

You can also optionally define an :func:`unload_finchan_ext()`
function, which will be called if the user unloads the extension.

You can put your extension modules anywhere you want, as long as
they can be imported by Python's standard import mechanism.  However,
to make it easy to write extensions, you can also put your extensions
in a configured path `config.ext_path`.
This directory is added to ``sys.path`` automatically.

the `finchan` has two built-in extension module,
:any:`finchan.exts.timer_source` and `finchan.exts.timer_callback` for test
