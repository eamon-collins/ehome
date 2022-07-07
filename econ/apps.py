from django.apps import AppConfig


class EconConfig(AppConfig):
    name = 'econ'
    def ready(self):
        import econ.crawl as crawl
        crawl.setup_timed_scraping()