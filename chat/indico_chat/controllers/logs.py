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

from __future__ import unicode_literals

from datetime import datetime
from tempfile import NamedTemporaryFile

from flask import request, flash, redirect, jsonify
from werkzeug.utils import secure_filename

from indico.core.config import Config
from indico.core.plugins import url_for_plugin
from indico.util.i18n import _
from MaKaC.common.log import ModuleNames
from MaKaC.conference import LocalFile

from indico_chat.controllers.base import RHEventChatroomMixin, RHChatManageEventBase
from indico_chat.views import WPChatEventMgmt
from indico_chat.xmpp import retrieve_logs


class RHChatManageEventLogs(RHEventChatroomMixin, RHChatManageEventBase):
    """UI to retrieve logs for a chatroom"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        RHEventChatroomMixin._checkParams(self)

    def _process(self):
        if not retrieve_logs(self.chatroom):
            flash(_('There are no logs available for this room.'), 'warning')
            return redirect(url_for_plugin('.manage_rooms', self.event))
        return WPChatEventMgmt.render_template('manage_event_logs.html', self._conf, event_chatroom=self.event_chatroom,
                                               start_date=self.event.getAdjustedStartDate(),
                                               end_date=self.event.getAdjustedEndDate())


class RHChatManageEventRetrieveLogsBase(RHEventChatroomMixin, RHChatManageEventBase):
    """Retrieves logs for a chatroom"""

    def _checkParams(self, params):
        RHChatManageEventBase._checkParams(self, params)
        RHEventChatroomMixin._checkParams(self)

        if 'get_all_logs' not in request.values:
            self.start_date = datetime.strptime(request.values['start_date'], '%d/%m/%Y').date()
            self.end_date = datetime.strptime(request.values['end_date'], '%d/%m/%Y').date()
            self.date_filter = True
        else:
            self.start_date = self.end_date = None
            self.date_filter = False

    def _get_logs(self):
        return retrieve_logs(self.chatroom, self.start_date, self.end_date)


class RHChatManageEventShowLogs(RHChatManageEventRetrieveLogsBase):
    """Shows the logs for a chatroom"""

    def _process(self):
        logs = self._get_logs()
        if not logs:
            if self.date_filter:
                msg = _('Could not find any logs for the given timeframe.')
            else:
                msg = _('Could not find any logs for the chatroom.')
            return jsonify(success=False, msg=msg)
        return jsonify(success=True, html=logs, params=request.args.to_dict())


class RHChatManageEventAttachLogs(RHChatManageEventRetrieveLogsBase):
    """Attachs the logs for a chatroom to the event"""

    def _checkParams(self, params):
        RHChatManageEventRetrieveLogsBase._checkParams(self, params)
        self.material_name = request.form['material_name'].strip()
        self.file_repo_id = None

    def _process(self):
        logs = self._get_logs()
        if not logs:
            return jsonify(success=False, msg=_('No logs found'))
        self._create_material(logs)
        return jsonify(success=True)

    def _create_material(self, logs):
        tmpfile = NamedTemporaryFile(suffix='indico.tmp', dir=Config.getInstance().getUploadedFilesTempDir())
        tmpfile.write(logs)
        tmpfile.flush()
        filename = secure_filename('{}.html'.format(self.material_name))
        registry = self.event.getMaterialRegistry()

        # Create the material type. The ID must match the title besides casing or we end up
        # creating new types all the time...
        mf = registry.getById(b'chat logs')
        mat = mf.get(self.event)
        if mat is None:
            mat = mf.create(self.event)
            mat.setProtection(1)
            mat.setTitle(b'Chat Logs')
            mat.setDescription(b'Chat logs for this event')

        # Create the actual material
        resource = LocalFile()
        resource.setName(filename)
        resource.setDescription("Chat logs for the chat room '{}'".format(self.chatroom.name).encode('utf-8'))
        resource.setFileName(filename)
        resource.setFilePath(tmpfile.name)
        resource.setProtection(0)

        # Store the file in the file repository. self.file_repo_id is set in case of a retry
        mat.addResource(resource, forcedFileId=self.file_repo_id)
        self.file_repo_id = resource.getRepositoryId()

        # Log the action
        log_info = {b'subject': b"Added file {} (chat logs)".format(filename)}
        self.event.getLogHandler().logAction(log_info, ModuleNames.MATERIAL)
