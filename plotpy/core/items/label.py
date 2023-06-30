# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see plotpy/__init__.py for details)

# pylint: disable=C0103

"""
plotpy.widgets.label
------------------------

The `labels` module provides plot items related to labels and legends:
    * :py:class:`.label.LabelItem`
    * :py:class:`.label.LegendBoxItem`
    * :py:class:`.label.SelectedLegendBoxItem`
    * :py:class:`.label.RangeComputation`
    * :py:class:`.label.RangeComputation2d`
    * :py:class:`.label.DataInfoLabel`

A label or a legend is a plot item (derived from QwtPlotItem) that may be
displayed on a 2D plotting widget like :py:class:`.baseplot.BasePlot`.

Reference
~~~~~~~~~

.. autoclass:: LabelItem
   :members:
.. autoclass:: LegendBoxItem
   :members:
.. autoclass:: SelectedLegendBoxItem
   :members:
.. autoclass:: RangeComputation
   :members:
.. autoclass:: RangeComputation2d
   :members:
.. autoclass:: DataInfoLabel
   :members:
.. autoclass:: ObjectInfo
   :members:
"""

import numpy as np
from guidata.configtools import get_icon
from guidata.utils import update_dataset
from guidata.utils.misc import assert_interfaces_valid
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qwt import QwtPlotItem

from plotpy.config import CONF, _
from plotpy.core.interfaces.common import (
    IBasePlotItem,
    ISerializableType,
    IShapeItemType,
)
from plotpy.core.items.curve.base import CurveItem
from plotpy.core.styles.label import LabelParam

ANCHORS = {
    "TL": lambda r: (r.left(), r.top()),
    "TR": lambda r: (r.right(), r.top()),
    "BL": lambda r: (r.left(), r.bottom()),
    "BR": lambda r: (r.right(), r.bottom()),
    "L": lambda r: (r.left(), (r.top() + r.bottom()) / 2.0),
    "R": lambda r: (r.right(), (r.top() + r.bottom()) / 2.0),
    "T": lambda r: ((r.left() + r.right()) / 2.0, r.top()),
    "B": lambda r: ((r.left() + r.right()) / 2.0, r.bottom()),
    "C": lambda r: ((r.left() + r.right()) / 2.0, (r.top() + r.bottom()) / 2.0),
}


