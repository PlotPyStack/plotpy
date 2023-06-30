# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see plotpy/__init__.py for details)

"""PlotDialog test"""

# guitest: show

import numpy as np
from guidata.qthelpers import qt_app_context

from plotpy.core.builder import make
from plotpy.core.plot.plotwidget import PlotDialog, PlotType


def plot(*items):
    win = PlotDialog(
        edit=False,
        toolbar=True,
        wintitle="PlotDialog test",
        options=dict(
            title="Title", xlabel="xlabel", ylabel="ylabel", type=PlotType.CURVE
        ),
    )
    plot = win.manager.get_plot()
    for item in items:
        plot.add_item(item)
    win.manager.get_itemlist_panel().show()
    plot.set_items_readonly(False)
    win.show()

    return win, plot.get_items()


def test_plot():
    """Test plot"""
    x = np.linspace(-10, 10, 200)
    dy = x / 100.0
    y = np.sin(np.sin(np.sin(x)))
    x2 = np.linspace(-10, 10, 20)
    y2 = np.sin(np.sin(np.sin(x2)))
    with qt_app_context(exec_loop=True):
        curve2 = make.curve(x2, y2, color="g", curvestyle="Sticks")
        curve2.setTitle("toto")
        _persist_plot, items = plot(
            make.curve(x, y, color="b"),
            curve2,
            make.curve(x, np.sin(2 * y), color="r"),
            make.merror(x, y / 2, dy),
            make.label(
                "Relative position <b>outside</b>", (x[0], y[0]), (-10, -10), "BR"
            ),
            make.label("Relative position <i>inside</i>", (x[0], y[0]), (10, 10), "TL"),
            make.label("Absolute position", "R", (0, 0), "R"),
            make.legend("TR"),
            make.marker(
                position=(5.0, 0.8),
                label_cb=lambda x, y: "A = %.2f" % x,
                markerstyle="|",
                movable=False,
            ),
        )


if __name__ == "__main__":
    test_plot()
