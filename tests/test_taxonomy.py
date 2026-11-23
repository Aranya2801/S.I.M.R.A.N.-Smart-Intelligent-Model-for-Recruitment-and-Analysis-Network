from simran.taxonomy import load_taxonomy

tax = load_taxonomy()


def skills(text):
    return set(tax.extract(text))


def test_aliases_map_to_canonical():
    assert skills("Worked with k8s, Postgres and ReactJS") == {"kubernetes", "postgresql", "react"}


def test_longest_alias_wins():
    # "react native" must not also count as plain react
    assert skills("Built apps in React Native") == {"react native"}


def test_symbols_in_names():
    assert {"c++", "c#", ".net", "node.js"} <= skills("Languages: C++, C#, .NET, Node.js")


def test_negation_is_ignored():
    assert "kafka" not in skills("No hands-on experience with Kafka yet")


def test_ambiguous_words_need_context():
    assert "go" not in skills("Happy to go the extra mile")
    assert "go" in skills("Languages: Python, Go, SQL")
    assert "rest api" not in skills("the rest of the team")


def test_related_is_symmetric():
    assert tax.is_related("mysql", "postgresql") and tax.is_related("postgresql", "mysql")
