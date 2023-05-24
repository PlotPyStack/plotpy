# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see plotpy/__init__.py for details)

"""
Masked Image test, creating the MaskedImageItem object via make.maskedimage

Masked image items are constructed using a masked array item. Masked data is
ignored in computations, like the average cross sections.
"""

import os
import pickle

from guidata.qthelpers import qt_app_context

from plotpy.core.builder import make
from plotpy.core.plot.plotwidget import PlotDialog, PlotType
from plotpy.core.tools.image import ImageMaskTool

SHOW = True  # Show test in GUI-based test launcher

FNAME = "image_masked.pickle"


def test_image_masked():
    with qt_app_context(exec_loop=True):
        win = PlotDialog(
            toolbar=True,
            wintitle="Masked image item test",
            options={"type": PlotType.IMAGE},
        )
        win.manager.add_tool(ImageMaskTool)
        if os.access(FNAME, os.R_OK):
            print("Restoring mask...", end=" ")
            iofile = open(FNAME, "rb")
            image = pickle.load(iofile)
            iofile.close()
            print("OK")
        else:
            fname = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "brain.png"
            )
            image = make.maskedimage(
                filename=fname,
                colormap="gray",
                show_mask=True,
                xdata=[0, 20],
                ydata=[0, 25],
            )
        win.manager.get_plot().add_item(image)
        win.show()

    iofile = open(FNAME, "wb")
    pickle.dump(image, iofile)


if __name__ == "__main__":
    test_image_masked()
