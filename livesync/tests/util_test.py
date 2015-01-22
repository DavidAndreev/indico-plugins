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

from datetime import timedelta

import pytest

from indico.util.date_time import now_utc

from indico_livesync.models.agents import LiveSyncAgent
from indico_livesync.models.queue import LiveSyncQueueEntry, ChangeType
from indico_livesync.plugin import LiveSyncPlugin
from indico_livesync.util import make_compound_id, clean_old_entries


@pytest.mark.parametrize(('ref', 'expected'), (
    ({'type': 'event', 'event_id': '123'}, '123'),
    ({'type': 'contribution', 'event_id': '123', 'contrib_id': '456'}, '123.456'),
    ({'type': 'subcontribution', 'event_id': '123', 'contrib_id': '456', 'subcontrib_id': '789'}, '123.456.789'),
))
def test_make_compound_id(ref, expected):
    assert make_compound_id(ref) == expected


@pytest.mark.parametrize('ref_type', ('unknown', 'category'))
def test_make_compound_id_errors(ref_type):
    with pytest.raises(ValueError):
        make_compound_id({'type': ref_type})


def test_clean_old_entries(db):
    now = now_utc()
    agent = LiveSyncAgent(name='dummy', backend_name='dummy')
    for processed in (True, False):
        for day in range(10):
            db.session.add(LiveSyncQueueEntry(agent=agent, change=ChangeType.created, type='dummy', processed=processed,
                                              timestamp=now - timedelta(days=day, hours=12)))
    db.session.flush()
    # Nothing deleted with the setting's default value
    clean_old_entries()
    assert LiveSyncQueueEntry.find().count() == 20
    # Nothing deleted when explicitly set to 0 (which is the default)
    LiveSyncPlugin.settings.set('queue_entry_ttl', 0)
    clean_old_entries()
    assert LiveSyncQueueEntry.find().count() == 20
    # Only the correct entries deleted, and no unprocessed ones
    LiveSyncPlugin.settings.set('queue_entry_ttl', 3)
    clean_old_entries()
    assert LiveSyncQueueEntry.find(processed=False).count() == 10
    assert LiveSyncQueueEntry.find(processed=True).count() == 3
