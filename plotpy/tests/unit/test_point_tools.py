from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, Union

import numpy as np
import qtpy.QtCore as QC
import qtpy.QtGui as QG
import qtpy.QtWidgets as QW
from guidata.qthelpers import exec_dialog, qt_app_context

from plotpy.interfaces.items import ICurveItemType, IItemType
from plotpy.panels.base import PanelWidget
from plotpy.plot.plotwidget import PlotDialog, PlotWindow
from plotpy.tests import vistools as ptv
from plotpy.tests.features.test_auto_curve_image import make_curve_image_legend
from plotpy.tools import (
    CommandTool,
    EditPointTool,
    InteractiveTool,
    SelectPointsTool,
    SelectPointTool,
)
from plotpy.tools.curve import DownSamplingTool

if TYPE_CHECKING:

    from plotpy.items.curve.base import CurveItem
    from plotpy.items.image.base import BaseImageItem

CLICK = (QC.QEvent.Type.MouseButtonPress, QC.QEvent.Type.MouseButtonRelease)
ToolT = TypeVar("ToolT", bound=Union[InteractiveTool, CommandTool])


def keyboard_event(
    win: PlotDialog,
    qapp: QW.QApplication,
    key: QC.Qt.Key,
    mod=QC.Qt.KeyboardModifier.NoModifier,
):
    """Simulates a keyboard event on the plot.

    Args:
        win: window containing the plot
        qapp: Main QApplication instance
        key: Key to simulate
        mod: Keyboard modifier. Defaults to QC.Qt.KeyboardModifier.NoModifier.

    Returns:
        None
    """
    plot = win.manager.get_plot()
    canva: QW.QWidget = plot.canvas()  # type: ignore
    key_event = QG.QKeyEvent(QC.QEvent.Type.KeyPress, key, mod)
    qapp.sendEvent(canva, key_event)


def mouse_event_at_relative_plot_pos(
    win: PlotDialog,
    qapp: QW.QApplication,
    relative_xy: tuple[float, float],
    click_types: tuple[QC.QEvent.Type, ...] = (QC.QEvent.Type.MouseButtonPress,),
    mod=QC.Qt.KeyboardModifier.NoModifier,
) -> None:
    """Simulates a click on the plot at the given relative position.

    Args:
        win: window containing the plot
        qapp: Main QApplication instance
        relative_xy: Relative position of the click on the plot
        click_types: Different mouse button event types to send.
         Defaults to (QC.QEvent.Type.MouseButtonPress,).
        mod: Keyboard modifier. Defaults to QC.Qt.KeyboardModifier.NoModifier.

    Returns:
        None
    """
    plot = win.manager.get_plot()

    plot = win.manager.get_plot()
    canva: QW.QWidget = plot.canvas()  # type: ignore
    size = canva.size()
    pos_x, pos_y = (
        relative_xy[0] * size.width(),
        relative_xy[1] * size.height(),
    )
    # pos_x, pos_y = axes_to_canvas(plot.get_active_item(), x, y)
    canva_pos = QC.QPointF(pos_x, pos_y).toPoint()
    glob_pos = canva.mapToGlobal(canva_pos)
    # QTest.mouseClick(canva, QC.Qt.MouseButton.LeftButton, mod, canva_pos)

    for type_ in click_types:
        mouse_event_press = QG.QMouseEvent(
            type_,
            canva_pos,
            glob_pos,
            QC.Qt.MouseButton.LeftButton,
            QC.Qt.MouseButton.LeftButton,
            mod,
        )
        qapp.sendEvent(canva, mouse_event_press)


def drag_mouse(
    win: PlotWindow,
    qapp: QW.QApplication,
    x_path: np.ndarray,
    y_path: np.ndarray,
    mod=QC.Qt.KeyboardModifier.NoModifier,
    click=True,
) -> None:
    x0, y0 = x_path[0], y_path[0]
    xn, yn = x_path[-1], y_path[-1]
    press = (QC.QEvent.Type.MouseButtonPress,)
    move = (QC.QEvent.Type.MouseMove,)
    release = (QC.QEvent.Type.MouseButtonRelease,)

    if click:
        mouse_event_at_relative_plot_pos(win, qapp, (x0, y0), press, mod)
    for x, y in zip(x_path, y_path):
        mouse_event_at_relative_plot_pos(win, qapp, (x, y), move, mod)
    if click:
        mouse_event_at_relative_plot_pos(win, qapp, (xn, yn), release, mod)