class AbstractLabelItem(QwtPlotItem):
    """Draws a label on the canvas at position :
    G+C where G is a point in plot coordinates and C a point
    in canvas coordinates.
    G can also be an anchor string as in ANCHORS in which case
    the label will keep a fixed position wrt the canvas rect
    """

    _readonly = False
    _private = False

    def __init__(self, labelparam=None):
        super(AbstractLabelItem, self).__init__()
        self.selected = False
        self.anchor = None
        self.G = None
        self.C = None
        self.border_pen = None
        self.bg_brush = None
        if labelparam is None:
            self.labelparam = LabelParam(_("Label"), icon="label.png")
        else:
            self.labelparam = labelparam
            self.labelparam.update_label(self)
        self._can_select = True
        self._can_resize = False
        self._can_move = True
        self._can_rotate = False

    def set_style(self, section, option):
        """

        :param section:
        :param option:
        """
        self.labelparam.read_config(CONF, section, option)
        self.labelparam.update_label(self)

    def __reduce__(self):
        return (self.__class__, (self.labelparam,))

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        self.labelparam.update_param(self)
        writer.write(self.labelparam, group_name="labelparam")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        self.labelparam = LabelParam(_("Label"), icon="label.png")
        reader.read("labelparam", instance=self.labelparam)
        self.labelparam.update_label(self)
        if isinstance(self.G, np.ndarray):
            self.G = tuple(self.G)

    def get_text_rect(self):
        """

        :return:
        """
        return QC.QRectF(0.0, 0.0, 10.0, 10.0)

    def types(self):
        """

        :return:
        """
        return (IShapeItemType,)

    def set_text_style(self, font=None, color=None):
        """

        :param font:
        :param color:
        """
        raise NotImplementedError

    def get_top_left(self, xMap, yMap, canvasRect):
        """

        :param xMap:
        :param yMap:
        :param canvasRect:
        :return:
        """
        x0, y0 = self.get_origin(xMap, yMap, canvasRect)
        x0 += self.C[0]
        y0 += self.C[1]

        rect = self.get_text_rect()
        pos = ANCHORS[self.anchor](rect)
        x0 -= pos[0]
        y0 -= pos[1]
        return x0, y0

    def get_origin(self, xMap, yMap, canvasRect):
        """

        :param xMap:
        :param yMap:
        :param canvasRect:
        :return:
        """
        if self.G in ANCHORS:
            return ANCHORS[self.G](canvasRect)
        else:
            x0 = xMap.transform(self.G[0])
            y0 = yMap.transform(self.G[1])
            return x0, y0

    def set_selectable(self, state):
        """Set item selectable state"""
        self._can_select = state

    def set_resizable(self, state):
        """Set item resizable state
        (or any action triggered when moving an handle, e.g. rotation)"""
        self._can_resize = state

    def set_movable(self, state):
        """Set item movable state"""
        self._can_move = state

    def set_rotatable(self, state):
        """Set item rotatable state"""
        self._can_rotate = state

    def can_select(self):
        """

        :return:
        """
        return self._can_select

    def can_resize(self):
        """

        :return:
        """
        return self._can_resize

    def can_move(self):
        """

        :return:
        """
        return self._can_move

    def can_rotate(self):
        """

        :return:
        """
        return False  # TODO: Implement labels rotation?

    def set_readonly(self, state):
        """Set object readonly state"""
        self._readonly = state

    def is_readonly(self):
        """Return object readonly state"""
        return self._readonly

    def set_private(self, state):
        """Set object as private"""
        self._private = state

    def is_private(self):
        """Return True if object is private"""
        return self._private

    def invalidate_plot(self):
        """ """
        plot = self.plot()
        if plot:
            plot.invalidate()

    def select(self):
        """Select item"""
        if self.selected:
            # Already selected
            return
        self.selected = True
        w = self.border_pen.width()
        self.border_pen.setWidth(w + 1)
        self.invalidate_plot()

    def unselect(self):
        """Unselect item"""
        self.selected = False
        self.labelparam.update_label(self)
        self.invalidate_plot()

    def hit_test(self, pos):
        """

        :param pos:
        :return:
        """
        plot = self.plot()
        if plot is None:
            return
        rect = self.get_text_rect()
        canvasRect = plot.canvas().contentsRect()
        xMap = plot.canvasMap(self.xAxis())
        yMap = plot.canvasMap(self.yAxis())
        x, y = self.get_top_left(xMap, yMap, canvasRect)
        rct = QC.QRectF(x, y, rect.width(), rect.height())
        inside = rct.contains(pos.x(), pos.y())
        if inside:
            return self.click_inside(pos.x() - x, pos.y() - y)
        else:
            return 1000.0, None, False, None

    def click_inside(self, locx, locy):
        """

        :param locx:
        :param locy:
        :return:
        """
        return 2.0, 1, True, None

    def update_item_parameters(self):
        """ """
        self.labelparam.update_param(self)

    def get_item_parameters(self, itemparams):
        """

        :param itemparams:
        """
        self.update_item_parameters()
        itemparams.add("LabelParam", self, self.labelparam)

    def set_item_parameters(self, itemparams):
        """

        :param itemparams:
        """
        update_dataset(self.labelparam, itemparams.get("LabelParam"), visible_only=True)
        self.labelparam.update_label(self)
        if self.selected:
            self.select()

    def move_local_point_to(self, handle, pos, ctrl=None):
        """Move a handle as returned by hit_test to the new position pos
        ctrl: True if <Ctrl> button is being pressed, False otherwise"""
        if handle != -1:
            return

    def move_local_shape(self, old_pos, new_pos):
        """Translate the shape such that old_pos becomes new_pos
        in canvas coordinates"""
        if self.G in ANCHORS or not self.labelparam.move_anchor:
            # Move canvas offset
            lx, ly = self.C
            lx += new_pos.x() - old_pos.x()
            ly += new_pos.y() - old_pos.y()
            self.C = lx, ly
            self.labelparam.xc, self.labelparam.yc = lx, ly
        else:
            # Move anchor
            plot = self.plot()
            if plot is None:
                return
            lx0, ly0 = self.G
            cx = plot.transform(self.xAxis(), lx0)
            cy = plot.transform(self.yAxis(), ly0)
            cx += new_pos.x() - old_pos.x()
            cy += new_pos.y() - old_pos.y()
            lx1 = plot.invTransform(self.xAxis(), cx)
            ly1 = plot.invTransform(self.yAxis(), cy)
            self.G = lx1, ly1
            self.labelparam.xg, self.labelparam.yg = lx1, ly1
            plot.SIG_ITEM_MOVED.emit(self, lx0, ly0, lx1, ly1)

    def move_with_selection(self, delta_x, delta_y):
        """
        Translate the shape together with other selected items
        delta_x, delta_y: translation in plot coordinates
        """
        if self.G in ANCHORS or not self.labelparam.move_anchor:
            return
        lx0, ly0 = self.G
        lx1, ly1 = lx0 + delta_x, ly0 + delta_y
        self.G = lx1, ly1
        self.labelparam.xg, self.labelparam.yg = lx1, ly1

    def draw_frame(self, painter, x, y, w, h):
        """

        :param painter:
        :param x:
        :param y:
        :param w:
        :param h:
        """
        if self.labelparam.bgalpha > 0.0:
            painter.fillRect(x, y, w, h, self.bg_brush)
        if self.border_pen.width() > 0:
            painter.setPen(self.border_pen)
            painter.drawRect(x, y, w, h)


