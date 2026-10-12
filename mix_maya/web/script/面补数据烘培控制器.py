# coding=utf-8


from qtpy import QtWidgets, QtGui, QtCore
import os
import re
import functools

FPS_DATA = {}
FPS_DATA['24'] = '24fps'
FPS_DATA['25'] = '25fps'
FPS_DATA['30'] = '30fps'
FPS_DATA['60'] = '60fps'


FACE_LIST = [
'BrowDownLeft',
'BrowDownRight',
'BrowInnerUp',
'BrowOuterUpLeft',
'BrowOuterUpRight',
'CheekPuff',
'CheekSquintLeft',
'CheekSquintRight',
'EyeBlinkLeft',
'EyeBlinkRight',
'EyeLookDownLeft',
'EyeLookDownRight',
'EyeLookInLeft',
'EyeLookInRight',
'EyeLookOutLeft',
'EyeLookOutRight',
'EyeLookUpLeft',
'EyeLookUpRight',
'EyeSquintLeft',
'EyeSquintRight',
'EyeWideLeft',
'EyeWideRight',
'JawForward',
'JawLeft',
'JawOpen',
'JawRight',
'MouthClose',
'MouthDimpleLeft',
'MouthDimpleRight',
'MouthFrownLeft',
'MouthFrownRight',
'MouthFunnel',
'MouthLeft',
'MouthLowerDownLeft',
'MouthLowerDownRight',
'MouthPressLeft',
'MouthPressRight',
'MouthPucker',
'MouthRight',
'MouthRollLower',
'MouthRollUpper',
'MouthShrugLower',
'MouthShrugUpper',
'MouthSmileLeft',
'MouthSmileRight',
'MouthStretchLeft',
'MouthStretchRight',
'MouthUpperUpLeft',
'MouthUpperUpRight',
'NoseSneerLeft',
'NoseSneerRight'
]
FACE_MAPPING = {
    'EyeBlinkLeft':{
        'Cnt_LUprLid.translateY':-0.5
    },
    'EyeLookDownLeft':{
        'L_EyeCtrl.translateY':-10

    },
    'EyeLookInLeft':{
        'L_EyeCtrl.translateX':-10
    },
    'EyeLookOutLeft':{
        'L_EyeCtrl.translateX':10
    },
    'EyeLookUpLeft':{
        'L_EyeCtrl.translateY':10
    },
    'EyeSquintLeft':{
        'Cnt_LLwrLid.translateY':0.5
    },
    'EyeWideLeft':{
        'Cnt_LUprLid.translateY':0.5
    },
    'EyeBlinkRight':{
        'Cnt_RUprLid.translateY':-0.5
    },
    'EyeLookDownRight':{
        'R_EyeCtrl.translateY':-10
    },
    'EyeLookInRight':{
        'R_EyeCtrl.translateX':10
    },
    'EyeLookOutRight':{
        'R_EyeCtrl.translateX':-10
    },
    'EyeLookUpRight':{
        'R_EyeCtrl.translateY':10
    },
    'EyeSquintRight':{
        'Cnt_RLwrLid.translateY':0.5
    },
    'EyeWideRight':{
        'Cnt_RUprLid.translateY':0.5
    },
    'JawForward':{
        'Cnt_JawFwdBck.translateY':-1
    },
    'JawLeft':{
        'Cnt_Jaw.translateX':1
    },
    'JawRight':{
        'Cnt_Jaw.translateX':-1

    },
    'JawOpen':{
        'Cnt_Jaw.translateY':-2

    },
    'MouthClose':{
        'Cnt_Jaw.translateY':-0.015,
        'Cnt_Chin.translateY':-1

    },
    'MouthFunnel':{
        'Cnt_UprLipCurlOut.translateX':1,
        'Cnt_UprLipCurlOut.translateY':0.505,
        'Cnt_LwrLipCurlOut.translateX':1,
        'Cnt_LwrLipCurlOut.translateY':0.505,
        'Cnt_LUprLip.translateY':0.184,
        'Cnt_RUprLip.translateY':0.184,
        'Cnt_LLwrLip.translateY':-0.255,
        'Cnt_RLwrLip.translateY':-0.255,

    },
    'MouthPucker':{
        'Cnt_UprLipCurlOut.translateX':1,
        'Cnt_LwrLipCurlOut.translateX':1

    },
    'MouthLeft':{
        'Cnt_MouthLeftRight.translateX':1

    },
    'MouthRight':{
        'Cnt_MouthLeftRight.translateX':-1

    },
    'MouthSmileLeft':{
        'Cnt_LMouthCorner.translateX':0.5,
        'Cnt_LMouthCorner.translateY':0.5,
        'Cnt_LNose.translateY':1,
        'Cnt_LCheekUp.translateY':1

    },
    'MouthSmileRight':{
        'Cnt_RMouthCorner.translateX':-0.5,
        'Cnt_RMouthCorner.translateY':0.5,
        'Cnt_RNose.translateY':1,
        'Cnt_RCheekUp.translateY':1

    },
    'MouthFrownLeft':{
        'Cnt_LMouthCorner.translateY':-0.5,
        'Cnt_LLwrLip.translateY':-0.1

    },
    'MouthFrownRight':{
        'Cnt_RMouthCorner.translateY':-0.5,
        'Cnt_RLwrLip.translateY':-0.1

    },
    'MouthDimpleLeft':{
        'Cnt_LMouthCorner.translateX':0.5,
        'Cnt_LMouthCorner.translateY':0.2

    },
    'MouthDimpleRight':{
        'Cnt_RMouthCorner.translateX':-0.5,
        'Cnt_RMouthCorner.translateY':0.2

    },
    'MouthStretchLeft':{
        'Cnt_LMouthCorner.translateX':0.5,
        'Cnt_LMouthCorner.translateY':-0.5,
        'Cnt_LLwrLip.translateY':-0.2

    },
    'MouthStretchRight':{
        'Cnt_RMouthCorner.translateX':-0.5,
        'Cnt_RMouthCorner.translateY':-0.5,
        'Cnt_RLwrLip.translateY':-0.2

    },
    'MouthRollLower':{
        'Cnt_LwrLipCurlIn.translateY':1

    },
    'MouthRollUpper':{
        'Cnt_UprLipCurlIn.translateY':1

    },
    'MouthShrugLower':{
        'Cnt_LwrLip.translateY':0.3,
        'Cnt_RLwrLip.translateY':0.3,
        'Cnt_LLwrLip.translateY':0.3

    },
    'MouthShrugUpper':{
        'Cnt_UpLip.translateY':0.3,
        'Cnt_RUprLip.translateY':0.3,
        'Cnt_LUprLip.translateY':0.3

    },
    'MouthPressLeft':{
        'Cnt_LMouthCorner.translateX':-0.5,
        'Cnt_LUprLip.translateY':-0.2,
        'Cnt_LLwrLip.translateY':0.2,
        'Cnt_UpLip.translateY':-0.1,
        'Cnt_LwrLip.translateY':0.1

    },
    'MouthPressRight':{
        'Cnt_RMouthCorner.translateX':0.5,
        'Cnt_RUprLip.translateY':-0.2,
        'Cnt_RLwrLip.translateY':0.2,
        'Cnt_UpLip.translateY':-0.1,
        'Cnt_LwrLip.translateY':0.1

    },
    'MouthLowerDownLeft':{
        'Cnt_LLwrLip.translateY':-0.5

    },
    'MouthLowerDownRight':{
        'Cnt_RLwrLip.translateY':-0.5

    },
    'MouthUpperUpLeft':{
        'Cnt_LUprLip.translateY':0.5,
        'Cnt_LNose.translateY':1

    },
    'MouthUpperUpRight':{
        'Cnt_RUprLip.translateY':0.5,
        'Cnt_RNose.translateY':1

    },
    'BrowDownLeft':{
        'Cnt_LBrowInner.translateX':-1,
        'Cnt_LBrowInner.translateY':-1,
        'Cnt_LBrowInner.Turn':100,
        'Cnt_LBrowMiddle.translateY':-1,
        'Cnt_LBrowMiddle.Turn':-100,
        'Cnt_LBrowOuter.translateY':-1,
        'Cnt_LBrowOuter.Turn':-100

    },
    'BrowDownRight':{
        'Cnt_RBrowInner.translateX':1,
        'Cnt_RBrowInner.translateY':-1,
        'Cnt_RBrowInner.Turn':100,
        'Cnt_RBrowMiddle.translateY':-1,
        'Cnt_RBrowMiddle.Turn':-100,
        'Cnt_RBrowOuter.translateY':-1,
        'Cnt_RBrowOuter.Turn':-100

    },
    'BrowInnerUp':{
        'Cnt_LBrowInner.translateX':-1,
        'Cnt_LBrowInner.translateY':1,
        'Cnt_LBrowInner.Turn':100,
        'Cnt_RBrowInner.translateX':1,
        'Cnt_RBrowInner.translateY':1,
        'Cnt_RBrowInner.Turn':100

    },
    'BrowOuterUpLeft':{
        'Cnt_LBrowMiddle.translateY':1,
        'Cnt_LBrowMiddle.Turn':100,
        'Cnt_LBrowOuter.translateY':1,
        'Cnt_LBrowOuter.Turn':100

    },
    'BrowOuterUpRight':{
        'Cnt_RBrowMiddle.translateY':1,
        'Cnt_RBrowMiddle.Turn':100,
        'Cnt_RBrowOuter.translateY':1,
        'Cnt_RBrowOuter.Turn':100

    },
    'CheekPuff':{
        'Cnt_LCheekPuff.translateY':-1,
        'Cnt_RCheekPuff.translateY':-1

    },
    'CheekSquintLeft':{
        'Cnt_LCheekUp.translateY':1

    },
    'CheekSquintRight':{
        'Cnt_RCheekUp.translateY':1

    },
    'NoseSneerLeft':{
        'Cnt_LNose.translateX':-0.5,
        'Cnt_LNose.translateY':1

    },
    'NoseSneerRight':{
        'Cnt_RNose.translateX':0.5,
        'Cnt_RNose.translateY':1

    },
    'TongueOut':{
        'Cnt_Tongue.translateY':0.2,
        'Cnt_TongueOutIn.translateY':1
    }
}
class FaceRebuildWin(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(FaceRebuildWin, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        args_layout = QtWidgets.QFormLayout()

        _lay = QtWidgets.QHBoxLayout()
        face_data_label = QtWidgets.QLabel(u"面补数据文件:")
        self.face_data_line = QtWidgets.QLineEdit()
        self.face_data_line.setPlaceholderText(u'面补数据txt文件')
        face_data_btn = QtWidgets.QPushButton(u"浏览...")

        face_data_btn.clicked.connect(functools.partial(
                self.pick_file,  self.face_data_line))
        _lay.addWidget(self.face_data_line)
        _lay.addWidget(face_data_btn)
        args_layout.setWidget(0, QtWidgets.QFormLayout.LabelRole, face_data_label)
        args_layout.setLayout(0, QtWidgets.QFormLayout.FieldRole, _lay)

        # 
        # _lay = QtWidgets.QHBoxLayout()
        # face_mapping_label = QtWidgets.QLabel(u"控制器映射文件:")
        # self.face_mapping_line = QtWidgets.QLineEdit()
        # self.face_mapping_line.setPlaceholderText(u'请选择控制器映射txt文件')
        # face_mapping_btn = QtWidgets.QPushButton(u"浏览...")

        # face_mapping_btn.clicked.connect(functools.partial(
        #         self.pick_file,  self.face_mapping_line))
        # _lay.addWidget(self.face_mapping_line)
        # _lay.addWidget(face_mapping_btn)
        # args_layout.setWidget(1, QtWidgets.QFormLayout.LabelRole, face_mapping_label)
        # args_layout.setLayout(1, QtWidgets.QFormLayout.FieldRole, _lay)


        _lay = QtWidgets.QHBoxLayout()
        self.face_asset_label = QtWidgets.QLabel(u"角色名称空间:")
        self.face_asset_line = QtWidgets.QLineEdit()
        self.face_asset_line.setPlaceholderText(u'角色名称空间,如果没有则不填')
        args_layout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.face_asset_label)
        args_layout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.face_asset_line)


        _lay = QtWidgets.QHBoxLayout()
        self.face_fps_label = QtWidgets.QLabel(u"帧率:")
        self.face_fps_line = QtWidgets.QLineEdit()
        self.face_fps_line.setText('30')
        args_layout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.face_fps_label)
        args_layout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.face_fps_line)

        close_btn = QtWidgets.QPushButton(u"关闭")
        ok_btn = QtWidgets.QPushButton(u"解算")
        _btn_layout = QtWidgets.QHBoxLayout()
        _btn_layout.addWidget(close_btn)
        _btn_layout.addWidget(ok_btn)
        ok_btn.clicked.connect(self.main)
        close_btn.clicked.connect(self.close)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(args_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(_btn_layout)
        self.setMinimumWidth(500)
        self.setWindowTitle(u'面补数据烘培控制器')
        

    def main(self, *args, **kwargs):
        self.progress_bar.setValue(0)
        import maya.cmds as cmds
        # mapping_file = self.face_mapping_line.text()
        data_file = self.face_data_line.text()
        # if not mapping_file.endswith('.txt') or not data_file.endswith('.txt') :
        #     return
        # if not os.path.isfile(mapping_file) or not os.path.isfile(data_file):
        #     return
        fps = self.face_fps_line.text()
        if not fps:
            return
        if not fps in FPS_DATA:
            return
        
        cmds.currentUnit(t=FPS_DATA[fps])
        fps = int(fps)
        namespace = self.face_asset_line.text()
        # print(namespace)
        # face_list = []
        face_data = []
        # with open(mapping_file) as f:
        #     for i in f.readlines():
        #         face_list.append(i.replace('\n', ''))
        with open(data_file) as f:
            for i in f.readlines():
                face_data.append(i.replace('\n', ''))
        cmds.autoKeyframe(state=1)
        ctrl_count = len(FACE_LIST)
        self.progress_bar.setMaximum(len(face_data))
        start_frame = 0
        _start_frame = 0
        end_frame = 0
        for _index, _data in enumerate(face_data):
            blend_shape_data = eval(_data[_data.index('{'):_data.index('}')+1])['BlendShape']
            mat = re.match('<ref(\d*)\+\+aaaa1\+\+(.*)\+\+{"BlendShape"(.*)', _data)
            if mat:
                h, m, s,ms = mat.groups()[1].split(' ')[-1].split(':')
                # frame = int(int(h)*60*60*fps + int(m)*60*fps + int(s)*fps+ fps*float(ms)/1000)
                frame = int(int(h)*60*60*fps + int(m)*60*fps + int(s)*fps+ int(ms))
                if start_frame ==0:
                    start_frame = frame
                    _start_frame = frame
                else:
                    end_frame = frame
                    _start_frame += 1
                # cmds.currentTime(frame)
                cmds.currentTime(_start_frame)
                temp_attr = {}
                ctr_obj = []
                for i, v in enumerate(blend_shape_data):
                    if i >= ctrl_count:
                        break
                    _name = FACE_LIST[i].strip()
                    ctrs = FACE_MAPPING.get(_name)
                    if not ctrs:
                        continue
                    if namespace:
                        namespace.replace(':', '')
                    for ctr in ctrs:
                        _v = ctrs[ctr]
                        if namespace:
                            ctr = "{}:{}".format(namespace, ctr)
                        if ctr in temp_attr:
                            temp_attr[ctr] += _v*(v/1.0)
                        else:
                            temp_attr[ctr] = _v*(v/1.0)
                        ctr_obj.append(ctr.split('.')[0])
                            # cmds.setAttr(ctr, _v*(v/1.0))
                            # cmds.refresh()
                            # cmds.setKeyframe(ctr) 
                for _ctr in temp_attr:
                    try:
                        cmds.setAttr(_ctr, temp_attr[_ctr])
                    except Exception as e:
                        print('{} set error: {}'.format(_ctr, str(v)))
                ctr_obj = list(set(ctr_obj))
                cmds.setKeyframe([i for i in ctr_obj if cmds.objExists(i)], breakdown=0, preserveCurveShape=0, hierarchy=0, controlPoints=0, shape=0)
            self.progress_bar.setValue(_index+1)
        cmds.playbackOptions(aet=_start_frame, ast=start_frame, min=start_frame, max=_start_frame)
    def pick_file(self, line_edit):
        self.progress_bar.setValue(0)
        his_path = 'C:/'
        _path = line_edit.text()
        if _path:
            _root = os.path.dirname(_path)
            if os.path.isdir(_root):
                his_path = _root
        file_dialog = QtWidgets.QFileDialog(self, directory=his_path, filter='Text files(*.txt)')
        root_path, _ = file_dialog.getOpenFileName()
        if root_path and os.path.isfile(root_path):
            line_edit.setText(root_path)
FACE_REBUILD_WIN = None
def main():
    global FACE_REBUILD_WIN
    try:
        FACE_REBUILD_WIN.close()
        FACE_REBUILD_WIN.deleteLater()
    except:
        pass
    FACE_REBUILD_WIN = FaceRebuildWin()
    FACE_REBUILD_WIN.show()



