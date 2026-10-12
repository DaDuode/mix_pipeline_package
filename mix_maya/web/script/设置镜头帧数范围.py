import mix_toolkit.api
import maya.cmds as cmds

def main():
    context = mix_toolkit.api.get_current_engine().context
    start_frame = context.Entity['cut_in']# cutIn
    end_frame = context.Entity['cut_out']# cutOut

    cmds.playbackOptions(ast=start_frame, aet=end_frame)
