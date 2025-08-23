import os

from krita import DockWidget, DockWidgetFactory, DockWidgetFactoryBase, Extension, Krita
from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QColorDialog, QMessageBox, QVBoxLayout, QWidget

from .linalg import q_identity
from .loomis_head_generator import LoomisHead3D
from .trackball import TrackballWidget


class LoomisProportionsDocker(DockWidget):
    def __init__(self):
        super().__init__()

        self.doc = Krita.instance().activeDocument()
        self.loomis_head = LoomisHead3D()
        self.loomis_layer = None
        self.update_scheduled = False

        self.setWindowTitle("Loomis Head Controls")
        self.setMinimumSize(400, 500)
        self.connect_ui()
        self.activateWindow()
        self.create_loomis_layer()

    def canvasChanged(self, canvas):
        pass

    def with_schedule_update(self, fn):
        fn()
        self.schedule_update()

    def pick_stroke_color(self):
        old_hex = self.loomis_head.stroke_color
        old_qcolor = QColor(old_hex)

        dlg = QColorDialog(self)
        dlg.setOption(QColorDialog.DontUseNativeDialog, True)
        dlg.setCurrentColor(old_qcolor)

        def apply_color(col: QColor):
            if not col.isValid():
                return
            hex_rgb = col.name(QColor.HexRgb)
            self.loomis_head.set_stroke_color(hex_rgb)
            self.ui.strokeColorSwatch.setStyleSheet(f"background-color: {hex_rgb}; border: 1px solid #666;")
            self.schedule_update()

        dlg.currentColorChanged.connect(apply_color)
        dlg.colorSelected.connect(apply_color)

        def revert():
            self.loomis_head.set_stroke_color(old_hex)
            self.ui.strokeColorSwatch.setStyleSheet(f"background-color: {old_hex}; border: 1px solid #666;")
            self.schedule_update()

        dlg.rejected.connect(revert)
        dlg.exec_()

    def connect_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "LoomisDocker.ui")
        self.ui: QWidget = uic.loadUi(ui_path)
        self.setWidget(self.ui)

        host = self.ui.findChild(QWidget, "trackballHost")
        self.trackball = TrackballWidget(host)
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.trackball)

        self.trackball.orientation_changed.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_quaternion(v)))

        self.ui.sizeSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_scale(v * 0.01)))
        self.ui.sideCutSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_sidecut(v * 0.01)))
        self.ui.frontStrokeSlider.valueChanged.connect(
            lambda v: self.with_schedule_update(lambda: self.loomis_head.set_front_line_stroke(v))
        )
        self.ui.backStrokeSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_back_line_stroke(v)))

        self.ui.showArrow.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_arrow(v)))
        self.ui.showSilhouette.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_silhouette(v)))
        self.ui.showSideRims.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_side_rims(v)))
        self.ui.showSideCross.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_side_cross(v)))
        self.ui.strokeColorButton.clicked.connect(self.pick_stroke_color)
        self.ui.resetButton.clicked.connect(self.reset_view)
        self.ui.saveButton.clicked.connect(self.save_head)

    def schedule_update(self):
        if self.update_scheduled:
            return

        self.update_scheduled = True
        QTimer.singleShot(0, self.draw_lines_with_vectors)

    def create_loomis_layer(self):
        if self.loomis_layer:
            self.doc.rootNode().removeChildNode(self.loomis_layer)

        self.loomis_layer = self.doc.createVectorLayer("Loomis Head")
        self.doc.rootNode().addChildNode(self.loomis_layer, None)

        self.schedule_update()

    def draw_lines_with_vectors(self, samples: int = 256):
        if not self.doc or not self.loomis_layer:
            self.update_scheduled = False
            return

        svg = self.loomis_head.build_svg(
            width=self.doc.width(),
            height=self.doc.height(),
            dash_back="8,8",
            samples=samples,
        )

        for shape in self.loomis_layer.shapes():
            shape.remove()

        self.loomis_layer.addShapesFromSvg(svg)
        self.update_scheduled = False

    def reset_view(self):
        self.loomis_head.scale = 1.0
        self.trackball.reset(emit=False)
        self.loomis_head.set_quaternion(q_identity())

        self.schedule_update()

    def save_head(self):
        """
        Redrawing the head with higher accuracy.
        Can't test it on low end devices, so I may need to tone it down. 
        """

        samples = 256; """Default samples"""
        samples *= 4; """Higher rendering pass"""

        self.draw_lines_with_vectors(samples)
        self.doc = None
        self.loomis_layer = None
        self.loomis_head = None
        self.close()


class LoomisHeadPlugin(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("loomisHead", "Loomis Head", "tools/scripts")
        action.setToolTip("Create a 3D Loomis head guide")
        action.triggered.connect(self.activate_tool)

    def activate_tool(self):
        doc = Krita.instance().activeDocument()

        if not doc:
            error_box = QMessageBox()
            error_box.setWindowTitle("Error")
            error_box.setText("Can't find your canvas. Do you have one open?")
            error_box.exec()
            return

        docker_instance = LoomisProportionsDocker()

        Krita.instance().addDockWidgetFactory(
            DockWidgetFactory("myDocker", DockWidgetFactoryBase.DockPosition.DockTornOff, docker_instance)
        )

        docker_instance.show()
