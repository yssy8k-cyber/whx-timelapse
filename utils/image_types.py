"""项目中统一使用的 OpenCV 图像类型。"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


Frame = NDArray[np.uint8]
