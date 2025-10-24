import unittest
from types import SimpleNamespace

from PyEmailerAJM.searchers import SearcherFactory, AttributeSearcher, SubjectSearcher, OUTLOOK_ATSQL_ALIASES


class DummyLogger:
    def __init__(self):
        # mimic basic logging API used in code
        self.infos = []
        self.debugs = []
        self.warnings = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))


class DummyMsg:
    """Lightweight stand-in for an Outlook item wrapper.
    - Has both TitleCase and lowercase attribute variants to match current code paths.
    - Is callable and returns itself so [m() for m in matched_messages] works.
    """
    def __init__(self, Subject='', Body='', SenderName=''):
        self.Subject = Subject
        self.Body = Body
        self.SenderName = SenderName
        # lowercase duplicates to satisfy SubjectSearcher path which passes 'subject'
        self.subject = Subject
        self.body = Body
        self.sendername = SenderName

    def __call__(self):
        return self


class DummyPyEmailer:
    def __init__(self, messages):
        self._messages = messages

    def GetMessages(self, *args, **kwargs):
        return list(self._messages)


def make_messages():
    return [
        DummyMsg(Subject='Weekly Report', Body='The deployment succeeded', SenderName='Alice Smith'),
        DummyMsg(Subject='RE: Weekly Report', Body='Following up on report', SenderName='Bob Jones'),
        DummyMsg(Subject='FW: Weekly Report', Body='Fwd: see details', SenderName='Charlie'),
        DummyMsg(Subject='Random Topic', Body='Irrelevant body', SenderName='Dora'),
    ]


class TestSearcherFactory(unittest.TestCase):
    def setUp(self):
        self.messages = make_messages()
        self.get_messages = lambda: list(self.messages)
        self.logger = DummyLogger()
        self.factory = SearcherFactory()

    def test_available_types_includes_subject(self):
        available = self.factory.available_types()
        self.assertIn('subject', available)

    def test_registered_subject_searcher_returned_and_finds_subjects(self):
        s = self.factory.get_searcher('subject', get_messages=self.get_messages, logger=self.logger)
        self.assertIsInstance(s, SubjectSearcher)
        # Search for base subject should match exact plus RE/FW when defaults include prefixes
        results_exact = s.find_messages_by_attribute('Weekly Report', partial_match_ok=False)
        # should match exact, RE, and FW because SubjectSearcher accounts for prefixes
        self.assertEqual(len(results_exact), 3)
        self.assertTrue(all(isinstance(m, DummyMsg) for m in results_exact))

    def test_generic_attribute_keyword_variants(self):
        for key in ('attribute', 'attr', 'field'):
            with self.subTest(key=key):
                s = self.factory.get_searcher(key, attribute='Body', get_messages=self.get_messages, logger=self.logger)
                self.assertIsInstance(s, AttributeSearcher)
                out = s.find_messages_by_attribute('deployment succeeded', partial_match_ok=True)
                self.assertEqual(len(out), 1)
                self.assertEqual(out[0].Subject, 'Weekly Report')

    def test_direct_alias_attribute_name_case_insensitive(self):
        # choose a known alias from OUTLOOK_ATSQL_ALIASES
        alias = 'SenderName'
        self.assertIn(alias, OUTLOOK_ATSQL_ALIASES)

        # lower-cased search_type should still map
        s = self.factory.get_searcher(alias.lower(), get_messages=self.get_messages, logger=self.logger)
        self.assertIsInstance(s, AttributeSearcher)
        out = s.find_messages_by_attribute('alice', partial_match_ok=True)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].SenderName, 'Alice Smith')

    def test_py_emailer_keyword_maps_get_messages(self):
        py_emailer = DummyPyEmailer(self.messages)
        s = self.factory.get_searcher('attribute', attribute='Body', py_emailer=py_emailer, logger=self.logger)
        # Should work without explicitly passing get_messages
        out = s.find_messages_by_attribute('fwd: see', partial_match_ok=True)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].Subject, 'FW: Weekly Report')

    def test_invalid_type_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.factory.get_searcher('not_a_valid_type', get_messages=self.get_messages, logger=self.logger)
        msg = str(ctx.exception)
        self.assertIn('Invalid search type', msg)
        self.assertIn('Known:', msg)


if __name__ == '__main__':
    unittest.main()