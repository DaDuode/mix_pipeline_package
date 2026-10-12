#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'ShenMeng'


import os
import shutil
import traceback

import maya.cmds as cmds
import pymel.core as pmel

try:
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaUI as omui
except:
    import maya.OpenMaya as om
    import maya.OpenMayaUI as omui


def version_error(need_version):
    cmds.confirmDialog(
        icon='critical',
        title='软件版本错误（KMOKE）',
        message='将强制关闭软件！！当前版本和要求版本不一致：  \n    当前版本：%s\n    要求版本：%s' % (
            current_version(), need_version), button=['确定'])
    shutdown()


def current_version(need_version=''):
    if '.' in need_version:
        return cmds.about(v=1)
    return cmds.about(v=1).split('.')[0]


def current_scene():
    return cmds.file(q=1, sn=1)


def current_fps():
    FPS = {
        '2fps': 2,
        '3fps': 3,
        '4fps': 4,
        '5fps': 5,
        '6fps': 6,
        '8fps': 8,
        '10fps': 10,
        '12fps': 12,
        'game': 15,
        '16fps': 16,
        '20fps': 20,
        '23.976fps': 23.976,
        'film': 24,
        'pal': 25,
        '29.97fps': 29.97,
        '29.97df': 29.97,
        'ntsc': 30,
        '40fps': 40,
        '47.952fps': 47.952,
        'show': 48,
        'palf': 50,
        '59.94fps': 59.94,
        'ntscf': 60,
        '75fps': 75,
        '80fps': 80,
        '100fps': 100,
        '120fps': 120
    }
    _fps = str(cmds.currentUnit(q=1, t=1))
    return FPS[_fps]


def current_camera():
    mview = omui.M3dView()
    active_view = mview.active3dView()
    dagpath = om.MDagPath()
    active_view.getCamera(dagpath)
    cam_shape = dagpath.fullPathName()
    cam_node = pmel.PyNode(cam_shape)
    return cam_node


def shutdown():
    cmds.quit(f=1)


def open(path, workspace=None):
    if not workspace:
        workspace = os.path.dirname(path)
    cmds.workspace(workspace, openWorkspace=True)
    cmds.file(new=True, force=True)
    cmds.file(path, open=True, force=True, ignoreVersion=True)


def new(context=None, workspace=None):
    if workspace:
        cmds.workspace(workspace, openWorkspace=True)
    cmds.file(newFile=True, force=True)
    cmds.upAxis(axis='y', rv=1)
    if context:
        init_scene(context)


def save(path=None, workspace=None):
    if not path:
        cmds.file(save=True, force=True)
        return
    _dir = os.path.dirname(path)
    if not os.path.isdir(_dir):
        os.makedirs(_dir)
    if not workspace:
        workspace = os.path.dirname(path)
    cmds.workspace(workspace, openWorkspace=True)
    cmds.workspace(fileRule = ["sourceImages","sourceimages"])
    cmds.workspace(fileRule = ["3dPaintTextures","sourceimages/3dPaintTextures"])
    cmds.workspace(saveWorkspace = True)
    if cmds.file(q=1, sn=1):
        cmds.file(s=1, f=1)
    cmds.file(rn=path)
    if path.endswith('.mb'):
        cmds.file(s=1, f=1, type="mayaBinary")
    else:
        cmds.file(s=1, f=1, type="mayaAscii")


def copy_scene(path):
    cmds.file(save=True, force=True)
    _current_scene = current_scene()
    is_save_as = False
    try:
        src_name, src_post = os.path.splitext(_current_scene)
        tag_name, tag_post = os.path.splitext(path)
        if src_post == tag_post:
            shutil.copy2(_current_scene, path)
        else:
            is_save_as = True
            save(path)
        all_palettes = cmds.ls(type="xgmPalette")
        for palette in all_palettes:
            src_xgen = "{0}_{1}.xgen".format(src_name, palette)
            tag_xgen = "{0}_{1}.xgen".format(tag_name, palette)
            shutil.copy2(src_xgen, tag_xgen)
    except:
        raise IOError(traceback.format_exc())
    finally:
        if is_save_as:
            save(_current_scene)


def create_reference(filePath, namespace):
    pmel.system.createReference(filePath,
                                loadReferenceDepth="all",
                                mergeNamespacesOnClash=False,
                                namespace=namespace)


def init_scene(context, is_lock=False):
    if context.Entity['type'].lower() != 'asset':
        return
    if context.Step['code'].lower() != 'model':
        if context.Step['code'].lower() in ['afx']:
            if context.Task['code'].lower().endswith('groom'):
                for group_name in ['XGen_hair','XGen_eyebrow','XGen_eyelash','XGen_whiskers']:
                    make_group([
                            "XGenTransfer",
                            "XGen_head",
                            group_name
                        ])
                for group_name in ['XGen_torso','XGen_hand','XGen_foot','XGen_tail']:
                    make_group([
                            "XGenTransfer",
                            "XGen_body",
                            group_name
                        ])
                for group_name in ['head_XGenMesh_grp','body_XGenMesh_grp']:
                    make_group([
                            "bakeUvModel_grp",
                            group_name,
                        ])
            return

    asset_type = context.Entity['asset_type'].lower()
    asset_name = context.Entity['code']
    if asset_type.lower() == 'charactertype':
        make_group([
            "model",
            asset_name,
            "head_mesh_grp",
            "{}_Unfreeze".format(asset_name)
        ])
        make_group([
            "model",
            asset_name,
            "body_mesh_grp",
            "{}_Unfreeze".format(asset_name)
        ])
        make_group([
            "model",
            asset_name,
            "cloth_mesh_grp",
            "{}_Unfreeze".format(asset_name)
        ])
        make_group([
            "model",
            asset_name,
            "style3D_mesh_grp",
            "{}_Unfreeze".format(asset_name)
        ])
    else:
        make_group([
            "model",
            asset_name,
            "{}_Unfreeze".format(asset_name)
        ],
            is_lock=is_lock)
    make_group([
        "model",
        "{}_Other_Grp".format(asset_name),
        "{}_Vfx".format(asset_name)
    ],
        is_lock=is_lock)
    make_group([
        "model",
        "{}_Other_Grp".format(asset_name),
        "{}_Low".format(asset_name)
    ],
        is_lock=is_lock)


def make_group(nameList, children=None, is_lock=False):
    """
    """
    createList = []
    parentGroup = ''
    groupName = '|{}'.format('|'.join(nameList))
    if cmds.objExists(groupName):
        cmds.parent(children, groupName)
        return groupName
    for name in nameList:
        createList.append(name)
        groupName = '|{}'.format('|'.join(createList))
        if not cmds.objExists(groupName):
            if not parentGroup:
                _group = cmds.group(em=1, name=createList[-1])

            else:
                _group = cmds.group(
                    em=1, name=createList[-1], parent=parentGroup)
            if is_lock:
                cmds.lockNode(_group)
        parentGroup = groupName
    if children:
        cmds.parent(children, parentGroup)
    return parentGroup
