=========================
system architecture
=========================
Finchan is a event system framework,
its main modules are `Event`, `EventSource`, `Dispatcher`, `Subscribers`, `env` and `ExtManager`.

concept
=====================

The :class:`Event <finchan.event.Event>` is the input manner for `finchan`.

The :class:`EventSource <finchan.interface.event_source.AbsEventSource>`
is the original input for the system, it simulate the real world's things to `Event` as input.

The :class:`Dispatcher <finchan.dispatcher.LiveDispatcher>` is the engine of the system,
it manage all `EventSource`, all event `Subscriber`,
and dispath the events generated by `EventSource` or `Subscriber`, call the `Subscriber`'s callback.

The `Subscriber` is event subscriber, it subscriber event with a callback function,
when the event occurs, the `Dispatcher` dispatch the event and call the callback function.
The `Subscriber` can do anything with the callback function, include generate new events.

The :class:`env <finchan.env.Env>` is global environment for the system,
you can access it just by `from finchan.env import env`,
you can access environment variable setted by other modules, or set your own environment variable.

the :class:`ExtManager <finchan.exts.ExtManager>` manage all extensions for `finchan`.

Interfaces
================

kvstore
----------------
:class:`kvstore <finchan.interface.kvstore.AbsKvStore>` is persistent storage for finchan,
`finchan` framework just specified the interface for kvstore,
the implemention is done by extensions.

EventSource
----------------
The :class:`EventSource <finchan.interface.event_source.AbsEventSource>` defines the interface to
implent an EventSource, `finchan` system include a :any:`TimerSource <finchan.exts.timer_source>`,
if you need other EventSource, you should write an extension for `finchan`,
or check `finchan_exts <https://github.com/qytz/finchan_exts>`_ first.

Write an extension for finchan
==================================
refer :doc:`extend`.
