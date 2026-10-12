# coding=utf-8

from qtpy import QtWidgets, QtGui, QtCore
import socket
import re
import maya.cmds as cmds
import pymel.core as pmel
import maya.utils
NAMESPACE = ''
FACE_WIN = None
CONTROLLER_ATTR = []
CONTROLLER_TEMPLATE = [
    'Cnt_RBrowOuter.translateY',
    'Cnt_RBrowOuter.Turn',
    'Cnt_RBrowMiddle.translateY',
    'Cnt_RBrowMiddle.Turn',
    'Cnt_RBrowInner.translateX',
    'Cnt_RBrowInner.translateY',
    'Cnt_RBrowInner.Turn',
    'Cnt_LBrowInner.translateX',
    'Cnt_LBrowInner.translateY',
    'Cnt_LBrowInner.Turn',
    'Cnt_LBrowMiddle.translateY',
    'Cnt_LBrowMiddle.Turn',
    'Cnt_LBrowOuter.translateY',
    'Cnt_LBrowOuter.Turn',
    'Cnt_LLwrLid.translateY',
    'Cnt_LLwrLid.Turn',
    'Cnt_LLwrLid.move',
    'Cnt_LLwrLid.Corner_In_X',
    'Cnt_LLwrLid.Corner_In_Y',
    'Cnt_LLwrLid.Corner_Out_X',
    'Cnt_LLwrLid.Corner_Out_Y',
    'Cnt_LUprLid.translateY',
    'Cnt_LUprLid.Turn',
    'Cnt_LUprLid.move',
    'Cnt_RLwrLid.translateY',
    'Cnt_RLwrLid.Turn',
    'Cnt_RLwrLid.move',
    'Cnt_RLwrLid.Corner_In_X',
    'Cnt_RLwrLid.Corner_In_Y',
    'Cnt_RLwrLid.Corner_Out_X',
    'Cnt_RLwrLid.Corner_Out_Y',
    'Cnt_RUprLid.translateY',
    'Cnt_RUprLid.Turn',
    'Cnt_RUprLid.move',
    'EyeCtrl.translateX',
    'EyeCtrl.translateY',
    'EyeCtrl.translateZ',
    'EyeCtrl.absoluteAdditive',
    'Cnt_LMouthCorner.translateX',
    'Cnt_LMouthCorner.translateY',
    'Cnt_LMouthCorner.SubCorner_MoveX',
    'Cnt_LMouthCorner.SubCorner_MoveY',
    'Cnt_LMouthCorner.SubCorner_MoveZ',
    'Cnt_LMouthCorner.corner_down_stick',
    'Cnt_LMouthCorner.corner_up_stick',
    'Cnt_RMouthCorner.translateX',
    'Cnt_RMouthCorner.translateY',
    'Cnt_RMouthCorner.SubCorner_MoveX',
    'Cnt_RMouthCorner.SubCorner_MoveY',
    'Cnt_RMouthCorner.SubCorner_MoveZ',
    'Cnt_RMouthCorner.corner_down_stick',
    'Cnt_RMouthCorner.corner_up_stick',
    'Cnt_RUprLip.translateX',
    'Cnt_RUprLip.translateY',
    'Cnt_UpLip.translateY',
    'Cnt_LUprLip.translateX',
    'Cnt_LUprLip.translateY',
    'Cnt_MouthLeftRight.translateX',
    'Cnt_MouthLeftRight.translateY',
    'Cnt_MouthLeftRight.Turn',
    'Cnt_LwrLip.translateY',
    'Cnt_RLwrLip.translateX',
    'Cnt_RLwrLip.translateY',
    'Cnt_LLwrLip.translateX',
    'Cnt_LLwrLip.translateY',
    'Cnt_Chin.translateY',
    'Cnt_Jaw.translateX',
    'Cnt_Jaw.translateY',
    'Cnt_LCheekPuff.translateY',
    'Cnt_RCheekPuff.translateY',
    'Cnt_Tongue.translateX',
    'Cnt_Tongue.translateY',
    'Cnt_TongueOutIn.translateY',
    'Cnt_TongueTipUpDn.translateY',
    'Cnt_ThroatUpDn.translateY',
    'Cnt_LwrLipCurlOut.translateX',
    'Cnt_LwrLipCurlOut.translateY',
    'Cnt_LwrLipCurlIn.translateY',
    'Cnt_LwrLipSquash.translateX',
    'Cnt_LwrLipSquash.translateY',
    'Cnt_JawFwdBck.translateY',
    'Cnt_UprLipSquash.translateX',
    'Cnt_UprLipSquash.translateY',
    'Cnt_UprLipCurlIn.translateY',
    'Cnt_UprLipCurlOut.translateX',
    'Cnt_UprLipCurlOut.translateY',
    'Cnt_RCheekUp.translateY',
    'Cnt_RNose.translateX',
    'Cnt_RNose.translateY',
    'Cnt_LNose.translateX',
    'Cnt_LNose.translateY',
    'Cnt_LCheekUp.translateY'
]
class FaceArUDPListener(QtCore.QThread):
    TIME_OUT = QtCore.Signal(bool)
    stop_recv = False
    status = False
    def __init__(self, ip='127.0.0.1', port=11113):
        super(FaceArUDPListener, self).__init__()
        self._ip = ip
        self._port = port
        
    def set_ip(self, ip):
        if isinstance(ip, str) and re.match("(\d*).(\d*).(\d*).(\d*)", ip):
            self._ip = ip
        else:
            raise ValueError('IP ERROR')

    def run(self):
        if not self._ip:
            raise ValueError('ip is not set')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self._ip, self._port))
        while not self.stop_recv:
            data, addr = self.sock.recvfrom(1024*10)
            if not self.status:
                self.TIME_OUT.emit(False)
                self.status = True
            if data:
                data = data.decode('utf-8')
                data = eval(data[data.index('{'):-1])
                maya.utils.executeInMainThreadWithResult(update_anim, data, CONTROLLER_ATTR)
        try:
            self.sock.close()
        except:pass
        self.status = False


class NumberLineEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(NumberLineEdit, self).__init__(parent)
        _validator = QtGui.QRegExpValidator(QtCore.QRegExp('^\d[\d.]*'), self)
        self.setValidator(_validator)
 
             
class FaceArWin(QtWidgets.QDialog):

    def __init__(self,parent=None):
        super(FaceArWin, self).__init__(parent)
        self._title = 'VerFaceAR'
        self.setWindowTitle(self._title)
        self.isPreview = False
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        setbtn_width = 30
        setbtn_width = 30
        label_width = 85
        self.setMinimumWidth(420)
        self.setMinimumHeight(200)
        self.ip_label = QtWidgets.QLabel(u'I P 地址：')
        self.ip_label.setMinimumWidth(label_width)
        self.ip_label.setMaximumWidth(label_width)
        self.ip_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.ip_label.setEnabled(0)
        self.ip_edit = NumberLineEdit()
        self.ip_edit.setEnabled(0)
        self.ip_edit.setText('127.0.0.1')
        self.ip_set_btn = QtWidgets.QCheckBox()
        self.ip_set_btn.setMaximumWidth(setbtn_width)
        self.ip_set_btn.setMinimumWidth(setbtn_width)
        self.ip_set_btn.setCheckable(1)
        self.ip_set_btn.clicked.connect(self.on_ip_set_btn_toggled)
        ip_layout = QtWidgets.QHBoxLayout()
        ip_layout.addWidget(self.ip_label)
        ip_layout.addWidget(self.ip_edit)
        ip_layout.addWidget(self.ip_set_btn)
        ip_layout.setContentsMargins(0,0,0,0)
        ip_layout.setSpacing(4)
        self.namespace_label = QtWidgets.QLabel(u'目标资产：')
        self.namespace_label.setMinimumWidth(label_width)
        self.namespace_label.setDisabled(1)
        self.namespace_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.namespace_edit = QtWidgets.QLineEdit()
        self.namespace_edit.setEnabled(0)
        self.namespace_set_btn = QtWidgets.QCheckBox()
        self.namespace_set_btn.setMaximumWidth(setbtn_width)
        self.namespace_set_btn.setMinimumWidth(setbtn_width)
        self.namespace_set_btn.setCheckable(1)
        self.namespace_set_btn.clicked.connect(self.on_namespace_set_btn_toggled)
        namespace_set_frame_layout = QtWidgets.QHBoxLayout()
        namespace_set_frame_layout.setContentsMargins(0,0,0,0)
        namespace_set_frame_layout.setSpacing(4)
        namespace_set_frame_layout.addWidget(self.namespace_label)
        namespace_set_frame_layout.addWidget(self.namespace_edit)
        namespace_set_frame_layout.addWidget(self.namespace_set_btn)
        ###--- 连接 ---###
        self.connect_btn = QtWidgets.QPushButton(u'连接')
        self.connect_btn.clicked.connect(self.on_connect_btn_clicked)
        self.connect_btn.setEnabled(0)
        left_frame_layout = QtWidgets.QVBoxLayout(self)
        left_frame_layout.setContentsMargins(9,9,9,9)
        left_frame_layout.setSpacing(6)
        left_frame_layout.addLayout(ip_layout)
        left_frame_layout.addLayout(namespace_set_frame_layout)
        left_frame_layout.addWidget(self.connect_btn)
        self.facear_listener = FaceArUDPListener()
        self.facear_listener.TIME_OUT.connect(self.time_out)

    def time_out(self, status):
        if status:
            self.facear_listener.stop_recv = True
            self.set_connect_btn_info()
        else:
            self.facear_listener.stop_recv = False
            self.set_connect_btn_info(u'断开')
            
    def on_namespace_set_btn_toggled(self, status):
        """
        自定义名称空间
        """
        self.namespace_edit.setEnabled(status)
        self.namespace_label.setEnabled(status)
        sel_objs = pmel.ls(sl=1)
        if sel_objs:
            self.namespace_edit.setText(sel_objs[0].namespace().replace(':', ''))
        self.update_connect_btn()
    def update_connect_btn(self):
        global NAMESPACE
        global CONTROLLER_ATTR
        global CONTROLLER_TEMPLATE
        _ip = self.ip_edit.text()
        NAMESPACE = self.namespace_edit.text()
        if _ip and NAMESPACE:
            CONTROLLER_ATTR = []
            for attr in CONTROLLER_TEMPLATE:
                NAMESPACE = NAMESPACE.replace(':', '')
                _name = "{}:{}".format(NAMESPACE, attr.split('.')[0])
                if not cmds.objExists(_name):
                    self.connect_btn.setEnabled(0)
                    raise ValueError('%s not exists' % _name)
                _attr = "{}:{}".format(NAMESPACE, attr)
                CONTROLLER_ATTR.append(_attr)
            self.connect_btn.setEnabled(1)
        else:
            self.connect_btn.setEnabled(0)

    def on_ip_set_btn_toggled(self, status):
        """
        自定义ip
        """
        self.ip_edit.setEnabled(status)
        self.ip_label.setEnabled(status)
        if not status:
            self.facear_listener.set_ip(str(self.ip_edit.text()))
        self.update_connect_btn()

    def set_connect_btn_info(self, info='', enable=1):
        """
        设置连接按钮样式
        """
        color = 'rgb(255,255,255)'
        if not info:
            self.connect_btn.setText(u'连接')
            self.connect_btn.setEnabled(1)
        else:
            if enable:
                color = 'rgb(0,255,0)'
            else:
                color = 'rgb(255,255,0)'
            self.connect_btn.setText(info)
            self.connect_btn.setEnabled(enable)
        self.connect_btn.setStyleSheet('color:%s;' % str(color))
        
    def on_connect_btn_clicked(self):
        """
        连接事件
        """
        self.ip_edit.setEnabled(0)
        self.ip_label.setEnabled(0)
        self.namespace_edit.setEnabled(0)
        self.namespace_label.setEnabled(0)
        if self.facear_listener.status:
            self.facear_listener.stop_recv = True
            self.facear_listener.quit()
            self.set_connect_btn_info()
            self.namespace_set_btn.setEnabled(1)
            self.ip_set_btn.setEnabled(1)
        else:
            self.facear_listener.stop_recv = False
            self.facear_listener.start()
            self.set_connect_btn_info(u'连接中...', 0)
            self.namespace_set_btn.setEnabled(0)
            self.ip_set_btn.setEnabled(0)
    def closeEvent(self, event):
        self.facear_listener.stop_recv = True
        super(FaceArWin, self).closeEvent(event)


def update_anim(data, controllers):
    #print(data)
    for _attr, _value in zip(controllers, data['BlendShape']):
        cmds.setAttr(_attr, _value)
        


def main(*args, **kwargs):
    global FACE_WIN
    try:
        FACE_WIN.close()
        FACE_WIN.deleteLater()
    except:
        pass
    # 192.168.10.201
    FACE_WIN = FaceArWin()
    FACE_WIN.show()