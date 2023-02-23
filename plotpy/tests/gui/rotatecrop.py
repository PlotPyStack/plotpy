# -*- coding: utf-8 -*-
#
# Copyright © 2012 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see plotpy/__init__.py for details)

"""Rotate/crop test: using the scaler C++ engine to rotate/crop images"""


import os.path as osp

import numpy as np

from plotpy.widgets import io, qapplication
from plotpy.widgets.builder import make
from plotpy.widgets.plot.plotwidget import PlotDialog, PlotType
from plotpy.widgets.rotatecrop import (
    MultipleRotateCropWidget,
    RotateCropDialog,
    RotateCropWidget,
)

SHOW = True  # Show test in GUI-based test launcher


def imshow(data, title=None, hold=False):
    dlg = PlotDialog(wintitle=title, options={"type": PlotType.IMAGE})
    dlg.manager.get_plot().add_item(make.image(data))
    if hold:
        dlg.show()
    else:
        dlg.exec()


def create_test_data(fname, func=None):
    array0 = io.imread(osp.join(osp.dirname(__file__), fname), to_grayscale=True)
    if func is not None:
        array0 = func(array0)
    item0 = make.trimage(array0, dx=0.1, dy=0.1)
    return array0, item0


def widget_test(fname, qapp):
    """Test the rotate/crop widget"""
    _array0, item = create_test_data(fname)
    widget = RotateCropWidget(None, toolbar=True)
    widget.tools.set_item(item)
    widget.show()
    qapp.exec_()
    widget.tools.accept_changes()


def multiple_widget_test(fname, qapp):
    """Test the multiple rotate/crop widget"""
    _array0, item0 = create_test_data(fname)
    _array1, item1 = create_test_data(fname, func=lambda arr: np.rot90(arr, 1))
    _array2, item2 = create_test_data(fname, func=lambda arr: np.rot90(arr, 2))
    widget = MultipleRotateCropWidget(None)
    widget.set_items(item0, item1, item2)
    widget.show()
    qapp.exec_()
    widget.accept_changes()


def dialog_test(fname, interactive=True):
    """Test the rotate/crop dialog"""
    array0, item = create_test_data(fname)
    dlg = RotateCropDialog(None)
    dlg.tools.set_item(item)
    if interactive:
        ok = dlg.exec()
    else:
        dlg.show()
        dlg.accept()
        ok = True
    if ok:
        array1 = dlg.tools.output_array
        if array0.shape == array1.shape:
            if (array1 == array0).all() and not interactive:
                print("Test passed successfully.")
                return
            imshow(array1 - array0, title="array1-array0")
        else:
            print(array0.shape, "-->", array1.shape)
        imshow(array0, title="array0", hold=True)
        imshow(array1, title="array1")


if __name__ == "__main__":
    qapp = qapplication()  # analysis:ignore

    multiple_widget_test("brain.png", qapp)

    widget_test("brain.png", qapp)

    dialog_test(fname="brain.png", interactive=False)
    # dialog_test(fname="contrast.png", interactive=False)
    dialog_test(fname="brain.png", interactive=True)
