# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see plotpy/__init__.py for details)

# pylint: disable=C0103

"""
plotpy.widgets.fit
----------------------

The `fit` module provides an interactive curve fitting widget/dialog allowing:
    * to fit data manually (by moving sliders)
    * or automatically (with standard optimization algorithms
      provided by `scipy`).

Example
~~~~~~~

.. literalinclude:: ../../../tests/gui/fit.py
   :start-after: SHOW


.. image:: /images/screenshots/fit.png

Reference
~~~~~~~~~

.. autofunction:: guifit

.. autoclass:: FitDialog
   :members:
   :inherited-members:
.. autoclass:: FitParam
   :members:
   :inherited-members:
.. autoclass:: AutoFitParam
   :members:
   :inherited-members:
"""

import guidata
import numpy as np
from guidata.configtools import get_icon
from guidata.dataset.dataitems import (
    BoolItem,
    ChoiceItem,
    FloatItem,
    IntItem,
    StringItem,
)
from guidata.dataset.datatypes import DataSet
from guidata.qthelpers import (
    create_groupbox,
    exec_dialog,
    win32_fix_title_bar_background,
)
from guidata.utils import restore_dataset, update_dataset
from numpy import inf  # Do not remove this import (used by optimization funcs)
from qtpy import QtWidgets as QW
from qtpy.QtCore import Qt
from scipy.optimize import fmin, fmin_bfgs, fmin_cg, fmin_l_bfgs_b, fmin_powell, leastsq

from plotpy.config import _
from plotpy.core.builder import make
from plotpy.core.plot.base import PlotType
from plotpy.core.plot.plotwidget import SimplePlot


class AutoFitParam(DataSet):
    """Automatic fit parameters"""
    xmin = FloatItem("xmin")
    xmax = FloatItem("xmax")
    method = ChoiceItem(
        _("Method"),
        [
            ("simplex", "Simplex"),
            ("powel", "Powel"),
            ("bfgs", "BFGS"),
            ("l_bfgs_b", "L-BFGS-B"),
            ("cg", _("Conjugate Gradient")),
            ("lq", _("Least squares")),
        ],
        default="lq",
    )
    err_norm = StringItem(
        "enorm",
        default=2.0,
        help=_("for simplex, powel, cg and bfgs norm used " "by the error function"),
    )
    xtol = FloatItem(
        "xtol", default=0.0001, help=_("for simplex, powel, least squares")
    )
    ftol = FloatItem(
        "ftol", default=0.0001, help=_("for simplex, powel, least squares")
    )
    gtol = FloatItem("gtol", default=0.0001, help=_("for cg, bfgs"))
    norm = StringItem(
        "norm", default="inf", help=_("for cg, bfgs. inf is max, -inf is min")
    )


class FitParamDataSet(DataSet):
    """Fit parameter dataset"""
    name = StringItem(_("Name"))
    value = FloatItem(_("Value"), default=0.0)
    min = FloatItem(_("Min"), default=-1.0)
    max = FloatItem(_("Max"), default=1.0).set_pos(col=1)
    steps = IntItem(_("Steps"), default=5000)
    format = StringItem(_("Format"), default="%.3f").set_pos(col=1)
    logscale = BoolItem(_("Logarithmic"), _("Scale"))
    unit = StringItem(_("Unit"), default="").set_pos(col=1)


