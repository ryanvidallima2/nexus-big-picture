# -*- coding: utf-8 -*-
"""BigPictureApp: composicao dos mixins (extraido sem alteracao)."""

from .app_cards import AppCardsMixin
from .app_games import AppGamesMixin
from .app_remote import AppRemoteMixin
from .app_settings import AppSettingsMixin
from .app_shell import AppShellMixin
from .app_views import AppViewsMixin
from .cardflip import CardFlipMixin


class BigPictureApp(AppShellMixin, AppViewsMixin, AppGamesMixin,
                    AppCardsMixin, AppRemoteMixin, AppSettingsMixin,
                    CardFlipMixin):
    """Janela principal do Nexus (metodos vivem nos mixins)."""

