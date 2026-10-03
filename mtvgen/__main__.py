"""Allow running mtvgen as: python -m mtvgen"""

import sys
from .cli import main

sys.exit(main())