class FitParam:
    """Fit parameters"""

    def __init__(
        self,
        name,
        value,
        min,
        max,
        logscale=False,
        steps=5000,
        format="%.3f",
        size_offset=0,
        unit="",
    ):
        self.name = name
        self.value = value
        self.min = min
        self.max = max
        self.logscale = logscale
        self.steps = steps
        self.format = format
        self.unit = unit
        self.prefix_label = None
        self.lineedit = None
        self.unit_label = None
        self.slider = None
        self.button = None
        self._widgets = []
        self._size_offset = size_offset
        self._refresh_callback = None
        self.dataset = FitParamDataSet(title=_("Curve fitting parameter"))

    def copy(self):
        """Return a copy of this fitparam"""
        return self.__class__(
            self.name,
            self.value,
            self.min,
            self.max,
            self.logscale,
            self.steps,
            self.format,
            self._size_offset,
            self.unit,
        )

    def create_widgets(self, parent, refresh_callback):
        """Create widgets

        :param parent:
        :param refresh_callback:
        """
        self._refresh_callback = refresh_callback
        self.prefix_label = QW.QLabel()
        font = self.prefix_label.font()
        font.setPointSize(font.pointSize() + self._size_offset)
        self.prefix_label.setFont(font)
        self.button = QW.QPushButton()
        self.button.setIcon(get_icon("settings.png"))
        self.button.setToolTip(
            _("Edit '{name}' fit parameter properties").format(name=self.name)
        )
        self.button.clicked.connect(lambda: self.edit_param(parent))
        self.lineedit = QW.QLineEdit()
        self.lineedit.editingFinished.connect(self.line_editing_finished)
        self.unit_label = QW.QLabel(self.unit)
        self.slider = QW.QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setRange(0, self.steps - 1)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.update(refresh=False)
        self.add_widgets(
            [
                self.prefix_label,
                self.lineedit,
                self.unit_label,
                self.slider,
                self.button,
            ]
        )

    def add_widgets(self, widgets):
        """Add widgets

        :param widgets:
        """
        self._widgets += widgets

    def get_widgets(self):
        """Get widgets

        :return:
        """
        return self._widgets

    def set_scale(self, state):
        """Set scale

        :param state:
        """
        self.logscale = state > 0
        self.update_slider_value()

    def set_text(self, fmt=None):
        """Set text

        :param fmt:
        """
        style = "<span style='color: #444444'><b>{}</b></span>"
        self.prefix_label.setText(style.format(self.name))
        if self.value is None:
            value_str = ""
        else:
            if fmt is None:
                fmt = self.format
            value_str = fmt % self.value
        self.lineedit.setText(value_str)
        self.lineedit.setDisabled(bool(self.value == self.min and self.max == self.min))

    def line_editing_finished(self):
        """Line editing finished"""
        try:
            self.value = float(self.lineedit.text())
        except ValueError:
            self.set_text()
        self.update_slider_value()
        self._refresh_callback()

    def slider_value_changed(self, int_value):
        """Slider value changed

        :param int_value:
        """
        if self.logscale:
            total_delta = np.log10(1 + self.max - self.min)
            self.value = (
                self.min + 10 ** (total_delta * int_value / (self.steps - 1)) - 1
            )
        else:
            total_delta = self.max - self.min
            self.value = self.min + total_delta * int_value / (self.steps - 1)
        self.set_text()
        self._refresh_callback()

    def update_slider_value(self):
        """Update slider value"""
        if self.value is None or self.min is None or self.max is None:
            self.slider.setEnabled(False)
            if self.slider.parent() and self.slider.parent().isVisible():
                self.slider.show()
        elif self.value == self.min and self.max == self.min:
            self.slider.hide()
        else:
            self.slider.setEnabled(True)
            if self.slider.parent() and self.slider.parent().isVisible():
                self.slider.show()
            if self.logscale:
                value_delta = max([np.log10(1 + self.value - self.min), 0.0])
                total_delta = np.log10(1 + self.max - self.min)
            else:
                value_delta = self.value - self.min
                total_delta = self.max - self.min
            intval = int(self.steps * value_delta / total_delta)
            self.slider.blockSignals(True)
            self.slider.setValue(intval)
            self.slider.blockSignals(False)

    def edit_param(self, parent):
        """Edit param

        :param parent:
        """
        update_dataset(self.dataset, self)
        if self.dataset.edit(parent=parent):
            restore_dataset(self.dataset, self)
            if self.value > self.max:
                self.max = self.value
            if self.value < self.min:
                self.min = self.value
            self.update()

    def update(self, refresh=True):
        """Update

        :param refresh:
        """
        self.unit_label.setText(self.unit)
        self.slider.setRange(0, self.steps - 1)
        self.update_slider_value()
        self.set_text()
        if refresh:
            self._refresh_callback()


