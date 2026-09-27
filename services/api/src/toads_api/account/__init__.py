"""A member's own settings: which name the hub shows for them, and their own Warcraft Logs API key.

Rules live in `service.py` over the `AccountRepository` protocol (`repository.py`); `routes.py` is the HTTP adapter
and holds the permission checks. A saved key is write-only: no route, response or log line ever carries it back.
"""
