# coding=utf-8
from qtpy import QtWidgets, QtGui, QtCore
import maya.cmds as cmds
import pymel.core as pm
import maya.mel as mel

FK_dict = {
        # body/neck
        'pelvis':'RootX_M',
        'spine_01':'FKSpine1_M',
        'spine_02':'FKSpine2_M',
        'spine_03':'FKSpine3_M',
        'spine_04':'FKSpine4_M',
        'spine_05':'FKChest_M',
        'neck_01':'FKNeck1_M',
        'neck_02':'FKNeck2_M',
        'head':'FKHead_M',
        # arm
        'clavicle_l':'FKScapula_L',
        'upperarm_l':'FKShoulder_L',
        'lowerarm_l':'FKElbow_L',
        'hand_l':'FKWrist_L',
        # finger
        'thumb_01_l':'FKThumbFinger1_L',
        'thumb_02_l':'FKThumbFinger2_L',
        'thumb_03_l':'FKThumbFinger3_L',
        'index_metacarpal_l':'FKIndexFinger0_L',
        'index_01_l':'FKIndexFinger1_L',
        'index_02_l':'FKIndexFinger2_L',
        'index_03_l':'FKIndexFinger3_L',
        'middle_metacarpal_l':'FKMiddleFinger0_L',
        'middle_01_l':'FKMiddleFinger1_L',
        'middle_02_l':'FKMiddleFinger2_L',
        'middle_03_l':'FKMiddleFinger3_L',
        'ring_metacarpal_l':'FKRingFinger0_L',
        'ring_01_l':'FKRingFinger1_L',
        'ring_02_l':'FKRingFinger2_L',
        'ring_03_l':'FKRingFinger3_L',
        'pinky_metacarpal_l':'FKPinkyFinger0_L',
        'pinky_01_l':'FKPinkyFinger1_L',
        'pinky_02_l':'FKPinkyFinger2_L',
        'pinky_03_l':'FKPinkyFinger3_L',
        # leg
        'thigh_l':'FKHip_L',
        'calf_l':'FKKnee_L',
        'foot_l':'FKAnkle_L',
        'ball_l':'FKToes_L',

        'clavicle_r':'FKScapula_R',
        'upperarm_r':'FKShoulder_R',
        'lowerarm_r':'FKElbow_R',
        'hand_r':'FKWrist_R',
        'thumb_01_r':'FKThumbFinger1_R',
        'thumb_02_r':'FKThumbFinger2_R',
        'thumb_03_r':'FKThumbFinger3_R',
        'index_metacarpal_r':'FKIndexFinger0_R',
        'index_01_r':'FKIndexFinger1_R',
        'index_02_r':'FKIndexFinger2_R',
        'index_03_r':'FKIndexFinger3_R',
        'middle_metacarpal_r':'FKMiddleFinger0_R',
        'middle_01_r':'FKMiddleFinger1_R',
        'middle_02_r':'FKMiddleFinger2_R',
        'middle_03_r':'FKMiddleFinger3_R',
        'ring_metacarpal_r':'FKRingFinger0_R',
        'ring_01_r':'FKRingFinger1_R',
        'ring_02_r':'FKRingFinger2_R',
        'ring_03_r':'FKRingFinger3_R',
        'pinky_metacarpal_r':'FKPinkyFinger0_R',
        'pinky_01_r':'FKPinkyFinger1_R',
        'pinky_02_r':'FKPinkyFinger2_R',
        'pinky_03_r':'FKPinkyFinger3_R',
        'thigh_r':'FKHip_R',
        'calf_r':'FKKnee_R',
        'foot_r':'FKAnkle_R',
        'ball_r':'FKToes_R',
}

IK_dict = {
        'hand_l': 'IKArm_L',
        'foot_l': 'IKLeg_L',
        'ball_l': 'IKToes_L',

        'hand_r': 'IKArm_R',
        'foot_r': 'IKLeg_R',
        'ball_r': 'IKToes_R'
}

