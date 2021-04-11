# django-devdata

`django-devdata` provides a convenient workflow for creating development
databases seeded with anonymised production data. Have a development database
that contains useful data, and is fast to create and keep up to date.

## Elevator pitch

```python
# blog.models

class Post(models.Model):
    content = models.TextField()
    published = models.DateTimeField()


class Comment(models.Model):
    user = models.ForeignKey(User)
    post = models.ForeignKey(Post)
    text = models.TextField()

# settings.py
DEVDATA_STRATEGIES = {
    'auth.User': [
        # We want all internal users
        InternalUsersStrategy(name='internal_users'),
        # Get some random other users, we don't need everyone
        RandomSampleQuerySetStrategy(name='random_users', count=10),
    ],
    'blog.Post': [
        # Only the latest blog posts necessary for testing...
        LatestSampleQuerySetStrategy(name='latest_posts', count=3, order='-published'),
        # Except that one the weird edge case
        ExactQuerySetStrategy(name='edge_case', pks=(42,)),
    ],
    'blog.Comment': [
        # Get all the comments – devdata will automatically restrict to only
        # those that maintain referential integrity, i.e. comments from users
        # not selected, or on posts not selected, will be skipped.
        QuerySetStrategy(name='all'),
    ],
}
```

```shell
(prod)$ python manage.py devdata_export data
(prod)$ tar -cf data.tar data/
(local)$ scp prod:~/data.tar data.tar
(local)$ tar -xf data.tar
(local)$ python manage.py devdata_import data
```

#### Problem

In the same way that development environments being close in configuration to
production environments, it's important that the data in databases we use for
development is a realistic representation of that in production.

We could use a dump of a production database, but there are several problems
with this:

1. It's bad for user privacy and a security risk. It may not be allowed in some
   organisations.
2. Production databases can be too big, impractical or unusable.
3. Test data is limited to that available in production.
4. Preserving referential integrity for a sample of data is hard.

Another option is to use factories or fake data to generate the entire
development database. This is mostly desirable, but...

- It can be a burden to maintain factories once there are hundreds or thousands
  of them.
- It can be hard to retroactively add these to a Django site of a significant
  size.

#### Solution

`django-devdata` provides defines a three step workflow:

1. _Exporting_ data, with a customisable export strategies per model.
2. _Anonymising_ data, with customisable anonymisation per field/model.
3. _Importing_ data, with customisable importing per model.

`django-devdata` ships with built-in support for:

