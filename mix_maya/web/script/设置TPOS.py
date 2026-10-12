import maya.cmds as cmds
import maya.mel as mel

def main():
    
    result = cmds.promptDialog(
        title='Set_TPOS',
        message='Input the TPOS frame:',
        button=['OK', 'Cancel'],
        defaultButton='OK',
        cancelButton='Cancel',
        dismissString='Cancel',
        
    )
      
    if result == 'OK':
        TPOS_frame = int(cmds.promptDialog(q=1))
    else:
        return 
      
    current_start_frame = cmds.playbackOptions(q=1,minTime=1)
    set_TPOS_frame = current_start_frame - 50 
    cmds.playbackOptions(minTime=set_TPOS_frame)
      
    cmds.currentTime(TPOS_frame)
    cmds.select(cmds.ls(type='joint'))
    mel.eval('timeSliderCopyKey')
    cmds.currentTime(set_TPOS_frame)
    mel.eval('timeSliderPasteKey flase;') 
    
    cmds.cutKey(clear=1, iub=False, an="objects", t=(set_TPOS_frame+1, current_start_frame), o="keys")
    cmds.select(clear=1) 
    
    for i in cmds.ls(type = 'joint'):
        if 'pelvis' in i or 'root' in i :
            cmds.select(i)
            cmds.currentTime(current_start_frame)
            mel.eval('timeSliderCopyKey')
            cmds.currentTime(set_TPOS_frame)
            mel.eval('timeSliderPasteKey flase;')
            cmds.select(clear=1)