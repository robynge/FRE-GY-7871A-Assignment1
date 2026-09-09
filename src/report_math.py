"""Numeric and mathematical display shared by the report and notebook."""
from io import BytesIO
from html import escape
import numbers

import numpy as np


def format_number(value, digits=3, target="text"):
    """Keep small nonzero estimates visible with proper scientific notation."""
    if isinstance(value, (bool, np.bool_)):
        return str(value)
    if isinstance(value, numbers.Integral):
        return f"{value:,}"
    if isinstance(value, numbers.Real):
        if not np.isfinite(value):
            return "—"
        if 0 < abs(value) < .001:
            mantissa, exponent = f"{value:.2e}".split("e")
            exponent = str(int(exponent))
            if target == "markdown":
                return rf"${mantissa}\times 10^{{{exponent}}}$"
            if target in ("html", "pdf"):
                tag = "sup" if target == "html" else "super"
                return f"{mantissa} × 10<{tag}>{exponent}</{tag}>"
            return f"{mantissa} × 10" + exponent.translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))
        return f"{value:.{digits}f}"
    return escape(str(value)) if target in ("html", "pdf") else str(value)


def formula_image(expression, max_width=515):
    """Render a TeX math expression at 300 dpi using installed matplotlib."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image
    from reportlab.platypus import Image

    buffer = BytesIO()
    math_to_image("$" + expression + "$", buffer, dpi=300, format="png",
                  prop=FontProperties(size=12), color="#202020")
    buffer.seek(0)
    image = Image(buffer)
    scale = min(72 / 300, max_width / image.imageWidth)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    image.hAlign = "LEFT"
    return image


if __name__ == "__main__":
    assert format_number(.000169, target="markdown") == r"$1.69\times 10^{-4}$"
    assert format_number(-.000169, target="pdf") == "-1.69 × 10<super>-4</super>"
    assert format_number(.000169, target="html") == "1.69 × 10<sup>-4</sup>"
    assert format_number(float("nan")) == "—"
    assert format_number(0) == "0"
    assert 0 < formula_image(r"P_{cj}=\frac{\sum_{i\in c}tf_{ij}}{W_j}").drawWidth <= 515
    print("Scientific notation and formula rendering checks passed.")
