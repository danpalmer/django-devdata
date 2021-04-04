# Tests Structure

While there are unit tests for utilities, the main usage is tested with two
integration tests, an export and an import, on an example site.

### Export integration test

The export integration test uses the Django site in `tests/testsite`. It follows
this rough process:

1. Create `testsite`'s database.
2. Migrate the models.
3. Use `loaddata` to load seed test data.
4. Run an export.
5. Check that there were no errors on export.
6. Check that the exported data matches expectations.

### Import integration test

1. Run an import, using the given exported data.
2. Check that there were no errors on import.
3. Check that the imported data matches expectations.