Polar_vector= {
        "lowerarm_l":"PoleArm_L",
        "lowerarm_r":"PoleArm_R",
        "calf_r":"PoleLeg_R",
        "calf_l":"PoleLeg_L"
}

class ActionRebuildWin(QtWidgets.QDialog):


    def __init__(self, parent=None):
        super(ActionRebuildWin, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setLayout(QtWidgets.QVBoxLayout())

        args_layout = QtWidgets.QFormLayout()
        self.action_asset_label = QtWidgets.QLabel(u"控制器名称空间:")
        self.action_asset_line = QtWidgets.QLineEdit()
        self.action_asset_line.setPlaceholderText(u'控制器名称空间,如果没有则不填')

        args_layout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.action_asset_label)
        args_layout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.action_asset_line)
        self.layout().addLayout(args_layout)

        _btn_layout = QtWidgets.QVBoxLayout()
        rig_btn = QtWidgets.QPushButton(u"绑定")
        bake_btn = QtWidgets.QPushButton(u"烘培")
        import_joint_btn = QtWidgets.QPushButton(u'导入模板骨骼')
        import_anim_btn = QtWidgets.QPushButton(u'导入动捕数据')
        delete_Namespace_btn = QtWidgets.QPushButton(u'删除名称空间')
        display_rig_joint = QtWidgets.QPushButton(u'显示rig层骨骼')
        hide_rig_joint = QtWidgets.QPushButton(u'隐藏rig层骨骼')
        delecte_root_data = QtWidgets.QPushButton(u'删除root数据')
        _btn_layout.addWidget(import_joint_btn)
        _btn_layout.addWidget(delete_Namespace_btn)
        _btn_layout.addWidget(rig_btn)
        _btn_layout.addWidget(import_anim_btn)
        _btn_layout.addWidget(delecte_root_data)
        _btn_layout.addWidget(bake_btn)
        _btn_layout.addWidget(display_rig_joint)
        _btn_layout.addWidget(hide_rig_joint)
        import_joint_btn.clicked.connect(self.import_joint)
        delete_Namespace_btn.clicked.connect(self.delete_Namespace)
        rig_btn.clicked.connect(self.rig)
        import_anim_btn.clicked.connect(self.import_anim)
        bake_btn.clicked.connect(self.bake)
        display_rig_joint.clicked.connect(self.displlay)
        hide_rig_joint.clicked.connect(self.hide)
        delecte_root_data.clicked.connect(self.delete_root)
        self.layout().addLayout(_btn_layout)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(args_layout)
        main_layout.addLayout(_btn_layout)
        self.setMinimumWidth(500)
        self.setWindowTitle(u'动捕数据烘培控制器')
        
    def rig(self, *args, **kwargs):

        nameSpace = self.action_asset_line.text()

        for i in FK_dict:
            mel.eval('select -r {}'.format(i))
            mel.eval('select -tgl {}'.format(nameSpace+FK_dict[i]))
            mel.eval('doCreateParentConstraintArgList 1 { "1","0","0","0","0","0","0","0","1","","1" }')
            mel.eval('parentConstraint -mo -weight 1')
            mel.eval('select -cl')

        for i in IK_dict:
            # if IK_dict[i] in ['IKLocalArmShoulder_L','IKLocalLegHip_L','IKLocalArmShoulder_R','IKLocalLegHip_R']:
            #     continue
            mel.eval('select -r {}'.format(i))
            mel.eval('select -tgl {}'.format(nameSpace+IK_dict[i]))
            mel.eval('doCreateParentConstraintArgList 1 { "1","0","0","0","0","0","0","0","1","","1" }')
            mel.eval('parentConstraint -mo -weight 1')
            mel.eval('select -cl')
    
        for i in Polar_vector:
            mel.eval('select -r {}'.format(i))
            mel.eval('select -tgl {}'.format(nameSpace+Polar_vector[i]))
            mel.eval('doCreateParentConstraintArgList 1 { "1","0","0","0","0","1","1","1","1","","1" }')
            mel.eval('parentConstraint -mo -skipRotate x -skipRotate y -skipRotate z -weight 1')
            mel.eval('select -cl')

    def bake(self, *args, **kwargs):

        start_frame = cmds.playbackOptions(q=True,ast=1)
        end_frame = cmds.playbackOptions(q=True,aet=1)
        nameSpace = self.action_asset_line.text()
        Controllerlist=[]

        for i in FK_dict:
            Controllerlist.append(nameSpace+FK_dict[i])

        for i in IK_dict:
            # if IK_dict[i] in ['IKLocalArmShoulder_L','IKLocalLegHip_L','IKLocalArmShoulder_R','IKLocalLegHip_R']:
            #     continue
            Controllerlist.append(nameSpace+IK_dict[i])

        for i in Polar_vector:
            Controllerlist.append(nameSpace+Polar_vector[i])

        cmds.bakeResults(
            Controllerlist,
            simulation=True,
            time=(start_frame,end_frame),
            sampleBy=1,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            at=["tx", "ty", "tz", "rx", "ry", "rz"]
        )
    def import_joint(self,*args, **kwargs):
        
        mel.eval('FBXProperty Import|IncludeGrp|MergeMode -v "Add"')
        print(mel.eval('FBXProperty Import|IncludeGrp|MergeMode -q'))
        a = cmds.fileDialog2(cap=u'导入模板骨骼', ds=2, ff='*fbx', okc=u'导入', fm=1)
        
        if a:
            cmds.file(a[0], 
            i=True, 
            type="FBX", 
            ignoreVersion=True, 
            ra=True, 
            mergeNamespacesOnClash=False, 
            namespace=':', 
            options="v=0",
            pr=True, 
            importFrameRate=True, 
            importTimeRange="combine")
            
    def delete_Namespace(self,*args, **kwargs):
        mel.eval('NamespaceEditor;')

    def import_anim(self,*args, **kwargs):
        mel.eval('FBXProperty Import|IncludeGrp|MergeMode -v "Add and update animation"')
        print(mel.eval('FBXProperty Import|IncludeGrp|MergeMode -q'))
        b=cmds.fileDialog2(cap=u'导入动捕数据', ds=2, ff='*fbx', okc=u'导入', fm=1)
        if b:
            cmds.file(b[0], 
            i=True, 
            type="FBX", 
            ignoreVersion=True, 
            ra=True, 
            mergeNamespacesOnClash=False, 
            namespace=':', 
            options="v=0",
            pr=True, 
            importFrameRate=True, 
            importTimeRange="combine")

    def displlay(self,*args, **kwargs):
        sl_grp = cmds.ls(sl=True)
        sl_jnt = cmds.listRelatives(sl_grp, ad=True, type='joint')
        for jnt in sl_jnt:
            cmds.setAttr(jnt + '.drawStyle', 0)

    def hide(self,*args, **kwargs):
        sl_grp = cmds.ls(sl=True)
        sl_jnt = cmds.listRelatives(sl_grp, ad=True, type='joint')
        for jnt in sl_jnt:
            cmds.setAttr(jnt + '.drawStyle', 2)

    def delete_root(self, *args, **kwargs):
        root = cmds.ls(sl=True)[0]

        if root:
            mel.eval('cutKey -cl -t ":" -f ":" -at "tx" -at "ty" -at "tz" -at "rx" -at "ry" -at "rz" -at "sx" -at "sy" -at "sz" {};'.format(root))
            cmds.setAttr(root+'.translate',0,0,0)
            cmds.setAttr(root+'.rotate',0,0,0)
        else:
            print(u'请选择root节点')

                                
def main():

    global dialog
    dialog = ActionRebuildWin()
    dialog.show()