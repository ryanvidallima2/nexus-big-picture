# -*- coding: utf-8 -*-
"""Foco grade do hub (extraido sem alteracao)."""


class FocusManager:
    def __init__(self):
        self.focused_row = 0
        self.focused_col = 0

    def reset(self):
        self.focused_row = 0
        self.focused_col = 0
