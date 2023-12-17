# Contributing

`django-devdata` uses Poetry for packaging and Tox for testing. It is
recommended that you use Pyenv to provide versions of Python for testing, and
that you _do not_ use virtualenvs, but instead just use Poetry's built-in
virtualenv handling.

### Testing

```
poetry run tox
```

This should run all the tests across the supported Python and Django version
combinations.
