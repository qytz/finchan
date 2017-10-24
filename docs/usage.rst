=====
Usage
=====

steps
    + optional, write your own :class:`EventSource <finchan.interface.event_source.AbsEventSource>`
      :doc:`extension <extend>`.
    + write your own event subscriber `extension`.
    + configure the running with configure file.
    + run `finchan` with `finchan -c finchan.yml -vvvvv`

The example `EventSource` `extension` and `Subscriber` `extension` can be found in
`finchan/exts/` and `finchan_exts <https://github.com/qytz/finchan_exts>`_.
