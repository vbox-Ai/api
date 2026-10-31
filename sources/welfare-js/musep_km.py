# -*- coding: utf-8 -*-
"""暮色资源平台「快猫」（key=km）—— 自动生成的薄封装，勿手改。
   引擎与协议见同目录 muse_avbox.py
"""
import os
import sys
import importlib.util

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    from muse_avbox import Spider as _Base
except Exception:
    _spec = importlib.util.spec_from_file_location(
        "muse_avbox", os.path.join(_HERE, "muse_avbox.py"))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _Base = _mod.Spider


class Spider(_Base):
    MODULE = "km"
