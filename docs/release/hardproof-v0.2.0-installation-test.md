# Hardproof v0.2.0 Installation Test

Windows/Python 3.11 clean wheel and clean sdist installations passed. The installed wheel reports
version 0.2.0, exposes the `hermes_agent.plugins` entry point named `hardproof`, loads a callable
public `register`, and includes both SQL migrations, templates, skills, and `py.typed`. Twine checks
passed. The installed local Hermes Agent is 0.18.2 and exposes every required public API; its current
public Hardproof install remains v0.1.1 and was not replaced by this unpublished candidate.
