MNML - An ultra-minimal Python web framework
============================================

After growing out of the extensive feature set and perceived bloat of [Django][django], and inspired by the new wave of super-tiny Python WSGI/Web frameworks such as [Juno][juno], [Web.py][webpy], and [Newf][newf], I thought it a good exercise to write my own. MNML only includes features I feel are useful (if you disagree with the batteries I include you're free to use another framework).

Core Philosophy
---------------

MNML's core philosophy is that I really love writing Python and want to do that for most things, but I also want a certain level of "plumbing" taken care of for me. In addition, MNML:

* Provides URL mapping to HTTP response relationship, aka routing;
* Provides methods for all HTTP method verbs (`PUT` and `DELETE` are supported);
* Provides flexible regular expression matching for URLs with the ability to reverse said URLs (like Django's `reverse` function);
* Provides the ability to add middleware functions so one can alter the request or response as required;
* Does not dictate the template or ORM layer you should use - MNML is strictly about URL routing and serving, and tools needed to do so; and mostly
* Lets the implementer write Python, not a sub-set of Python.

Recommended Extensions
----------------------

* [Jinja2][jinja] for templates;
* [Beaker][beaker] for sessions;

[django]: http://www.djangoproject.com/
[juno]: http://github.com/breily/juno/tree
[webpy]: http://webpy.org/
[newf]: http://github.com/JaredKuolt/newf/tree
[jinja]: http://jinja.pocoo.org/2/
[beaker]: http://beaker.groovie.org/