from collections.abc import Callable
from typing import Type, Tuple, Optional

from . import BaseSearcher, AttributeSearcher, OUTLOOK_ATSQL_ALIASES


# noinspection PyProtectedMember
class SearcherFactory:
    """Dynamic factory returning a searcher class or instance for a given search option."""

    @staticmethod
    def available_types() -> Tuple[str, ...]:
        """All registered specialized search types (from subclasses that set SEARCH_TYPE)."""
        return tuple(sorted(BaseSearcher._REGISTRY.keys()))

    @staticmethod
    def get_searcher(search_type: str, *, attribute: Optional[str] = None, **kwargs) -> BaseSearcher:
        """
        Return an instance of a searcher matching `search_type`.

        - If `search_type` is a registered specialized type (e.g., 'subject'), returns that class.
        - Else, if `attribute` is provided (or can be inferred), returns a generic AttributeSearcher for that attribute.
        - Else, raises ValueError.

        Example calls:
            get_searcher('subject')
            get_searcher('attribute', attribute='Body')
        """

        # Optionally map py_emailer -> get_messages for convenience
        py_emailer: Callable | object | None = kwargs.pop('py_emailer', None)
        if py_emailer is not None and 'get_messages' not in kwargs:
            kwargs['get_messages'] = py_emailer.GetMessages

        key = (search_type or '').lower().strip()
        # 1) Registered specialized searchers
        if key in BaseSearcher._REGISTRY:
            cls: Type[BaseSearcher] = BaseSearcher._REGISTRY[key]
            return cls(**kwargs)

        # 2) Generic attribute path: explicit attribute name supplied
        if key in ("attribute", "attr", "field") and attribute:
            return AttributeSearcher(attribute=attribute, **kwargs)

        # 3) Convenience: if caller passes a known Outlook alias directly (e.g., 'Body'),
        #    treat `search_type` as the attribute name
        if key in {a.lower() for a in OUTLOOK_ATSQL_ALIASES}:
            return AttributeSearcher(attribute=search_type, **kwargs)

        raise ValueError(f"Invalid search type: {search_type!r}. "
                         f"Known: {SearcherFactory.available_types()} "
                         f"or use 'attribute' with a field name.")


if __name__ == '__main__':
    factory = SearcherFactory()

    # Specialized subject searcher (with RE/FW handling)
    subject_searcher = factory.get_searcher('subject')
    msgs = subject_searcher.find_messages_by_subject('Weekly Report', partial_match_ok=True)

    # Generic attribute searcher
    body_searcher = factory.get_searcher('attribute', attribute='Body')
    msgs2 = body_searcher.find_messages_by_attribute('deployment succeeded', partial_match_ok=True)

    # If you enabled dynamic per-attribute classes
    sender_searcher = factory.get_searcher('sendername')  # Body, To, CC, etc. also work
    msgs3 = sender_searcher.find_messages_by_attribute('Alice Smith')