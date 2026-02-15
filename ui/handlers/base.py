from typing import Any
import logging

class BaseHandler:
    """Base class for specialized event handlers."""
    def __init__(self, app: Any, ctx: Any):
        self.app = app
        self.ctx = ctx
        self.ui = ctx.ui
        self.config_manager = ctx.config_manager
        self.data_manager = ctx.data_manager
        self.tab_mgr = ctx.tab_mgr
        self.character_manager = ctx.character_manager
        self.image_proc = ctx.image_proc
        self.score_calc = ctx.score_calc
        self.logger = logging.getLogger(self.__class__.__name__)
