"""A clean checkout must not borrow a missing module from an editable install."""
import importlib
from pathlib import Path
import pkgutil
import sys
import app

def test_all_application_modules_resolve_inside_this_checkout():
    expected=Path(__file__).resolve().parents[1]/'app'
    assert Path(app.__file__).resolve().is_relative_to(expected)
    for module in pkgutil.walk_packages([str(expected)],prefix='app.'):
        importlib.import_module(module.name)
    outside=[name for name,module in sys.modules.items()
             if (name=='app' or name.startswith('app.')) and getattr(module,'__file__',None)
             and not Path(module.__file__).resolve().is_relative_to(expected)]
    assert outside==[],f'Application modules resolved outside the checkout: {outside}'