def add_fitparam_widgets_to(
    layout, fitparams, refresh_callback, param_cols=1, stretch_col=1
):
    """Add fitparam widgets to layout

    :param layout:
    :param fitparams:
    :param refresh_callback:
    :param param_cols:
    """
    row_contents = []
    row_nb = 0
    col_nb = 0
    for i, param in enumerate(fitparams):
        param.create_widgets(layout.parent(), refresh_callback)
        widgets = param.get_widgets()
        w_colums = len(widgets) + 1
        row_contents += [
            (widget, row_nb, j + col_nb * w_colums) for j, widget in enumerate(widgets)
        ]
        col_nb += 1
        if col_nb == param_cols:
            row_nb += 1
            col_nb = 0
    for widget, row, col in row_contents:
        layout.addWidget(widget, row, col)
    if fitparams:
        for col_nb in range(param_cols):
            layout.setColumnStretch(stretch_col + col_nb * w_colums, 5)
            if col_nb > 0:
                layout.setColumnStretch(col_nb * w_colums - 1, 1)


class FitWidgetTools(SimplePlot):
    """Fit widget tools"""

    def __init__(
        self,
        parent=None,
        wintitle="plotpy plot",
        icon="plotpy.svg",
        toolbar=False,
        options=None,
        panels=None,
        param_cols=1,
        legend_anchor="TR",
        auto_fit=True,
    ):
        self.parent = parent
        if wintitle is None:
            wintitle = _("Curve fitting")

        self.x = None
        self.y = None
        self.fitfunc = None
        self.fitargs = None
        self.fitkwargs = None
        self.fitparams = None
        self.autofit_prm = None

        self.data_curve = None
        self.fit_curve = None
        self.legend = None
        self.legend_anchor = legend_anchor
        self.xrange = None
        self.show_xrange = False

        self.param_cols = param_cols
        self.auto_fit_enabled = auto_fit
        self.button_list = []  # list of buttons to be disabled at startup

        self.fit_layout = None
        self.params_layout = None

        SimplePlot.__init__(
            self,
            parent=self.parent,
            wintitle=wintitle,
            icon=icon,
            toolbar=toolbar,
            options=options,
            panels=panels,
        )

        self.refresh()

    # QWidget API --------------------------------------------------------------
    def resizeEvent(self, event):
        """Reimplement Qt method

        :param event:
        """
        QW.QWidget.resizeEvent(self, event)
        self.get_plot().replot()

    # PlotWidgetMixin API -----------------------------------------------------
    def setup_widget_layout(self):
        """Setup widget layout"""
        self.fit_layout = QW.QHBoxLayout()
        self.params_layout = QW.QGridLayout()
        params_group = create_groupbox(
            self.parent, _("Fit parameters"), layout=self.params_layout
        )
        if self.auto_fit_enabled:
            auto_group = self.create_autofit_group()
            self.fit_layout.addWidget(auto_group)
        self.fit_layout.addWidget(params_group)
        self.plot_layout.addLayout(self.fit_layout, 1, 0)

        parent = self.parent
        vlayout = QW.QVBoxLayout(parent)
        vlayout.addWidget(self.toolbar)
        vlayout.addLayout(self.plot_layout)
        parent.setLayout(vlayout)

    def create_plot(self, options):
        """Create plot

        :param options:
        """
        SimplePlot.create_plot(self, options)
        for plot in self.get_plots():
            plot.SIG_RANGE_CHANGED.connect(self.range_changed)

    # Public API ---------------------------------------------------------------
    def set_data(
        self, x, y, fitfunc=None, fitparams=None, fitargs=None, fitkwargs=None
    ):
        """Set data

        :param x:
        :param y:
        :param fitfunc:
        :param fitparams:
        :param fitargs:
        :param fitkwargs:
        """
        if self.fitparams is not None and fitparams is not None:
            self.clear_params_layout()
        self.x = x
        self.y = y
        if fitfunc is not None:
            self.fitfunc = fitfunc
        if fitparams is not None:
            self.fitparams = fitparams
        if fitargs is not None:
            self.fitargs = fitargs
        if fitkwargs is not None:
            self.fitkwargs = fitkwargs
        self.autofit_prm = AutoFitParam(title=_("Automatic fitting options"))
        self.autofit_prm.xmin = x.min()
        self.autofit_prm.xmax = x.max()
        self.compute_imin_imax()
        if self.fitparams is not None and fitparams is not None:
            self.populate_params_layout()
        self.refresh()

    def set_fit_data(self, fitfunc, fitparams, fitargs=None, fitkwargs=None):
        """Set fit data

        :param fitfunc:
        :param fitparams:
        :param fitargs:
        :param fitkwargs:
        """
        if self.fitparams is not None:
            self.clear_params_layout()
        self.fitfunc = fitfunc
        self.fitparams = fitparams
        self.fitargs = fitargs
        self.fitkwargs = fitkwargs
        self.populate_params_layout()
        self.refresh()

    def clear_params_layout(self):
        """Clear params layout"""
        for i, param in enumerate(self.fitparams):
            for widget in param.get_widgets():
                if widget is not None:
                    self.params_layout.removeWidget(widget)
                    widget.hide()

    def populate_params_layout(self):
        """Populate params layout"""
        add_fitparam_widgets_to(
            self.params_layout, self.fitparams, self.refresh, param_cols=self.param_cols
        )

    def create_autofit_group(self):
        """Create autofit group

        :return:
        """
        parent = self.parent
        auto_button = QW.QPushButton(get_icon("apply.png"), _("Run"), parent)
        auto_button.clicked.connect(self.autofit)
        autoprm_button = QW.QPushButton(get_icon("settings.png"), _("Settings"), parent)
        autoprm_button.clicked.connect(self.edit_parameters)
        xrange_button = QW.QPushButton(get_icon("xrange.png"), _("Bounds"), parent)
        xrange_button.setCheckable(True)
        xrange_button.toggled.connect(self.toggle_xrange)
        auto_layout = QW.QVBoxLayout()
        auto_layout.addWidget(auto_button)
        auto_layout.addWidget(autoprm_button)
        auto_layout.addWidget(xrange_button)
        self.button_list += [auto_button, autoprm_button, xrange_button]
        return create_groupbox(parent, _("Automatic fit"), layout=auto_layout)

    def get_fitfunc_arguments(self):
        """Return fitargs and fitkwargs"""
        fitargs = self.fitargs
        if self.fitargs is None:
            fitargs = []
        fitkwargs = self.fitkwargs
        if self.fitkwargs is None:
            fitkwargs = {}
        return fitargs, fitkwargs

    def refresh(self, slider_value=None):
        """Refresh Fit Tool dialog box"""
        # Update button states
        enable = (
            self.x is not None
            and self.y is not None
            and self.x.size > 0
            and self.y.size > 0
            and self.fitfunc is not None
            and self.fitparams is not None
            and len(self.fitparams) > 0
        )
        for btn in self.button_list:
            btn.setEnabled(enable)

        if not enable:
            # Fit widget is not yet configured
            return

        fitargs, fitkwargs = self.get_fitfunc_arguments()
        yfit = self.fitfunc(
            self.x, [p.value for p in self.fitparams], *fitargs, **fitkwargs
        )

        plot = self.get_plot()

        if self.legend is None:
            self.legend = make.legend(anchor=self.legend_anchor)
            plot.add_item(self.legend)

        if self.xrange is None:
            self.xrange = make.range(0.0, 1.0)
            plot.add_item(self.xrange)
        self.xrange.set_range(self.autofit_prm.xmin, self.autofit_prm.xmax)
        self.xrange.setVisible(self.show_xrange)

        if self.data_curve is None:
            self.data_curve = make.curve([], [], _("Data"), color="b", linewidth=2)
            plot.add_item(self.data_curve)
        self.data_curve.set_data(self.x, self.y)

        if self.fit_curve is None:
            self.fit_curve = make.curve([], [], _("Fit"), color="r", linewidth=2)
            plot.add_item(self.fit_curve)
        self.fit_curve.set_data(self.x, yfit)

        plot.replot()
        plot.disable_autoscale()

    def range_changed(self, xrange_obj, xmin, xmax):
        """Range changed

        :param xrange_obj:
        :param xmin:
        :param xmax:
        """
        self.autofit_prm.xmin, self.autofit_prm.xmax = xmin, xmax
        self.compute_imin_imax()

    def toggle_xrange(self, state):
        """Toggle xrange visibility

        :param state:
        """
        self.xrange.setVisible(state)
        plot = self.get_plot()
        plot.replot()
        if state:
            plot.set_active_item(self.xrange)
        self.show_xrange = state

    def edit_parameters(self):
        """Edit fit parameters"""
        if self.autofit_prm.edit(parent=self):
            self.xrange.set_range(self.autofit_prm.xmin, self.autofit_prm.xmax)
            plot = self.get_plot()
            plot.replot()
            self.compute_imin_imax()

    def compute_imin_imax(self):
        """Compute i_min and i_max"""
        self.i_min = self.x.searchsorted(self.autofit_prm.xmin)
        self.i_max = self.x.searchsorted(self.autofit_prm.xmax, side="right")

    def errorfunc(self, params):
        """Get error function

        :param params:
        :return:
        """
        x = self.x[self.i_min : self.i_max]
        y = self.y[self.i_min : self.i_max]
        fitargs, fitkwargs = self.get_fitfunc_arguments()
        return y - self.fitfunc(x, params, *fitargs, **fitkwargs)

    def autofit(self):
        """Autofit

        :return:
        """
        meth = self.autofit_prm.method
        x0 = np.array([p.value for p in self.fitparams])
        if meth == "lq":
            x = self.autofit_lq(x0)
        elif meth == "simplex":
            x = self.autofit_simplex(x0)
        elif meth == "powel":
            x = self.autofit_powel(x0)
        elif meth == "bfgs":
            x = self.autofit_bfgs(x0)
        elif meth == "l_bfgs_b":
            x = self.autofit_l_bfgs(x0)
        elif meth == "cg":
            x = self.autofit_cg(x0)
        else:
            return
        for v, p in zip(x, self.fitparams):
            p.value = v
        self.refresh()
        for prm in self.fitparams:
            prm.update()

    def get_norm_func(self):
        """Get norm function

        :return:
        """
        prm = self.autofit_prm
        err_norm = eval(prm.err_norm)

        def func(params):
            """

            :param params:
            :return:
            """
            err = np.linalg.norm(self.errorfunc(params), err_norm)
            return err

        return func

    def autofit_simplex(self, x0):
        """Autofit using simplex

        :param x0:
        :return:
        """
        prm = self.autofit_prm

        x = fmin(self.get_norm_func(), x0, xtol=prm.xtol, ftol=prm.ftol)
        return x

    def autofit_powel(self, x0):
        """Autofit using Powell

        :param x0:
        :return:
        """
        prm = self.autofit_prm

        x = fmin_powell(self.get_norm_func(), x0, xtol=prm.xtol, ftol=prm.ftol)
        return x

    def autofit_bfgs(self, x0):
        """Autofit using BFGS

        :param x0:
        :return:
        """
        prm = self.autofit_prm

        x = fmin_bfgs(self.get_norm_func(), x0, gtol=prm.gtol, norm=eval(prm.norm))
        return x

    def autofit_l_bfgs(self, x0):
        """Autofit using L-BFGS-B

        :param x0:
        :return:
        """
        prm = self.autofit_prm
        bounds = [(p.min, p.max) for p in self.fitparams]

        x, _f, _d = fmin_l_bfgs_b(
            self.get_norm_func(), x0, pgtol=prm.gtol, approx_grad=1, bounds=bounds
        )
        return x

    def autofit_cg(self, x0):
        """Autofit using conjugate gradient

        :param x0:
        :return:
        """
        prm = self.autofit_prm

        x = fmin_cg(self.get_norm_func(), x0, gtol=prm.gtol, norm=eval(prm.norm))
        return x

    def autofit_lq(self, x0):
        """Autofit using leastsq

        :param x0:
        :return:
        """
        prm = self.autofit_prm

        def func(params):
            """

            :param params:
            :return:
            """
            err = self.errorfunc(params)
            return err

        x, _ier = leastsq(func, x0, xtol=prm.xtol, ftol=prm.ftol)
        return x

    def get_values(self):
        """Convenience method to get fit parameter values"""
        return [param.value for param in self.fitparams]


