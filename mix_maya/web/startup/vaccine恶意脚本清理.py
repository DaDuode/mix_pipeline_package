import pymel.core as pmel
import os
import maya.cmds as cmds


def clear_vaccine():
    all_script = pmel.ls(type='script')
    for script in all_script:
        if script.name().endswith('vaccine_gene') or script.name().endswith('breed_gene'):
            script.before.set('')
            pmel.delete(script)
    root = os.path.join(cmds.internalVar(userAppDir=True),
                        'scripts').replace('\\', '/')
    for _name in ['vaccine.py', 'vaccine.pyc', 'userSetup.py']:
        _file = os.path.join(root, _name).replace('\\', '/')
        if os.path.isfile(_file):
            os.remove(_file)


def main():
    cmds.scriptJob(e=['PostSceneRead', clear_vaccine])
    cmds.scriptJob(e=['SceneOpened', clear_vaccine])
    clear_vaccine()
