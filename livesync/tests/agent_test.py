# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from mock import MagicMock

from indico_livesync.base import LiveSyncBackendBase
from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType


class DummyBackend(LiveSyncBackendBase):
    """Dummy agent

    A dummy agent for testing
    """

    def _get_excluded_categories(self):
        return set()


class NonDescriptiveAgent(LiveSyncBackendBase):
    """Nondescriptive agent"""


class MockCategory(object):
    def __init__(self, id_, subcategories=None):
        self.id = id_
        self.subcategories = subcategories or set()

    def getId(self):
        return self.id


class MockCategoryManager(object):
    # a
    # |- b
    # `- c
    #    |- d
    #       |- e
    #       `- f
    categories = {
        'a': MockCategory('a', {'b', 'c'}),
        'b': MockCategory('b'),
        'c': MockCategory('c', {'d'}),
        'd': MockCategory('d', {'e', 'f'}),
        'e': MockCategory('e'),
        'f': MockCategory('f')
    }

    @classmethod
    def getById(cls, id_):
        return cls.categories[id_]


def test_title_description():
    """Test if title/description are extracted from docstring"""
    assert DummyBackend.title == 'Dummy agent'
    assert DummyBackend.description == 'A dummy agent for testing'
    assert NonDescriptiveAgent.title == 'Nondescriptive agent'
    assert NonDescriptiveAgent.description == 'no description available'


def test_run_initial():
    """Test if run_initial_export calls the uploader properly"""
    backend = DummyBackend(MagicMock())
    mock_uploader = MagicMock()
    backend.uploader = lambda x: mock_uploader
    events = object()
    backend.run_initial_export(events)
    mock_uploader.run_initial.assert_called_with(events)


def test_run(mocker):
    """Test if run calls the fetcher/uploader properly"""
    mocker.patch.object(DummyBackend, 'fetch_records')
    backend = DummyBackend(MagicMock())
    mock_uploader = MagicMock()
    backend.uploader = lambda x: mock_uploader
    backend.run()
    assert backend.fetch_records.called
    assert mock_uploader.run.called


def test_fetch_records(db, mocker):
    """Test if the correct records are fetched"""
    mocker.patch.object(DummyBackend, '_is_entry_excluded', return_value=False)
    agent = LiveSyncAgent(backend_name='dummy', name='dummy')
    backend = DummyBackend(agent)
    db.session.add(agent)
    queue = [LiveSyncQueueEntry(change=ChangeType.created, type='dummy', processed=True),
             LiveSyncQueueEntry(change=ChangeType.created, type='dummy')]
    agent.queue = queue
    db.session.flush()
    assert backend.fetch_records() == [queue[1]]
    assert backend._is_entry_excluded.call_count == 1
    backend._is_entry_excluded.assert_called_with(queue[1])


def test_excluded_categories(mocker, monkeypatch):
    """Test if category exclusions work"""
    monkeypatch.setattr('indico_livesync.base.CategoryManager', MockCategoryManager)
    plugin = mocker.patch('indico_livesync.base.LiveSyncPlugin')
    plugin.settings.get.return_value = [{'id': 'invalid'}, {'id': 'c'}, {'id': 'd'}]
    backend = LiveSyncBackendBase(MagicMock())
    assert backend.excluded_categories == {'c', 'd', 'e', 'f'}
