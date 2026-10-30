# -*- coding: utf-8 -*-
"""Maya adapter for task-driven file operations (Maya 2024, no PyMEL required)."""
import json
import os
import re
import shutil

import maya.cmds as cmds


class SceneModifiedError(RuntimeError):
    """Opening/newing a scene would discard unsaved edits."""


def current_version(need_version=''):
    """Return the actual installed version, never the requested sentinel value."""
    actual = str(cmds.about(version=True))
    if '.' in str(need_version):
        parts = [str(cmds.about(majorVersion=True)), str(cmds.about(minorVersion=True)), str(cmds.about(patchVersion=True))]
        return '.'.join(parts[:len(str(need_version).split('.'))])
    return actual


def version_matches(required):
    required = str(required or '').strip()
    if required.lower() in ('', 'latest', 'default', 'none'):
        return True
    return current_version(required) == required


def version_error(need_version):
    raise RuntimeError('Maya version mismatch: running {}, required {}'.format(current_version(need_version), need_version))


def current_scene():
    return cmds.file(query=True, sceneName=True) or ''


def current_fps():
    unit = cmds.currentUnit(query=True, time=True)
    aliases = {'game': 15, 'film': 24, 'pal': 25, 'ntsc': 30, 'show': 48, 'palf': 50, 'ntscf': 60,
               '23.976fps': 23.976, '29.97fps': 29.97, '29.97df': 29.97, '47.952fps': 47.952, '59.94fps': 59.94}
    if unit in aliases:
        return aliases[unit]
    if str(unit).endswith('fps'):
        return float(unit[:-3])
    raise ValueError('Unrecognized Maya time unit: ' + str(unit))


def current_camera():
    """Return the current model panel's camera transform as a full DAG path."""
    if cmds.about(batch=True):
        return None
    candidates = [cmds.getPanel(withFocus=True), cmds.getPanel(underPointer=True)]
    candidates.extend(cmds.getPanel(visiblePanels=True) or [])
    for panel in candidates:
        if panel and cmds.getPanel(typeOf=panel) == 'modelPanel':
            camera = cmds.modelPanel(panel, query=True, camera=True)
            if cmds.nodeType(camera) == 'camera':
                camera = (cmds.listRelatives(camera, parent=True, fullPath=True) or [camera])[0]
            return (cmds.ls(camera, long=True) or [camera])[0]
    return None


def shutdown(force=False):
    cmds.quit(force=force)


def _path(value):
    if not value:
        raise ValueError('A file path is required')
    return os.path.abspath(os.path.expandvars(os.path.expanduser(os.fspath(value))))


def _file_type(path):
    extension = os.path.splitext(path)[1].lower()
    if extension not in ('.ma', '.mb'):
        raise ValueError('Maya scene path must end in .ma or .mb')
    return 'mayaAscii' if extension == '.ma' else 'mayaBinary'


def _same_path(a, b):
    return bool(a and b and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b)))


def _clean_scene(force):
    if not force and cmds.file(query=True, modified=True):
        raise SceneModifiedError('The current scene has unsaved edits; save it before opening/newing a scene')


def _workspace(workspace):
    if workspace:
        workspace = _path(workspace)
        if not os.path.isdir(workspace):
            raise IOError('Workspace directory does not exist: ' + workspace)
        cmds.workspace(workspace, openWorkspace=True)


def open(path, workspace=None, force=False, ignore_version=False):
    path = _path(path)
    if not os.path.isfile(path):
        raise IOError('Maya scene does not exist: ' + path)
    _clean_scene(force)
    _workspace(workspace)
    cmds.file(path, open=True, force=force, ignoreVersion=ignore_version)
    return current_scene()


def new(context=None, workspace=None, force=False, up_axis=None):
    _clean_scene(force)
    if up_axis is not None and up_axis not in ('y', 'z'):
        raise ValueError('up_axis must be y or z')
    _workspace(workspace)
    cmds.file(newFile=True, force=force)
    if up_axis:
        cmds.upAxis(axis=up_axis, rotateView=True)
    if context is not None:
        init_scene(context)
    return current_scene()


def save(path=None, workspace=None, overwrite=False):
    """Save once to the requested file; never first save over the old version."""
    original = current_scene()
    destination = _path(path) if path else original
    if not destination:
        raise ValueError('The scene is unnamed; provide a .ma or .mb path')
    file_type = _file_type(destination)
    different = not _same_path(original, destination)
    if different and os.path.exists(destination) and not overwrite:
        raise FileExistsError('Destination scene already exists: ' + destination)
    if workspace and not os.path.isdir(_path(workspace)):
        raise IOError('Workspace directory does not exist: ' + str(workspace))
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    _workspace(workspace)
    modified = cmds.file(query=True, modified=True)
    try:
        if different:
            cmds.file(rename=destination)
        cmds.file(save=True, force=True, type=file_type)
    except Exception:
        if different:
            cmds.file(rename=original or 'untitled')
        cmds.file(modified=modified)
        raise
    return current_scene()


