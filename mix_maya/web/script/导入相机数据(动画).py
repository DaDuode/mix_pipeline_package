import os
import maya.cmds as cmds
from qtpy import QtWidgets, QtCore,QtGui

class ImportFBXDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ImportFBXDialog, self).__init__(parent)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setWindowTitle("Import FBX")
        self.setFixedSize(300, 200)
        self.create_widgets()
        self.create_layouts()
    
    def create_widgets(self):
       
        self.filepath_edit = QtWidgets.QLineEdit()
        self.browse_button = QtWidgets.QPushButton("1.Browse")
        self.import_button = QtWidgets.QPushButton("2.Import")
        self.run_cutkey_button = QtWidgets.QPushButton("3.run_cutkey")
        self.time_range_button = QtWidgets.QPushButton("4.run_timeChange")
        self.custom_timechange_button = QtWidgets.QPushButton("5.custom_timeChange")
        self.custom_changetime_number_lineditor = QtWidgets.QLineEdit()
        self.custom_changetime_number_lineditor.setPlaceholderText(u'请先输入 自定义挪动帧数')
        self.custom_changetime_number_lineditor.setValidator(QtGui.QIntValidator())


        self.browse_button.clicked.connect(self.browse_file)
        self.import_button.clicked.connect(self.import_file)
        self.run_cutkey_button.clicked.connect(self.run_cutkey)
        self.time_range_button.clicked.connect(self.run_timeChange)
        self.custom_timechange_button.clicked.connect(self.run_custom_timechange)
    def create_layouts(self):
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.filepath_edit)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.import_button)
        layout.addWidget(self.run_cutkey_button)
        layout.addWidget(self.time_range_button)
        self.custom_changetime_layout =QtWidgets.QHBoxLayout()
        self.custom_changetime_layout.addWidget(self.custom_changetime_number_lineditor)
        self.custom_changetime_layout.addWidget(self.custom_timechange_button)
        layout.addLayout(self.custom_changetime_layout)
    
    def browse_file(self):
        fbx_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select FBX file", u"D:/Ver_Cache/Frame_range/Cam_fbx", "FBX files (*.fbx)")
        if fbx_file:
            self.filepath_edit.setText(fbx_file)
    
    def import_file(self):
        source_cameras = cmds.listCameras()
        fbx_file = self.filepath_edit.text()
        if fbx_file:
            camera_nodes = cmds.file(
                fbx_file,
                type="FBX",
                i=True,
                returnNewNodes = True,
                ignoreVersion=True,
                renameAll=True,
                namespace=":",
                mergeNamespacesOnClash=False,
                preserveReferences=True,
                force=True,
                buildLoadSettings = True,
                importTimeRange = 'override',
                importFrameRate = True)
                
                
            list_camera = cmds.listCameras()
            for i in source_cameras:
                list_camera.remove(i)
            print(list_camera)
            if len(list_camera) == 1:
                if not cmds.objExists(os.path.basename(fbx_file).split('.')[0]):       
                    cmds.rename(list_camera[0],os.path.basename(fbx_file).split('.')[0])
                    self.camera=os.path.basename(fbx_file).split('.')[0].replace('(','_').replace(')','_')
                else:
                    cmds.delete(os.path.basename(fbx_file).split('.')[0])
                    cmds.rename(list_camera[0],os.path.basename(fbx_file).split('.')[0])
                    self.camera=os.path.basename(fbx_file).split('.')[0]
            else:
                raise ValueError('camera not find')
           


                     
    def run_cutkey(self):
        
        fbx_file = self.filepath_edit.text()      
        start = int(os.path.basename(fbx_file).split('_Cam')[1].split('_')[1])
        end = int(os.path.basename(fbx_file).split('_Cam')[1].split('_')[2].split('.')[0])
        
        self.start = start
        self.end = end
        print(start)
        print(end)
      
        attributes = ['translateX', 'translateY', 'translateZ', 
                    'rotateX', 'rotateY', 'rotateZ', 
                    'scaleX', 'scaleY', 'scaleZ','focusDistance']
        keyframes = set()
        for attr in attributes:
           
            attr_name = self.camera + '.' + attr
        
            keys = cmds.keyframe(attr_name, query=True)
            if keys:
                keyframes.update(keys)
        keyframe_list = sorted(keyframes)
        self.offset =  0 - start
        cmds.select(self.camera)
        cmds.cutKey(clear=1, iub=False, an='objects', t=(keyframe_list[0]-100,start) ,o='keys')
        cmds.select(self.camera)
        cmds.cutKey(clear=1, iub=False, an='objects', t=(end+1, keyframe_list[-1]+100) ,o='keys')
    def run_timeChange(self):
        cmds.select(self.camera)
        cmds.keyframe(edit=True, relative=True, timeChange=self.offset)
        start_time = cmds.playbackOptions( animationStartTime=0)
        start_time = cmds.playbackOptions( minTime=0)
        end_time = cmds.playbackOptions(animationEndTime=self.offset+self.end)
        end_time = cmds.playbackOptions(maxTime=self.offset+self.end)
    def run_custom_timechange(self):
        data = self.custom_changetime_number_lineditor.text()
        if data:
            cmds.keyframe(edit=True, relative=True, timeChange=int(data))


       


def main():
    global DIALOG
    try:
        DIALOG.close()
    except Exception as e:
        print(str(e))
    DIALOG = ImportFBXDialog()
    DIALOG.show()