- Exporting full tables
- Exporting subsets (random, latest, specified primary keys)
- Anonymising data with [`faker`](https://github.com/joke2k/faker/)
- Importing exported data
- Importing data from [`factory-boy`](https://github.com/FactoryBoy/factory_boy)
  factories

In addition to this, the structure provided by `django-devdata` can be extended
to support extraction from other data sources, to import/export Django fixtures,
or to work with other factory libraries.

Exporting, anonymising, and importing, are all configurable, and
`django-devdata`'s base classes will help do this without much work.

## Workflow

#### Exporting

This step allows a sync strategy to persist some data that will be used to
create a new development database. For example, the `QuerySetStrategy` can
export data from a table to a filesystem for later import.

This can be used for:

- Exporting a manually created database for other developers to use.
- Exporting realistic data from a production database.
- A cron job to maintain a development dataset hosted on cloud storage.

This step is optional (the built-in factory strategy doesn't do this).

#### Anonymisation

This step is critical when using `django-devdata` to export from production
sources. It's not a distinct step, but rather an opt-out part of the export
step.

#### Importing

This step is responsible for creating a new database and filling it. If any
exporting strategies have been used those must have run first, or their outputs
must have been downloaded if they are being shared/hosted somewhere.

Factory-based strategies generate data during this process.

## Customising

#### Strategies

The `django-devdata` strategies define how an import and optionally an export
happen. Each model is configured with a list of Strategies to use.

Classes are provided to inherit from for customising this behaviour:

- `Strategy` – the base class of all strategies.
- `Exportable` – a mixin that opts this strategy in to the export step.
- `QuerySetStrategy` – the base of all strategies that export production data
  to a filesystem. Handles referential integrity, serialisation, and
  anonymisation of the data pre-export.
- `FactoryStrategy` – the base of all strategies that create data based on
  `factory-boy` factories.

The API necessary for classes to implement is small, and there are customisation
points provided for common patterns.

In our experience most models can be exported with just the un-customised
`QuerySetStrategy`, some will need to use other pre-provided strategies, and
a small number will need custom exporters based on the classes provided.

#### Anonymisers

Anonymisers are configured by field name, and by model and field name.

Each anonymiser is a function that takes a number of kwargs with useful context
and returns a new value, compatible with the Django JSON encoder/decoder.

The signature for an anonymiser is:

```python
def anonymise(*, obj: Model, field: str, pii_value: Any, fake: Faker) -> Any:
    ...
```

There are several anonymisers provided to use or to build off:

- `faker_anonymise` – Use `faker` to anonymise this field with the provided
  generator, e.g. `faker_anonymise('pyint', min_value=15, max_value=85)`.
- `const` – anonymise to a constant value, e.g. `const('ch_XXXXXXXX')`.
- `random_foreign_key` – anonymise to a random foreign key.

`django-devdata`'s anonymisation is not intended to be perfect, but rather to be
a reasonable default for creating useful data that does a good enough job by
default. _Structure_ in data can be used to de-anonymise users in some cases
with advanced techniques, and `django-devdata` does not attempt to solve for
this case as most attackers, users, and legislators, are more concerned about
obviously personally identifiable information such as names and email addresses.
This anonymisation is no replacement for encryption at-rest with tools like
FileVault or BitLocker on development machines.

An example of this pragmatism in anonymisation is the `preserve_nulls` argument
taken by some built-in anonymisers. This goes against _true_ anonymisation, but
the absence of data is typically not of much use to attackers (or concern for
users), if the actual data is anonymised, while this can be of huge benefit to
developers in maintaining data consistency.

#### Settings

`django-devdata` makes heavy use of Django settings for both defining how it
should act for your site, and also for configuring how you'll use your workflow.

```python
"""
django-devdata default settings, with documentation on usage.
"""

# Required
# A mapping of app model label to list of strategies to be used.
DEVDATA_STRATEGIES = ...
# {'auth.User': [QuerySetStrategy(name='all')], 'sessions.Session': []}

# Optional
# A mapping of field name to an anonymiser to be used for all fields with that
# name.
DEVDATA_FIELD_ANONYMISERS = {}
# {'first_name': faker_anonymise('first_name'), 'ip': const('127.0.0.1')}

# Optional
# A mapping of app model label to a mapping of fields and anonymisers to be
# scoped to just that model.
DEVDATA_MODEL_ANONYMISERS = {}
# {'auth.User': {'first_name': faker_anonymise('first_name')}}

# Optional
# List of locales to be used for Faker in generating anonymised data.
DEVDATA_FAKER_LOCALES = None
# ['en_GB', 'en_AU']

# Optional
# In many codebases, there will only be a few models that will do most of the
# work to restrict the total export size – only taking a few users, or a few
# comments – for many models a default behaviour of taking everything
# following the restrictions from other models would be sufficient. This setting
# allows for specifying a default strategy.
# Important:
# - When using this, no errors will be raised if a model is missed from the list
#   of strategies.
# - This strategy is not added to all models, and it does not override an empty
#   list of strategies. It is only used when a model is not defined in the
#   strategy config at all.
DEVDATA_DEFAULT_STRATEGY = None
```

Strategies can be defined either as a strategy instance, or a tuple of
dotted-path and kwargs, for example the following are equivalent:

```python
DEVDATA_STRATEGIES = {
    'auth.User': [
        QuerySetStrategy(name='all_users'),
    ],
}

DEVDATA_STRATEGIES = {
    'auth.User': [
        ('devdata.strategies.QuerySetStrategy', {'name': 'all_users'}),
    ],
}
```

This alternate configuration format is provided in cases of extensive use of
custom strategies, as strategies often import models, but due to the Django
startup process models can't be imported until the settings have been imported.