class LabelItem(AbstractLabelItem):
    """ """

    __implements__ = (IBasePlotItem, ISerializableType)

    def __init__(self, text=None, labelparam=None):
        self.text_string = "" if text is None else text
        self.text = QG.QTextDocument()
        super(LabelItem, self).__init__(labelparam)
        self.setIcon(get_icon("label.png"))

    def __reduce__(self):
        return (self.__class__, (self.text_string, self.labelparam))

    def serialize(self, writer):
        """Serialize object to HDF5 writer"""
        super(LabelItem, self).serialize(writer)
        writer.write(self.text_string, group_name="text")

    def deserialize(self, reader):
        """Deserialize object from HDF5 reader"""
        super(LabelItem, self).deserialize(reader)
        self.set_text(reader.read("text", func=reader.read_unicode))

    def types(self):
        """

        :return:
        """
        return (IShapeItemType, ISerializableType)

    def set_pos(self, x, y):
        """

        :param x:
        :param y:
        """
        self.G = x, y
        self.labelparam.abspos = False
        self.labelparam.xg, self.labelparam.yg = x, y

    def get_plain_text(self):
        """

        :return:
        """
        return str(self.text.toPlainText())

    def set_text(self, text=None):
        """

        :param text:
        """
        if text is not None:
            self.text_string = text
        self.text.setHtml(f"<div>{self.text_string}</div>")

    def set_text_style(self, font=None, color=None):
        """

        :param font:
        :param color:
        """
        if font is not None:
            self.text.setDefaultFont(font)
        if color is not None:
            self.text.setDefaultStyleSheet("div { color: %s; }" % color)
        self.set_text()

    def get_text_rect(self):
        """

        :return:
        """
        sz = self.text.size()
        return QC.QRectF(0, 0, sz.width(), sz.height())

    def update_text(self):
        """ """
        pass

    def draw(self, painter, xMap, yMap, canvasRect):
        """

        :param painter:
        :param xMap:
        :param yMap:
        :param canvasRect:
        """
        self.update_text()
        x, y = self.get_top_left(xMap, yMap, canvasRect)
        x0, y0 = self.get_origin(xMap, yMap, canvasRect)
        painter.save()
        self.marker.drawSymbols(painter, [QC.QPointF(x0, y0)])
        painter.restore()
        sz = self.text.size()
        self.draw_frame(painter, int(x), int(y), int(sz.width()), int(sz.height()))
        painter.setPen(QG.QPen(QG.QColor(self.labelparam.color)))
        painter.translate(x, y)
        self.text.drawContents(painter)


assert_interfaces_valid(LabelItem)


LEGEND_WIDTH = 30  # Length of the sample line
LEGEND_SPACEH = 5  # Spacing between border, sample, text, border
LEGEND_SPACEV = 3  # Vertical space between items