def copy_scene(path, overwrite=False):
    """Export a copy without saving or renaming the current working scene."""
    destination = _path(path)
    file_type = _file_type(destination)
    source = current_scene()
    if _same_path(source, destination):
        raise ValueError('Copy destination must differ from the current scene')
    pairs = []
    if source:
        src_base = os.path.splitext(source)[0]
        dst_base = os.path.splitext(destination)[0]
        palettes = cmds.ls(type='xgmPalette') or [] if 'xgmPalette' in (cmds.allNodeTypes() or []) else []
        for palette in palettes:
            src = '{}_{}.xgen'.format(src_base, palette)
            if os.path.isfile(src):
                pairs.append((src, '{}_{}.xgen'.format(dst_base, palette)))
    for target in [destination] + [target for _, target in pairs]:
        if os.path.exists(target) and not overwrite:
            raise FileExistsError('Copy destination already exists: ' + target)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    modified = cmds.file(query=True, modified=True)
    try:
        cmds.file(destination, exportAll=True, preserveReferences=True, type=file_type, force=overwrite)
        for src, dst in pairs:
            shutil.copy2(src, dst)
    finally:
        cmds.file(modified=modified)
    return destination


def create_reference(filePath, namespace):
    path = _path(filePath)
    if not os.path.isfile(path):
        raise IOError('Reference file does not exist: ' + path)
    if not namespace or not str(namespace).strip(':'):
        raise ValueError('A non-root reference namespace is required')
    return cmds.file(path, reference=True, namespace=namespace, loadReferenceDepth='all', mergeNamespacesOnClash=False)


def _context_data(context):
    data = context.to_dict() if hasattr(context, 'to_dict') else context
    if not isinstance(data, dict):
        raise TypeError('context must be a dictionary or Context')
    return data


def set_env(context):
    """Synchronize task environment data without modifying the scene/workspace."""
    data = _context_data(context)
    prefix = (os.environ.get('MSC_DCC_APP_CODE') or os.environ.get('DCC_APP_CODE') or 'MAYA').upper() + '_'
    values = {prefix + 'CONTEXT_JSON': json.dumps(data, ensure_ascii=False)}
    for entity in ['Project', 'Entity', 'Step', 'Task', 'User', 'Software']:
        item = data.get(entity) or {}
        if not isinstance(item, dict):
            raise TypeError(entity + ' context must be a dictionary')
        for key in ['id', 'code']:
            if key in item:
                values[prefix + entity.upper() + '_' + key.upper()] = str(item[key])
    user = data.get('User') or {}
    if 'code' in user:
        values[prefix + 'USER'] = str(user['code'])
    entity = data.get('Entity') or {}
    if 'type' in entity:
        values[prefix + 'ENTITY_TYPE'] = str(entity['type'])
    os.environ.update(values)
    return data


def init_scene(context, is_lock=False):
    data = _context_data(context)
    entity, step, task = (data.get(k) or {} for k in ['Entity', 'Step', 'Task'])
    if str(entity.get('type', '')).lower() != 'asset':
        return []
    step_code = str(step.get('code', '')).lower()
    if step_code == 'groom' or (step_code == 'afx' and str(task.get('code', '')).lower().endswith('groom')):
        paths = [['XGenTransfer', 'XGen_head', name] for name in ['XGen_hair', 'XGen_eyebrow', 'XGen_eyelash', 'XGen_whiskers']]
        paths += [['XGenTransfer', 'XGen_body', name] for name in ['XGen_torso', 'XGen_hand', 'XGen_foot', 'XGen_tail']]
        paths += [['bakeUvModel_grp', name] for name in ['head_XGenMesh_grp', 'body_XGenMesh_grp']]
    elif step_code in ('mod', 'model'):
        name = entity.get('code')
        _validate_name(name)
        if str(entity.get('asset_type', '')).lower() in ('chars', 'char', 'character', 'charactertype'):
            paths = [['model', name, group, name + '_Unfreeze'] for group in ['head_mesh_grp', 'body_mesh_grp', 'cloth_mesh_grp', 'style3D_mesh_grp']]
        else:
            paths = [['model', name, name + '_Unfreeze']]
        paths += [['model', name + '_Other_Grp', name + suffix] for suffix in ['_Vfx', '_Low']]
    else:
        return []
    return [make_group(path, is_lock=is_lock) for path in paths]


def _validate_name(name):
    if not isinstance(name, str) or not re.match(r'^[^\W\d]\w*$', name, re.UNICODE):
        raise ValueError('Invalid Maya group name: ' + str(name))


def make_group(nameList, children=None, is_lock=False):
    if not nameList:
        raise ValueError('Group hierarchy is empty')
    for name in nameList:
        _validate_name(name)
    created = []
    parent = ''
    for name in nameList:
        full_name = parent + '|' + name
        if not cmds.objExists(full_name):
            options = {'empty': True, 'name': name}
            if parent:
                options['parent'] = parent
            node = cmds.group(**options)
            created.append(node)
        parent = full_name
    if children:
        cmds.parent(children, parent)
    if is_lock:
        for node in reversed(created):
            cmds.lockNode(node, lock=True)
    return parent


__all__ = ['SceneModifiedError', 'current_version', 'version_matches', 'version_error', 'current_scene',
           'current_fps', 'current_camera', 'shutdown', 'open', 'new', 'save', 'copy_scene',
           'create_reference', 'set_env', 'init_scene', 'make_group']