class FitWidget(QW.QWidget):
    """Fit widget"""

    def __init__(
        self,
        wintitle=None,
        icon="plotpy.svg",
        toolbar=False,
        options=None,
        parent=None,
        panels=None,
        param_cols=1,
        legend_anchor="TR",
        auto_fit=False,
    ):
        super().__init__(parent)
        self.tools = FitWidgetTools(
            self,
            parent=self,
            wintitle=wintitle,
            icon=icon,
            toolbar=toolbar,
            options=options,
            panels=panels,
            param_cols=param_cols,
            legend_anchor=legend_anchor,
            auto_fit=auto_fit,
        )


class FitDialog(QW.QDialog):
    """Fit dialog box"""

    def __init__(
        self,
        wintitle=None,
        icon="plotpy.svg",
        edit=True,
        toolbar=False,
        options=None,
        parent=None,
        panels=None,
        param_cols=1,
        legend_anchor="TR",
        auto_fit=False,
    ):
        super().__init__(parent)
        win32_fix_title_bar_background(self)
        self.edit = edit
        self.button_layout = None
        self.tools = FitWidgetTools(
            parent=self,
            wintitle=wintitle,
            icon=icon,
            toolbar=toolbar,
            options=options,
            panels=panels,
            param_cols=param_cols,
            legend_anchor=legend_anchor,
            auto_fit=auto_fit,
        )
        self.setWindowFlags(Qt.Window)

    def setup_widget_layout(self):
        """Setup widget layout"""
        self.tools.setup_widget_layout(self)
        if self.edit:
            self.install_button_layout()

    def install_button_layout(self):
        """Install button box"""
        bbox = QW.QDialogButtonBox(QW.QDialogButtonBox.Ok | QW.QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        self.button_list += [bbox.button(QW.QDialogButtonBox.Ok)]

        self.button_layout = QW.QHBoxLayout()
        self.button_layout.addStretch()
        self.button_layout.addWidget(bbox)

        vlayout = self.layout()
        vlayout.addSpacing(10)
        vlayout.addLayout(self.button_layout)


def guifit(
    x,
    y,
    fitfunc,
    fitparams,
    fitargs=None,
    fitkwargs=None,
    wintitle=None,
    title=None,
    xlabel=None,
    ylabel=None,
    param_cols=1,
    auto_fit=True,
    winsize=None,
    winpos=None,
):
    """GUI-based curve fitting tool"""
    _app = guidata.qapplication()
    win = FitDialog(
        edit=True,
        wintitle=wintitle,
        toolbar=True,
        param_cols=param_cols,
        auto_fit=auto_fit,
        options=dict(title=title, xlabel=xlabel, ylabel=ylabel, type=PlotType.CURVE),
    )
    win.tools.set_data(x, y, fitfunc, fitparams, fitargs, fitkwargs)
    if winsize is not None:
        win.resize(*winsize)
    if winpos is not None:
        win.move(*winpos)
    if exec_dialog(win):
        return win.get_values()


if __name__ == "__main__":
    x = np.linspace(-10, 10, 1000)
    y = np.cos(1.5 * x) + np.random.rand(x.shape[0]) * 0.2

    def fit(x, params):
        """

        :param x:
        :param params:
        :return:
        """
        a, b = params
        return np.cos(b * x) + a

    a = FitParam("Offset", 1.0, 0.0, 2.0)
    b = FitParam("Frequency", 1.05, 0.0, 10.0, logscale=True)
    params = [a, b]
    values = guifit(x, y, fit, params, auto_fit=True)
    print(values)
    print([param.value for param in params])
