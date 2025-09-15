from .searchers import SubjectSearcher

# TODO: flesh me out
class SearcherFactory:
    SEARCHER_CLASSES = [SubjectSearcher,]

    @staticmethod
    def get_searcher(search_type):
        if search_type == 'subject':
            return SubjectSearcher()
        else:
            raise ValueError('Invalid search type')