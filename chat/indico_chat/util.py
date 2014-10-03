# This file is part of Indico.
# Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
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

from __future__ import unicode_literals

from indico.util.user import retrieve_principals


def get_chat_admins():
    """Returns a list of chat admins

    :return: list of Avatar/Group objects
    """
    from indico_chat.plugin import ChatPlugin
    return retrieve_principals(ChatPlugin.settings.get('admins'))


def is_chat_admin(user):
    """Checks if a user is a chat admin"""
    return any(principal.containsUser(user) for principal in get_chat_admins())
