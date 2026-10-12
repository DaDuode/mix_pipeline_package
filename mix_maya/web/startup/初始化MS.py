#!/usr/bin/env python
# -*- coding: utf8 -*-




def main():
    from LiveLink import initLiveLink
    from Megascans import Installer
    from DHI import DHIPluginLoader
    try:
        DHIPluginLoader.load()
    finally:   
        Installer.createMSshelf()
        initLiveLink()