class LegendBoxItem(AbstractLabelItem):
    """ """

    __implements__ = (IBasePlotItem, ISerializableType)

    def __init__(self, labelparam=None):
        self.font = None
        self.color = None
        super(LegendBoxItem, self).__init__(labelparam)
        # saves the last computed sizes
        self.sizes = 0.0, 0.0, 0.0, 0.0
        self.setIcon(get_icon("legend.png"))

    def types(self):
        """

        :return:
        """
        return (IShapeItemType, ISerializableType)

    def get_legend_items(self):
        """

        :return:
        """
        plot = self.plot()
        if plot is None:
            return []
        text_items = []
        for item in plot.get_items():
            if not isinstance(item, CurveItem) or not self.include_item(item):
                continue
            text = QG.QTextDocument()
            text.setDefaultFont(self.font)
            text.setDefaultStyleSheet("div { color: %s; }" % self.color)
            text.setHtml(f"<div>{item.param.label}</div>")
            text_items.append((text, item.pen(), item.brush(), item.symbol()))
        return text_items

    def include_item(self, item):
        """

        :param item:
        :return:
        """
        return item.isVisible()

    def get_legend_size(self, items):
        """

        :param items:
        :return:
        """
        width = 0
        height = 0
        for text, _, _, _ in items:
            sz = text.size()
            if sz.width() > width:
                width = sz.width()
            if sz.height() > height:
                height = sz.height()

        TW = LEGEND_SPACEH * 3 + LEGEND_WIDTH + width
        TH = len(items) * (height + LEGEND_SPACEV) + LEGEND_SPACEV
        self.sizes = TW, TH, width, height
        return self.sizes

    def set_text_style(self, font=None, color=None):
        """

        :param font:
        :param color:
        """
        if font is not None:
            self.font = font
        if color is not None:
            self.color = color

    def get_text_rect(self):
        """

        :return:
        """
        items = self.get_legend_items()
        TW, TH, _width, _height = self.get_legend_size(items)
        return QC.QRectF(0.0, 0.0, TW, TH)

    def draw(self, painter, xMap, yMap, canvasRect):
        """

        :param painter:
        :param xMap:
        :param yMap:
        :param canvasRect:
        """
        items = self.get_legend_items()
        TW, TH, _width, height = self.get_legend_size(items)

        x, y = self.get_top_left(xMap, yMap, canvasRect)
        self.draw_frame(painter, int(x), int(y), int(TW), int(TH))

        y0 = int(y + LEGEND_SPACEV)
        x0 = int(x + LEGEND_SPACEH)
        for text, ipen, ibrush, isymbol in items:
            isymbol.drawSymbols(
                painter, [QC.QPointF(x0 + LEGEND_WIDTH / 2, y0 + height / 2)]
            )
            painter.save()
            painter.setPen(ipen)
            painter.setBrush(ibrush)
            painter.drawLine(
                x0, int(y0 + height / 2), int(x0 + LEGEND_WIDTH), int(y0 + height / 2)
            )
            x1 = x0 + LEGEND_SPACEH + LEGEND_WIDTH
            painter.translate(x1, y0)
            text.drawContents(painter)
            painter.restore()
            y0 += height + LEGEND_SPACEV

    def click_inside(self, lx, ly):
        """

        :param lx:
        :param ly:
        :return:
        """
        # hit_test already called get_text_rect for us...
        _TW, _TH, _width, height = self.sizes
        line = (ly - LEGEND_SPACEV) / (height + LEGEND_SPACEV)
        line = int(line)
        if LEGEND_SPACEH <= lx <= (LEGEND_WIDTH + LEGEND_SPACEH):
            # We hit a legend line, select the corresponding curve
            # and do as if we weren't hit...
            items = [
                item
                for item in self.plot().get_items()
                if self.include_item(item) and isinstance(item, CurveItem)
            ]
            if line < len(items):
                return 1000.0, None, False, items[line]
        return 2.0, 1, True, None

    def update_item_parameters(self):
        """ """
        self.labelparam.update_param(self)

    def get_item_parameters(self, itemparams):
        """

        :param itemparams:
        """
        self.update_item_parameters()
        itemparams.add("LegendParam", self, self.labelparam)

    def set_item_parameters(self, itemparams):
        """

        :param itemparams:
        """
        update_dataset(
            self.labelparam, itemparams.get("LegendParam"), visible_only=True
        )
        self.labelparam.update_label(self)
        if self.selected:
            self.select()


