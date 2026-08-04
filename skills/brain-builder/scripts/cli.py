"""Argument scanning shared by the kit's scripts.

Every script here takes the same shape of arguments — `--name value`,
`--name=value`, bare flags, and positional paths — and each hand-rolled copy of
that loop drifted its own error wording. One scanner keeps the wording identical
across scripts, which matters because these messages are read by a model
mid-build, not by a developer with the source open.

`gen_router.py` keeps its own scanner: it landed with the brain contract and its
CLI is under test, so it is left alone deliberately rather than churned.

Stdlib only.
"""


class UsageError(Exception):
    """Bad arguments — the caller turns this into an exit code of 2."""


def scan(argv, options=None, flags=()):
    """Split `argv[1:]` into positional arguments and option values.

    `options` maps each `--name` to its default; `flags` names the arguments
    that take no value and come back as `True`. Returns `(positional, values)`.
    """
    values = dict(options or {})
    positional = []
    pending = iter(argv[1:])
    for argument in pending:
        name, _, inline = argument.partition("=")
        if name in flags:
            values[name] = True
        elif name in values:
            value = inline if inline else next(pending, None)
            if not value:
                raise UsageError("{} needs a value".format(name))
            values[name] = value
        elif name.startswith("-"):
            raise UsageError("unknown argument {}".format(argument))
        else:
            positional.append(argument)
    return positional, values
