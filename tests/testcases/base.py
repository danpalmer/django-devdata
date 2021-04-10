import itertools

TESTCASES = []


class TestCaseRegistryMeta(type):
    def __new__(mcs, name, bases, attrs):
        klass = super().__new__(mcs, name, bases, attrs)
        if name != "DevdataTestCase":
            TESTCASES.append(klass())
        return klass


class DevdataTestCase(metaclass=TestCaseRegistryMeta):
    def get_original_data(self):
        raise NotImplementedError

    def assert_on_exported_data(self, exported_data):
        pass

    def assert_on_imported_data(self, connection):
        pass

    #

    def _original_pks(self, model):
        return set(
            x["pk"]
            for x in self.get_original_data()
            if x["model"].lower() == model.lower()
        )

    def _exported_pks(self, exported_data, model, strategy=None):
        strategies = exported_data[model]
        if strategy is not None:
            exported = strategies[strategy]
        else:
            exported = itertools.chain(*strategies.values())
        return set(x["pk"] for x in exported)