assert_interfaces_valid(LegendBoxItem)


class SelectedLegendBoxItem(LegendBoxItem):
    """ """

    def __init__(self, dataset=None, itemlist=None):
        super(SelectedLegendBoxItem, self).__init__(dataset)
        self.itemlist = [] if itemlist is None else itemlist

    def __reduce__(self):
        # XXX filter itemlist for picklabel items
        return (self.__class__, (self.labelparam, []))

    def include_item(self, item):
        """

        :param item:
        :return:
        """
        return LegendBoxItem.include_item(self, item) and item in self.itemlist

    def add_item(self, item):
        """

        :param item:
        """
        self.itemlist.append(item)


class ObjectInfo(object):
    def get_text(self):
        """

        :return:
        """
        return ""


class RangeInfo(ObjectInfo):
    """ObjectInfo handling XRangeSelection shape informations: x, dx

    label: formatted string
    xrangeselection: XRangeSelection object
    function: input arguments are x, dx ; returns objects used to format the
    label. Default function is `lambda x, dx: (x, dx)`.

    Example:
    -------

    x = linspace(-10, 10, 10)
    y = sin(sin(sin(x)))
    xrangeselection = make.range(-2, 2)
    RangeInfo(u"x = %.1f ± %.1f cm", xrangeselection,
              lambda x, dx: (x, dx))
    disp = make.info_label('BL', comp, title="titre")
    """

    def __init__(self, label, xrangeselection, function=None):
        self.label = str(label)
        self.range = xrangeselection
        if function is None:
            function = lambda x, dx: (x, dx)
        self.func = function

    def get_text(self):
        """

        :return:
        """
        x0, x1 = self.range.get_range()
        x = 0.5 * (x0 + x1)
        dx = 0.5 * (x1 - x0)
        return self.label % self.func(x, dx)


class RangeComputation(ObjectInfo):
    """ObjectInfo showing curve computations relative to a XRangeSelection
    shape.

    label: formatted string
    curve: CurveItem object
    xrangeselection: XRangeSelection object
    function: input arguments are x, y arrays (extraction of arrays
    corresponding to the xrangeselection X-axis range)"""

    def __init__(self, label, curve, xrangeselection, function=None):
        self.label = str(label)
        self.curve = curve
        self.range = xrangeselection
        if function is None:
            function = lambda x, dx: (x, dx)
        self.func = function

    def set_curve(self, curve):
        """

        :param curve:
        """
        self.curve = curve

    def get_text(self):
        """

        :return:
        """
        x0, x1 = self.range.get_range()
        data = self.curve.get_data()
        X = data[0]
        i0 = X.searchsorted(x0)
        i1 = X.searchsorted(x1)
        if i0 > i1:
            i0, i1 = i1, i0
        vectors = []
        for vector in data:
            if vector is None:
                vectors.append(None)
            elif i0 == i1:
                vectors.append(np.array([np.NaN]))
            else:
                vectors.append(vector[i0:i1])
        return self.label % self.func(*vectors)


class RangeComputation2d(ObjectInfo):
    """ """

    def __init__(self, label, image, rect, function):
        self.label = str(label)
        self.image = image
        self.rect = rect
        self.func = function

    def get_text(self):
        """

        :return:
        """
        x0, y0, x1, y1 = self.rect.get_rect()
        x, y, z = self.image.get_data(x0, y0, x1, y1)
        res = self.func(x, y, z)
        return self.label % res


class DataInfoLabel(LabelItem):
    """ """

    __implements__ = (IBasePlotItem,)

    def __init__(self, labelparam=None, infos=None):
        super(DataInfoLabel, self).__init__(None, labelparam)
        if isinstance(infos, ObjectInfo):
            infos = [infos]
        self.infos = infos

    def __reduce__(self):
        return (self.__class__, (self.labelparam, self.infos))

    def types(self):
        """

        :return:
        """
        return (IShapeItemType,)

    def update_text(self):
        """ """
        title = self.labelparam.label
        if title:
            text = ["<b>%s</b>" % title]
        else:
            text = []
        for info in self.infos:
            text.append(info.get_text())
        self.set_text("<br/>".join(text))
