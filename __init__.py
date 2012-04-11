#!/usr/bin/python

# Copyright (C) 2012 Rainer Hihn ( rainer@hihn.org )
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 1, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from xl import (
	event,
	player,
	providers,
	settings,
	trax
)
from xl.player.adapters import (
	PlaybackAdapter,
	QueueAdapter
)
from xlgui import main
from xlgui.widgets import menu
import glib, gtk, logging, os, random, time, thread

PATH 		= os.path.dirname(os.path.realpath(__file__))
SHUFFLE		= None
logger 		= logging.getLogger(__name__)
	
### Plugin Handling ###

def enable(exaile):
	if (exaile.loading):
		event.add_callback(_enable, 'exaile_loaded')
	else:
		_enable(None, exaile, None)

def _enable(eventname, exaile, nothing):
	'''
		Called when plugin is loaded.
	'''
	global SHUFFLE
	SHUFFLE = Shuffle(exaile)

def disable(exaile):
	'''
		Called when plugin is unloaded.  Remove Menu Item. Clean up.
	'''
	global SHUFFLE
	if SHUFFLE:
		SHUFFLE = None

### The Actual Stuff ###

class Shuffle(PlaybackAdapter):
	def __init__(self, exaile):
		logger.debug('__init__() called')
		self.exaile = exaile
		self.do_shuffle = False
		self.playlist_handle = main.get_selected_playlist().playlist
		self.last_artists = []
		self.myTrack = None
		self.tracks = list()
		self.ban_repeat = 20 # ban an artist for x tracks

		for track in self.exaile.collection.get_tracks():
 			self.tracks.append(track.get_loc_for_io() or [])

		# Menu
		providers.register('menubar-tools-menu', menu.simple_separator(None, ['track-properties']))
		self.menu = menu.check_menu_item('shuffle', ['plugin-sep'], 'Shuffle', 
			lambda *x: self.do_shuffle, lambda w, n, p, c: self.on_toggled(w))
		providers.register('menubar-tools-menu', self.menu)		
		event.add_callback(self.on_playback_track_start, "playback_track_start", player.PLAYER)

	def on_toggled(self, menuitem):
		'''
			Enables or disables the shuffle plugin.
		'''
		if menuitem.get_active():
			logger.debug('Shuffle activated.')
			self.do_shuffle = True
			self.play()
		else:
			logger.debug('Shuffle deactivated.')
			self.do_shuffle = False

	def remove_menu_item(self):
		'''
			Remove the Menu item.
		'''
		if self.menu_item:
		    self.menu_item.hide()
		    self.menu_item.destroy()
		    self.menu_item = None		
		
	def play(self):
		'''
			Calls find_track() and checks if it returns an artist
			that is redundant. Adds the track to the playlist and 
			adds the artist to the last_artists. 
			Also removes the first item from last_artists (if its full).
		'''
		while True:
			if (self.is_redundant(self.find_track()) == False):
				break
	
		self.playlist_handle.append(self.myTrack)

		if ( len(self.last_artists) >= self.ban_repeat ):
			self.last_artists.pop(0)

		self.last_artists.append(self.myTrack.get_tag_display("artist"))
		self.myTrack = None
	
	def is_redundant(self, myTrack):
		'''
			Return True if its redundant
			Checks if the Artist was already a shuffle-result 
			the last x times. x can be set via self.ban_repeat (default: 20).
		'''
		for i in self.last_artists:
			if i == myTrack.get_tag_display("artist"):
				logger.debug("Banning "+myTrack.get_tag_display("artist")+" for Redundancy!")
				return True

		self.myTrack = myTrack
		return False

	def find_track(self):
		'''
			Returns a random track from the collection.
		'''
		random.seed()
		random_track_id = random.randint(1, len(self.tracks))
		random_track_uri = self.tracks[random_track_id]

		myTrack = trax.Track(random_track_uri)
		return myTrack

	def on_playback_track_start(self, event, player, track):
		'''
			Callback for when a track starts. The next track will be
			added when a track starts, not when a track fades out.
		'''
		self.play()