"""Bank grants: Discord users a global officer lets import bank snapshots or run the request queue without making them
officers (docs/bank.md "Grants").

Rules live in `service.py` over the `BankGrantRepository` protocol (`repository.py`); `sql.py` keeps them in hub-db and
`routes.py` is the global tier's HTTP adapter. The RBAC layer (`rbac.deps`) reads a member's grants on every request
and `rbac.permissions.can` honours them on raid-day routes, so a grant reaches the same `require(...)` check an
officer's role does.
"""
