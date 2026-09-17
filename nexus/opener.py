# -*- coding: utf-8 -*-
"""Abertura via deep-link / URL (extraido sem alteracao)."""

import subprocess
import webbrowser

from .streamings import STREAMINGS_DB


class StreamingOpener:
    def __init__(self, settings=None):
        self.all_services = {**STREAMINGS_DB}
        self.settings = settings if settings is not None else {}

    def effective_url(self, service_name):
        settings = self.settings or {}
        over = settings.get("custom_urls", {}).get(service_name)
        if over:
            return over
        info = self.all_services.get(service_name)
        if info is None:
            info = settings.get("custom_streamings", {}).get(service_name, {})
        return info.get("url", "#")

    def open_content(self, service_name, content_id=None):
        settings = self.settings or {}
        over = settings.get("custom_urls", {}).get(service_name)
        if over:
            url = over.replace("{id}", content_id) if content_id else over
            webbrowser.open(url)
            return
        info = self.all_services.get(service_name)
        if info is None:
            info = settings.get("custom_streamings", {}).get(service_name, {})
        url = info.get("url", "#")

        if content_id and info.get("deep_link"):
            deep = info["deep_link"].replace("{id}", content_id)
            try:
                subprocess.Popen(["cmd", "/c", "start", "", deep], shell=False)
                return
            except:
                pass

        if content_id and info.get("url_template"):
            url = info["url_template"].replace("{id}", content_id)

        webbrowser.open(url)

