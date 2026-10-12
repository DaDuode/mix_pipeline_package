#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'HuangShuai'
import os
import maya.mel as mel
import maya.OpenMaya as om
import maya.cmds as cmds
def motionFbxBindPose(skinNode):
    skinObj=om.MObject()
    mSelList=om.MSelectionList()
    om.MGlobal.getSelectionListByName(skinNode,mSelList)
    mSelList.getDependNode(0,skinObj)
    mfnSkinNode=om.MFnDependencyNode(skinObj)
    bindPreMtxPlug=mfnSkinNode.findPlug('bindPreMatrix')
    infJoints=cmds.skinCluster(skinNode,q=1,inf=1)
    num=len(infJoints)
    for i in range(num):
        mtxPlug=bindPreMtxPlug.elementByLogicalIndex(i)
        plugObj=mtxPlug.asMObject()
        mfnMtxData=om.MFnMatrixData(plugObj)
        preMatrix=mfnMtxData.matrix()
        transformMatrix=om.MTransformationMatrix(preMatrix.inverse())
        translation=transformMatrix.translation(om.MSpace.kWorld)
        rotation=transformMatrix.eulerRotation()
        
        angleX=om.MAngle(rotation.x,om.MAngle.kRadians)
        angleY=om.MAngle(rotation.y,om.MAngle.kRadians)
        angleZ=om.MAngle(rotation.z,om.MAngle.kRadians)
        
        cmds.xform(infJoints[i],ws=1,t=[translation.x,translation.y,translation.z],ro=[angleX.asDegrees(),angleY.asDegrees(),angleZ.asDegrees()])
def gotoBindPose():
    tmpList=cmds.listConnections('Root_M',type='skinCluster')
    skinNodes=list(set(tmpList))
    if skinNodes:
        for i in skinNodes:
            motionFbxBindPose(i)
def get_path():
    folder_path = os.path.dirname(__file__)
    result_path = folder_path.replace('\\', '/')
    return result_path

def convertMocapToRig():
    source_file = os.path.join(get_path(),'convertMocapToRig.mel')
    result_file = source_file.replace('\\', '/')
    string_cmd = 'source "%s";%s;' % (result_file, "convertMocapToRig")
    gotoBindPose()
    mel.eval(string_cmd)