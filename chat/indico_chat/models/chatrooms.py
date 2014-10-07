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

from sqlalchemy.ext.declarative import declared_attr

from indico.core.db.sqlalchemy import db, UTCDateTime
from indico.util.date_time import now_utc
from indico.util.string import return_ascii
from MaKaC.user import AvatarHolder
from MaKaC.conference import ConferenceHolder
from indico_chat.xmpp import generate_jid, delete_room


class Chatroom(db.Model):
    __tablename__ = 'chatrooms'

    @declared_attr
    def __table_args__(cls):
        return (db.UniqueConstraint(cls.jid_node, cls.custom_server),
                {'schema': 'plugin_chat'})

    #: Chatroom ID
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    #: Node of the chatroom's JID (the part before `@domain`)
    jid_node = db.Column(
        db.String,
        nullable=False
    )
    #: Name of the chatroom
    name = db.Column(
        db.String,
        nullable=False
    )
    #: Description of the chatroom
    description = db.Column(
        db.Text,
        nullable=False,
        default=''
    )
    #: Password to join the room
    password = db.Column(
        db.String,
        nullable=False,
        default=''
    )
    #: Custom Jabber MUC server hostname
    custom_server = db.Column(
        db.String,
        nullable=False,
        default=''
    )
    #: ID of the creator
    created_by_id = db.Column(
        db.Integer,
        nullable=False,
        index=True
    )
    #: Creation timestamp of the chatroom
    created_dt = db.Column(
        UTCDateTime,
        nullable=False,
        default=now_utc
    )
    #: Modification timestamp of the chatroom
    modified_dt = db.Column(
        UTCDateTime
    )

    @property
    def locator(self):
        return {'chatroom_id': self.id}

    @property
    def created_by_user(self):
        """The Avatar who created the chatroom."""
        return AvatarHolder().getById(str(self.created_by_id))

    @created_by_user.setter
    def created_by_user(self, user):
        self.created_by_id = int(user.getId())

    @property
    def server(self):
        """The server name of the chatroom.

        Usually the default one unless a custom one is set.
        """
        from indico_chat.plugin import ChatPlugin

        return self.custom_server or ChatPlugin.settings.get('muc_server')

    @return_ascii
    def __repr__(self):
        server = self.server
        if self.custom_server:
            server = '!' + server
        return '<Chatroom({}, {}, {}, {})>'.format(self.id, self.name, self.jid_node, server)

    def __committed__(self, change):
        super(Chatroom, self).__committed__(change)
        if change == 'delete':
            delete_room(self)

    def generate_jid(self):
        """Generates the JID based on the room name"""
        assert self.jid_node is None
        self.jid_node = generate_jid(self.name)


class ChatroomEventAssociation(db.Model):
    __tablename__ = 'chatroom_events'
    __table_args__ = {'schema': 'plugin_chat'}

    #: ID of the event
    event_id = db.Column(
        db.Integer,
        primary_key=True,
        index=True,
        autoincrement=False
    )
    #: ID of the chatroom
    chatroom_id = db.Column(
        db.Integer,
        db.ForeignKey('plugin_chat.chatrooms.id'),
        primary_key=True,
        index=True
    )
    #: If the chatroom should be hidden on the event page
    hidden = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    #: If the password should be visible on the event page
    show_password = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    #: The associated :class:Chatroom
    chatroom = db.relationship(
        'Chatroom',
        lazy=False,
        backref=db.backref('events', cascade='all, delete-orphan')
    )

    @property
    def locator(self):
        return dict(self.event.getLocator(), **self.chatroom.locator)

    @property
    def event(self):
        return ConferenceHolder().getById(str(self.event_id))

    @event.setter
    def event(self, event):
        self.event_id = int(event.getId())

    @return_ascii
    def __repr__(self):
        return '<ChatroomEventAssociation({}, {})>'.format(self.event_id, self.chatroom)

    @classmethod
    def find_for_event(cls, event, include_hidden=False, **kwargs):
        """Returns a Query that retrieves the chatrooms for an event

        :param event: an indico event (with a numeric ID)
        :param include_hidden: if hidden chatrooms should be included, too
        :param kwargs: extra kwargs to pass to ``find()``
        """
        query = cls.find(event_id=int(event.id), **kwargs)
        if not include_hidden:
            query = query.filter(~cls.hidden)
        return query

    def delete(self):
        """Deletes the event chatroom and if necessary the chatroom, too.

        :return: True if the associated chatroom was also
                 deleted, otherwise False
        """
        db.session.delete(self)
        db.session.flush()
        if not self.chatroom.events:
            db.session.delete(self.chatroom)
            return True
        return False
