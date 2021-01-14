"""
FlatTree works with nested dictionaries or lists.
"""
__title__ = __name__
__description__ = __doc__.replace('\n', ' ').replace('\r', '').strip()
__version__ = '3.0.0'
__author__ = 'Aleksandr Mikhailov'
__author_email__ = 'dev@avidclam.com'
__copyright__ = '2021 Aleksandr Mikhailov'

from .settings import get_default_settings
from .public import FlatTree
