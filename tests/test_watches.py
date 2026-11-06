import os
import tempfile
import unittest

from background import DownloadWatcher
from models import Query
from search import SearchService
from test_search import FakeProvider, release
from transmission import Torrent
from watches import WatchService


class RecordingNotifier:
    def __init__(self):
        self.sent = []

    def send(self, title, message, url=""):
        self.sent.append((title, message))


class WatchServiceTest(unittest.TestCase):
    def setUp(self):
        self.provider = FakeProvider([release(n) for n in range(5)])
        self.notifier = RecordingNotifier()
        self.path = os.path.join(tempfile.mkdtemp(), "watches.json")
        self.service = WatchService(SearchService([self.provider]), self.notifier, self.path)

    def test_existing_releases_do_not_notify(self):
        self.service.add("Films", "fake", Query())
        self.service.check_all()
        self.assertEqual(self.notifier.sent, [])

    def test_new_release_notifies_once(self):
        self.service.add("Films", "fake", Query())
        self.provider.releases.insert(0, release(99))
        self.service.check_all()
        self.service.check_all()
        self.assertEqual(self.notifier.sent, [("Nouvelle release : Films", "Film.99")])

    def test_watches_survive_restart_and_removal(self):
        watch = self.service.add("Dune", "fake", Query(text="dune", langs=("MULTI",)))
        reloaded = WatchService(SearchService([self.provider]), self.notifier, self.path)
        self.assertEqual([(w.label, w.query.langs, w.query.sort) for w in reloaded.all()], [("Dune", ("MULTI",), "date")])
        reloaded.remove(watch.id)
        self.assertEqual(WatchService(SearchService([self.provider]), self.notifier, self.path).all(), [])


def torrent(n: int, progress: float) -> Torrent:
    return Torrent(id=n, hash=f"h{n}", name=f"Torrent {n}", state="downloading", progress=progress, size=1,
                   down_rate=0, up_rate=0, eta=-1, ratio=0.0, error="", added=0, done=0)


class FakeTransmission:
    def __init__(self, torrents):
        self.list = torrents

    def torrents(self):
        return self.list


class DownloadWatcherTest(unittest.TestCase):
    def test_notifies_only_newly_completed_downloads(self):
        transmission = FakeTransmission([torrent(1, 1.0), torrent(2, 0.5)])
        notifier = RecordingNotifier()
        watcher = DownloadWatcher(transmission, notifier)
        watcher.check()                                     # 1er passage : rien
        transmission.list = [torrent(1, 1.0), torrent(2, 1.0)]
        watcher.check()
        watcher.check()
        self.assertEqual(notifier.sent, [("Téléchargement terminé", "Torrent 2")])


if __name__ == "__main__":
    unittest.main()
