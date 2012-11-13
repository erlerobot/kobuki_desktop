#!/usr/bin/env python
#       
# License: BSD
#   https://raw.github.com/yujinrobot/kobuki_desktop/master/kobuki_qtestsuite/LICENSE 
#
##############################################################################
# Imports
##############################################################################

import os
from python_qt_binding.QtCore import Signal, Slot, pyqtSlot
from python_qt_binding.QtGui import QFrame, QVBoxLayout
import math

import roslib
roslib.load_manifest('kobuki_qtestsuite')
import rospy
from qt_gui_py_common.worker_thread import WorkerThread
from rqt_plot.plot_widget import PlotWidget
from kobuki_testsuite import Rotate
from kobuki_comms.msg import RobotStateEvent

# Local resource imports
import detail.common_rc
import detail.text_rc
from detail.battery_profile_frame_ui import Ui_battery_profile_frame
from full_size_data_plot import FullSizeDataPlot

##############################################################################
# Classes
##############################################################################

class BatteryProfileFrame(QFrame):
    def __init__(self, parent=None):
        super(BatteryProfileFrame, self).__init__(parent)
        self._battery_topic_name = "/mobile_base/sensors/core/battery"
        self._ui = Ui_battery_profile_frame()
        self._motion = Rotate('/cmd_vel')
        self.robot_state_subscriber = rospy.Subscriber("/mobile_base/events/robot_state", RobotStateEvent, self.robot_state_callback)
        self._motion_thread = None

    def setupUi(self):
        self._ui.setupUi(self)
        self._plot_layout = QVBoxLayout(self._ui.battery_profile_group_box)
        self._plot_widget = PlotWidget()
        self._plot_widget.setWindowTitle("Battery Profile")
        self._plot_widget.topic_edit.setText(self._battery_topic_name)
        self._plot_layout.addWidget(self._plot_widget)
        self._plot_widget.switch_data_plot_widget(FullSizeDataPlot(self._plot_widget))
        self._ui.start_button.setEnabled(True)
        self._ui.stop_button.setEnabled(False)
        self._motion.init(self._ui.angular_speed_spinbox.value())

    def shutdown(self):
        rospy.loginfo("Kobuki TestSuite: battery test shutdown")
        self._motion.shutdown()

    ##########################################################################
    # Motion Callbacks
    ##########################################################################

    def _run_finished(self):
        self._ui.start_button.setEnabled(True)
        self._ui.stop_button.setEnabled(False)
        
    ##########################################################################
    # Qt Callbacks
    ##########################################################################
    @Slot()
    def on_start_button_clicked(self):
        self._plot_widget._start_time = rospy.get_time()
        self._plot_widget.enable_timer(True)
        try:
            self._plot_widget.remove_topic(self._battery_topic_name)
        except KeyError:
            pass
        self._plot_widget.add_topic(self._battery_topic_name)
        self._ui.start_button.setEnabled(False)
        self._ui.stop_button.setEnabled(True)
        self._motion_thread = WorkerThread(self._motion.execute, self._run_finished)
        self._motion_thread.start()

    @Slot()
    def on_stop_button_clicked(self):
        '''
          Hardcore stoppage - straight to zero.
        '''
        self.stop()
        
    def stop(self):
        self._motion.stop()
        if self._motion_thread:
            self._motion_thread.wait()
        self._plot_widget.enable_timer(False)
        self._ui.start_button.setEnabled(True)
        self._ui.stop_button.setEnabled(False)
        
    @pyqtSlot(float)
    def on_angular_speed_spinbox_valueChanged(self, value):
        self._motion.init(self._ui.angular_speed_spinbox.value())

    ##########################################################################
    # Ros Callbacks
    ##########################################################################

    def robot_state_callback(self, data):
        if data.state == RobotStateEvent.OFFLINE:
            self.stop()
