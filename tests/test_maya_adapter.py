# -*- coding: utf-8 -*-
"""Run only in a separate mayapy process with a temporary MAYA_APP_DIR."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import maya.standalone
maya.standalone.initialize(name='python')
import maya.cmds as cmds

SOURCE = Path(__file__).resolve().parents[1] / 'mix_maya/src/api.py'
spec = importlib.util.spec_from_file_location('_mix_adapter_test', str(SOURCE))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class MayaAdapterTests(unittest.TestCase):
    def setUp(self):
        cmds.file(newFile=True, force=True)
        self.temp = tempfile.TemporaryDirectory(prefix='mix-maya-adapter-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        cmds.file(newFile=True, force=True)
        assert self.root.parent.resolve() == Path(tempfile.gettempdir()).resolve()
        assert self.root.name.startswith('mix-maya-adapter-')
        self.temp.cleanup()

    def test_real_version_and_mismatch_never_quit_maya(self):
        self.assertEqual(api.current_version('latest'), '2024')
        self.assertTrue(api.version_matches('2024'))
        self.assertTrue(api.version_matches('latest'))
        self.assertFalse(api.version_matches('202'))
        self.assertFalse(api.version_matches('2023'))
        with patch.object(cmds, 'quit', side_effect=AssertionError('Must not quit')):
            with self.assertRaises(RuntimeError):
                api.version_error('2023')

    def test_save_as_does_not_write_the_previous_version(self):
        cmds.createNode('transform', name='firstNode')
        first = self.root / 'asset_V001.ma'
        second = self.root / 'asset_V002.ma'
        api.save(first)
        original = first.read_bytes()
        cmds.createNode('transform', name='secondNode')
        api.save(second)
        self.assertEqual(first.read_bytes(), original)
        self.assertIn('secondNode', second.read_text(encoding='utf-8'))
        self.assertEqual(os.path.normcase(api.current_scene()), os.path.normcase(str(second).replace('\\', '/')))

    def test_modified_scene_guards_open_and_new(self):
        source = self.root / 'source.ma'
        api.save(source)
        cmds.createNode('transform', name='unsavedNode')
        with self.assertRaises(api.SceneModifiedError):
            api.open(source)
        with self.assertRaises(api.SceneModifiedError):
            api.new()
        self.assertTrue(cmds.objExists('unsavedNode'))

    def test_missing_file_does_not_clear_the_scene(self):
        cmds.createNode('transform', name='keepNode')
        with self.assertRaises(IOError):
            api.open(self.root / 'missing.ma', force=True)
        self.assertTrue(cmds.objExists('keepNode'))

    def test_save_rejects_overwrite_and_unknown_extensions(self):
        api.save(self.root / 'source.ma')
        original = api.current_scene()
        destination = self.root / 'occupied.ma'
        destination.write_text('keep existing file', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            api.save(destination)
        with self.assertRaises(ValueError):
            api.save(self.root / 'wrong.txt')
        self.assertEqual(api.current_scene(), original)
        self.assertEqual(destination.read_text(), 'keep existing file')

    def test_save_failure_restores_the_original_name_and_dirty_state(self):
        api.save(self.root / 'source.ma')
        original = api.current_scene()
        cmds.createNode('transform', name='unsavedNode')
        real_file = cmds.file
        def fail_save(*args, **kwargs):
            if kwargs.get('save'):
                raise RuntimeError('Simulated disk failure')
            return real_file(*args, **kwargs)
        with patch.object(cmds, 'file', side_effect=fail_save):
            with self.assertRaisesRegex(RuntimeError, 'disk failure'):
                api.save(self.root / 'failed.ma')
        self.assertEqual(api.current_scene(), original)
        self.assertTrue(cmds.file(query=True, modified=True))
        self.assertTrue(cmds.objExists('unsavedNode'))

    def test_export_copy_keeps_current_file_and_unsaved_edits(self):
        api.save(self.root / 'working.ma')
        original = api.current_scene()
        original_bytes = Path(original).read_bytes()
        node = cmds.createNode('transform', name='copyNode')
        cmds.select(node)
        destination = self.root / 'copy.mb'
        api.copy_scene(destination)
        self.assertTrue(destination.exists())
        self.assertEqual(api.current_scene(), original)
        self.assertTrue(cmds.file(query=True, modified=True))
        self.assertEqual(Path(original).read_bytes(), original_bytes)
        self.assertEqual(cmds.ls(selection=True), [node])

    def test_current_mod_chars_context_and_idempotent_groups(self):
        ctx = {'Entity': {'code': 'Hero', 'type': 'Asset', 'asset_type': 'Chars'},
               'Step': {'code': 'Mod'}, 'Task': {'code': 'Mod'}}
        api.init_scene(ctx, is_lock=True)
        self.assertTrue(cmds.objExists('|model|Hero|head_mesh_grp|Hero_Unfreeze'))
        before = set(cmds.ls(long=True))
        api.init_scene(ctx, is_lock=True)
        self.assertEqual(set(cmds.ls(long=True)), before)

    def test_other_steps_do_not_create_model_hierarchies(self):
        for step in ['Art', 'Tex', 'Rig']:
            self.assertEqual(api.init_scene({'Entity': {'code': 'Hero', 'type': 'Asset'},
                                            'Step': {'code': step}}), [])
        self.assertFalse(cmds.objExists('|model'))

    def test_task_environment_changes_without_scene_changes(self):
        node = cmds.createNode('transform', name='keepNode')
        original = api.current_scene()
        ctx = {'Project': {'id': 'p', 'code': 'proj_test'}, 'Entity': {'id': 'asset', 'code': 'Hero', 'type': 'Asset'},
               'Step': {'id': 'step', 'code': 'Mod'}, 'Task': {'id': 'task2', 'code': 'Mod'},
               'User': {'id': 'u', 'code': 'artist'}}
        with patch.dict(os.environ, {'DCC_APP_CODE': 'MAYA'}):
            api.set_env(ctx)
            self.assertEqual(os.environ['MAYA_TASK_ID'], 'task2')
            self.assertEqual(json.loads(os.environ['MAYA_CONTEXT_JSON'])['Entity']['id'], 'asset')
        self.assertEqual(api.current_scene(), original)
        self.assertTrue(cmds.objExists(node))

    def test_native_reference_without_pymel(self):
        cmds.createNode('transform', name='referenceObject')
        source = self.root / 'reference.ma'
        api.save(source)
        api.new(force=True)
        api.create_reference(source, 'assetRef')
        self.assertTrue(cmds.objExists('assetRef:referenceObject'))

    def test_batch_camera_and_custom_frame_rate(self):
        self.assertIsNone(api.current_camera())
        cmds.currentUnit(time='23.976fps')
        self.assertAlmostEqual(api.current_fps(), 23.976)
        cmds.currentUnit(time='120fps')
        self.assertEqual(api.current_fps(), 120)


if __name__ == '__main__':
    unittest.main()