def create_window(
    tool_class: type[ToolT],
    active_item_type: type[IItemType] = ICurveItemType,
    panels: list[type[PanelWidget]] | None = None,
) -> tuple[PlotWindow, ToolT]:

    items: list[CurveItem | BaseImageItem] = make_curve_image_legend()
    win = ptv.show_items(items, wintitle="Unit test plot", auto_tools=False)
    plot = win.manager.get_plot()
    for item in win.manager.get_plot().get_items()[::-1]:
        plot.set_active_item(item)
    last_active_item = plot.get_last_active_item(active_item_type)
    plot.set_active_item(last_active_item)

    if panels is not None:
        for panel in panels:
            win.manager.add_panel(panel())

    tool = win.manager.add_tool(tool_class)
    tool.activate()
    return win, tool


def test_free_select_point_tool():
    with qt_app_context(exec_loop=False) as qapp:
        win, tool = create_window(SelectPointTool)
        mouse_event_at_relative_plot_pos(
            win,
            qapp,
            (0.5, 0.5),
            CLICK,
        )
        assert tool.get_coordinates() is not None
        exec_dialog(win)


def test_contrained_select_point_tool():
    with qt_app_context(exec_loop=False) as qapp:
        win, tool = create_window(SelectPointTool)
        tool.on_active_item = True
        mouse_event_at_relative_plot_pos(
            win,
            qapp,
            (0.5, 0.5),
            CLICK,
        )
        assert tool.get_coordinates() is not None
        exec_dialog(win)


def test_select_points_tool():
    with qt_app_context(exec_loop=False) as qapp:
        win, tool = create_window(tool_class=SelectPointsTool)
        mod = QC.Qt.KeyboardModifier.ControlModifier

        mouse_event_at_relative_plot_pos(win, qapp, (0.4, 0.5), CLICK, mod)
        assert len(tool.get_coordinates() or ()) == 1

        mouse_event_at_relative_plot_pos(win, qapp, (0.5, 0.5), CLICK, mod)
        mouse_event_at_relative_plot_pos(win, qapp, (0.6, 0.5), CLICK, mod)
        assert len(tool.get_coordinates() or ()) == 3

        mouse_event_at_relative_plot_pos(win, qapp, (0.6, 0.5), CLICK, mod)
        assert len(tool.get_coordinates() or ()) == 2

        mouse_event_at_relative_plot_pos(win, qapp, (0.7, 0.5), CLICK, mod)
        assert len(tool.get_coordinates() or ()) == 3

        mouse_event_at_relative_plot_pos(win, qapp, (0.1, 0.1), CLICK)
        assert len(tool.get_coordinates() or ()) == 1

        exec_dialog(win)


def test_edit_point_tool():
    with qt_app_context(exec_loop=False) as qapp:
        win, tool = create_window(EditPointTool)
        curve_item: CurveItem = win.manager.get_plot().get_active_item()  # type: ignore
        orig_x, orig_y = curve_item.get_data()

        assert orig_x is not None and orig_y is not None
        orig_x, orig_y = orig_x.copy(), orig_y.copy()

        assert tool is not None

        # must activate downsampling because the curve is too dense so the selection
        # distance threshold is too small for the programmed drag to select the first
        # point
        curve_item.param.dsamp_factor = 20
        win.manager.add_tool(DownSamplingTool).activate()
        # The steps must be very small to ensure the mouse passes close
        # enough to the first point of the curve to move it (distance < threshold)
        n = 1000
        min_v, max_v = 0, 1
        x_path = np.full(n, min_v)
        y_path = np.linspace(max_v, min_v, n)
        drag_mouse(win, qapp, x_path, y_path)

        x_path = np.full(n, max_v)

        drag_mouse(win, qapp, x_path, y_path)
        curve_changes = tool.get_changes()[curve_item]
        for i, (x, y) in curve_changes.items():
            x_arr, y_arr = curve_item.get_data()
            assert x == x_arr[i]
            assert y == y_arr[i]

        tool.get_arrays()
        tool.get_initial_arrays()

        keyboard_event(
            win, qapp, QC.Qt.Key.Key_Z, QC.Qt.KeyboardModifier.ControlModifier
        )

        assert len(curve_changes) == 0

        restored_x, restored_y = curve_item.get_data()
        assert restored_x is not None and restored_y is not None
        assert np.allclose(orig_x, restored_x)
        assert np.allclose(orig_y, restored_y)

        mouse_event_at_relative_plot_pos(win, qapp, (0.5, 0.5), CLICK)
        tool.trigger_insert_point_at_selection()

        new_x, new_y = curve_item.get_data()
        assert len(new_x) == len(orig_x) + 1 and len(new_y) == len(orig_y) + 1

        tool.reset_arrays()
        assert tool.get_changes() == {}
        x_arr, y_arr = curve_item.get_data()
        assert np.in1d(x_arr, orig_x).all() and np.in1d(y_arr, orig_y).all()

        exec_dialog(win)


if __name__ == "__main__":
    test_free_select_point_tool()
    test_contrained_select_point_tool()
    test_select_points_tool()
    test_edit_point_tool()
